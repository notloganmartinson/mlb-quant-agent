import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from thefuzz import process
from core.db_manager import MLBDbManager
import statsapi

load_dotenv()
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

def fetch_events_for_date(date_str):
    # Historical events endpoint
    timestamp = f"{date_str}T12:00:00Z"
    url = f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'date': timestamp
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 401:
            return "401_UNAUTHORIZED" # Signal to use synthetic fallback
        if resp.status_code != 200:
            print(f"  [Odds API] Error fetching events for {date_str}: {resp.status_code} - {resp.text}")
            return []
        
        data = resp.json()
        return data.get('data', [])
    except Exception as e:
        print(f"  [Odds API] Exception fetching events for {date_str}: {e}")
        return []

def fetch_k_lines_for_event(event_id, date_str):
    timestamp = f"{date_str}T12:00:00Z"
    url = f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'pitcher_strikeouts',
        'date': timestamp,
        'oddsFormat': 'american'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return {}
            
        data = resp.json()
        lines = {}
        bookmakers = data.get('data', {}).get('bookmakers', [])
        for bookmaker in bookmakers:
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'pitcher_strikeouts':
                    for outcome in market.get('outcomes', []):
                        pitcher = outcome.get('description')
                        bet_type = outcome.get('name') # 'Over' or 'Under'
                        point = outcome.get('point')
                        price = outcome.get('price')
                        
                        if pitcher and point and price:
                            if pitcher not in lines:
                                lines[pitcher] = {'line': point}
                            lines[pitcher][f'odds_{bet_type.lower()}'] = price
        return lines
    except Exception as e:
        print(f"  [Odds API] Error fetching odds for event {event_id}: {e}")
        return {}

def calculate_synthetic_line(sp_k_minus_bb, opp_lineup_k_pct):
    """Calculates a Vegas-style fair line based on rolling K metrics."""
    if sp_k_minus_bb is None or opp_lineup_k_pct is None:
        return 4.5 # Default fallback
    
    # Estimate K% from K-BB% by adding league avg 8% walk rate
    k_pct = sp_k_minus_bb + 0.08
    # Normalize opponent K% against league average of 22%
    opp_mult = opp_lineup_k_pct / 0.22
    
    # Assume 23 batters faced (roughly 5.5 to 6 innings)
    exp_ks = 23 * k_pct * opp_mult
    
    # Snap to nearest 0.5
    line = round(exp_ks * 2) / 2
    if line % 1 == 0:
        line -= 0.5 # Ensure it's a .5 line to prevent pushes
    
    # Cap absurd lines
    return max(3.5, min(line, 8.5))

def patch_synthetic_lines(manager, date):
    """Fallback method to calculate fair synthetic lines for backtesting."""
    games_query = f"""
        SELECT game_id, home_sp_k_minus_bb, away_lineup_k_pct, 
               away_sp_k_minus_bb, home_lineup_k_pct
        FROM historical_training_data 
        WHERE game_date = '{date}'
    """
    games = manager.query_agent_data(games_query)
    updated_count = 0
    
    for g in games:
        h_line = calculate_synthetic_line(g['home_sp_k_minus_bb'], g['away_lineup_k_pct'])
        a_line = calculate_synthetic_line(g['away_sp_k_minus_bb'], g['home_lineup_k_pct'])
        
        # Standard Juice
        over_juice, under_juice = -115, -115
        
        sql = """
            UPDATE historical_training_data 
            SET home_sp_k_line = ?, home_sp_k_odds_over = ?, home_sp_k_odds_under = ?,
                away_sp_k_line = ?, away_sp_k_odds_over = ?, away_sp_k_odds_under = ?
            WHERE game_id = ?
        """
        with manager._get_connection() as conn:
            conn.execute(sql, (h_line, over_juice, under_juice, a_line, over_juice, under_juice, g['game_id']))
        updated_count += 1
        
    print(f"  -> {date}: Generated {updated_count} Synthetic K-Lines.")

def update_k_lines():
    manager = MLBDbManager()
    
    query = """
        SELECT DISTINCT game_date 
        FROM historical_training_data 
        WHERE home_sp_k_line IS NULL 
           OR home_sp_k_odds_over IS NULL 
        ORDER BY game_date DESC
    """
    dates = [row['game_date'] for row in manager.query_agent_data(query)]
    
    print(f"Attempting to fetch or synthesize K-lines for {len(dates)} dates...")
    
    for date in dates:
        print(f"Processing date: {date}")
        events = fetch_events_for_date(date)
        
        if events == "401_UNAUTHORIZED":
            print("  [Fallback] Odds API restricted (Free Tier). Using Synthetic Vegas Lines.")
            patch_synthetic_lines(manager, date)
            continue
            
        if not events:
            time.sleep(1)
            continue
            
        api_lines = {}
        for event in events:
            event_id = event['id']
            event_lines = fetch_k_lines_for_event(event_id, date)
            api_lines.update(event_lines)
            time.sleep(0.5)
            
        if not api_lines:
            continue
            
        games_query = f"""
            SELECT game_id, home_team_id, away_team_id 
            FROM historical_training_data 
            WHERE game_date = '{date}'
        """
        games = manager.query_agent_data(games_query)
        schedule = statsapi.schedule(date=date)
        
        updated_count = 0
        for g in games:
            match = next((s for s in schedule if s['game_id'] == g['game_id']), None)
            if not match: continue
            
            h_name = match.get('home_probable_pitcher')
            a_name = match.get('away_probable_pitcher')
            
            h_data, a_data = None, None
            
            if h_name:
                best_match, score = process.extractOne(h_name, list(api_lines.keys())) or (None, 0)
                if score > 85: h_data = api_lines[best_match]
            
            if a_name:
                best_match, score = process.extractOne(a_name, list(api_lines.keys())) or (None, 0)
                if score > 85: a_data = api_lines[best_match]
                
            if h_data or a_data:
                sql = """
                    UPDATE historical_training_data 
                    SET home_sp_k_line = ?, home_sp_k_odds_over = ?, home_sp_k_odds_under = ?,
                        away_sp_k_line = ?, away_sp_k_odds_over = ?, away_sp_k_odds_under = ?
                    WHERE game_id = ?
                """
                
                h_line = h_data.get('line') if h_data else None
                h_over = h_data.get('odds_over') if h_data else None
                h_under = h_data.get('odds_under') if h_data else None
                
                a_line = a_data.get('line') if a_data else None
                a_over = a_data.get('odds_over') if a_data else None
                a_under = a_data.get('odds_under') if a_data else None
                
                with manager._get_connection() as conn:
                    conn.execute(sql, (h_line, h_over, h_under, a_line, a_over, a_under, g['game_id']))
                updated_count += 1
        
        print(f"  -> {date}: Patched {updated_count} actual games.")
        time.sleep(1)

if __name__ == "__main__":
    update_k_lines()
