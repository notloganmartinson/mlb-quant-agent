import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

from scripts.fetch_historical_odds import fetch_sbr_odds_playwright

def test_fetch():
    date_to_test = "2025-04-01"
    print(f"Testing SBR fetch for {date_to_test}...")
    
    try:
        games = fetch_sbr_odds_playwright(date_to_test)
        
        if games:
            print(f"Successfully extracted {len(games)} games!")
            for game in games[:5]: # Show first 5
                print(f"  {game['away_team']} @ {game['home_team']}: ML {game['home_ml']}/{game['away_ml']}, Total {game['total']}")
        else:
            print("Failed to extract any games. The site might be blocked by the plane Wi-Fi or the structure changed.")
    except Exception as e:
        print(f"Fatal error during fetch: {e}")

if __name__ == "__main__":
    test_fetch()
