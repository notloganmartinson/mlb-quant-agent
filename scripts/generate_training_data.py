import pandas as pd
import statsapi
from core.db_manager import MLBDbManager
from core import stats_calculator
from datetime import datetime, timedelta
import time
from concurrent.futures import ThreadPoolExecutor

def clean_stat(val):
    if isinstance(val, str):
        if val in ['.---', '-.--']: return 0.0
        try: return float(val)
        except: return 0.0
    return val if val is not None else 0.0

def fetch_team_logs(team_id, season, group='pitching'):
    try:
        data = statsapi.get('team_stats', {'teamId': team_id, 'stats': 'gameLog', 'group': group, 'season': season})
        splits = data.get('stats', [{}])[0].get('splits', [])
        logs = []
        for s in splits:
            stat = s.get('stat', {}).copy()
            logs.append({
                'team_id': int(team_id),
                'date': s.get('date'),
                'game_pk': s.get('game', {}).get('gamePk'),
                'isHome': s.get('isHome', False),
                'strikeOuts': int(stat.get('strikeOuts', 0)),
                'baseOnBalls': int(stat.get('baseOnBalls', 0)),
                'battersFaced': int(stat.get('battersFaced', 0)),
                'groundOuts': int(stat.get('groundOuts', 0)),
                'airOuts': int(stat.get('airOuts', 0)),
                'atBats': int(stat.get('atBats', 0)),
                'doubles': int(stat.get('doubles', 0)),
                'triples': int(stat.get('triples', 0)),
                'homeRuns': int(stat.get('homeRuns', 0)),
                'obp': clean_stat(stat.get('obp', 0.315)),
                'plateAppearances': int(stat.get('plateAppearances', 0))
            })
        return logs
    except: return []

def fetch_player_logs_chunked(player_ids, season):
    """Fetches gameLog stats for a chunk of player IDs."""
    try:
        id_str = ",".join(map(str, player_ids))
        data = statsapi.get('people', {'personIds': id_str, 'hydrate': f'stats(group=hitting,type=gameLog,season={season})'})
        
        all_logs = []
        for p in data.get('people', []):
            p_id = p.get('id')
            p_stats = p.get('stats', [])
            if not p_stats: continue
            
            splits = p_stats[0].get('splits', [])
            for s in splits:
                stat = s.get('stat', {}).copy()
                all_logs.append({
                    'player_id': p_id,
                    'date': s.get('date'),
                    'game_pk': s.get('game', {}).get('gamePk'),
                    'isHome': s.get('isHome', False),
                    'atBats': int(stat.get('atBats', 0)),
                    'doubles': int(stat.get('doubles', 0)),
                    'triples': int(stat.get('triples', 0)),
                    'homeRuns': int(stat.get('homeRuns', 0)),
                    'obp': clean_stat(stat.get('obp', 0.315)),
                    'plateAppearances': int(stat.get('plateAppearances', 0))
                })
        return all_logs
    except Exception as e:
        print(f"Error fetching player logs chunk: {e}")
        return []

def get_rolling_feature_map(season):
    manager = MLBDbManager()
    teams = manager.query_agent_data("SELECT mlb_id FROM team_mappings")
    team_ids = [int(t['mlb_id']) for t in teams]
    
    print(f"Fetching pitcher handedness for {season}...")
    players = statsapi.get('sports_players', {'sportId': 1, 'season': season})
    hand_map = {p['id']: p.get('pitchHand', {}).get('code', 'R') for p in players.get('people', []) if 'id' in p}
    
    print(f"Fetching full schedule for {season} to map starters...")
    games = statsapi.get('schedule', {'sportId': 1, 'startDate': f'{season}-03-01', 'endDate': f'{season}-11-15', 'hydrate': 'probablePitcher,lineups'})
    
    game_hand_map = {}
    game_lineup_map = {}
    for d in games.get('dates', []):
        for g in d.get('games', []):
            pk = g.get('gamePk')
            home_sp = g.get('teams', {}).get('home', {}).get('probablePitcher', {}).get('id')
            away_sp = g.get('teams', {}).get('away', {}).get('probablePitcher', {}).get('id')
            game_hand_map[pk] = {
                'home_sp_hand': hand_map.get(home_sp, 'R'), 
                'away_sp_hand': hand_map.get(away_sp, 'R')
            }
            # Extract starting 9 lineups
            home_lineup = [p['id'] for p in g.get('lineups', {}).get('homePlayers', [])[:9]]
            away_lineup = [p['id'] for p in g.get('lineups', {}).get('awayPlayers', [])[:9]]
            game_lineup_map[pk] = {'home': home_lineup, 'away': away_lineup}
    
    # 1. Team-Level Pitching Logs
    all_pitching = []
    print(f"Fetching team pitching logs for {len(team_ids)} teams...")
    for tid in team_ids:
        all_pitching.extend(fetch_team_logs(tid, season, 'pitching'))
        time.sleep(0.01)
    df_p = pd.DataFrame(all_pitching)

    # 2. Individual Player Hitting Logs
    print(f"Fetching individual hitter stats for {season}...")
    h_data = statsapi.get('stats', {'stats': 'season', 'group': 'hitting', 'season': season, 'playerPool': 'all', 'limit': 1500})
    hitter_ids = [s['player']['id'] for s in h_data['stats'][0]['splits']]
    
    all_hitting = []
    chunk_size = 50
    print(f"Fetching hitting logs for {len(hitter_ids)} players in chunks of {chunk_size}...")
    for i in range(0, len(hitter_ids), chunk_size):
        chunk = hitter_ids[i:i+chunk_size]
        all_hitting.extend(fetch_player_logs_chunked(chunk, season))
        print(f"  Processed {i+len(chunk)} / {len(hitter_ids)} players...")
        time.sleep(0.1)
    df_h = pd.DataFrame(all_hitting)
    
    if df_p.empty or df_h.empty: return {}, {}, {}

    def get_opp_hand(row):
        gmap = game_hand_map.get(row['game_pk'], {})
        if row.get('isHome'):
            return gmap.get('away_sp_hand', 'R')
        return gmap.get('home_sp_hand', 'R')
        
    df_h['opp_sp_hand'] = df_h.apply(get_opp_hand, axis=1)

    lookup = {}
    all_dates = pd.date_range(f"{season}-03-01", f"{season}-11-15").strftime('%Y-%m-%d')

    # Team Pitching Lookup
    for tid in team_ids:
        tp = df_p[df_p['team_id'] == tid].sort_values('date').drop_duplicates('date')
        if not tp.empty:
            p_cols = ['strikeOuts', 'baseOnBalls', 'battersFaced', 'groundOuts', 'airOuts']
            tp_roll = tp[p_cols].expanding().sum().shift(1).fillna(0)
            tp_roll['strikeOuts'] += 22
            tp_roll['baseOnBalls'] += 8
            tp_roll['battersFaced'] += 100
            tp_roll['groundOuts'] += 40
            tp_roll['airOuts'] += 30
            tp['siera'] = stats_calculator.calculate_siera(tp_roll['strikeOuts'], tp_roll['baseOnBalls'], tp_roll['battersFaced'], tp_roll['groundOuts'], tp_roll['airOuts'], 0)
            tp['k_bb'] = stats_calculator.calculate_k_minus_bb_percent(tp_roll['strikeOuts'], tp_roll['baseOnBalls'], tp_roll['battersFaced'])
            tp_filled = tp.set_index('date').reindex(all_dates).ffill().bfill()
            for d, row in tp_filled.iterrows():
                lookup[(tid, d, 'p')] = {'siera': float(row['siera']), 'k_bb': float(row['k_bb'])}

    # Individual Hitting Lookup (Dual-Rolling Matrix)
    print(f"Building individual split ledgers for {len(hitter_ids)} players...")
    for pid in hitter_ids:
        th = df_h[df_h['player_id'] == pid].sort_values('date').drop_duplicates('date')
        if not th.empty:
            for hand in ['L', 'R']:
                th_hand = th[th['opp_sp_hand'] == hand].copy()
                if th_hand.empty:
                    # Provide defaults (priors) if no split data exists yet
                    for d in all_dates:
                        lookup[(pid, d, 'h', hand)] = {'iso': 0.15, 'woba': 0.315, 'pa': 0.0}
                    continue
                
                h_cols = ['atBats', 'doubles', 'triples', 'homeRuns', 'plateAppearances']
                th_roll = th_hand[h_cols].expanding().sum().shift(1).fillna(0)
                
                # Bayesian Prior (League Average Padding)
                th_roll['atBats'] += 100
                th_roll['doubles'] += 5
                th_roll['triples'] += 1
                th_roll['homeRuns'] += 3
                th_roll['plateAppearances'] += 110
                
                th_hand['iso'] = stats_calculator.calculate_iso(th_roll['atBats'], th_roll['doubles'], th_roll['triples'], th_roll['homeRuns'])
                th_hand['woba'] = th_hand['obp'].expanding().mean().shift(1).fillna(0.315)
                # Track cumulative PA without the prior for the stability metric
                th_hand['pa_count'] = th_hand['plateAppearances'].expanding().sum().shift(1).fillna(0)
                
                th_hand_filled = th_hand.set_index('date').reindex(all_dates).ffill().bfill()
                for d, row in th_hand_filled.iterrows():
                    lookup[(pid, d, 'h', hand)] = {
                        'iso': float(row['iso']), 
                        'woba': float(row['woba']),
                        'pa': float(row['pa_count'])
                    }
                
    return lookup, game_hand_map, game_lineup_map

def generate_rolling_stats(season):
    manager = MLBDbManager()
    print(f"\n--- Starting Honest Ingestion for {season} ---")
    feature_map, game_hand_map, game_lineup_map = get_rolling_feature_map(season)
    if not feature_map:
        print(f"Failed to build feature map for {season}.")
        return
        
    months = [
        ("03-01", "03-31"), ("04-01", "04-30"), ("05-01", "05-31"), 
        ("06-01", "06-30"), ("07-01", "07-31"), ("08-01", "08-31"), 
        ("09-01", "09-30"), ("10-01", "11-15")
    ]
    
    print(f"Populating games for {season} in monthly chunks...")
    for start, end in months:
        try:
            games = statsapi.schedule(start_date=f"{season}-{start}", end_date=f"{season}-{end}")
            month_games = [g for g in games if g['status'] == 'Final']
            
            for g in month_games:
                date = g['game_date']
                game_pk = g['game_id']
                h_id, a_id = int(g['home_id']), int(g['away_id'])
                
                # Pitching (Team Proxy for now)
                h_p = feature_map.get((h_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                a_p = feature_map.get((a_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                
                # Opposing starter hand
                h_sp_hand = game_hand_map.get(game_pk, {}).get('home_sp_hand', 'R')
                a_sp_hand = game_hand_map.get(game_pk, {}).get('away_sp_hand', 'R')
                
                # Lineup Roll-Up (Individual Batters)
                lineups = game_lineup_map.get(game_pk, {'home': [], 'away': []})
                
                def get_lineup_metrics(p_ids, opp_hand):
                    isos, wobas, pas = [], [], []
                    for pid in p_ids:
                        m = feature_map.get((pid, date, 'h', opp_hand), {'iso': 0.15, 'woba': 0.315, 'pa': 0.0})
                        isos.append(m['iso'])
                        wobas.append(m['woba'])
                        pas.append(m['pa'])
                    
                    if not isos: return 0.15, 0.315, 0.0
                    return sum(isos)/len(isos), sum(wobas)/len(wobas), sum(pas)/len(pas)

                h_lineup_iso, h_lineup_woba, h_lineup_pa = get_lineup_metrics(lineups['home'], a_sp_hand)
                a_lineup_iso, a_lineup_woba, a_lineup_pa = get_lineup_metrics(lineups['away'], h_sp_hand)
                
                manager.upsert_historical_training_data({
                    "game_id": g['game_id'], "game_date": date, "home_team_id": h_id, "away_team_id": a_id,
                    "home_team_won": 1 if g['home_score'] > g['away_score'] else 0,
                    "home_team_runs": g['home_score'], "away_team_runs": g['away_score'],
                    "home_sp_siera": h_p['siera'], "away_sp_siera": a_p['siera'],
                    "home_sp_k_minus_bb": h_p['k_bb'], "away_sp_k_minus_bb": a_p['k_bb'],
                    "home_bullpen_siera": h_p['siera'], "away_bullpen_siera": a_p['siera'],
                    "home_lineup_iso_vs_pitcher_hand": h_lineup_iso, "away_lineup_iso_vs_pitcher_hand": a_lineup_iso,
                    "home_lineup_woba_vs_pitcher_hand": h_lineup_woba, "away_lineup_woba_vs_pitcher_hand": a_lineup_woba,
                    "home_lineup_pa": h_lineup_pa, "away_lineup_pa": a_lineup_pa,
                    "park_factor_runs": 1.0, "temperature": 70.0, "wind_speed": 5.0, "wind_direction": "Neutral",
                    "closing_home_moneyline": None, "closing_away_moneyline": None, "closing_total": None,
                    "home_sp_rolling_stuff": 100.0, "away_sp_rolling_stuff": 100.0
                })
            
            print(f"  Processed {season}-{start} to {end}. Sleeping 2s...")
            time.sleep(2)
        except Exception as e:
            print(f"  Error in range {start}-{end}: {e}")
            continue

    print(f"Season {season} Complete.")

if __name__ == "__main__":
    for s in [2023, 2024, 2025]:
        generate_rolling_stats(s)
