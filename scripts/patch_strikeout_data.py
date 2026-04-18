import statsapi
from core.db_manager import MLBDbManager
from concurrent.futures import ThreadPoolExecutor
import time
import sys

def fetch_and_update(game_id):
    """Fetches correct strikeout counts for a single game."""
    try:
        box = statsapi.boxscore_data(game_id)
        hp = box.get('homePitchers', [])
        ap = box.get('awayPitchers', [])
        
        # Skip header row (index 0), starter is index 1
        home_k = int(hp[1].get('k', 0)) if len(hp) > 1 else 0
        away_k = int(ap[1].get('k', 0)) if len(ap) > 1 else 0
        
        return (game_id, home_k, away_k)
    except Exception as e:
        return None

def patch_strikeouts():
    manager = MLBDbManager()
    
    # Identify games that need patching
    print("Querying database for poisoned rows...")
    games = manager.query_agent_data("SELECT game_id FROM historical_training_data WHERE home_sp_strikeouts = 0 AND away_sp_strikeouts = 0")
    game_ids = [g['game_id'] for g in games]
    
    total = len(game_ids)
    if total == 0:
        print("No poisoned rows found.")
        return

    print(f"Found {total} games to patch. Fetching boxscores using 15 threads...")
    
    results = []
    processed = 0
    
    # Process in chunks of 500 to show progress and avoid overwhelming the API
    chunk_size = 500
    for i in range(0, total, chunk_size):
        chunk = game_ids[i:i+chunk_size]
        with ThreadPoolExecutor(max_workers=15) as executor:
            chunk_results = list(executor.map(fetch_and_update, chunk))
            results.extend([r for r in chunk_results if r is not None])
        
        processed += len(chunk)
        print(f"  Progress: {processed}/{total} games fetched...")
        time.sleep(1) # Brief rest between chunks

    print(f"\nApplying {len(results)} updates to the database...")
    
    # Use the internal connection for a bulk transaction
    conn = manager._get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany("""
            UPDATE historical_training_data 
            SET home_sp_strikeouts = ?, away_sp_strikeouts = ? 
            WHERE game_id = ?
        """, [(hk, ak, gid) for gid, hk, ak in results])
        conn.commit()
        print(f"Successfully patched {len(results)} games.")
    except Exception as e:
        conn.rollback()
        print(f"Error during database update: {e}")

if __name__ == "__main__":
    patch_strikeouts()
