import os
import sys
import pandas as pd
import numpy as np
import joblib
from psycopg2.extras import execute_batch

# Ensure project root is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db_manager import MLBDbManager

def predict_today():
    """
    Loads today's matchups from betting_markets, predicts the win probabilities
    using the calibrated XGBoost model, and updates the database.
    """
    print("--- Starting Daily Model Inference ---")
    
    manager = MLBDbManager()
    
    # 1. Fetch Today's Games
    query = "SELECT * FROM betting_markets"
    games = manager.query_agent_data(query)
    
    if not games:
        print("No games found in betting_markets. Inference skipped.")
        return
        
    df = pd.DataFrame(games)
    
    # 2. Features Required by Model (matching ml/preprocess.py)
    features = [
        'home_sp_rolling_stuff', 'away_sp_rolling_stuff', 
        'home_sp_k_minus_bb', 'away_sp_k_minus_bb',
        'home_bullpen_siera', 'away_bullpen_siera',
        'home_bullpen_k_bb', 'away_bullpen_k_bb',
        'home_lineup_iso_vs_pitcher_hand', 'away_lineup_iso_vs_pitcher_hand',
        'home_lineup_woba_vs_pitcher_hand', 'away_lineup_woba_vs_pitcher_hand',
        'home_lineup_pa', 'away_lineup_pa',
        'home_lineup_k_pct', 'away_lineup_k_pct',
        'park_factor_runs', 'park_factor_k', 'temperature', 'wind_speed', 'density_altitude',
        'umpire_k_pct', 'closing_total'
    ]
    meta_features = ['home_team_id', 'away_team_id']
    
    # Ensure all features exist in the dataframe, fill missing with 0
    for f in features + meta_features:
        if f not in df.columns:
            df[f] = 0.0
            
    X = df[features + meta_features].copy()
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # 3. Load Models
    model_path = os.path.join(os.path.dirname(__file__), "../models/xgboost_baseline.joblib")
    calib_path = os.path.join(os.path.dirname(__file__), "../models/calibration_model.joblib")
    calib_away_path = os.path.join(os.path.dirname(__file__), "../models/calibration_model_away.joblib")
    
    if not os.path.exists(model_path) or not os.path.exists(calib_path) or not os.path.exists(calib_away_path):
        print("Model files not found. Please train models first. Inference skipped.")
        return
        
    model = joblib.load(model_path)
    iso_reg = joblib.load(calib_path)
    iso_reg_away = joblib.load(calib_away_path)
    
    # 4. Predict
    # Raw probabilities
    raw_probs = model.predict_proba(X)[:, 1]
    raw_probs_away = 1.0 - raw_probs
    
    # Calibrate probabilities
    home_probs = iso_reg.predict(raw_probs)
    away_probs = iso_reg_away.predict(raw_probs_away)
    
    # Ensure probabilities are between 0 and 1
    home_probs = np.clip(home_probs, 0.0, 1.0)
    away_probs = np.clip(away_probs, 0.0, 1.0)
    
    # 5. Update Database
    updates = []
    for idx, row in df.iterrows():
        updates.append({
            'model_prob_home': float(home_probs[idx]),
            'model_prob_away': float(away_probs[idx]),
            'game_id': int(row['game_id'])
        })
        
    sql = """
        UPDATE betting_markets
        SET model_prob_home = %(model_prob_home)s,
            model_prob_away = %(model_prob_away)s
        WHERE game_id = %(game_id)s
    """
    
    conn = manager._get_connection()
    try:
        with conn.cursor() as cursor:
            execute_batch(cursor, sql, updates)
        if not manager._shared_conn:
            conn.commit()
    finally:
        if not manager._shared_conn:
            conn.close()
            
    print(f"Successfully updated predictions for {len(updates)} games in betting_markets.")

if __name__ == "__main__":
    predict_today()
