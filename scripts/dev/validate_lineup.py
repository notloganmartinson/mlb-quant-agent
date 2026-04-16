import statsapi
import pandas as pd
from core import stats_calculator

def get_iso_upto(player_id, date, season):
    data = statsapi.get('people', {'personIds': str(player_id), 'hydrate': f'stats(group=hitting,type=gameLog,season={season})'})
    if not data.get('people'): return 0.160
    splits = data['people'][0].get('stats', [{}])[0].get('splits', [])
    
    logs = []
    for s in splits:
        if s['date'] < date:
            st = s['stat']
            logs.append({'ab': int(st.get('atBats', 0)), 'doubles': int(st.get('doubles', 0)), 'triples': int(st.get('triples', 0)), 'hr': int(st.get('homeRuns', 0))})
    
    df = pd.DataFrame(logs)
    if df.empty: return 0.160
    totals = df.sum()
    return stats_calculator.calculate_iso(totals['ab'] + 100, totals['doubles'] + 5, totals['triples'] + 1, totals['hr'] + 3)

def validate():
    dates = ['2024-09-26', '2024-09-27'] # Yankees vs Orioles (26), Yankees vs Pirates (27)
    yankees_id = 147
    
    for date in dates:
        sched = statsapi.get('schedule', {'sportId': 1, 'date': date, 'hydrate': 'lineups'})
        game = next(g for g in sched['dates'][0]['games'] if g['teams']['home']['team']['id'] == yankees_id or g['teams']['away']['team']['id'] == yankees_id)
        
        is_home = game['teams']['home']['team']['id'] == yankees_id
        side = 'home' if is_home else 'away'
        lineup = game['lineups'][f'{side}Players'][:9]
        
        names = [p['fullName'] for p in lineup]
        isos = [get_iso_upto(p['id'], date, 2024) for p in lineup]
        avg_iso = sum(isos) / len(isos)
        
        print(f"\n--- Yankees on {date} ---")
        print(f"Opponent: {game['teams']['away' if is_home else 'home']['team']['name']}")
        print(f"Aaron Judge Start: {592450 in [p['id'] for p in lineup]}")
        print(f"Lineup: {names}")
        print(f"Aggregate Lineup ISO: {avg_iso:.4f}")

validate()
