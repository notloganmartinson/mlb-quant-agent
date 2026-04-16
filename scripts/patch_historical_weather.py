import sqlite3
import pandas as pd
import statsapi
import concurrent.futures
from core.db_manager import MLBDbManager

def parse_wind(wind_str):
    """Parses wind string like '5 mph, Out To CF' into (speed, direction)."""
    if not wind_str:
        return 5.0, "Neutral"
    try:
        parts = wind_str.split(',')
        speed_part = parts[0].strip().split(' ')[0]
        speed = float(speed_part)
        direction = parts[1].strip() if len(parts) > 1 else "Neutral"
        return speed, direction
    except:
        return 5.0, "Neutral"

def patch_weather():
    manager = MLBDbManager("data/mlb_betting.db")
    conn = manager._get_connection()
    
    print("Finding games that need weather patching...")
    # Find dates where we still have the hardcoded 70.0 default
    dates_df = pd.read_sql_query(
        "SELECT DISTINCT game_date FROM historical_training_data WHERE temperature = 70.0 ORDER BY game_date",
        conn
    )
    missing_dates = dates_df['game_date'].tolist()
    
    if not missing_dates:
        print("No games need weather patching.")
        return

    updates = []
    
    def fetch_day_weather(date):
        day_updates = []
        try:
            # Fetch schedule for the day with weather hydration
            sched = statsapi.get('schedule', {'sportId': 1, 'date': date, 'hydrate': 'weather'})
            for d_item in sched.get('dates', []):
                for g in d_item.get('games', []):
                    game_id = g['gamePk']
                    w = g.get('weather', {})
                    
                    # API returns temp as a string
                    temp_str = w.get('temp')
                    if temp_str:
                        temp = float(temp_str)
                        wind_str = w.get('wind')
                        speed, direction = parse_wind(wind_str)
                        
                        day_updates.append((temp, speed, direction, game_id))
        except Exception as e:
            print(f"Error fetching {date}: {e}")
        return day_updates

    print(f"Fetching historical weather for {len(missing_dates)} days using 10 workers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_day_weather, missing_dates))
        
    for r in results:
        updates.extend(r)

    print(f"Applying {len(updates)} weather updates to the database...")
    if updates:
        # Batch update the historical training table
        conn.executemany(
            "UPDATE historical_training_data SET temperature = ?, wind_speed = ?, wind_direction = ? WHERE game_id = ?",
            updates
        )
        conn.commit()
    
    conn.close()
    print("Weather patching complete!")

if __name__ == "__main__":
    patch_weather()
