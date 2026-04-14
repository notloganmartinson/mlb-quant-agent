import pandas as pd
import statsapi
from core.db_manager import MLBDbManager
from core import stats_calculator
from datetime import datetime, timedelta
import time

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

def get_rolling_feature_map(season):
    manager = MLBDbManager()
    teams = manager.query_agent_data("SELECT mlb_id FROM team_mappings")
    team_ids = [int(t['mlb_id']) for t in teams]
    
    all_pitching = []
    all_hitting = []
    
    print(f"Fetching logs for {len(team_ids)} teams in {season}...")
    for tid in team_ids:
        all_pitching.extend(fetch_team_logs(tid, season, 'pitching'))
        all_hitting.extend(fetch_team_logs(tid, season, 'hitting'))
        time.sleep(0.01)

    df_p = pd.DataFrame(all_pitching)
    df_h = pd.DataFrame(all_hitting)
    
    if df_p.empty or df_h.empty: return {}

    lookup = {}
    all_dates = pd.date_range(f"{season}-03-01", f"{season}-11-15").strftime('%Y-%m-%d')

    for tid in team_ids:
        # PITCHING
        tp = df_p[df_p['team_id'] == tid].sort_values('date').drop_duplicates('date')
        if not tp.empty:
            p_cols = ['strikeOuts', 'baseOnBalls', 'battersFaced', 'groundOuts', 'airOuts']
            tp_roll = tp[p_cols].expanding().sum().shift(1).fillna(0)
            
            # Prior
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

        # HITTING
        th = df_h[df_h['team_id'] == tid].sort_values('date').drop_duplicates('date')
        if not th.empty:
            h_cols = ['atBats', 'doubles', 'triples', 'homeRuns', 'plateAppearances']
            th_roll = th[h_cols].expanding().sum().shift(1).fillna(0)
            
            th_roll['atBats'] += 100
            th_roll['doubles'] += 5
            th_roll['triples'] += 1
            th_roll['homeRuns'] += 3
            th_roll['plateAppearances'] += 110
            
            th['iso'] = stats_calculator.calculate_iso(th_roll['atBats'], th_roll['doubles'], th_roll['triples'], th_roll['homeRuns'])
            th['woba'] = th['obp'].expanding().mean().shift(1).fillna(0.315)
            
            th_filled = th.set_index('date').reindex(all_dates).ffill().bfill()
            for d, row in th_filled.iterrows():
                lookup[(tid, d, 'h')] = {'iso': float(row['iso']), 'woba': float(row['woba'])}
                
    return lookup

def generate_rolling_stats(season):
    manager = MLBDbManager()
    print(f"\n--- Starting Honest Ingestion for {season} ---")
    feature_map = get_rolling_feature_map(season)
    
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
                h_id, a_id = int(g['home_id']), int(g['away_id'])
                
                h_p = feature_map.get((h_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                a_p = feature_map.get((a_id, date, 'p'), {'siera': 4.2, 'k_bb': 0.14})
                h_h = feature_map.get((h_id, date, 'h'), {'iso': 0.15, 'woba': 0.315})
                a_h = feature_map.get((a_id, date, 'h'), {'iso': 0.15, 'woba': 0.315})
                
                manager.upsert_historical_training_data({
                    "game_id": g['game_id'], "game_date": date, "home_team_id": h_id, "away_team_id": a_id,
                    "home_team_won": 1 if g['home_score'] > g['away_score'] else 0,
                    "home_sp_siera": h_p['siera'], "away_sp_siera": a_p['siera'],
                    "home_sp_k_minus_bb": h_p['k_bb'], "away_sp_k_minus_bb": a_p['k_bb'],
                    "home_bullpen_siera": h_p['siera'], "away_bullpen_siera": a_p['siera'],
                    "home_lineup_iso_vs_pitcher_hand": h_h['iso'], "away_lineup_iso_vs_pitcher_hand": a_h['iso'],
                    "home_lineup_woba_vs_pitcher_hand": h_h['woba'], "away_lineup_woba_vs_pitcher_hand": a_h['woba'],
                    "park_factor_runs": 1.0, "temperature": 70.0, "wind_speed": 5.0, "wind_direction": "Neutral",
                    "closing_home_moneyline": None, "closing_away_moneyline": None, "closing_total": None
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
