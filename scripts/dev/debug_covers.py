import os
from playwright.sync_api import sync_playwright
def run():
    url = "https://www.covers.com/sport/baseball/mlb/props/pitcher-strikeouts?date=2024-06-01"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        try:
            print("Title:", page.title())
            html = page.content()
            print("K Props Table Found:", "pitcher-strikeouts" in html.lower())
            print("Line 5.5 found:", "5.5" in html)
        except Exception as e:
            print("Failed:", e)
        browser.close()
if __name__ == "__main__":
    run()
