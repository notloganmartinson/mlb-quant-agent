import os
import requests
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from core.db_manager import MLBDbManager

load_dotenv()
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

def archive_today_props():
    """
    Fetches upcoming player props from The Odds API and archives them.
    Builds a proprietary historical dataset over time for free.
    """
    if not ODDS_API_KEY:
        print("Error: ODDS_API_KEY not found in .env")
        return

    print(f"Archiving MLB Player Props for {datetime.now().strftime('%Y-%m-%d')}...")
    
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'pitcher_strikeouts',
        'oddsFormat': 'american'
    }
    
    try:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            print(f"Odds API Error: {resp.status_code}")
            return
            
        events = resp.json()
        manager = MLBDbManager()
        game_date = datetime.now().strftime('%Y-%m-%d')
        
        archived_count = 0
        for event in events:
            home_team = event.get('home_team')
            away_team = event.get('away_team')
            
            for bookmaker in event.get('bookmakers', []):
                source = bookmaker.get('key')
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'pitcher_strikeouts':
                        for outcome in market.get('outcomes', []):
                            pitcher_name = outcome.get('description')
                            line = outcome.get('point')
                            price = outcome.get('price')
                            bet_name = outcome.get('name') # 'Over' or 'Under'
                            
                            # We need to group Over/Under for the same pitcher into one row or handle separately
                            # For simplicity, we'll UPSERT and update the specific column
                            
                            sql = """
                                INSERT INTO historical_prop_archive 
                                (player_name, game_date, market_key, source, line)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(player_name, game_date, market_key, source) 
                                DO UPDATE SET line=excluded.line
                            """
                            
                            col_to_update = "odds_over" if bet_name.lower() == 'over' else "odds_under"
                            update_sql = f"UPDATE historical_prop_archive SET {col_to_update} = ? WHERE player_name = ? AND game_date = ? AND market_key = ? AND source = ?"
                            
                            with manager._get_connection() as conn:
                                conn.execute(sql, (pitcher_name, game_date, 'pitcher_strikeouts', source, line))
                                conn.execute(update_sql, (price, pitcher_name, game_date, 'pitcher_strikeouts', source))
                            archived_count += 1
                            
        print(f"Successfully archived {archived_count} prop outcomes.")
        
    except Exception as e:
        print(f"Error archiving props: {e}")

if __name__ == "__main__":
    archive_today_props()
