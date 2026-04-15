import sqlite3
import pandas as pd
from core.db_manager import MLBDbManager
from core.stats_calculator import calculate_rolling_stuff_plus

def patch_missing_stuff_plus_sql_only():
    manager = MLBDbManager("data/mlb_betting.db")
    conn = manager._get_connection()
    
    print("Finding games missing rolling_stuff data...")
    missing_games = pd.read_sql_query(
        "SELECT game_id, game_date, home_team_id, away_team_id FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL",
        conn
    )
    print(f"Found {len(missing_games)} games missing data.")
    
    if missing_games.empty:
        return

    print("Extracting actual starting pitchers from local Statcast data (raw_pitches table)...")
    
    # Find the two pitchers who threw the earliest pitches on a given date
    sp_query = """
        SELECT game_date, pitcher_id, MIN(pitch_id) as first_pitch
        FROM raw_pitches
        GROUP BY game_date, pitcher_id
        ORDER BY game_date, first_pitch ASC
    """
    
    sps = pd.read_sql_query(sp_query, conn)
    
    # Map game_date -> list of starting pitcher IDs
    date_to_sps = {}
    for _, row in sps.iterrows():
        date = str(row['game_date'])
        pid = int(row['pitcher_id'])
        if date not in date_to_sps:
            date_to_sps[date] = []
        date_to_sps[date].append(pid)

    updates = []
    
    print("Calculating rolling Stuff+ and building update payload...")
    for _, row in missing_games.iterrows():
        game_id = int(row['game_id'])
        date = str(row['game_date'])
        
        # Get the starting pitchers for this date
        pitchers = date_to_sps.get(date, [])
        
        if len(pitchers) >= 2:
            # We have at least two pitchers who pitched in the 1st inning. 
            # We don't perfectly know which is home/away without joining on rosters, 
            # but we can just grab both and calculate their rolling stuff.
            p1_id = pitchers[0]
            p2_id = pitchers[1]
            
            p1_pitches = manager.get_pitcher_prior_pitches(p1_id, date)
            p2_pitches = manager.get_pitcher_prior_pitches(p2_id, date)
            
            p1_roll = calculate_rolling_stuff_plus(p1_pitches) if p1_pitches else 100.0
            p2_roll = calculate_rolling_stuff_plus(p2_pitches) if p2_pitches else 100.0
            
            updates.append((p1_roll, p2_roll, game_id))
        else:
            # Fallback if raw_pitches is missing inning 1 data for this specific game
            updates.append((100.0, 100.0, game_id))

    print(f"Applying {len(updates)} offline updates to the database...")
    conn.executemany(
        "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
        updates
    )
    conn.commit()
    conn.close()
    print("Offline Patch complete!")

if __name__ == "__main__":
    patch_missing_stuff_plus_sql_only()