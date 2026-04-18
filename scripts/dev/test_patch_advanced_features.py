import sys
import os
sys.path.append(os.getcwd())

from scripts.patch_advanced_k_features import calculate_park_k_factor
from core.db_manager import MLBDbManager
import statsapi

def test_run():
    manager = MLBDbManager()
    query = "SELECT game_id, game_date, home_team_id, away_team_id FROM historical_training_data ORDER BY game_date ASC LIMIT 2"
    games = manager.query_agent_data(query)
    
    team_history = {}
    
    for g in games:
        game_pk = g['game_id']
        h_id = g['home_team_id']
        park_factor = calculate_park_k_factor(h_id, team_history)
        print(f"Game {game_pk} ({g['game_date']}) - Park Factor (Prior): {park_factor}")
        
        box = statsapi.get('game_boxscore', {'gamePk': game_pk})
        umpire_id = None
        for o in box.get('officials', []):
            if o.get('officialType') == 'Home Plate':
                umpire_id = o.get('official', {}).get('id')
                name = o.get('official', {}).get('fullName')
                print(f"  Home Plate Umpire ID: {umpire_id} ({name})")
                break
        
        if not umpire_id:
            print("  No Home Plate umpire found.")
            
        # Test stats extraction
        h_k = sum([int(p.get('stats', {}).get('pitching', {}).get('strikeOuts', 0)) for p in box.get('teams', {}).get('home', {}).get('players', {}).values()])
        h_pa = sum([int(p.get('stats', {}).get('pitching', {}).get('battersFaced', 0)) for p in box.get('teams', {}).get('home', {}).get('players', {}).values()])
        print(f"  Home Team Ks: {h_k}, PAs: {h_pa}")
        
        a_k = sum([int(p.get('stats', {}).get('pitching', {}).get('strikeOuts', 0)) for p in box.get('teams', {}).get('away', {}).get('players', {}).values()])
        a_pa = sum([int(p.get('stats', {}).get('pitching', {}).get('battersFaced', 0)) for p in box.get('teams', {}).get('away', {}).get('players', {}).values()])
        print(f"  Away Team Ks: {a_k}, PAs: {a_pa}")
        print("-" * 40)

if __name__ == '__main__':
    test_run()
