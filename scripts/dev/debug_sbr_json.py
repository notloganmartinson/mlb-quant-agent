import os
import sys
import json
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Add project root to path
sys.path.append(os.getcwd())

def debug_sbr_json(date_str):
    url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
    print(f"Debugging SBR JSON for {date_str}...")
    
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
            
            for table in odds_tables:
                if table.get('league') == 'MLB':
                    game_rows = table.get('oddsTableModel', {}).get('gameRows', [])
                    if game_rows:
                        # Inspect the first game's oddsViews
                        first_game = game_rows[0]
                        print(f"Game: {first_game.get('gameView', {}).get('awayTeam', {}).get('fullName')} @ {first_game.get('gameView', {}).get('homeTeam', {}).get('fullName')}")
                        
                        odds_views = first_game.get('oddsViews', [])
                        for i, view in enumerate(odds_views):
                            if view:
                                line = view.get('currentLine', {})
                                if line.get('total') is not None:
                                    print(f"\nFound Total in Book {i}!")
                                    print(f"Book {i} Current Line Data: {line}")
                                    break
                        else:
                            print("\nNo totals found in any oddsViews for the default Moneyline view.")
                        break
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            context.close()

if __name__ == "__main__":
    debug_sbr_json("2025-04-01")
