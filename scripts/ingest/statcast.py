import pybaseball
import pandas as pd
import time
import gc
import sys
import os
from core.db_manager import MLBDbManager
from datetime import datetime, timedelta

# MLB Regular Season Ranges (Approximate to cover all games)
SEASONS = {
    2022: ("2022-04-07", "2022-10-05"),
    2023: ("2023-03-30", "2023-10-01"),
    2024: ("2024-03-20", "2024-09-29"),
    2025: ("2025-03-27", "2025-09-28"),
}

PROGRESS_LOG = "scripts/ingest/statcast_progress.log"

def log_progress(date_str):
    with open(PROGRESS_LOG, "w") as f:
        f.write(date_str)

def get_last_progress():
    if os.path.exists(PROGRESS_LOG):
        with open(PROGRESS_LOG, "r") as f:
            return f.read().strip()
    return None

def ingest_production_statcast():
    """
    Production-scale ingestion: 7-day chunks, parallelized, memory-safe.
    """
    manager = MLBDbManager()
    whiff_descriptions = ['swinging_strike', 'swinging_strike_blocked']
    
    last_processed = get_last_progress()
    
    for year in sorted(SEASONS.keys()):
        start_str, end_str = SEASONS[year]
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")
        
        # If we have progress, skip until we hit the resume point
        if last_processed:
            resume_dt = datetime.strptime(last_processed, "%Y-%m-%d")
            if end_dt <= resume_dt:
                print(f"Skipping {year} (already processed up to {last_processed})")
                continue
            if start_dt < resume_dt:
                start_dt = resume_dt + timedelta(days=1)

        print(f"--- Starting Season: {year} ({start_dt.strftime('%Y-%m-%d')} to {end_str}) ---")
        
        current_dt = start_dt
        while current_dt <= end_dt:
            chunk_end = min(current_dt + timedelta(days=6), end_dt)
            s_str = current_dt.strftime("%Y-%m-%d")
            e_str = chunk_end.strftime("%Y-%m-%d")
            
            print(f"Fetching {s_str} to {e_str}...")
            
            try:
                # parallel=True uses multiprocessing to speed up CSV parsing/fetching
                df = pybaseball.statcast(start_dt=s_str, end_dt=e_str, parallel=True)
                
                if df is not None and not df.empty:
                    # Filter for rows with minimal required physics data
                    required_cols = ['release_speed', 'pfx_x', 'pfx_z', 'pitcher', 'vx0', 'vy0', 'vz0']
                    df = df.dropna(subset=required_cols)
                    
                    print(f"  Inserting {len(df)} pitches...")
                    for _, row in df.iterrows():
                        try:
                            whiff = 1 if row['description'] in whiff_descriptions else 0
                            data = {
                                "pitcher_id": int(row['pitcher']),
                                "game_date": str(row['game_date']),
                                "pitch_type": str(row['pitch_type']) if pd.notnull(row['pitch_type']) else None,
                                "release_speed": float(row['release_speed']),
                                "pfx_x": float(row['pfx_x']),
                                "pfx_z": float(row['pfx_z']),
                                "release_spin_rate": float(row['release_spin_rate']) if pd.notnull(row['release_spin_rate']) else None,
                                "release_extension": float(row['release_extension']) if pd.notnull(row['release_extension']) else None,
                                "vx0": float(row['vx0']),
                                "vy0": float(row['vy0']),
                                "vz0": float(row['vz0']),
                                "ax": float(row['ax']),
                                "ay": float(row['ay']),
                                "az": float(row['az']),
                                "sz_top": float(row['sz_top']),
                                "sz_bot": float(row['sz_bot']),
                                "plate_x": float(row['plate_x']),
                                "plate_z": float(row['plate_z']),
                                "description": str(row['description']),
                                "whiff": whiff
                            }
                            manager.upsert_raw_pitch(data)
                        except Exception:
                            continue
                    
                    print(f"  Done. Memory cleanup...")
                    del df
                    gc.collect()
                
                # Update progress and rest
                log_progress(e_str)
                print(f"  Progress saved: {e_str}. Sleeping 2s...")
                time.sleep(2)
                
            except Exception as e:
                print(f"  CRITICAL ERROR in chunk {s_str} to {e_str}: {e}")
                print("  Stopping. Check logs and restart script to resume.")
                return

            current_dt = chunk_end + timedelta(days=1)

if __name__ == "__main__":
    ingest_production_statcast()
