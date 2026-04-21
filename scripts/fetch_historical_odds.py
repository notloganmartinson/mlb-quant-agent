import os
import sys
import sqlite3
import pandas as pd
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from core.db_manager import MLBDbManager

def fetch_sbr_odds_playwright(date_str):
    extracted_games = {} # Keyed by home_team
    
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".playwright_session")
        context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        # 1. Fetch Moneyline
        ml_url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
        print(f"  [SBR] Fetching ML for {date_str}...")
        try:
            page.goto(ml_url, wait_until="networkidle", timeout=60000)
            raw_json = page.evaluate("document.getElementById('__NEXT_DATA__').textContent")
            data = json.loads(raw_json)
            game_rows = []
            for table in data.get('props', {}).get('pageProps', {}).get('oddsTables', []):
                if table.get('league') == 'MLB':
                    game_rows.extend(table.get('oddsTableModel', {}).get('gameRows', []))
            
            for row in game_rows:
                home_team = row.get('gameView', {}).get('homeTeam', {}).get('fullName')
                away_team = row.get('gameView', {}).get('awayTeam', {}).get('fullName')
                if not home_team: continue
                
                for view in row.get('oddsViews', []):
                    if not view: continue
                    line = view.get('currentLine', {})
                    home_ml = line.get('homeMoneyLine') or line.get('homeOdds')
                    away_ml = line.get('awayMoneyLine') or line.get('awayOdds')
                    if home_ml:
                        extracted_games[home_team] = {
                            'home_team': home_team, 'away_team': away_team,
                            'home_ml': home_ml, 'away_ml': away_ml, 'total': None
                        }
                        break
        except Exception as e:
            print(f"    [!] ML Error: {e}")

        # 2. Fetch Totals
        total_url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/totals/?date={date_str}"
        print(f"  [SBR] Fetching Totals for {date_str}...")
        try:
            page.goto(total_url, wait_until="networkidle", timeout=60000)
            raw_json = page.evaluate("document.getElementById('__NEXT_DATA__').textContent")
            data = json.loads(raw_json)
            game_rows = []
            for table in data.get('props', {}).get('pageProps', {}).get('oddsTables', []):
                if table.get('league') == 'MLB':
                    game_rows.extend(table.get('oddsTableModel', {}).get('gameRows', []))
            
            for row in game_rows:
                home_team = row.get('gameView', {}).get('homeTeam', {}).get('fullName')
                if home_team in extracted_games:
                    for view in row.get('oddsViews', []):
                        if not view: continue
                        total = view.get('currentLine', {}).get('total')
                        if total:
                            extracted_games[home_team]['total'] = total
                            break
        except Exception as e:
            print(f"    [!] Total Error: {e}")
            
        context.close()
            
    return list(extracted_games.values())

def update_historical_odds(date_limit=None):
    manager = MLBDbManager()
    query = "SELECT DISTINCT game_date FROM historical_training_data WHERE closing_home_moneyline IS NULL ORDER BY game_date DESC"
    dates = [row['game_date'] for row in manager.query_agent_data(query)]
    
    if date_limit: dates = [d for d in dates if date_limit in d]
    
    print(f"Syncing Odds for {len(dates)} dates...")
    
    for date in dates:
        games = fetch_sbr_odds_playwright(date)
        updated = 0
        for g in games:
            h_id = manager.resolve_team_id(g['home_team'])
            if h_id:
                sql = "UPDATE historical_training_data SET closing_home_moneyline = ?, closing_away_moneyline = ?, closing_total = ? WHERE game_date = ? AND home_team_id = ?"
                with manager._get_connection() as conn:
                    cursor = conn.execute(sql, (g['home_ml'], g['away_ml'], g['total'], date, h_id))
                    if cursor.rowcount > 0: updated += 1
        print(f"  -> {date}: Updated {updated} games.")
        time.sleep(1)

if __name__ == "__main__":
    update_historical_odds(None)
