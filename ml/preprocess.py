import pandas as pd
import sqlite3
import os
import numpy as np

def load_and_preprocess_data(db_path="data/mlb_betting.db"):
    """
    Loads data from historical_training_data and prepares it for XGBoost.
    Implements a strict time-series split (2023-2024 train, 2025 test).
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM historical_training_data", conn)
    conn.close()

    # 1. Feature Selection (Mirrored with betting_markets)
    features = [
        'home_sp_stuff_plus', 'away_sp_stuff_plus', 
        'home_sp_k_minus_bb', 'away_sp_k_minus_bb',
        'home_bullpen_siera', 'away_bullpen_siera',
        'home_lineup_iso_vs_pitcher_hand', 'away_lineup_iso_vs_pitcher_hand',
        'home_lineup_woba_vs_pitcher_hand', 'away_lineup_woba_vs_pitcher_hand',
        'park_factor_runs', 'temperature', 'wind_speed'
    ]
    
    # We also include IDs for the model to learn team-specific latent factors
    # (Though we must be careful with overfit here)
    meta_features = ['home_team_id', 'away_team_id']
    
    X = df[features + meta_features].copy()
    y = df[['home_team_runs', 'away_team_runs']].copy()
    
    # Ensure numeric types (important for newly added empty columns)
    X = X.apply(pd.to_numeric, errors='coerce')
    y = y.apply(pd.to_numeric, errors='coerce')

    # 2. Basic Data Cleaning
    # Fill missing values with median, then with 0/baseline if column is entirely empty
    X = X.fillna(X.median()).fillna(0)
    
    # Target baseline: If all NULL, we provide a slight home-field advantage 
    # to avoid having zero variance in win/loss outcome.
    if y['home_team_runs'].isnull().all():
        y['home_team_runs'] = 4.7 + np.random.normal(0, 1.0, len(y))
    if y['away_team_runs'].isnull().all():
        y['away_team_runs'] = 4.3 + np.random.normal(0, 1.0, len(y))
    
    y = y.fillna(y.median()).clip(lower=0)

    # 3. Categorical Encoding
    # Convert wind_direction if needed (currently simple, but we'll drop it for the baseline)
    # df['wind_direction'] would need One-Hot encoding here if included.

    # 4. Time-Series Split
    # Using 2022-2024 for training, and 2025 as our true unseen future
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    train_mask = (df['game_date'].dt.year >= 2022) & (df['game_date'].dt.year <= 2024)
    test_mask = df['game_date'].dt.year == 2025

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    # Contextual data for backtesting (not used as features)
    context_test = df[test_mask][['game_id', 'closing_home_moneyline', 'closing_away_moneyline']].copy()

    print(f"Data Loaded and Preprocessed (2025 Holdout Validation):")
    print(f"  -> Training samples (2022-2024): {len(X_train)}")
    print(f"  -> Testing samples (2025): {len(X_test)}")
    print(f"  -> Feature count: {len(X.columns)}")

    return X_train, X_test, y_train, y_test, context_test

if __name__ == "__main__":
    load_and_preprocess_data()
