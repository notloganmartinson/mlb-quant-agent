import pandas as pd
import sqlite3
import os
import sys
import xgboost as xgb
import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

import argparse
from tools.experiment_logger import logger

# Ensure project root is in path for imports
sys.path.append(os.getcwd())

def load_k_prop_data(db_path="data/mlb_betting.db"):
    """
    Loads data for strikeout props, stacking home and away pitchers.
    Implements a strict time-series split (2022-2024 train, 2025 test).
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM historical_training_data", conn)
    conn.close()

    # Features and Targets for both Home and Away
    # Features (X): sp_rolling_stuff, sp_k_minus_bb, opposing_lineup_k_pct, and park_factor_runs.
    
    # Home Pitcher Data
    home_features = pd.DataFrame({
        'sp_rolling_stuff': df['home_sp_rolling_stuff'],
        'sp_k_minus_bb': df['home_sp_k_minus_bb'],
        'opposing_lineup_k_pct': df['away_lineup_k_pct'],
        'park_factor_runs': df['park_factor_runs'],
        'park_factor_k': df['park_factor_k'],
        'umpire_k_pct': df['umpire_k_pct'],
        'bullpen_k_bb': df['home_bullpen_k_bb'],
        'game_date': df['game_date'],
        'strikeouts': df['home_sp_strikeouts']
    })
    
    # Away Pitcher Data
    away_features = pd.DataFrame({
        'sp_rolling_stuff': df['away_sp_rolling_stuff'],
        'sp_k_minus_bb': df['away_sp_k_minus_bb'],
        'opposing_lineup_k_pct': df['home_lineup_k_pct'],
        'park_factor_runs': df['park_factor_runs'],
        'park_factor_k': df['park_factor_k'],
        'umpire_k_pct': df['umpire_k_pct'],
        'bullpen_k_bb': df['away_bullpen_k_bb'],
        'game_date': df['game_date'],
        'strikeouts': df['away_sp_strikeouts']
    })
    
    # Stack them
    stacked_df = pd.concat([home_features, away_features], ignore_index=True)
    stacked_df['game_date'] = pd.to_datetime(stacked_df['game_date'])
    
    # Drop rows where target is missing (though our ingestion should prevent this)
    stacked_df = stacked_df.dropna(subset=['strikeouts'])
    
    # Split
    train_mask = (stacked_df['game_date'].dt.year >= 2022) & (stacked_df['game_date'].dt.year <= 2024)
    test_mask = stacked_df['game_date'].dt.year == 2025
    
    train_df = stacked_df[train_mask]
    test_df = stacked_df[test_mask]
    
    features = ['sp_rolling_stuff', 'sp_k_minus_bb', 'opposing_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'bullpen_k_bb']
    
    X_train = train_df[features].apply(pd.to_numeric, errors='coerce')
    y_train = train_df['strikeouts'].apply(pd.to_numeric, errors='coerce')
    
    X_test = test_df[features].apply(pd.to_numeric, errors='coerce')
    y_test = test_df['strikeouts'].apply(pd.to_numeric, errors='coerce')
    
    # Median imputation based on training set
    x_median = X_train.median()
    X_train = X_train.fillna(x_median).fillna(0)
    X_test = X_test.fillna(x_median).fillna(0)
    
    return X_train, X_test, y_train, y_test

def train_k_props(label="Strikeout Baseline"):
    """
    Trains an XGBRegressor to predict SP strikeout counts.
    Uses count:poisson objective for count data.
    """
    print(f"Training Starting Pitcher Strikeout Model: {label}...")
    
    X_train, X_test, y_train, y_test = load_k_prop_data()
    
    if len(X_train) == 0:
        print("Error: No training data found. Have you run generate_training_data.py for 2022-2024?")
        return

    features = X_train.columns.tolist()
    params = {
        'n_estimators': 300,
        'max_depth': 4,
        'learning_rate': 0.05,
        'objective': 'count:poisson',
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }

    # 1. Initialize Model
    model = xgb.XGBRegressor(**params)

    # 2. Train Model
    model.fit(X_train, y_train)

    # 3. Evaluation
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    metrics = {
        'mae': round(float(mae), 4),
        'rmse': round(float(rmse), 4)
    }

    print("\nStrikeout Model Evaluation (2025 Holdout):")
    print(f"  -> Mean Absolute Error (MAE): {mae:.4f}")
    print(f"  -> Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"  -> Sample Predictions (Top 5):")
    for i in range(min(5, len(y_test))):
        print(f"     Actual: {y_test.iloc[i]} | Predicted: {y_pred[i]:.2f}")

    # 4. Save Model
    model_path = "models/xgboost_k_props.joblib"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    # 5. Log to Experiment Registry
    logger.log_run(
        label=label,
        model_type="XGBRegressor_K_Props",
        features=features,
        parameters=params,
        metrics=metrics,
        artifacts=[model_path]
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=str, default="Manual Training Run")
    args = parser.parse_args()
    
    train_k_props(label=args.label)
