import sqlite3
import pandas as pd
import statsapi
import time
from core.db_manager import MLBDbManager

def calculate_park_k_factor(team_id, team_history):
    """
    Calculates a 1-year rolling Park K-Factor (Fangraphs method).
    Factor = (Home K% / Away K%) * 100.
    Defaults to 100 (Neutral) if insufficient data.
    """
    stats = team_history.get(team_id, {'home_k': 500, 'home_pa': 2200, 'away_k': 500, 'away_pa': 2200})
    
    if stats['home_pa'] < 1000 or stats['away_pa'] < 1000:
        return 100.0 # Neutral prior
        
    home_k_pct = stats['home_k'] / stats['home_pa']
    away_k_pct = stats['away_k'] / stats['away_pa']
    
    if away_k_pct == 0:
        return 100.0
        
    factor = (home_k_pct / away_k_pct) * 100
    # Cap absurd values due to small sample size noise
    return max(85.0, min(factor, 115.0))

def run_patch():
    manager = MLBDbManager()
    
    # Query ALL games to build the pure, lookahead-free rolling memory
    query = """
    SELECT game_id, game_date, home_team_id, away_team_id, umpire_k_pct, park_factor_k
    FROM historical_training_data
    ORDER BY game_date ASC, game_id ASC
    """
    games = manager.query_agent_data(query)
    print(f"Loaded {len(games)} games for advanced feature generation.")
    
    # Bayesian Priors
    umpire_history = {} # ID -> {'k': 220, 'pa': 1000} (league avg 22%)
    team_history = {} # ID -> {'home_k': 0, 'home_pa': 0, 'away_k': 0, 'away_pa': 0}
    
    updated_count = 0
    total_missing = sum(1 for g in games if g['umpire_k_pct'] is None)
    print(f"Total missing advanced features: {total_missing} games.")
    
    if total_missing == 0:
        print("Database is fully patched.")
        return

    for idx, g in enumerate(games):
        game_pk = g['game_id']
        h_id = g['home_team_id']
        a_id = g['away_team_id']
        
        needs_patch = g['umpire_k_pct'] is None
        
        # 1. Generate Point-in-Time Features BEFORE the game happens
        park_factor = calculate_park_k_factor(h_id, team_history)
        
        umpire_id = None
        ump_k_pct = 0.220 # Default
        
        try:
            # We must fetch boxscore to find the umpire and the game results
            box = statsapi.get('game_boxscore', {'gamePk': game_pk})
            officials = box.get('officials', [])
            for o in officials:
                if o.get('officialType') == 'Home Plate':
                    umpire_id = o.get('official', {}).get('id')
                    break
                    
            if umpire_id:
                u_stats = umpire_history.get(umpire_id, {'k': 220, 'pa': 1000})
                ump_k_pct = u_stats['k'] / u_stats['pa']
                
            # Execute Patch if missing
            if needs_patch:
                sql = "UPDATE historical_training_data SET umpire_k_pct = ?, park_factor_k = ? WHERE game_id = ?"
                with manager._get_connection() as conn:
                    conn.execute(sql, (ump_k_pct, park_factor, game_pk))
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"  [{updated_count}/{total_missing}] Patched up to {g['game_date']}")
            
            # 2. Extract Game Results to update dictionaries AFTER the game
            # This ensures Strict Forward-Only flow (no lookahead bias)
            h_k = sum([int(p.get('stats', {}).get('pitching', {}).get('strikeOuts', 0)) for p in box.get('teams', {}).get('home', {}).get('players', {}).values()])
            h_pa = sum([int(p.get('stats', {}).get('pitching', {}).get('battersFaced', 0)) for p in box.get('teams', {}).get('home', {}).get('players', {}).values()])
            
            a_k = sum([int(p.get('stats', {}).get('pitching', {}).get('strikeOuts', 0)) for p in box.get('teams', {}).get('away', {}).get('players', {}).values()])
            a_pa = sum([int(p.get('stats', {}).get('pitching', {}).get('battersFaced', 0)) for p in box.get('teams', {}).get('away', {}).get('players', {}).values()])
            
            # Update Umpire History
            if umpire_id:
                if umpire_id not in umpire_history:
                    umpire_history[umpire_id] = {'k': 220, 'pa': 1000}
                umpire_history[umpire_id]['k'] += (h_k + a_k)
                umpire_history[umpire_id]['pa'] += (h_pa + a_pa)
                
            # Update Team History
            if h_id not in team_history: team_history[h_id] = {'home_k': 500, 'home_pa': 2200, 'away_k': 500, 'away_pa': 2200}
            if a_id not in team_history: team_history[a_id] = {'home_k': 500, 'home_pa': 2200, 'away_k': 500, 'away_pa': 2200}
            
            team_history[h_id]['home_k'] += h_k
            team_history[h_id]['home_pa'] += h_pa
            
            team_history[a_id]['away_k'] += a_k
            team_history[a_id]['away_pa'] += a_pa
            
            time.sleep(0.05) # Rate limit safety
            
        except Exception as e:
            print(f"Error processing {game_pk}: {e}")
            time.sleep(1)

    print(f"Finished patching. Total updated: {updated_count}")

if __name__ == "__main__":
    run_patch()
