import requests
import time
from core.db_manager import MLBDbManager

# --- STADIUM MAPPING (LAT/LON) ---
# Values approximate for weather lookups
STADIUM_COORDS = {
    108: {"lat": 33.8003, "lon": -117.8827, "name": "Angel Stadium"},
    109: {"lat": 33.4455, "lon": -112.0667, "name": "Chase Field"},
    110: {"lat": 39.2841, "lon": -76.6215, "name": "Camden Yards"},
    111: {"lat": 42.3467, "lon": -71.0972, "name": "Fenway Park"},
    112: {"lat": 41.8299, "lon": -87.6339, "name": "Guaranteed Rate Field"},
    113: {"lat": 39.0975, "lon": -84.5071, "name": "Great American Ball Park"},
    114: {"lat": 41.4962, "lon": -81.6852, "name": "Progressive Field"},
    115: {"lat": 39.7559, "lon": -104.9942, "name": "Coors Field"},
    116: {"lat": 42.3390, "lon": -83.0485, "name": "Comerica Park"},
    117: {"lat": 29.7573, "lon": -95.3555, "name": "Minute Maid Park"},
    118: {"lat": 39.0517, "lon": -94.4803, "name": "Kauffman Stadium"},
    119: {"lat": 34.0739, "lon": -118.2400, "name": "Dodger Stadium"},
    120: {"lat": 38.8730, "lon": -77.0074, "name": "Nationals Park"},
    121: {"lat": 40.7571, "lon": -73.8458, "name": "Citi Field"},
    133: {"lat": 38.5833, "lon": -121.5167, "name": "Sutter Health Park"}, # Athletics 2026
    134: {"lat": 40.4469, "lon": -80.0057, "name": "PNC Park"},
    135: {"lat": 32.7076, "lon": -117.1570, "name": "Petco Park"},
    136: {"lat": 47.5914, "lon": -122.3323, "name": "T-Mobile Park"},
    137: {"lat": 37.7786, "lon": -122.3893, "name": "Oracle Park"},
    138: {"lat": 38.6226, "lon": -90.1928, "name": "Busch Stadium"},
    139: {"lat": 27.7682, "lon": -82.6534, "name": "Tropicana Field"},
    140: {"lat": 32.7513, "lon": -97.0827, "name": "Globe Life Field"},
    141: {"lat": 43.6414, "lon": -79.3894, "name": "Rogers Centre"},
    142: {"lat": 44.9817, "lon": -93.2778, "name": "Target Field"},
    143: {"lat": 39.9061, "lon": -75.1665, "name": "Citizens Bank Park"},
    144: {"lat": 33.8907, "lon": -84.4678, "name": "Truist Park"},
    145: {"lat": 41.9484, "lon": -87.6553, "name": "Wrigley Field"},
    146: {"lat": 25.7783, "lon": -80.2198, "name": "LoanDepot Park"},
    147: {"lat": 40.8296, "lon": -73.9262, "name": "Yankee Stadium"},
    158: {"lat": 43.0285, "lon": -87.9712, "name": "American Family Field"},
}

def calculate_density_altitude(temp_c, pressure_hpa):
    """
    Calculates Density Altitude in feet.
    temp_c: Temperature in Celsius
    pressure_hpa: Surface Pressure in hPa (millibars)
    """
    pressure_alt = (1 - (pressure_hpa / 1013.25)**0.190284) * 145366.45
    isa_temp = 15 - (0.0019812 * pressure_alt)
    density_alt = pressure_alt + (118.8 * (temp_c - isa_temp))
    return density_alt

def patch_historical_weather():
    """Fetches historical weather for all games in the DB using Open-Meteo."""
    manager = MLBDbManager()
    query = "SELECT game_id, game_date, home_team_id FROM historical_training_data WHERE density_altitude IS NULL ORDER BY game_date ASC, game_id ASC"
    games = manager.query_agent_data(query)
    
    total = len(games)
    print(f"Patching weather for {total} games...")
    
    for idx, g in enumerate(games):
        game_id = g['game_id']
        date = g['game_date']
        tid = g['home_team_id']
        coords = STADIUM_COORDS.get(tid)
        
        if not coords: continue
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": coords['lat'],
            "longitude": coords['lon'],
            "start_date": date,
            "end_date": date,
            "hourly": "temperature_2m,surface_pressure,wind_speed_10m,wind_direction_10m",
            "timezone": "auto" # Use auto timezone
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('hourly', {})
                if 'temperature_2m' in data and len(data['temperature_2m']) > 19:
                    temp = data['temperature_2m'][19]
                    press = data['surface_pressure'][19]
                    wind_speed = data['wind_speed_10m'][19]
                    wind_dir = data['wind_direction_10m'][19]
                    
                    da = calculate_density_altitude(temp, press)
                    
                    sql = """
                        UPDATE historical_training_data 
                        SET temperature = ?, wind_speed = ?, wind_direction = ?, density_altitude = ?
                        WHERE game_id = ?
                    """
                    with manager._get_connection() as conn:
                        conn.execute(sql, (temp * 1.8 + 32, wind_speed * 0.621371, str(wind_dir), da, game_id))
                else:
                    print(f"  [Warning] Incomplete weather data for game {game_id} on {date}")
            else:
                print(f"  [Error] API returned {resp.status_code} for game {game_id}")
                if resp.status_code == 429:
                    print("  [Rate Limit] Sleeping for 60 seconds...")
                    time.sleep(60)
            
            if (idx + 1) % 10 == 0: # Print every 10 games to see movement
                print(f"  [{idx+1}/{total}] Patched up to {date}")
                
            time.sleep(0.1) # Slightly slower to avoid rate limits
        except Exception as e:
            print(f"Error patching weather for game {game_id}: {e}")
            time.sleep(2)
            continue

def fetch_weather(matchups):
    """Fetches weather data for today's matchups using stadium coordinates."""
    print("Fetching weather data for matchups...")
    manager = MLBDbManager()
    for g in matchups:
        stadium = g['home_team']
        coords = STADIUM_COORDS.get(stadium)
        if coords:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=temperature_2m,wind_speed_10m,wind_direction_10m"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    w = response.json().get('current', {})
                    sql = "INSERT INTO park_factors_and_weather (game_id, home_team, stadium_name, temperature, wind_speed_mph, wind_direction) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(game_id) DO UPDATE SET temperature=excluded.temperature"
                    with manager._get_connection() as conn: 
                        conn.execute(sql, (
                            g['game_id'], stadium, f"{stadium} Stadium", 
                            w.get('temperature_2m'), w.get('wind_speed_10m'), 
                            str(w.get('wind_direction_10m'))
                        ))
            except Exception as e:
                print(f"Error fetching weather for {stadium}: {e}")
                continue
    print("Weather data ingestion complete.")

if __name__ == "__main__":
    pass
