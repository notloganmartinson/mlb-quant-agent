import pandas as pd
import joblib
import matplotlib.pyplot as plt
import sqlite3
import os
import sys
import numpy as np
from scipy.stats import skellam

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def run_2025_backtest():
    """
    Simulates the 2025 season using the optimized XGBoost model 
    and calculates P&L using the Kelly Criterion.
    """
    print("Starting 2025 Historical Backtest...")
    
    # 1. Load Data & Model
    X_train, X_test, y_train, y_test, context_test = load_and_preprocess_data()
    model_path = "models/xgboost_optimized.joblib"
    calib_path = "models/calibration_model.joblib"
    if not os.path.exists(model_path) or not os.path.exists(calib_path):
        print(f"Error: Models not found at {model_path} or {calib_path}. Run ml/train_xgboost.py first.")
        return
    model = joblib.load(model_path)
    iso_reg = joblib.load(calib_path)

    # 2. Get Predicted Probabilities (p)
    y_test_pred = model.predict(X_test)
    test_prob_win_raw = skellam.sf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_prob_tie_raw = skellam.pmf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    
    # Skellam Correction: Account for ties
    test_win_prob_raw = (test_prob_win_raw / (1 - test_prob_tie_raw)).reshape(-1, 1)
    probs = iso_reg.predict_proba(test_win_prob_raw)[:, 1]
    
    # 3. Create results dataframe
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)
    results_df = pd.DataFrame({
        'game_id': context_test['game_id'],
        'home_p': probs,
        'actual_win': y_test_won, # 1 if home won, 0 if away won
        'home_ml': context_test['closing_home_moneyline'],
        'home_lineup_pa': X_test['home_lineup_pa']
    })

    # Drop games with missing market data
    initial_count = len(results_df)
    results_df = results_df.dropna(subset=['home_ml'])
    results_df = results_df[results_df['home_ml'] != 0]
    dropped = initial_count - len(results_df)
    if dropped > 0:
        print(f"  [!] Flag: Dropped {dropped} games due to missing market data.")

    # 4. Convert American to Decimal Odds
    def am_to_dec(ml):
        if ml > 0: return (ml / 100) + 1
        else: return (100 / abs(ml)) + 1
    
    results_df['home_dec'] = results_df['home_ml'].apply(am_to_dec)

    # 5. Kelly Criterion Logic with Variance Adjustment (LCF)
    fractional_kelly = 0.25
    
    results_df['home_kelly'] = ((results_df['home_dec'] - 1) * results_df['home_p'] - (1 - results_df['home_p'])) / (results_df['home_dec'] - 1)
    results_df['home_edge'] = (results_df['home_p'] * results_df['home_dec']) - 1
    
    # Lineup Confidence Factor (LCF): Scale stake based on cumulative PA (Stabilization at 250 PA)
    results_df['lcf'] = (results_df['home_lineup_pa'] / 250.0).clip(upper=1.0)
    
    # Decide which side to bet (Home Only with Dynamic EV Thresholding)
    def determine_bet(row):
        vegas_implied = 1 / row['home_dec']
        if vegas_implied >= 0.40:
            ev_threshold = 0.05 # 5% for Slight Underdogs and Favorites
        else:
            ev_threshold = 0.08 # 8% for Heavy Underdogs (protecting from noise)
            
        if row['home_edge'] > ev_threshold:
            # Apply LCF to the fractional stake
            final_stake = max(0, row['home_kelly']) * fractional_kelly * row['lcf']
            return 'HOME', final_stake
        return 'NONE', 0.0

    bets = results_df.apply(determine_bet, axis=1, result_type='expand')
    results_df['side_bet'], results_df['stake_pct'] = bets[0], bets[1]
    
    # 6. Calculate P&L
    results_df['profit'] = np.where(
        results_df['side_bet'] == 'HOME',
        np.where(results_df['actual_win'] == 1, results_df['stake_pct'] * (results_df['home_dec'] - 1), -results_df['stake_pct']),
        0.0
    )
    results_df['cumulative_pnl'] = results_df['profit'].cumsum()

    # 7. Metrics
    total_profit = results_df['profit'].sum()
    roi = (total_profit / results_df['stake_pct'].sum()) if results_df['stake_pct'].sum() > 0 else 0
    total_bets = len(results_df[results_df['side_bet'] != 'NONE'])
    bets_won = len(results_df[(results_df['side_bet'] != 'NONE') & (results_df['profit'] > 0)])
    win_rate = (bets_won / total_bets) if total_bets > 0 else 0
    
    summary = f"""
2025 Backtest Summary (A/B Test: Stable Baseline + Dynamic EV Thresholding):
  -> Total Games Simulated: {len(results_df)}
  -> Total Bets Placed: {total_bets}
  -> Total Bets Won: {bets_won}
  -> Win Rate: {win_rate:.2%}
  -> Total Profit (Units): {total_profit:.2f}
  -> Simulated ROI: {roi:.2%}
"""
    print(summary)

    # 8. Plot P&L Graph & Export Summary
    os.makedirs("reports", exist_ok=True)
    with open("reports/backtest_2025_summary.txt", "w") as f:
        f.write(summary)
    
    plt.figure(figsize=(10, 6))
    plt.plot(results_df['cumulative_pnl'], label='Cumulative P&L (Kelly 0.25)')
    plt.title('2025 MLB Model Backtest (Proprietary Features)')
    plt.xlabel('Game Number')
    plt.ylabel('Units')
    plt.grid(True)
    plt.legend()
    
    os.makedirs("reports", exist_ok=True)
    plt.savefig("reports/backtest_2025.png")
    print("\nP&L Graph saved to reports/backtest_2025.png")

if __name__ == "__main__":
    run_2025_backtest()
