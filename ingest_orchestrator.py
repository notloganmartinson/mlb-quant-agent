import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.ingest.stats import ingest_mlb_official_stats
from scripts.ingest.odds import fetch_odds_espn
from scripts.ingest.environment import fetch_weather
from scripts.fetch_live_odds import fetch_odds_api

def run_daily_ingestion(season=2026):
    """
    Orchestrates the daily data ingestion pipeline.
    Sequence:
    1. MLB Official Stats (Players, Teams, Bullpens)
    2. Live Market Odds (External API)
    3. ESPN Matchups and Odds
    4. Environment (Weather based on matchups)
    """
    print(f"--- Starting {season} Daily Ingestion Pipeline ---")
    
    # 1. Official MLB Stats
    ingest_mlb_official_stats(season=season)
    
    # 2. External Live Odds
    print("Fetching live market odds from external API...")
    fetch_odds_api()
    
    # 3. ESPN Odds & Matchups
    matchups = fetch_odds_espn()
    
    # 4. Environment & Weather
    if matchups:
        fetch_weather(matchups)
    else:
        print("No matchups found to fetch weather for.")

    print(f"\n--- {season} Daily Ingestion Complete ---")

if __name__ == "__main__":
    # Default to current season
    run_daily_ingestion(season=2026)
