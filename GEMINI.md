# AST REPO MAP
SYSTEM INSTRUCTIONS:
1. LOGIC OMITTED: Functions are NOT empty. Implementations are abstracted for context efficiency.
2. READ/WRITE PROTOCOL: To modify a function, you MUST ask the user to provide the specific file path first. Do NOT hallucinate modifications without the source file.
3. ARCHITECTURAL GROUNDING: Refer to `research-notes.md` for refactor history and `pitfalls.md` for known technical hurdles.
4. PRECISION: Use exact class, function, and file names from this map.

---

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
def run_daily_ingestion(season): # Orchestrates the daily data ingestion pipeline.

# tools/lineup_analyzer.py
class LineupAnalyzer:
    def __init__(self):
    def get_todays_games(self): # Fetches today's game schedule and gamePks.
    def analyze_lineup(self, game_pk, team_type): # Fetches the starting lineup for a game and calculates weighted metrics.
    def run_daily_analysis(self): # Iterates through all today's games and prints the lineup strength.

# tools/value_finder.py
class ValueFinder:
    def __init__(self):
    def get_weighted_stat(self, player_id, stat_name): # Calculates a weighted average of 2025 (70%) and 2026 (30%) stats
    def find_value_today(self):

# tools/predict_games.py
def predict_todays_games(): # Loads the optimized XGBoost model and applies it to today's betting_markets.

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
def train_baseline_xgboost(): # Trains an initial XGBoost model and establishes a baseline Log-Loss.

# ml/train_stuff_plus.py
def train_stuff_plus(): # Trains a pitch-level model to calculate Stuff+ (normalized whiff probability).

# ml/optimize.py
def optimize_xgboost(): # Performs Grid Search to find the best hyperparameters for the MLB model.

# ml/backtest.py
def run_2025_backtest(): # Simulates the 2025 season using the optimized XGBoost model

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

# scripts/migrate.py
def run_migrations(): # Architects a safe, patch-based database migration system.

# scripts/patch_historical_stuff_plus.py
def patch_missing_stuff_plus():

# scripts/ingest_historical.py
def ingest_2025_baseline(): # Automated ingestion of full 2025 season stats to provide a stable baseline.

# scripts/fetch_live_odds.py
def fetch_odds_api(): # Standalone utility to fetch live MLB odds (Moneyline, Run Line, Totals)

# scripts/generate_training_data.py
def clean_stat(val):
def fetch_team_logs(team_id, season, group):
def fetch_player_logs_chunked(player_ids, season): # Fetches gameLog stats for a chunk of player IDs.
def get_rolling_feature_map(season):
def generate_rolling_stats(season):

# scripts/fetch_historical_odds.py
def fetch_sbr_odds_playwright(date_str):
def update_historical_odds(date_limit):

# scripts/generate_repo_map.py
def format_function(node, indent): # Helper to format a function signature, return type, and brief docstring.
def parse_file(filepath): # Parses a Python file and returns its AST skeleton.
def generate_map(root_dir): # Walks the directory and builds the repo map.

# scripts/patch_historical_weather.py
def parse_wind(wind_str): # Parses wind string like '5 mph, Out To CF' into (speed, direction).
def patch_weather():

# scripts/archive/patch_2022_offline.py
def patch_missing_stuff_plus_sql_only():

# scripts/archive/patch_2022_stuff_plus.py
def patch_missing_stuff_plus():

# scripts/archive/patch_2022_memory.py
def patch_missing_stuff_plus_memory():

# scripts/archive/patch_2022_fast.py
def patch_missing_stuff_plus_fast():

# scripts/ingest/environment.py
def fetch_weather(matchups): # Fetches weather data for today's matchups using stadium coordinates.

# scripts/ingest/odds.py
def fetch_odds_espn(): # Fetches live MLB odds and probable pitchers from ESPN.

# scripts/ingest/mlb_official_stats.py
def ingest_mlb_official_stats(season): # Fetches raw stats and computes metrics for 2026.

# scripts/ingest/statcast.py
def log_progress(date_str):
def get_last_progress():
def ingest_production_statcast(): # Production-scale ingestion: 7-day chunks, parallelized, memory-safe.

# scripts/dev/validate_lineup.py
def get_iso_upto(player_id, date, season):
def validate():

# scripts/dev/debug_sbr.py
def debug_sbr_fetch(date_str):
```
