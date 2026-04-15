import sqlite3
import pandas as pd
import statsapi
import time
from core.stats_calculator import calculate_rolling_stuff_plus

def patch_missing_stuff_plus_fast():
    db_path = "data/mlb_betting.db"
    conn = sqlite3.connect(db_path)
    
    print("Finding dates with missing rolling_stuff data...")
    missing_dates_df = pd.read_sql_query(
        "SELECT DISTINCT game_date FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL ORDER BY game_date",
        conn
    )
    missing_dates = missing_dates_df['game_date'].tolist()
    print(f"Found {len(missing_dates)} unique days with missing data.")
    
    if not missing_dates:
        print("No missing data found. Exiting.")
        return

    print("Re-calculating daily rolling stats from raw_pitches (Local)...")
    query_sorted = "SELECT pitcher_id, game_date, stuff_plus FROM raw_pitches WHERE stuff_plus IS NOT NULL ORDER BY pitcher_id, game_date, pitch_id"
    chunks = pd.read_sql_query(query_sorted, conn, chunksize=100000)
    
    pitcher_histories = {}
    daily_rolling_stats = {}
    
    for i, chunk in enumerate(chunks):
        for _, row in chunk.iterrows():
            pid = int(row['pitcher_id'])
            date = str(row['game_date'])
            val = row['stuff_plus']
            
            if pid not in pitcher_histories:
                pitcher_histories[pid] = []
                
            if (pid, date) not in daily_rolling_stats:
                daily_rolling_stats[(pid, date)] = calculate_rolling_stuff_plus(pitcher_histories[pid])
                
            pitcher_histories[pid].append(val)
            
    print("Finished building rolling stats dictionary.")

    print("Fetching bulk schedule data with Lineup hydration (Fast API Method)...")
    updates = []
    games_processed = 0
    
    for date in missing_dates:
        try:
            # Hydrating 'lineups' gets us the starting pitcher for every game on this date in exactly ONE network request.
            schedule_data = statsapi.get('schedule', {'sportId': 1, 'date': date, 'hydrate': 'lineups'})
            
            for date_item in schedule_data.get('dates', []):
                for game in date_item.get('games', []):
                    game_id = game['gamePk']
                    
                    # Extract Starting Pitchers from the Lineups array
                    h_sp_id = None
                    a_sp_id = None
                    
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
                        h_roll = daily_rolling_stats.get((int(h_sp_id), date), 100.0)
                        a_roll = daily_rolling_stats.get((int(a_sp_id), date), 100.0)
                        updates.append((h_roll, a_roll, game_id))
                        games_processed += 1
                    else:
                        # Fallback if no lineup is available (e.g., rained out game incorrectly logged)
                        updates.append((100.0, 100.0, game_id))
                        
            # Sleep 0.2s between days. 180 days * 0.2s = 36 seconds total execution time.
            time.sleep(0.2) 
            
        except Exception as e:
            print(f"  Error fetching bulk schedule for {date}: {e}")
            
    print(f"Successfully mapped {games_processed} games.")
    print(f"Applying updates to the database...")
    
    conn.executemany(
        "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
        updates
    )
    conn.commit()
    conn.close()
    print("Fast Patch complete!")

if __name__ == "__main__":
    patch_missing_stuff_plus_fast()