-- MLB Betting Database Schema
-- Last Updated: 2026-04-12

-- Drop existing tables to ensure schema migrations are applied correctly
DROP TABLE IF EXISTS starting_pitchers;
DROP TABLE IF EXISTS bullpens;
DROP TABLE IF EXISTS hitting_lineups;
DROP TABLE IF EXISTS betting_markets;
DROP TABLE IF EXISTS historical_training_data;
DROP TABLE IF EXISTS park_factors_and_weather;
DROP TABLE IF EXISTS sportsbook_odds;
DROP TABLE IF EXISTS team_mappings;

-- Table 1: starting_pitchers (Season-Aware)
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
);

-- Table 2: bullpens (Season-Aware)
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
);

-- Table 3: hitting_lineups (Season-Aware)
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
);

-- Table 4: park_factors_and_weather
CREATE TABLE IF NOT EXISTS park_factors_and_weather (
    game_id INTEGER PRIMARY KEY,
    home_team TEXT NOT NULL,
    stadium_name TEXT,
    park_factor_runs REAL,
    park_factor_hr REAL,
    temperature REAL,
    wind_speed_mph REAL,
    wind_direction TEXT
);

-- Table 5: betting_markets (Live Predictions - Mirrored with Training Data)
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
);

-- Table 8: historical_training_data (1:1 Mirror of betting_markets + Target)
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
);

-- Table 6: sportsbook_odds (Detailed multi-book data)
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
);

-- Table 7: team_mappings (The "Translator" Table)
CREATE TABLE IF NOT EXISTS team_mappings (
    mlb_id INTEGER PRIMARY KEY,
    team_name_short TEXT,
    team_full_name TEXT,
    odds_api_name TEXT,
    espn_name TEXT,
    fangraphs_abbr TEXT
);
