import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def debug_fetch():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=os.path.join(os.getcwd(), ".playwright_session_vi_debug"), headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        url = "https://www.vegasinsider.com/mlb/odds/player-props/?date=2025-04-10"
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
            with open('vi_debug.html', 'w') as f:
                f.write(html)
            print("Saved vi_debug.html")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            context.close()

if __name__ == "__main__":
    debug_fetch()
