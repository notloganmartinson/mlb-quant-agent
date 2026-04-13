import sqlite3

def build_database():
    """
    Initializes/Updates the mlb_betting.db with season-aware tables.
    """
    db_name = "data/mlb_betting.db"
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Drop existing tables to ensure schema migrations are applied correctly
    cursor.execute("DROP TABLE IF EXISTS starting_pitchers")
    cursor.execute("DROP TABLE IF EXISTS bullpens")
    cursor.execute("DROP TABLE IF EXISTS hitting_lineups")
    cursor.execute("DROP TABLE IF EXISTS betting_markets")
    cursor.execute("DROP TABLE IF EXISTS historical_training_data")
    cursor.execute("DROP TABLE IF EXISTS park_factors_and_weather")
    cursor.execute("DROP TABLE IF EXISTS sportsbook_odds")
    cursor.execute("DROP TABLE IF EXISTS team_mappings")

    # Table 1: starting_pitchers (Season-Aware)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS starting_pitchers (
            player_id INTEGER,
            season INTEGER,
            name TEXT NOT NULL,
            date_updated TEXT,
            stuff_plus REAL,
            location_plus REAL,
            pitching_plus REAL,
            xfip REAL,
            siera REAL,
            era REAL,
            k_minus_bb_percent REAL,
            iso REAL,
            k_pct REAL,
            PRIMARY KEY (player_id, season)
        )
    """)

    # Table 2: bullpens (Season-Aware)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bullpens (
            team_id INTEGER,
            season INTEGER,
            team_name TEXT NOT NULL,
            date_updated TEXT,
            bullpen_xfip REAL,
            bullpen_siera REAL,
            top_relievers_rest_days INTEGER,
            total_pitches_last_3_days INTEGER,
            PRIMARY KEY (team_id, season)
        )
    """)

    # Table 3: hitting_lineups (Season-Aware)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hitting_lineups (
            team_id INTEGER,
            season INTEGER,
            team_name TEXT NOT NULL,
            date_updated TEXT,
            iso_vs_rhp REAL,
            iso_vs_lhp REAL,
            woba REAL,
            iso REAL,
            k_percent REAL,
            PRIMARY KEY (team_id, season)
        )
    """)

    # Table 4: park_factors_and_weather
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS park_factors_and_weather (
            game_id INTEGER PRIMARY KEY,
            home_team TEXT NOT NULL,
            stadium_name TEXT,
            park_factor_runs REAL,
            park_factor_hr REAL,
            temperature REAL,
            wind_speed_mph REAL,
            wind_direction TEXT
        )
    """)

    # Table 5: betting_markets (Live Predictions - Mirrored with Training Data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betting_markets (
            game_id INTEGER PRIMARY KEY,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_pitcher TEXT,
            away_pitcher TEXT,
            -- Pitching Features
            home_sp_siera REAL,
            away_sp_siera REAL,
            home_sp_k_minus_bb REAL,
            away_sp_k_minus_bb REAL,
            home_bullpen_siera REAL,
            away_bullpen_siera REAL,
            -- Hitting Features
            home_lineup_iso_vs_pitcher_hand REAL,
            away_lineup_iso_vs_pitcher_hand REAL,
            home_lineup_woba_vs_pitcher_hand REAL,
            away_lineup_woba_vs_pitcher_hand REAL,
            -- Environment & Park
            park_factor_runs REAL,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            -- Market Data
            full_game_home_moneyline INTEGER,
            full_game_away_moneyline INTEGER,
            full_game_total REAL,
            implied_prob_home REAL
        )
    """)

    # Table 8: historical_training_data (1:1 Mirror of betting_markets + Target)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_training_data (
            game_id INTEGER PRIMARY KEY,
            game_date TEXT,
            home_team_id INTEGER,
            away_team_id INTEGER,
            -- THE TARGET
            home_team_won INTEGER, 
            -- Pitching Features
            home_sp_siera REAL,
            away_sp_siera REAL,
            home_sp_k_minus_bb REAL,
            away_sp_k_minus_bb REAL,
            home_bullpen_siera REAL,
            away_bullpen_siera REAL,
            -- Hitting Features
            home_lineup_iso_vs_pitcher_hand REAL,
            away_lineup_iso_vs_pitcher_hand REAL,
            home_lineup_woba_vs_pitcher_hand REAL,
            away_lineup_woba_vs_pitcher_hand REAL,
            -- Environment & Park
            park_factor_runs REAL,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            -- Market/Baseline
            closing_home_moneyline INTEGER,
            closing_away_moneyline INTEGER,
            closing_total REAL
        )
    """)

    # Table 6: sportsbook_odds (Detailed multi-book data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sportsbook_odds (
            game_id INTEGER,
            book_name TEXT NOT NULL,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_ml INTEGER,
            away_ml INTEGER,
            home_rl REAL,
            away_rl REAL,
            rl_price_home INTEGER,
            rl_price_away INTEGER,
            total REAL,
            total_over_price INTEGER,
            total_under_price INTEGER,
            last_updated TEXT,
            PRIMARY KEY (game_id, book_name)
        )
    """)

    # Table 7: team_mappings (The "Translator" Table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_mappings (
            mlb_id INTEGER PRIMARY KEY,
            team_name_short TEXT,
            team_full_name TEXT,
            odds_api_name TEXT,
            espn_name TEXT,
            fangraphs_abbr TEXT
        )
    """)

    conn.commit()
    seed_team_mappings(conn)
    conn.close()
    print(f"Database schema refactored and perfectly mirrored.")

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
