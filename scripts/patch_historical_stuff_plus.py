import sqlite3
import pandas as pd
import statsapi
import concurrent.futures
import threading
from core.db_manager import MLBDbManager
from core.stats_calculator import calculate_rolling_stuff_plus

def patch_missing_stuff_plus():
    manager = MLBDbManager("data/mlb_betting.db")
    conn = manager._get_connection()
    
    print("Finding missing stuff dates...")
    missing_dates_df = pd.read_sql_query(
        "SELECT DISTINCT game_date FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL ORDER BY game_date",
        conn
    )
    missing_dates = missing_dates_df['game_date'].tolist()
    
    if not missing_dates:
        print("No missing stuff dates found.")
        return

    updates = []
    lock = threading.Lock()
    completed_count = 0

    def fetch_day(date):
        day_updates = []
        try:
            # Use probablePitcher hydration to get the historical starters
            schedule = statsapi.get('schedule', {'sportId': 1, 'date': date, 'hydrate': 'probablePitcher'})
            for date_item in schedule.get('dates', []):
                for game in date_item.get('games', []):
                    game_id = game['gamePk']
                    
                    h_sp_id = game.get('teams', {}).get('home', {}).get('probablePitcher', {}).get('id')
                    a_sp_id = game.get('teams', {}).get('away', {}).get('probablePitcher', {}).get('id')
                            
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
            print(f"Error patching {date}: {e}")
        
        nonlocal completed_count
        with lock:
            completed_count += 1
            if completed_count % 50 == 0:
                print(f"  Progress: {completed_count}/{len(missing_dates)} days fetched...")
        return day_updates

    print(f"Fetching API schedules for {len(missing_dates)} days using 10 workers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_day, missing_dates))
        
    for r in results:
        updates.extend(r)

    print(f"Applying {len(updates)} updates to the database...")
    if updates:
        conn.executemany(
            "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
            updates
        )
        conn.commit()
    
    conn.close()
    print("Done!")

if __name__ == "__main__":
    patch_missing_stuff_plus()
