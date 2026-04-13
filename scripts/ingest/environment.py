import requests
from core.db_manager import MLBDbManager

# --- STADIUM MAPPING (LAT/LON) ---
STADIUM_COORDS = {
    "Yankees": {"lat": 40.8296, "lon": -73.9262},
    "Dodgers": {"lat": 34.0739, "lon": -118.2400},
    "Braves": {"lat": 33.8907, "lon": -84.4678},
    "Red Sox": {"lat": 42.3467, "lon": -71.0972},
    "Mets": {"lat": 40.7571, "lon": -73.8458},
    "Cubs": {"lat": 41.9484, "lon": -87.6553},
}

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
    # Example usage requires a list of matchups
    # fetch_weather([{"game_id": 123456, "home_team": "Yankees"}])
    pass
