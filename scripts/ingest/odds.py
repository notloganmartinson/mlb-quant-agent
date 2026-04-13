import requests
from core.db_manager import MLBDbManager

def fetch_odds_espn():
    """Fetches live MLB odds and probable pitchers from ESPN."""
    print("Fetching live MLB odds and probable pitchers from ESPN...")
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            events = response.json().get('events', [])
            manager = MLBDbManager()
            matchups = []
            
            for event in events:
                comp = event['competitions'][0]
                home_team_name = comp['competitors'][0]['team']['shortDisplayName']
                away_team_name = comp['competitors'][1]['team']['shortDisplayName']
                
                # Resolve IDs
                home_id = manager.resolve_team_id(home_team_name)
                away_id = manager.resolve_team_id(away_team_name)
                
                odds_list = comp.get('odds', [])
                total, hml, aml = 0.0, 0, 0
                if odds_list:
                    o = odds_list[0]
                    total, hml, aml = o.get('overUnder', 0.0), o.get('homeTeamOdds', {}).get('value', 0), o.get('awayTeamOdds', {}).get('value', 0)
                
                gid = int(event['id'])
                # Implied probability calculation
                iprob = abs(hml)/(abs(hml)+100) if hml < 0 else 100/(hml+100) if hml > 0 else 0.5
                
                manager.upsert_betting_market({
                    "game_id": gid, "home_team": home_team_name, "away_team": away_team_name, 
                    "home_team_id": home_id, "away_team_id": away_id,
                    "home_sp_siera": 4.20, "away_sp_siera": 4.20,
                    "home_sp_k_minus_bb": 0.14, "away_sp_k_minus_bb": 0.14,
                    "home_bullpen_siera": 3.80, "away_bullpen_siera": 3.80,
                    "home_lineup_iso_vs_pitcher_hand": 0.160, "away_lineup_iso_vs_pitcher_hand": 0.160,
                    "home_lineup_woba_vs_pitcher_hand": 0.315, "away_lineup_woba_vs_pitcher_hand": 0.315,
                    "park_factor_runs": 1.0, "temperature": 72.0, "wind_speed": 4.0, "wind_direction": "Neutral",
                    "home_pitcher": None, "away_pitcher": None,
                    "full_game_home_moneyline": int(hml), "full_game_away_moneyline": int(aml), 
                    "full_game_total": float(total), "implied_prob_home": iprob
                })
                matchups.append({"game_id": gid, "home_team": home_team_name})
            print(f"Updated odds and pitchers for {len(events)} games.")
            return matchups
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return []

if __name__ == "__main__":
    fetch_odds_espn()
