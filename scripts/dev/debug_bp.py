import json
from playwright.sync_api import sync_playwright

def run():
    url = "https://www.bettingpros.com/mlb/odds/player-props/strikeouts/?date=2024-06-01"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        try:
            data = page.evaluate("document.getElementById('__NEXT_DATA__').textContent")
            with open("bp_data.json", "w") as f:
                f.write(data)
            print("Saved bp_data.json")
        except Exception as e:
            print("Failed:", e)
        browser.close()

if __name__ == "__main__":
    run()
