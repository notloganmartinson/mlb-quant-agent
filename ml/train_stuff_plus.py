import pandas as pd
import xgboost as xgb
import numpy as np
import os
import sys
import sqlite3
import gc
import statsapi
from datetime import datetime

# Ensure project root is in path for imports
sys.path.append(os.getcwd())

from core.db_manager import MLBDbManager
from core.stats_calculator import calculate_vaa, calculate_break_magnitude, calculate_rolling_stuff_plus

def train_stuff_plus():
    """
    Trains a pitch-level model to calculate Stuff+ (normalized whiff probability).
    Uses chunking to prevent OOM and calculates point-in-time rolling metrics.
    """
    manager = MLBDbManager()
    db_path = manager.db_path
    
    features = [
        'release_speed', 'pfx_x', 'pfx_z', 'release_spin_rate', 
        'release_extension', 'vaa', 'break_magnitude'
    ]
    cat_features = ['pitch_type']
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    
    # 0. Preparation
    print("Fetching unique pitch types for encoding...")
    all_pitch_types = pd.read_sql_query(
        "SELECT DISTINCT pitch_type FROM raw_pitches WHERE pitch_type IS NOT NULL", 
        conn
    )['pitch_type'].tolist()
    all_pitch_types = sorted(all_pitch_types)
    print(f"Detected {len(all_pitch_types)} pitch types.")

    # 1. Training Pass (Incremental)
    print("\n--- PASS 1: Training Model (Incremental) ---")
    params = {
        'max_depth': 5,
        'eta': 0.05,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'nthread': 4,
        'random_state': 42
    }
    
    model = None
    total_pitches = 0
    
    query = "SELECT * FROM raw_pitches WHERE whiff IS NOT NULL"
    chunks = pd.read_sql_query(query, conn, chunksize=100000)
    
    for i, chunk in enumerate(chunks):
        # Feature Engineering
        chunk['vaa'] = calculate_vaa(chunk['vy0'], chunk['ay'], chunk['vz0'], chunk['az'])
        chunk['break_magnitude'] = calculate_break_magnitude(chunk['pfx_x'], chunk['pfx_z'])
        
        # Preprocessing
        chunk = chunk.dropna(subset=features + cat_features + ['whiff'])
        if chunk.empty: continue
        
        X = pd.get_dummies(chunk[features + cat_features], columns=cat_features)
        for pt in all_pitch_types:
            col = f"pitch_type_{pt}"
            if col not in X.columns: X[col] = 0
        X = X.reindex(sorted(X.columns), axis=1)
        y = chunk['whiff']
        
        dtrain = xgb.DMatrix(X, label=y)
        # Incremental training: pass the previous booster to xgb_model
        model = xgb.train(params, dtrain, xgb_model=model, num_boost_round=10)
        
        total_pitches += len(chunk)
        if (i + 1) % 5 == 0:
            print(f"  Processed {i+1} chunks ({total_pitches} pitches)...")
        
        del chunk, X, y, dtrain
        gc.collect()

    print(f"Model training complete. Total pitches: {total_pitches}")

    # 2. Global Normalization Stats
    print("\n--- PASS 2: Calculating Global Stats for Normalization ---")
    pwhiff_sums = {pt: 0.0 for pt in all_pitch_types}
    pwhiff_counts = {pt: 0 for pt in all_pitch_types}
    
    chunks = pd.read_sql_query(query, conn, chunksize=100000)
    for i, chunk in enumerate(chunks):
        chunk['vaa'] = calculate_vaa(chunk['vy0'], chunk['ay'], chunk['vz0'], chunk['az'])
        chunk['break_magnitude'] = calculate_break_magnitude(chunk['pfx_x'], chunk['pfx_z'])
        chunk = chunk.dropna(subset=features + cat_features + ['whiff'])
        if chunk.empty: continue
        
        X = pd.get_dummies(chunk[features + cat_features], columns=cat_features)
        for pt in all_pitch_types:
            col = f"pitch_type_{pt}"
            if col not in X.columns: X[col] = 0
        X = X.reindex(sorted(X.columns), axis=1)
        
        dtest = xgb.DMatrix(X)
        chunk['pWhiff'] = model.predict(dtest)
        
        grouped = chunk.groupby('pitch_type')['pWhiff'].agg(['sum', 'count'])
        for pt, row in grouped.iterrows():
            if pt in pwhiff_sums:
                pwhiff_sums[pt] += row['sum']
                pwhiff_counts[pt] += row['count']
        
        if (i + 1) % 5 == 0:
            print(f"  Scored {i+1} chunks for stats...")
            
        del chunk, X, dtest
        gc.collect()

    avg_pwhiff_by_type = {
        pt: (pwhiff_sums[pt] / pwhiff_counts[pt] if pwhiff_counts[pt] > 0 else 0.1) 
        for pt in all_pitch_types
    }
    print(f"Normalization factors (Avg pWhiff per type) calculated.")

    # 3. Scoring & Rolling Averages
    print("\n--- PASS 3: Scoring & Calculating Rolling Stuff+ ---")
    # Sort chronologically per pitcher to calculate point-in-time rolling average
    query_sorted = "SELECT * FROM raw_pitches ORDER BY pitcher_id, game_date, pitch_id"
    chunks = pd.read_sql_query(query_sorted, conn, chunksize=100000)
    
    pitcher_histories = {} # pitcher_id -> list of stuff_plus
    update_data = [] # (stuff_plus, pitch_id)
    daily_rolling_stats = {} # (pitcher_id, date) -> rolling_stuff_BEFORE_date

    for i, chunk in enumerate(chunks):
        chunk['vaa'] = calculate_vaa(chunk['vy0'], chunk['ay'], chunk['vz0'], chunk['az'])
        chunk['break_magnitude'] = calculate_break_magnitude(chunk['pfx_x'], chunk['pfx_z'])
        
        # Calculate scores where features are present
        mask = chunk[features + cat_features].notna().all(axis=1)
        if mask.any():
            X_score = pd.get_dummies(chunk.loc[mask, features + cat_features], columns=cat_features)
            for pt in all_pitch_types:
                col = f"pitch_type_{pt}"
                if col not in X_score.columns: X_score[col] = 0
            X_score = X_score.reindex(sorted(X_score.columns), axis=1)
            
            dscore = xgb.DMatrix(X_score)
            chunk.loc[mask, 'pWhiff'] = model.predict(dscore)
            
            # Apply normalization
            chunk.loc[mask, 'stuff_plus'] = chunk.loc[mask].apply(
                lambda row: (row['pWhiff'] / avg_pwhiff_by_type.get(row['pitch_type'], 0.1)) * 100, 
                axis=1
            )

        # Process each pitch for rolling history
        for _, row in chunk.iterrows():
            pid = int(row['pitcher_id'])
            date = str(row['game_date'])
            
            if pid not in pitcher_histories:
                pitcher_histories[pid] = []
            
            # Capture the rolling average BEFORE today's pitches
            if (pid, date) not in daily_rolling_stats:
                daily_rolling_stats[(pid, date)] = calculate_rolling_stuff_plus(pitcher_histories[pid])
            
            # Update history with today's pitch result
            if not pd.isna(row['stuff_plus']):
                pitcher_histories[pid].append(row['stuff_plus'])
                update_data.append((round(float(row['stuff_plus']), 2), int(row['pitch_id'])))

        # Incremental DB update
        if len(update_data) >= 100000:
            print(f"  Writing {len(update_data)} pitch scores to DB...")
            conn.executemany("UPDATE raw_pitches SET stuff_plus = ? WHERE pitch_id = ?", update_data)
            conn.commit()
            update_data = []

        if (i + 1) % 5 == 0:
            print(f"  Processed {i+1} chunks for rolling metrics...")
            
        del chunk
        gc.collect()

    if update_data:
        conn.executemany("UPDATE raw_pitches SET stuff_plus = ? WHERE pitch_id = ?", update_data)
        conn.commit()

    # 4. Update players with Latest Seasonal Values
    print("\n--- PASS 4: Updating players (Latest Rolling) ---")
    current_season = datetime.now().year
    sp_count = 0
    for pid, history in pitcher_histories.items():
        if history:
            latest_val = calculate_rolling_stuff_plus(history)
            manager.update_player_stuff_plus(pid, current_season, round(latest_val, 2))
            sp_count += 1
    print(f"Updated {sp_count} pitchers in players table.")

    # 5. Link and Update historical_training_data
    print("\n--- PASS 5: Updating historical_training_data (Look-Ahead Bias Fix) ---")
    htd_df = pd.read_sql_query("SELECT game_id, game_date, home_team_id, away_team_id FROM historical_training_data", conn)
    print(f"Processing {len(htd_df)} historical games...")
    
    processed_count = 0
    htd_updates = []
    
    # Chunk by month to prevent 503 timeouts
    months = [
        ("03-01", "03-31"), ("04-01", "04-30"), ("05-01", "05-31"), 
        ("06-01", "06-30"), ("07-01", "07-31"), ("08-01", "08-31"), 
        ("09-01", "09-30"), ("10-01", "11-15")
    ]

    htd_df['year'] = pd.to_datetime(htd_df['game_date']).dt.year
    for year in sorted(htd_df['year'].unique()):
        print(f"  Fetching SP info for {year} season...")
        for start, end in months:
            s_date = f"{year}-{start}"
            e_date = f"{year}-{end}"
            print(f"    Fetching {s_date} to {e_date}...")
            
            try:
                import time
                games = statsapi.schedule(start_date=s_date, end_date=e_date)
                game_sp_map = {} 
                for g in games:
                    h_sp_id = g.get('home_probable_pitcher_id')
                    a_sp_id = g.get('away_probable_pitcher_id')
                    if h_sp_id and a_sp_id:
                        game_sp_map[int(g['game_id'])] = (int(h_sp_id), int(a_sp_id))
                
                # Apply to HTD rows in this date range
                mask = (pd.to_datetime(htd_df['game_date']) >= pd.to_datetime(s_date)) & \
                       (pd.to_datetime(htd_df['game_date']) <= pd.to_datetime(e_date))
                range_htd = htd_df[mask]
                
                for _, row in range_htd.iterrows():
                    gid = int(row['game_id'])
                    date = str(row['game_date'])
                    if gid in game_sp_map:
                        h_pid, a_pid = game_sp_map[gid]
                        h_roll = daily_rolling_stats.get((h_pid, date), 100.0)
                        a_roll = daily_rolling_stats.get((a_pid, date), 100.0)
                        htd_updates.append((h_roll, a_roll, gid))
                        processed_count += 1
                
                time.sleep(2) # Prevent 503
            except Exception as e:
                print(f"      Error fetching range {s_date}-{e_date}: {e}")
                continue

    if htd_updates:
        print(f"  Updating {len(htd_updates)} games in historical_training_data...")
        conn.executemany(
            "UPDATE historical_training_data SET home_sp_rolling_stuff = ?, away_sp_rolling_stuff = ? WHERE game_id = ?", 
            htd_updates
        )
        conn.commit()

    conn.close()
    print("\n--- STUFF+ SPRINT COMPLETE ---")

if __name__ == "__main__":
    train_stuff_plus()
