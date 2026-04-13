import os
import sqlite3
import pandas as pd
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from core.db_manager import MLBDbManager

def fetch_sbr_odds_playwright(date_str):
    url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
    print(f"  [SBR] Fetching {date_str} via Playwright JSON extraction...")
    
    extracted_games = []
    
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".playwright_session")
        context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Extract __NEXT_DATA__ using JavaScript in the browser
            raw_json = page.evaluate("document.getElementById('__NEXT_DATA__').textContent")
            full_data = json.loads(raw_json)
            
            page_props = full_data.get('props', {}).get('pageProps', {})
            odds_tables = page_props.get('oddsTables', [])
            
            game_rows = []
            for table in odds_tables:
                if table.get('league') == 'MLB':
                    game_rows.extend(table.get('oddsTableModel', {}).get('gameRows', []))
            
            for row in game_rows:
                game_view = row.get('gameView', {})
                home_team = game_view.get('homeTeam', {}).get('fullName')
                away_team = game_view.get('awayTeam', {}).get('fullName')
                
                home_ml, away_ml, total = None, None, None
                for view in row.get('oddsViews', []):
                    if not view: continue
                    line = view.get('currentLine', {})
                    if not line: continue
                    home_ml = line.get('homeMoneyLine')
                    if home_ml is not None:
                        away_ml = line.get('awayMoneyLine')
                        total = line.get('total')
                        break
                
                if home_team and away_team and home_ml is not None:
                    extracted_games.append({
                        'home_team': home_team, 'away_team': away_team,
                        'home_ml': home_ml, 'away_ml': away_ml, 'total': total
                    })
            
        except Exception as e:
            print(f"    [!] Playwright Error: {e}")
        finally:
            context.close()
            
    return extracted_games

def update_historical_odds(date_limit=None):
    manager = MLBDbManager()
    query = "SELECT DISTINCT game_date FROM historical_training_data WHERE closing_home_moneyline IS NULL ORDER BY game_date DESC"
    dates = [row['game_date'] for row in manager.query_agent_data(query)]
    
    if date_limit: dates = [d for d in dates if date_limit in d]
    
    print(f"Syncing Odds for {len(dates)} dates...")
    
    for date in dates[:5]:
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
    update_historical_odds('2025-06')
