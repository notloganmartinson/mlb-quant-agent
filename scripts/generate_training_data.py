import pandas as pd
import statsapi
from core.db_manager import MLBDbManager
from core import stats_calculator
from datetime import datetime, timedelta
import time
import os
import numpy as np

def clean_stat(val):
    if isinstance(val, str):
        if val in ['.---', '-.--']: return 0.0
        try: return float(val)
        except: return 0.0
    return val if val is not None else 0.0

def fetch_player_logs_chunked(player_ids, season, group='hitting'):
    """Fetches gameLog stats for a chunk of player IDs."""
    try:
        id_str = ",".join(map(str, player_ids))
        data = statsapi.get('people', {'personIds': id_str, 'hydrate': f'stats(group={group},type=gameLog,season={season})'})
        
        all_logs = []
        for p in data.get('people', []):
            p_id = p.get('id')
            p_stats = p.get('stats', [])
            if not p_stats: continue
            
            splits = p_stats[0].get('splits', [])
            for s in splits:
                stat = s.get('stat', {}).copy()
                log_entry = {
                    'player_id': p_id,
                    'date': s.get('date'),
                    'game_pk': s.get('game', {}).get('gamePk'),
                    'isHome': s.get('isHome', False)
                }
                
                if group == 'hitting':
                    log_entry.update({
                        'team_id': int(s.get('team', {}).get('id', 0)),
                        'atBats': int(stat.get('atBats', 0)),
                        'doubles': int(stat.get('doubles', 0)),
                        'triples': int(stat.get('triples', 0)),
                        'homeRuns': int(stat.get('homeRuns', 0)),
                        'strikeOuts': int(stat.get('strikeOuts', 0)),
                        'obp': clean_stat(stat.get('obp', 0.315)),
                        'plateAppearances': int(stat.get('plateAppearances', 0))
                    })
                else: # pitching
                    log_entry.update({
                        'team_id': int(s.get('team', {}).get('id', 0)),
                        'gamesStarted': int(stat.get('gamesStarted', 0)),
                        'strikeOuts': int(stat.get('strikeOuts', 0)),
                        'baseOnBalls': int(stat.get('baseOnBalls', 0)),
                        'battersFaced': int(stat.get('battersFaced', 0)),
                        'groundOuts': int(stat.get('groundOuts', 0)),
                        'airOuts': int(stat.get('airOuts', 0))
                    })
                all_logs.append(log_entry)
        return all_logs
    except Exception as e:
        print(f"Error fetching {group} logs chunk: {e}")
        return []

def get_rolling_feature_map(season):
    manager = MLBDbManager()
    
    print(f"Fetching full schedule for {season}...")
    games_data = statsapi.get('schedule', {'sportId': 1, 'startDate': f'{season}-03-01', 'endDate': f'{season}-11-15', 'hydrate': 'probablePitcher,lineups'})
    
    game_meta_map = {}
    pitcher_ids = set()
    hitter_ids = set()
    
    for d in games_data.get('dates', []):
        for g in d.get('games', []):
            pk = g.get('gamePk')
            h_sp_id = g.get('teams', {}).get('home', {}).get('probablePitcher', {}).get('id')
            a_sp_id = g.get('teams', {}).get('away', {}).get('probablePitcher', {}).get('id')
            if h_sp_id: pitcher_ids.add(h_sp_id)
            if a_sp_id: pitcher_ids.add(a_sp_id)
            
            h_lineup = [p['id'] for p in g.get('lineups', {}).get('homePlayers', [])[:9]]
            a_lineup = [p['id'] for p in g.get('lineups', {}).get('awayPlayers', [])[:9]]
            for p in h_lineup + a_lineup: hitter_ids.add(p)
            
            game_meta_map[pk] = {'home_sp_id': h_sp_id, 'away_sp_id': a_sp_id, 'home_lineup': h_lineup, 'away_lineup': a_lineup}

    print(f"Fetching pitcher handedness...")
    players_resp = statsapi.get('sports_players', {'sportId': 1, 'season': season})
    hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in players_resp.get('people', []) if 'id' in p}
    for pk in game_meta_map:
        game_meta_map[pk]['home_sp_hand'] = hand_map.get(game_meta_map[pk]['home_sp_id'], 'R')
        game_meta_map[pk]['away_sp_hand'] = hand_map.get(game_meta_map[pk]['away_sp_id'], 'R')

    chunk_size = 50
    print(f"Fetching logs for {len(pitcher_ids)} pitchers and {len(hitter_ids)} hitters...")
    
    all_pitching = []
    p_list = list(pitcher_ids)
    for i in range(0, len(p_list), chunk_size):
        all_pitching.extend(fetch_player_logs_chunked(p_list[i:i+chunk_size], season, 'pitching'))
        time.sleep(0.05)
    df_p = pd.DataFrame(all_pitching)

    all_hitting = []
    h_list = list(hitter_ids)
    for i in range(0, len(h_list), chunk_size):
        all_hitting.extend(fetch_player_logs_chunked(h_list[i:i+chunk_size], season, 'hitting'))
        time.sleep(0.05)
    df_h = pd.DataFrame(all_hitting)
    
    if df_p.empty or df_h.empty: return {}, game_meta_map, {}

    # Add opponent hand to hitter logs
    df_h['opp_sp_hand'] = df_h['game_pk'].map(lambda x: game_meta_map.get(x, {}).get('away_sp_hand' if df_h[df_h['game_pk']==x]['isHome'].iloc[0] else 'home_sp_hand', 'R'))

    lookup = {}
    all_dates = pd.date_range(f"{season}-03-01", f"{season}-11-15").strftime('%Y-%m-%d')

    # 1. Vectorized Pitcher Stats (Starters)
    print("Vectorizing starter rolling stats...")
    df_p = df_p.sort_values(['player_id', 'date']).drop_duplicates(['player_id', 'date'])
    p_cols = ['strikeOuts', 'baseOnBalls', 'battersFaced', 'groundOuts', 'airOuts']
    
    # Cumulative sums shifted by 1 game to avoid look-ahead bias
    p_roll = df_p.groupby('player_id')[p_cols].cumsum().groupby(df_p['player_id']).shift(1).fillna(0)
    p_roll['strikeOuts'] += 20; p_roll['baseOnBalls'] += 8; p_roll['battersFaced'] += 100; p_roll['groundOuts'] += 40; p_roll['airOuts'] += 30
    
    df_p['siera'] = stats_calculator.calculate_siera(p_roll['strikeOuts'], p_roll['baseOnBalls'], p_roll['battersFaced'], p_roll['groundOuts'], p_roll['airOuts'], 0)
    df_p['k_bb'] = stats_calculator.calculate_k_minus_bb_percent(p_roll['strikeOuts'], p_roll['baseOnBalls'], p_roll['battersFaced'])
    
    # Starter Lookup Pivot
    p_pivot = df_p.pivot(index='date', columns='player_id', values=['siera', 'k_bb']).reindex(all_dates).ffill().fillna({'siera': 4.20, 'k_bb': 0.14})
    
    # 2. Bullpen Stats (Top 5 Relievers per Team)
    print("Vectorizing bullpen rolling stats...")
    df_rp = df_p[df_p['gamesStarted'] == 0].copy()
    # Rolling sums for relievers (using their cumulative stats up to the date)
    rp_roll = df_rp.groupby(['team_id', 'player_id'])[p_cols].cumsum().groupby([df_rp['team_id'], df_rp['player_id']]).shift(1).fillna(0)
    df_rp['bf_rank'] = rp_roll['battersFaced']
    
    bullpen_lookup = {}
    team_ids = set(df_p['team_id'].unique())
    
    for d in all_dates:
        # Get latest cumulative stats for each reliever on this team up to date d
        day_rp = df_rp[df_rp['date'] < d]
        if day_rp.empty:
            for tid in team_ids: bullpen_lookup[(tid, d)] = {'siera': 4.2, 'k_bb': 0.14}
            continue
            
        latest_rp = day_rp.sort_values('date').groupby(['team_id', 'player_id']).last().reset_index()
        for tid in team_ids:
            team_rp = latest_rp[latest_rp['team_id'] == tid].sort_values('bf_rank', ascending=False).head(5)
            if team_rp.empty:
                bullpen_lookup[(tid, d)] = {'siera': 4.2, 'k_bb': 0.14}
            else:
                bullpen_lookup[(tid, d)] = {'siera': team_rp['siera'].mean(), 'k_bb': team_rp['k_bb'].mean()}

    # 3. Vectorized Hitter Stats
    print("Vectorizing hitter split rolling stats...")
    df_h = df_h.sort_values(['player_id', 'opp_sp_hand', 'date']).drop_duplicates(['player_id', 'opp_sp_hand', 'date'])
    h_cols = ['atBats', 'doubles', 'triples', 'homeRuns', 'plateAppearances', 'strikeOuts']
    
    h_roll = df_h.groupby(['player_id', 'opp_sp_hand'])[h_cols].cumsum().groupby([df_h['player_id'], df_h['opp_sp_hand']]).shift(1).fillna(0)
    h_roll['atBats'] += 100; h_roll['plateAppearances'] += 110; h_roll['strikeOuts'] += 24
    
    df_h['iso'] = stats_calculator.calculate_iso(h_roll['atBats'], h_roll['doubles'] + 5, h_roll['triples'] + 1, h_roll['homeRuns'] + 3)
    df_h['woba'] = df_h.groupby(['player_id', 'opp_sp_hand'])['obp'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0.315)
    df_h['k_pct'] = h_roll['strikeOuts'] / h_roll['plateAppearances']
    df_h['pa_count'] = h_roll['plateAppearances'] - 110
    
    print("Populating lookup dictionary...")
    for d in all_dates:
        day_p = p_pivot.loc[d]
        for pid in pitcher_ids:
            if ('siera', pid) in day_p:
                lookup[(pid, d, 'p')] = {'siera': day_p[('siera', pid)], 'k_bb': day_p[('k_bb', pid)]}
            else:
                lookup[(pid, d, 'p')] = {'siera': 4.20, 'k_bb': 0.14}

    print("Building hitter lookup matrix...")
    for hand in ['L', 'R']:
        h_split = df_h[df_h['opp_sp_hand'] == hand]
        if h_split.empty:
            for d in all_dates:
                for pid in hitter_ids: lookup[(pid, d, 'h', hand)] = {'iso': 0.15, 'woba': 0.315, 'k_pct': 0.22, 'pa': 0.0}
            continue

        h_pivot = h_split.pivot(index='date', columns='player_id', values=['iso', 'woba', 'k_pct', 'pa_count']).reindex(all_dates).ffill().fillna({'iso': 0.15, 'woba': 0.315, 'k_pct': 0.22, 'pa_count': 0.0})
        for d in all_dates:
            day_h = h_pivot.loc[d]
            for pid in hitter_ids:
                if ('iso', pid) in day_h:
                    lookup[(pid, d, 'h', hand)] = {'iso': day_h[('iso', pid)], 'woba': day_h[('woba', pid)], 'k_pct': day_h[('k_pct', pid)], 'pa': day_h[('pa_count', pid)]}
                else:
                    lookup[(pid, d, 'h', hand)] = {'iso': 0.15, 'woba': 0.315, 'k_pct': 0.22, 'pa': 0.0}

    return lookup, game_meta_map, bullpen_lookup

def generate_rolling_stats(season):
    manager = MLBDbManager()
    print(f"\n--- Starting Optimized Ingestion for {season} ---")
    feature_map, game_meta_map, bullpen_map = get_rolling_feature_map(season)
    
    months = [("03-01", "03-31"), ("04-01", "04-30"), ("05-01", "05-31"), ("06-01", "06-30"), ("07-01", "07-31"), ("08-01", "08-31"), ("09-01", "09-30"), ("10-01", "11-15")]
    
    for start, end in months:
        try:
            games = statsapi.schedule(start_date=f"{season}-{start}", end_date=f"{season}-{end}")
            month_games = [g for g in games if g['status'] == 'Final']
            
            for g in month_games:
                date = g['game_date']
                game_pk = g['game_id']
                h_id, a_id = int(g['home_id']), int(g['away_id'])
                meta = game_meta_map.get(game_pk, {})
                h_sp_id, a_sp_id = meta.get('home_sp_id'), meta.get('away_sp_id')
                
                h_p_feat = feature_map.get((h_sp_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                a_p_feat = feature_map.get((a_sp_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                
                h_bp_feat = bullpen_map.get((h_id, date), {'siera': 4.2, 'k_bb': 0.14})
                a_bp_feat = bullpen_map.get((a_id, date), {'siera': 4.2, 'k_bb': 0.14})

                h_roll_stuff = 100.0
                if h_sp_id:
                    pitches = manager.get_pitcher_prior_pitches(h_sp_id, date)
                    if pitches: h_roll_stuff = stats_calculator.calculate_rolling_stuff_plus(pitches)

                a_roll_stuff = 100.0
                if a_sp_id:
                    pitches = manager.get_pitcher_prior_pitches(a_sp_id, date)
                    if pitches: a_roll_stuff = stats_calculator.calculate_rolling_stuff_plus(pitches)
                
                def get_lineup_metrics(p_ids, opp_hand):
                    isos, wobas, pas, k_pcts = [], [], [], []
                    for pid in p_ids:
                        m = feature_map.get((pid, date, 'h', opp_hand), {'iso': 0.15, 'woba': 0.315, 'k_pct': 0.22, 'pa': 0.0})
                        isos.append(m['iso']); wobas.append(m['woba']); pas.append(m['pa']); k_pcts.append(m['k_pct'])
                    if not isos: return 0.15, 0.315, 0.0, 0.22
                    return sum(isos)/len(isos), sum(wobas)/len(wobas), sum(pas)/len(pas), sum(k_pcts)/len(k_pcts)

                h_lineup_iso, h_lineup_woba, h_lineup_pa, h_lineup_k = get_lineup_metrics(meta.get('home_lineup', []), meta.get('away_sp_hand', 'R'))
                a_lineup_iso, a_lineup_woba, a_lineup_pa, a_lineup_k = get_lineup_metrics(meta.get('away_lineup', []), meta.get('home_sp_hand', 'R'))
                
                h_sp_k, a_sp_k = 0, 0
                try:
                    box = statsapi.boxscore_data(game_pk)
                    for p in box.get('homePitchers', []):
                        if p.get('personId') == h_sp_id: h_sp_k = int(p.get('k', 0))
                    for p in box.get('awayPitchers', []):
                        if p.get('personId') == a_sp_id: a_sp_k = int(p.get('k', 0))
                except: pass

                manager.upsert_historical_training_data({
                    "game_id": game_pk, "game_date": date, "home_team_id": h_id, "away_team_id": a_id,
                    "home_team_won": 1 if g['home_score'] > g['away_score'] else 0,
                    "home_team_runs": g['home_score'], "away_team_runs": g['away_score'],
                    "home_sp_siera": h_p_feat['siera'], "away_sp_siera": a_p_feat['siera'],
                    "home_sp_k_minus_bb": h_p_feat['k_bb'], "away_sp_k_minus_bb": a_p_feat['k_bb'],
                    "home_bullpen_siera": h_bp_feat['siera'], "away_bullpen_siera": a_bp_feat['siera'],
                    "home_bullpen_k_bb": h_bp_feat['k_bb'], "away_bullpen_k_bb": a_bp_feat['k_bb'],
                    "home_lineup_iso_vs_pitcher_hand": h_lineup_iso, "away_lineup_iso_vs_pitcher_hand": a_lineup_iso,
                    "home_lineup_woba_vs_pitcher_hand": h_lineup_woba, "away_lineup_woba_vs_pitcher_hand": a_lineup_woba,
                    "home_lineup_pa": h_lineup_pa, "away_lineup_pa": a_lineup_pa,
                    "home_lineup_k_pct": h_lineup_k, "away_lineup_k_pct": a_lineup_k,
                    "home_sp_strikeouts": h_sp_k, "away_sp_strikeouts": a_sp_k,
                    "home_sp_rolling_stuff": h_roll_stuff, "away_sp_rolling_stuff": a_roll_stuff,
                    "park_factor_runs": 1.0, "temperature": 70.0, "wind_speed": 5.0, "wind_direction": "Neutral",
                    "closing_home_moneyline": None, "closing_away_moneyline": None, "closing_total": None
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"Error in {season} {start}: {e}")

if __name__ == "__main__":
    for s in [2022, 2023, 2024, 2025]:
        generate_rolling_stats(s)
