# AST REPO MAP
SYSTEM INSTRUCTIONS:
1. LOGIC OMITTED: Functions are NOT empty. Implementations are abstracted for context efficiency.
2. READ/WRITE PROTOCOL: To modify a function, you MUST ask the user to provide the specific file path first. Do NOT hallucinate modifications without the source file.
3. ARCHITECTURAL GROUNDING: Refer to `research-notes.md` for refactor history and `pitfalls.md` for known technical hurdles.
4. PRECISION: Use exact class, function, and file names from this map.

---

## DATABASE SCHEMA (`core/schema.sql`)
```sql
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
DROP TABLE IF EXISTS raw_pitches;

-- Table 1: players (Season-Aware)
CREATE TABLE IF NOT EXISTS players (
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
    home_team_runs INTEGER,
    away_team_runs INTEGER,
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
    closing_home_ml INTEGER,
    closing_away_ml INTEGER,
    opening_home_ml INTEGER,
    opening_away_ml INTEGER,
    home_rl REAL,
    away_rl REAL,
    rl_price_home INTEGER,
    rl_price_away INTEGER,
    closing_total REAL,
    opening_total REAL,
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

-- Table 9: raw_pitches (Statcast Training Data)
CREATE TABLE IF NOT EXISTS raw_pitches (
    pitch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitcher_id INTEGER,
    game_date TEXT,
    pitch_type TEXT,
    release_speed REAL,
    pfx_x REAL,
    pfx_z REAL,
    release_spin_rate REAL,
    release_extension REAL,
    vx0 REAL,
    vy0 REAL,
    vz0 REAL,
    ax REAL,
    ay REAL,
    az REAL,
    sz_top REAL,
    sz_bot REAL,
    plate_x REAL,
    plate_z REAL,
    description TEXT,
    whiff INTEGER
);

```

## PYTHON ARCHITECTURE
```python

# agent.py
class MLBAgent:
    def __init__(self, db_path): # Initializes the MLB Quant Agent with Dependency Injection for the database.
    def execute_sql(self, query) -> str: # Executes a read-only SQL query against the mlb_betting SQLite database.
    def get_live_schema(self) -> str: # Pulls the exact table structures directly from SQLite using the injected manager.
    def _get_config(self): # Builds the agent configuration with tools and dynamic system instruction.
    def run(self): # Starts the ReAct loop for the agent.
def prompt_agent(): # Entry point for the script.

# ingest_orchestrator.py
def run_daily_stats_ingestion(season): # Task 1: Heavy Stats & Environment
def run_odds_ingestion(): # Task 2: Odds & CLV Tracking
def start_scheduler():

# tools/lineup_analyzer.py
class LineupAnalyzer:
    def __init__(self):
    def get_todays_games(self): # Fetches today's game schedule and gamePks.
    def analyze_lineup(self, game_pk, team_type): # Fetches the starting lineup for a game and calculates weighted metrics.
    def run_daily_analysis(self): # Iterates through all today's games and prints the lineup strength.

# tools/experiment_logger.py
class QuantLogger:
    def __init__(self, db_path):
    def _init_db(self):
    def log_run(self, label, model_type, features, parameters, metrics, artifacts): # Logs a single experiment run.

# tools/value_finder.py
class ValueFinder:
    def __init__(self):
    def get_weighted_stat(self, player_id, stat_name): # Calculates a weighted average of 2025 (70%) and 2026 (30%) stats
    def find_value_today(self):

# tests/test_stats_calculator.py
def test_calculate_iso_scalar():
def test_calculate_iso_vectorized():
def test_calculate_iso_zero_ab_raises():
def test_calculate_k_minus_bb_percent_scalar():
def test_calculate_k_minus_bb_percent_zero_pa_raises():
def test_calculate_siera_scalar():
def test_calculate_siera_vectorized():
def test_calculate_siera_zero_pa_raises():
def test_calculate_siera_none_pa_raises():
def test_calculate_vaa_scalar():
def test_calculate_vaa_none_raises():
def test_calculate_break_magnitude():
def test_calculate_rolling_stuff_plus_logic():

# ml/preprocess.py
def load_and_preprocess_data(db_path): # Loads data from historical_training_data and prepares it for XGBoost.

# ml/train_xgboost.py
def train_baseline_xgboost(): # Trains an XGBoost binary classifier to predict home team win probability directly.

# ml/train_stuff_plus.py
def train_stuff_plus(): # Trains a pitch-level model to calculate Stuff+ (normalized whiff probability).

# ml/optimize.py
def optimize_xgboost(): # Performs Grid Search to find the best hyperparameters for the MLB binary classifier.

# ml/backtest_k_props.py
def american_to_decimal(american): # Converts American odds to Decimal odds.
def calculate_kelly(p, dec_odds, fraction): # Calculates Fractional Kelly Criterion bet size.
def run_k_prop_backtest(label): # Evaluates the strikeout model on 2025 data.

# ml/train_k_props.py
def load_k_prop_data(db_path): # Loads data for strikeout props, stacking home and away pitchers.
def train_k_props(label): # Trains an XGBRegressor to predict SP strikeout counts.

# ml/backtest.py
def run_2025_backtest(): # Simulates the 2025 season using the optimized XGBoost Binary Classifier

# core/db_builder.py
def build_database(): # Initializes/Updates the mlb_betting.db using the patch-based migration system.
def seed_team_mappings(conn): # Populates the team_mappings table with canonical MLB data.

# core/stats_calculator.py
def calculate_siera(so, bb, pa, gb, fb, pu): # Calculates Skill-Interactive Earned Run Average (SIERA).
def calculate_k_minus_bb_percent(so, bb, pa): # Calculates K-BB%.
def calculate_iso(ab, doubles, triples, hr): # Calculates Isolated Power (ISO).
def calculate_vaa(vy0, ay, vz0, az): # Calculates Vertical Approach Angle (VAA) at the plate (y=1.417 ft).
def calculate_break_magnitude(pfx_x, pfx_z): # Calculates the total movement magnitude (in inches).
def calculate_rolling_stuff_plus(pitch_values, window, prior_val, prior_weight): # Calculates the point-in-time rolling Stuff+ for a pitcher.

# core/db_manager.py
class MLBDbManager:
    def __init__(self, db_path):
    def _get_connection(self):
    def __enter__(self): # Enable 'with MLBDbManager() as manager:' for bulk transactions.
    def __exit__(self, exc_type, exc_val, exc_tb):
    def upsert_player_stats(self, data):
    def upsert_many_player_stats(self, data_list): # Optimized bulk upsert for player statistics.
    def upsert_hitting_lineup(self, data):
    def upsert_many_hitting_lineups(self, data_list):
    def upsert_bullpen(self, data):
    def upsert_many_bullpens(self, data_list):
    def upsert_betting_market(self, data): # Live prediction table with full ML feature set.
    def upsert_historical_training_data(self, data): # Historical training table - 1:1 mirror of live features + Target + Closing Lines.
    def upsert_sportsbook_odds(self, data): # Inserts or updates detailed odds for a specific sportsbook.
    def upsert_raw_pitch(self, data): # Inserts a raw Statcast pitch for training.
    def update_player_stuff_plus(self, player_id, season, stuff_plus): # Surgically update Stuff+ for a player/season.
    def update_pitch_stuff_plus(self, pitch_id, stuff_plus): # Update individual pitch-level Stuff+.
    def get_pitcher_prior_pitches(self, pitcher_id, game_date): # Fetches all Stuff+ values for a pitcher before a specific date.
    def resolve_team_id(self, name) -> int: # Translates a team name into the canonical mlb_id.
    def query_agent_data(self, sql_query):

# scripts/patch_strikeout_data.py
def fetch_and_update(game_id): # Fetches correct strikeout counts for a single game.
def patch_strikeouts():

# scripts/migrate.py
def run_migrations(): # Architects a safe, patch-based database migration system.

# scripts/patch_historical_stuff_plus.py
def patch_missing_stuff_plus():

# scripts/archive_daily_props.py
def archive_today_props(): # Fetches upcoming player props from The Odds API and archives them.

# scripts/ingest_historical.py
def ingest_2025_baseline(): # Automated ingestion of full 2025 season stats to provide a stable baseline.

# scripts/fetch_live_odds.py
def fetch_odds_api(): # Standalone utility to fetch live MLB odds (Moneyline, Run Line, Totals)

# scripts/generate_training_data.py
def clean_stat(val):
def fetch_player_logs_chunked(player_ids, season, group): # Fetches gameLog stats for a chunk of player IDs.
def get_rolling_feature_map(season):
def generate_rolling_stats(season):

# scripts/fetch_historical_k_lines.py
def fetch_events_for_date(date_str):
def fetch_k_lines_for_event(event_id, date_str):
def calculate_synthetic_line(sp_k_minus_bb, opp_lineup_k_pct): # Calculates a Vegas-style fair line based on rolling K metrics.
def patch_synthetic_lines(manager, date): # Fallback method to calculate fair synthetic lines for backtesting.
def update_k_lines():

# scripts/fetch_historical_odds.py
def fetch_sbr_odds_playwright(date_str):
def update_historical_odds(date_limit):

# scripts/patch_advanced_k_features.py
def calculate_park_k_factor(team_id, team_history): # Calculates a 1-year rolling Park K-Factor (Fangraphs method).
def run_patch():

# scripts/generate_repo_map.py
def format_function(node, indent): # Helper to format a function signature, return type, and brief docstring.
def parse_file(filepath): # Parses a Python file and returns its AST skeleton.
def generate_map(root_dir): # Walks the directory and builds the repo map.

# scripts/patch_historical_weather.py
def parse_wind(wind_str): # Parses wind string like '5 mph, Out To CF' into (speed, direction).
def patch_weather():

# scripts/ingest/environment.py
def calculate_density_altitude(temp_c, pressure_hpa): # Calculates Density Altitude in feet.
def patch_historical_weather(): # Fetches historical weather for all games in the DB using Open-Meteo.
def fetch_weather(matchups): # Fetches weather data for today's matchups using stadium coordinates.

# scripts/ingest/odds.py
def fetch_odds_espn(): # Fetches live MLB odds and probable pitchers from ESPN.

# scripts/ingest/mlb_official_stats.py
def ingest_mlb_official_stats(season): # Fetches raw stats and computes metrics for 2026.

# scripts/ingest/statcast.py
def log_progress(date_str):
def get_last_progress():
def ingest_production_statcast(): # Production-scale ingestion: 7-day chunks, parallelized, memory-safe.
```
