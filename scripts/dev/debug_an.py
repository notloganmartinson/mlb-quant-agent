import os
from playwright.sync_api import sync_playwright

def run():
    url = "https://www.actionnetwork.com/mlb/props/strikeouts?date=2024-06-01"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        try:
            print(page.title())
            rows = page.locator("div[class*='best-odds']").all_inner_texts()
            print(f"Found {len(rows)} rows.")
            print(rows[:2])
        except Exception as e:
            print("Failed:", e)
        browser.close()

if __name__ == "__main__":
    run()
