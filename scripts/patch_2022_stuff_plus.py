import sqlite3
import pandas as pd
from datetime import datetime

def patch_missing_stuff_plus():
    db_path = "data/mlb_betting.db"
    conn = sqlite3.connect(db_path)
    
    print("Finding games missing rolling_stuff data...")
    missing_games = pd.read_sql_query(
        "SELECT game_id, game_date, home_team_id, away_team_id FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL",
        conn
    )
    print(f"Found {len(missing_games)} games missing data (mostly 2022).")
    
    if len(missing_games) == 0:
        print("No missing data found. Exiting.")
        return

    # 1. Identify Starting Pitchers from raw_pitches
    print("Extracting actual starting pitchers from Statcast data (first pitch of the game)...")
    # For each game, find the pitcher who threw pitch #1 for the home team (top 1st) and away team (bottom 1st)
    sp_query = """
        SELECT game_date, pitcher_id, inning
        FROM (
            SELECT game_date, pitcher_id, inning,
                   ROW_NUMBER() OVER(PARTITION BY game_date, inning ORDER BY pitch_id ASC) as rn
            FROM raw_pitches
            WHERE inning IN (1, 2) -- Inning 1 (Top) is Away team batting (Home pitching), Inning 1 (Bottom) is Home team batting (Away pitching). If Away bats in top 1, home pitches in top 1. Actually, raw_pitches usually has 'inning_topbot'. Let's just find the first pitcher for each team in the game.
        )
        WHERE rn = 1
    """
    
    # A more robust way to find the SPs for a game date: find the pitcher who threw the most pitches in the first inning.
    # But since we need team context, let's just pull all pitchers and their first pitch time.
    
    print("Re-calculating daily rolling stats from raw_pitches...")
    # We need to rebuild the daily_rolling_stats dictionary that was in train_stuff_plus.py
    from core.stats_calculator import calculate_rolling_stuff_plus
    
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

    # 2. Use statsapi.schedule to reliably get the game_id to SP mapping, but this time we handle the missing probable_pitcher_id
    # Wait, the issue is statsapi doesn't have the probable pitcher.
    # We MUST use the actual boxscore or raw_pitches to find the SP.
    print("Fetching boxscores to identify starting pitchers...")
    import statsapi
    import time
    
    updates = []
    
    for i, row in missing_games.iterrows():
        game_id = int(row['game_id'])
        date = str(row['game_date'])
        
        try:
            box = statsapi.boxscore_data(game_id)
            home_pitchers = box.get('homePitchers', [])
            away_pitchers = box.get('awayPitchers', [])
            
            h_sp_id = home_pitchers[1]['personId'] if len(home_pitchers) > 1 else (home_pitchers[0]['personId'] if home_pitchers else None)
            a_sp_id = away_pitchers[1]['personId'] if len(away_pitchers) > 1 else (away_pitchers[0]['personId'] if away_pitchers else None)
            
            # The first pitcher listed in the boxscore array is usually the starter.
            # Actually, boxscore_data returns an array of pitchers. The first one is the starter.
            if home_pitchers: h_sp_id = home_pitchers[0].get('personId')
            if away_pitchers: a_sp_id = away_pitchers[0].get('personId')
            
            if h_sp_id and a_sp_id:
                h_roll = daily_rolling_stats.get((int(h_sp_id), date), 100.0)
                a_roll = daily_rolling_stats.get((int(a_sp_id), date), 100.0)
                updates.append((h_roll, a_roll, game_id))
            else:
                # Fallback if boxscore fails
                updates.append((100.0, 100.0, game_id))
                
            if i % 100 == 0:
                print(f"  Processed {i}/{len(missing_games)} games...")
            time.sleep(0.5) # Be gentle with the API
            
        except Exception as e:
            print(f"Error fetching boxscore for game {game_id}: {e}")
            updates.append((100.0, 100.0, game_id))
            
    print(f"Applying {len(updates)} updates to the database...")
    conn.executemany(
        "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
        updates
    )
    conn.commit()
    conn.close()
    print("Patch complete.")

if __name__ == "__main__":
    patch_missing_stuff_plus()
