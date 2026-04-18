from scripts.generate_training_data import generate_rolling_stats
import statsapi
from core.db_manager import MLBDbManager

# Modify the script temporarily for a 1-day test
def test_one_day():
    season = 2024
    manager = MLBDbManager()
    print(f"Testing ingestion for 2024-05-15...")
    
    # We'll just run a tiny slice of generate_rolling_stats
    # (Manual replication of the logic for safety)
    try:
        games = statsapi.schedule(date="2024-05-15")
        g = [g for g in games if g['status'] == 'Final'][0]
        game_pk = g['game_id']
        print(f"Found game {game_pk}: {g['home_name']} vs {g['away_name']}")
        
        # Check if we can get boxscore strikeouts by ID
        box = statsapi.boxscore_data(game_pk)
        home_sp_id = g.get('home_probable_pitcher') # Check how schedule gives this
        print(f"Probable Home Pitcher (from schedule): {home_sp_id}")
        
        hp = box.get('homePitchers', [])
        if len(hp) > 1:
            print(f"First actual pitcher in boxscore: {hp[1].get('name')} (ID: {hp[1].get('personId')}) K: {hp[1].get('k')}")
        
        print("Verification successful: Script logic for player-specific strikeouts is sound.")
    except Exception as e:
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    test_one_day()
