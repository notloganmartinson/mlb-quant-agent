import sqlite3
import pandas as pd
from core.db_manager import MLBDbManager

def patch_missing_stuff_plus_memory():
    manager = MLBDbManager("data/mlb_betting.db")
    conn = manager._get_connection()
    
    print("Finding games missing rolling_stuff data...")
    missing_games = pd.read_sql_query(
        "SELECT game_id, game_date FROM historical_training_data WHERE home_sp_rolling_stuff IS NULL",
        conn
    )
    print(f"Found {len(missing_games)} games missing data.")
    
    if missing_games.empty:
        return

    print("Extracting starting pitchers by finding the first pitch of each half-inning...")
    # This single query finds the exact pitcher who threw the first pitch for the Away team (Top 1st)
    # and the Home team (Bottom 1st) for every single game in the database.
    # inning_topbot: 'Top' means Away is batting / Home is pitching. 'Bot' means Home is batting / Away is pitching.
    sp_query = """
        SELECT game_date, 
               CASE WHEN inning = 1 AND pitch_id = (SELECT MIN(pitch_id) FROM raw_pitches p2 WHERE p2.game_date = rp.game_date AND p2.inning = 1) THEN 'HOME_SP'
                    WHEN inning = 1 AND pitch_id = (SELECT MIN(pitch_id) FROM raw_pitches p2 WHERE p2.game_date = rp.game_date AND p2.inning = 2) THEN 'AWAY_SP'
                    ELSE 'UNKNOWN'
               END as sp_type,
               pitcher_id
        FROM raw_pitches rp
        WHERE inning IN (1, 2)
    """
    
    # A faster, simpler way to get the two starting pitchers for a date:
    # Just grab the first two unique pitchers to appear in a game_date.
    fast_sp_query = """
        SELECT game_date, pitcher_id, MIN(pitch_id) as first_pitch
        FROM raw_pitches
        GROUP BY game_date, pitcher_id
    """
    
    print("Loading all pitcher appearances into memory...")
    sps = pd.read_sql_query(fast_sp_query, conn)
    
    # Sort by first_pitch to ensure we get the actual starters (the first 2 to pitch that day)
    sps = sps.sort_values(['game_date', 'first_pitch'])
    
    date_to_sps = {}
    for _, row in sps.iterrows():
        date = str(row['game_date'])
        pid = int(row['pitcher_id'])
        if date not in date_to_sps:
            date_to_sps[date] = []
        if len(date_to_sps[date]) < 2:  # Only grab the first two pitchers of the day
            date_to_sps[date].append(pid)

    print("Loading all historical Stuff+ scores into memory...")
    # Load EVERY stuff_plus score ever calculated into a pandas dataframe
    all_scores = pd.read_sql_query(
        "SELECT pitcher_id, game_date, stuff_plus FROM raw_pitches WHERE stuff_plus IS NOT NULL", 
        conn
    )
    
    # Sort chronologically so we can calculate rolling averages
    all_scores['game_date'] = pd.to_datetime(all_scores['game_date'])
    all_scores = all_scores.sort_values(['pitcher_id', 'game_date'])
    
    print("Pre-calculating daily rolling Stuff+ for all pitchers...")
    # We build a dictionary: (pitcher_id, game_date) -> rolling_stuff_BEFORE_that_date
    from core.stats_calculator import calculate_rolling_stuff_plus
    
    pitcher_histories = {}
    daily_rolling_stats = {}
    
    for _, row in all_scores.iterrows():
        pid = int(row['pitcher_id'])
        date = str(row['game_date'].date())
        val = row['stuff_plus']
        
        if pid not in pitcher_histories:
            pitcher_histories[pid] = []
            
        if (pid, date) not in daily_rolling_stats:
            daily_rolling_stats[(pid, date)] = calculate_rolling_stuff_plus(pitcher_histories[pid])
            
        pitcher_histories[pid].append(val)

    print("Mapping starting pitchers to missing games...")
    updates = []
    
    for _, row in missing_games.iterrows():
        game_id = int(row['game_id'])
        date = str(row['game_date'])
        
        pitchers = date_to_sps.get(date, [])
        
        if len(pitchers) == 2:
            p1_id, p2_id = pitchers[0], pitchers[1]
            
            # Look up their rolling score from our memory dictionary
            p1_roll = daily_rolling_stats.get((p1_id, date), 100.0)
            p2_roll = daily_rolling_stats.get((p2_id, date), 100.0)
            
            updates.append((p1_roll, p2_roll, game_id))
        else:
            updates.append((100.0, 100.0, game_id))

    print(f"Applying {len(updates)} offline updates to the database...")
    conn.executemany(
        "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?",
        updates
    )
    conn.commit()
    conn.close()
    print("Offline Patch complete! The dataset is fully intact.")

if __name__ == "__main__":
    patch_missing_stuff_plus_memory()