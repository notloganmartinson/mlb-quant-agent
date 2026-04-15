import pandas as pd
import joblib
import sqlite3
import os
import sys
from datetime import datetime

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from core.db_manager import MLBDbManager

def predict_todays_games():
    """
    Loads the optimized XGBoost model and applies it to today's betting_markets.
    """
    print(f"--- LIVE ML PREDICTION ENGINE (April 12, 2026) ---")
    
    # 1. Load Models
    model_path = "models/xgboost_optimized.joblib"
    calib_path = "models/calibration_model.joblib"
    
    if not os.path.exists(model_path) or not os.path.exists(calib_path):
        print(f"Error: Models not found. Run ml/train_xgboost.py first.")
        return
    
    model = joblib.load(model_path)
    iso_reg = joblib.load(calib_path)

    # 2. Fetch Live Market Data
    manager = MLBDbManager()
    conn = sqlite3.connect("data/mlb_betting.db")
    df_live = pd.read_sql_query("SELECT * FROM betting_markets", conn)
    conn.close()

    if df_live.empty:
        print("No games found in betting_markets. Run scripts/ingest_daily.py first.")
        return

    # 3. Format Features (Must match Training Set exactly)
    features = [
        'home_sp_rolling_stuff', 'away_sp_rolling_stuff', 
        'home_sp_k_minus_bb', 'away_sp_k_minus_bb',
        'home_bullpen_siera', 'away_bullpen_siera',
        'home_lineup_iso_vs_pitcher_hand', 'away_lineup_iso_vs_pitcher_hand',
        'home_lineup_woba_vs_pitcher_hand', 'away_lineup_woba_vs_pitcher_hand',
        'park_factor_runs', 'temperature', 'wind_speed',
        'home_team_id', 'away_team_id'
    ]
    
    X_live = df_live[features].apply(pd.to_numeric, errors='coerce').fillna(0) # Basic fallback

    # 4. Generate Probabilities (p) using Poisson + Skellam
    from scipy.stats import skellam
    y_pred = model.predict(X_live)
    
    # Skellam Correction: Account for ties (impossible in MLB)
    prob_home_win_raw = skellam.sf(0, y_pred[:, 0], y_pred[:, 1])
    prob_tie_raw = skellam.pmf(0, y_pred[:, 0], y_pred[:, 1])
    probs_raw = prob_home_win_raw / (1 - prob_tie_raw)
    
    # Apply Calibration
    probs = iso_reg.transform(probs_raw)
    
    # 5. Kelly Calculation & Reporting
    print(f"{'Matchup':<40} | {'Vegas Prob':<10} | {'Our Prob':<10} | {'Kelly Stake'}")
    print("-" * 85)

    for i, row in df_live.iterrows():
        our_p = probs[i]
        vegas_p = row['implied_prob_home'] or 0.5
        
        # Convert American ML to Decimal for Kelly
        ml = row['full_game_home_moneyline'] or 0
        if ml > 0: b = (ml / 100)
        elif ml < 0: b = (100 / abs(ml))
        else: b = 0.91 # Default -110 if missing
        
        # Kelly Stake = (bp - q) / b
        if b > 0:
            kelly = (b * our_p - (1 - our_p)) / b
        else:
            kelly = 0
            
        stake_pct = max(0, kelly) * 0.25 # 1/4 Kelly for safety
        
        summary = f"{row['away_team']} @ {row['home_team']}"
        print(f"{summary:<40} | {vegas_p:<10.1%} | {our_p:<10.1%} | {stake_pct:.2%}")

if __name__ == "__main__":
    predict_todays_games()
