import os
import sys
import time
import schedule

# Ensure project root is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.ingest.mlb_official_stats import ingest_mlb_official_stats
from scripts.ingest.odds import fetch_odds_espn
from scripts.ingest.environment import fetch_weather
from scripts.fetch_live_odds import fetch_odds_api

def run_daily_stats_ingestion(season=2026):
    """
    Task 1: Heavy Stats & Environment
    Runs once per day early in the morning.
    """
    print(f"--- Starting {season} Daily Stats Ingestion ---")
    
    # 1. Official MLB Stats
    ingest_mlb_official_stats(season=season)
    
    # We need matchups to fetch weather. We fetch from ESPN here (free) 
    # to get the matchups without hitting the expensive Odds API.
    print("Fetching initial ESPN matchups for weather correlation...")
    matchups = fetch_odds_espn()
    
    # 2. Environment & Weather
    if matchups:
        fetch_weather(matchups)
    else:
        print("No matchups found to fetch weather for.")

    print(f"--- {season} Daily Stats Ingestion Complete ---")

def run_odds_ingestion():
    """
    Task 2: Odds & CLV Tracking
    Runs 4 times a day during relevant MLB windows to conserve Odds API credits.
    """
    print("--- Starting Odds & CLV Ingestion ---")
    
    # 1. External Live Odds (The expensive Odds API call)
    print("Fetching live market odds from external API...")
    fetch_odds_api()
    
    # 2. ESPN Odds & Matchups (Keep in sync)
    print("Fetching updated ESPN odds...")
    fetch_odds_espn()

    print("--- Odds & CLV Ingestion Complete ---")

def start_scheduler():
    print("Starting MLB Agent Background Scheduler...")
    print("Credit-Saving Mode Active: Odds API fetched 4x daily.")
    
    # Task 1: Heavy Stats once per day at 6:00 AM
    schedule.every().day.at("06:00").do(run_daily_stats_ingestion, season=2026)
    
    # Task 2: Odds & CLV exactly 4 times a day
    schedule.every().day.at("09:00").do(run_odds_ingestion)
    schedule.every().day.at("13:00").do(run_odds_ingestion)
    schedule.every().day.at("17:00").do(run_odds_ingestion)
    schedule.every().day.at("20:00").do(run_odds_ingestion)
    
    print("Scheduler is running. Press Ctrl+C to exit.")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    start_scheduler()