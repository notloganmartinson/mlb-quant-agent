import sqlite3
import pandas as pd
import statsapi
from concurrent.futures import ThreadPoolExecutor
from core.db_manager import MLBDbManager
from core.stats_calculator import calculate_rolling_stuff_plus

def patch_missing_stuff_plus():
    manager = MLBDbManager("data/mlb_betting.db")
    conn = manager._get_connection()
    
    missing_dates_df = pd.read_sql_query(
        "SELECT DISTINCT game_date FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL ORDER BY game_date",
        conn
    )
    missing_dates = missing_dates_df['game_date'].tolist()
    
    if not missing_dates:
        return

    updates = []
    
    print(f"Fetching API schedules for {len(missing_dates)} days (will take ~15 seconds)...")
    
    # We can parallelize the API calls to make it lighting fast
    import concurrent.futures
    def fetch_day(date):
        day_updates = []
        try:
            schedule = statsapi.get('schedule', {'sportId': 1, 'date': date, 'hydrate': 'lineups'})
            for date_item in schedule.get('dates', []):
                for game in date_item.get('games', []):
                    game_id = game['gamePk']
                    h_sp_id, a_sp_id = None, None
                    
                    lineups = game.get('lineups', {})
                    for p in lineups.get('homePlayers', []):
                        if p.get('position', {}).get('abbreviation') == 'P':
                            h_sp_id = p.get('id')
                            break
                    for p in lineups.get('awayPlayers', []):
                        if p.get('position', {}).get('abbreviation') == 'P':
                            a_sp_id = p.get('id')
                            break
                            
                    if h_sp_id and a_sp_id:
                        # Lazy evaluation of rolling stuff directly from SQLite
                        h_pitches = manager.get_pitcher_prior_pitches(int(h_sp_id), date)
                        a_pitches = manager.get_pitcher_prior_pitches(int(a_sp_id), date)
                        
                        h_roll = calculate_rolling_stuff_plus(h_pitches) if h_pitches else 100.0
                        a_roll = calculate_rolling_stuff_plus(a_pitches) if a_pitches else 100.0
                        
                        day_updates.append((h_roll, a_roll, game_id))
                    else:
                        day_updates.append((100.0, 100.0, game_id))
        except Exception as e:
            pass
        return day_updates

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_day, missing_dates))
        
    for r in results:
        updates.extend(r)

    print(f"Applying {len(updates)} updates to the database...")
    conn.executemany(
        "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
        updates
    )
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    patch_missing_stuff_plus()