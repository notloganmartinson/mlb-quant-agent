import os
import sys
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def debug_scrape():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=os.path.join(os.getcwd(), ".playwright_session_vi_debug_2"), headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        url = "https://www.vegasinsider.com/mlb/odds/player-props/?date=2025-04-10"
        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Check for STRIKEOUTS text
        content = page.content()
        if "STRIKEOUTS" in content.upper():
            print("Found STRIKEOUTS text on page.")
        else:
            print("STRIKEOUTS text NOT found on page.")
            
        # Try to find the table
        table_count = page.locator('table.odds-widget-table').count()
        print(f"Found {table_count} tables with class 'odds-widget-table'.")
        
        # Try to find the "See All" button for strikeouts and click it
        see_all = page.locator('span[data-role="seeall"]').first
        if see_all.count() > 0:
            print("Clicking 'See All' button...")
            see_all.click()
            page.wait_for_timeout(2000)
            
        # Get all tr[data-name]
        rows = page.locator('tr[data-name]')
        print(f"Found {rows.count()} rows with data-name attribute.")
        
        if rows.count() > 0:
            print(f"First 5 names: {[rows.nth(i).get_attribute('data-name') for i in range(min(5, rows.count()))]}")

        context.close()

if __name__ == "__main__":
    debug_scrape()
