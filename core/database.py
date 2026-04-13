import sqlite3
import os

def build_database():
    """
    Initializes/Updates the mlb_betting.db with season-aware tables.
    Reads schema from schema.sql to ensure atomicity and separation of concerns.
    """
    db_name = "data/mlb_betting.db"
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        # Execute the script containing all DROP and CREATE statements
        cursor.executescript(schema_sql)
        conn.commit()
        
        # Seed canonical data
        seed_team_mappings(conn)
        
        print(f"Database schema refactored and built from {schema_path}.")
    except Exception as e:
        print(f"Error building database: {e}")
        conn.rollback()
    finally:
        conn.close()

def seed_team_mappings(conn):
    """Populates the team_mappings table with canonical MLB data."""
    teams = [
        (108, "Angels", "Los Angeles Angels", "Los Angeles Angels", "Angels", "LAA"),
        (109, "Diamondbacks", "Arizona Diamondbacks", "Arizona Diamondbacks", "Diamondbacks", "ARI"),
        (110, "Orioles", "Baltimore Orioles", "Baltimore Orioles", "Orioles", "BAL"),
        (111, "Red Sox", "Boston Red Sox", "Boston Red Sox", "Red Sox", "BOS"),
        (112, "Cubs", "Chicago Cubs", "Chicago Cubs", "Cubs", "CHC"),
        (113, "Reds", "Cincinnati Reds", "Cincinnati Reds", "Reds", "CIN"),
        (114, "Guardians", "Cleveland Guardians", "Cleveland Guardians", "Guardians", "CLE"),
        (115, "Rockies", "Colorado Rockies", "Colorado Rockies", "Rockies", "COL"),
        (116, "Tigers", "Detroit Tigers", "Detroit Tigers", "Tigers", "DET"),
        (117, "Astros", "Houston Astros", "Houston Astros", "Astros", "HOU"),
        (118, "Royals", "Kansas City Royals", "Kansas City Royals", "Royals", "KC"),
        (119, "Dodgers", "Los Angeles Dodgers", "Los Angeles Dodgers", "Dodgers", "LAD"),
        (120, "Nationals", "Washington Nationals", "Washington Nationals", "Nationals", "WSH"),
        (121, "Mets", "New York Mets", "New York Mets", "Mets", "NYM"),
        (133, "Athletics", "Oakland Athletics", "Oakland Athletics", "Athletics", "OAK"),
        (134, "Pirates", "Pittsburgh Pirates", "Pittsburgh Pirates", "Pirates", "PIT"),
        (135, "Padres", "San Diego Padres", "San Diego Padres", "Padres", "SD"),
        (136, "Mariners", "Seattle Mariners", "Seattle Mariners", "Mariners", "SEA"),
        (137, "Giants", "San Francisco Giants", "San Francisco Giants", "Giants", "SF"),
        (138, "Cardinals", "St. Louis Cardinals", "St. Louis Cardinals", "Cardinals", "STL"),
        (139, "Rays", "Tampa Bay Rays", "Tampa Bay Rays", "Rays", "TB"),
        (140, "Rangers", "Texas Rangers", "Texas Rangers", "Rangers", "TEX"),
        (141, "Blue Jays", "Toronto Blue Jays", "Toronto Blue Jays", "Blue Jays", "TOR"),
        (142, "Twins", "Minnesota Twins", "Minnesota Twins", "Twins", "MIN"),
        (143, "Phillies", "Philadelphia Phillies", "Philadelphia Phillies", "Phillies", "PHI"),
        (144, "Braves", "Atlanta Braves", "Atlanta Braves", "Braves", "ATL"),
        (145, "White Sox", "Chicago White Sox", "Chicago White Sox", "White Sox", "CHW"),
        (146, "Marlins", "Miami Marlins", "Miami Marlins", "Marlins", "MIA"),
        (147, "Yankees", "New York Yankees", "New York Yankees", "Yankees", "NYY"),
        (158, "Brewers", "Milwaukee Brewers", "Milwaukee Brewers", "Brewers", "MIL")
    ]
    
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO team_mappings 
        (mlb_id, team_name_short, team_full_name, odds_api_name, espn_name, fangraphs_abbr) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, teams)
    conn.commit()

if __name__ == "__main__":
    build_database()
