import os
import json
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def debug_sbr_fetch(date_str):
    url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
    print(f"DEBUG: Fetching {url}")
    
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".playwright_session_debug")
        context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            raw_json = page.evaluate("document.getElementById('__NEXT_DATA__').textContent")
            full_data = json.loads(raw_json)
            
            page_props = full_data.get('props', {}).get('pageProps', {})
            odds_tables = page_props.get('oddsTables', [])
            
            print(f"Found {len(odds_tables)} odds tables.")
            for i, table in enumerate(odds_tables):
                league = table.get('league')
                game_count = len(table.get('oddsTableModel', {}).get('gameRows', []))
                print(f"Table {i}: League={league}, Games={game_count}")
                if league == 'MLB' and game_count > 0:
                    for row in table.get('oddsTableModel', {}).get('gameRows', []):
                        gv = row.get('gameView', {})
                        ht = gv.get('homeTeam', {}).get('fullName')
                        at = gv.get('awayTeam', {}).get('fullName')
                        print(f"Game: {at} @ {ht}")
                        for view in row.get('oddsViews', []):
                            line = (view or {}).get('currentLine', {})
                            print(f"  Line: {line}")
                            if line and line.get('homeMoneyLine') is not None:
                                print(f"    SUCCESS: Home ML={line.get('homeMoneyLine')}")

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            context.close()

if __name__ == "__main__":
    debug_sbr_fetch('2025-10-25') # A post-season date
