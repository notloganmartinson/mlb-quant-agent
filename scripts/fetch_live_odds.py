import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from core.db_manager import MLBDbManager

load_dotenv()

# The specific bookmakers we want to track for Line Shopping
TARGET_BOOKS = {
    'draftkings': 'DraftKings',
    'fanduel': 'FanDuel',
    'betmgm': 'BetMGM'
}

def fetch_odds_api():
    """
    Standalone utility to fetch live MLB odds (Moneyline, Run Line, Totals)
    from DraftKings, FanDuel, and BetMGM using The Odds API.
    """
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("Error: ODDS_API_KEY is missing from .env file.")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pinging The Odds API for live lines...")
    
    # Requesting h2h (moneyline), spreads (run line), and totals (over/under)
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": "draftkings,fanduel,betmgm"
    }
    
    manager = MLBDbManager()
    captured_count = 0

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            games = response.json()
            
            for game in games:
                # We generate a simple hash of the game ID to match our integer schema
                game_id_str = game.get('id', '')
                game_id = abs(hash(game_id_str)) % (10**8) 
                home_team_name = game['home_team']
                away_team_name = game['away_team']
                
                # Resolve IDs from mapping table
                home_id = manager.resolve_team_id(home_team_name)
                away_id = manager.resolve_team_id(away_team_name)
                
                for book in game.get('bookmakers', []):
                    book_key = book['key']
                    if book_key in TARGET_BOOKS:
                        book_name = TARGET_BOOKS[book_key]
                        
                        # Initialize default values
                        odds_data = {
                            "game_id": game_id,
                            "book_name": book_name,
                            "home_team_id": home_id,
                            "away_team_id": away_id,
                            "home_ml": None,
                            "away_ml": None,
                            "home_rl": None,
                            "away_rl": None,
                            "rl_price_home": None,
                            "rl_price_away": None,
                            "total": None,
                            "total_over_price": None,
                            "total_under_price": None,
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Parse the markets
                        for market in book.get('markets', []):
                            outcomes = market.get('outcomes', [])
                            
                            if market['key'] == 'h2h':
                                for o in outcomes:
                                    if o['name'] == home_team_name: odds_data['home_ml'] = o['price']
                                    elif o['name'] == away_team_name: odds_data['away_ml'] = o['price']
                                    
                            elif market['key'] == 'spreads':
                                for o in outcomes:
                                    if o['name'] == home_team_name: 
                                        odds_data['home_rl'] = o.get('point')
                                        odds_data['rl_price_home'] = o['price']
                                    elif o['name'] == away_team_name: 
                                        odds_data['away_rl'] = o.get('point')
                                        odds_data['rl_price_away'] = o['price']
                                        
                            elif market['key'] == 'totals':
                                for o in outcomes:
                                    odds_data['total'] = o.get('point') # Both over/under usually have same point
                                    if o['name'].lower() == 'over': odds_data['total_over_price'] = o['price']
                                    elif o['name'].lower() == 'under': odds_data['total_under_price'] = o['price']
                        
                        # Save to database
                        manager.upsert_sportsbook_odds(odds_data)
                        captured_count += 1
                        
            print(f"Successfully captured {captured_count} individual sportsbook lines.")
        else:
            print(f"API Error: Status {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Fetch error: {e}")

if __name__ == "__main__":
    fetch_odds_api()
