import pandas as pd
import joblib
import matplotlib.pyplot as plt
import sqlite3
import os
import sys
import numpy as np

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def run_2025_backtest():
    """
    Simulates the 2025 season using the optimized XGBoost Binary Classifier
    and calculates P&L using the Kelly Criterion.
    """
    print("Starting 2025 Historical Backtest (Binary Classifier)...")
    
    # 1. Load Data & Model
    X_train, X_test, y_train, y_test, context_test = load_and_preprocess_data()
    model_path = "models/xgboost_baseline.joblib"
    calib_path = "models/calibration_model.joblib"
    calib_away_path = "models/calibration_model_away.joblib"
    
    if not all(os.path.exists(p) for p in [model_path, calib_path, calib_away_path]):
        print(f"Error: Models not found. Run ml/train_xgboost.py first.")
        return
        
    model = joblib.load(model_path)
    iso_reg = joblib.load(calib_path)
    iso_reg_away = joblib.load(calib_away_path)

    # 2. Get Predicted Probabilities (p)
    raw_probs = model.predict_proba(X_test)[:, 1]
    
    # Dual Isotonic Calibration
    home_probs = iso_reg.predict(raw_probs)
    away_probs = iso_reg_away.predict(1.0 - raw_probs)
    
    # 3. Create results dataframe
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)
    results_df = pd.DataFrame({
        'game_id': context_test['game_id'],
        'home_p': home_probs,
        'away_p': away_probs,
        'actual_win': y_test_won, # 1 if home won, 0 if away won
        'home_ml': context_test['closing_home_moneyline'],
        'away_ml': context_test['closing_away_moneyline'],
        'home_lineup_pa': X_test['home_lineup_pa']
    })

    # Drop games with missing market data
    initial_count = len(results_df)
    results_df = results_df.dropna(subset=['home_ml', 'away_ml'])
    results_df = results_df[(results_df['home_ml'] != 0) & (results_df['away_ml'] != 0)]
    dropped = initial_count - len(results_df)
    if dropped > 0:
        print(f"  [!] Flag: Dropped {dropped} games due to missing market data.")

    # 4. Convert American to Decimal Odds
    def am_to_dec(ml):
        if ml > 0: return (ml / 100) + 1
        else: return (100 / abs(ml)) + 1
    
    results_df['home_dec'] = results_df['home_ml'].apply(am_to_dec)
    results_df['away_dec'] = results_df['away_ml'].apply(am_to_dec)

    # 5. Kelly Criterion Logic with Variance Adjustment (LCF)
    fractional_kelly = 0.25
    
    results_df['home_kelly'] = ((results_df['home_dec'] - 1) * results_df['home_p'] - (1 - results_df['home_p'])) / (results_df['home_dec'] - 1)
    results_df['home_edge'] = (results_df['home_p'] * results_df['home_dec']) - 1

    results_df['away_kelly'] = ((results_df['away_dec'] - 1) * results_df['away_p'] - (1 - results_df['away_p'])) / (results_df['away_dec'] - 1)
    results_df['away_edge'] = (results_df['away_p'] * results_df['away_dec']) - 1
    
    # Lineup Confidence Factor (LCF): Scale stake based on cumulative PA (Stabilization at 250 PA)
    results_df['lcf'] = (results_df['home_lineup_pa'] / 250.0).clip(upper=1.0)
    
    # Decide which side to bet (Both Sides with Dynamic EV Thresholding)
    def determine_bet(row):
        home_implied = 1 / row['home_dec']
        away_implied = 1 / row['away_dec']
        
        home_ev_threshold = 0.05 if home_implied >= 0.40 else 0.08
        away_ev_threshold = 0.05 if away_implied >= 0.40 else 0.08
        
        home_valid = row['home_edge'] > home_ev_threshold
        away_valid = row['away_edge'] > away_ev_threshold
        
        if home_valid and away_valid:
            if row['home_edge'] > row['away_edge']:
                return 'HOME', max(0, row['home_kelly']) * fractional_kelly * row['lcf']
            else:
                return 'AWAY', max(0, row['away_kelly']) * fractional_kelly * row['lcf']
        elif home_valid:
            return 'HOME', max(0, row['home_kelly']) * fractional_kelly * row['lcf']
        elif away_valid:
            return 'AWAY', max(0, row['away_kelly']) * fractional_kelly * row['lcf']
            
        return 'NONE', 0.0

    bets = results_df.apply(determine_bet, axis=1, result_type='expand')
    results_df['side_bet'], results_df['stake_pct'] = bets[0], bets[1]
    
    # 6. Calculate P&L
    results_df['profit'] = np.where(
        results_df['side_bet'] == 'HOME',
        np.where(results_df['actual_win'] == 1, results_df['stake_pct'] * (results_df['home_dec'] - 1), -results_df['stake_pct']),
        np.where(
            results_df['side_bet'] == 'AWAY',
            np.where(results_df['actual_win'] == 0, results_df['stake_pct'] * (results_df['away_dec'] - 1), -results_df['stake_pct']),
            0.0
        )
    )
    results_df['cumulative_pnl'] = results_df['profit'].cumsum()

    # 7. Metrics
    total_profit = results_df['profit'].sum()
    roi = (total_profit / results_df['stake_pct'].sum()) if results_df['stake_pct'].sum() > 0 else 0
    total_bets = len(results_df[results_df['side_bet'] != 'NONE'])
    bets_won = len(results_df[(results_df['side_bet'] != 'NONE') & (results_df['profit'] > 0)])
    win_rate = (bets_won / total_bets) if total_bets > 0 else 0

    def calc_side_metrics(side):
        side_df = results_df[results_df['side_bet'] == side]
        count = len(side_df)
        if count == 0: return 0, 0, 0, 0, 0
        wins = len(side_df[side_df['profit'] > 0])
        wr = wins / count
        prof = side_df['profit'].sum()
        side_roi = (prof / side_df['stake_pct'].sum()) if side_df['stake_pct'].sum() > 0 else 0
        return count, wins, wr, prof, side_roi

    h_bets, h_wins, h_win_rate, h_profit, h_roi = calc_side_metrics('HOME')
    a_bets, a_wins, a_win_rate, a_profit, a_roi = calc_side_metrics('AWAY')
    
    summary = f"""
2025 Backtest Summary (Binary Classifier + Dual Calibration):
  -> Total Games Simulated: {len(results_df)}
  -> Total Bets Placed: {total_bets}
  -> Total Bets Won: {bets_won}
  -> Win Rate: {win_rate:.2%}
  -> Total Profit (Units): {total_profit:.2f}
  -> Simulated ROI: {roi:.2%}

--- HOME Splits ---
  -> Bets Placed: {h_bets}
  -> Bets Won: {h_wins}
  -> Win Rate: {h_win_rate:.2%}
  -> Profit: {h_profit:.2f} Units
  -> ROI: {h_roi:.2%}

--- AWAY Splits ---
  -> Bets Placed: {a_bets}
  -> Bets Won: {a_wins}
  -> Win Rate: {a_win_rate:.2%}
  -> Profit: {a_profit:.2f} Units
  -> ROI: {a_roi:.2%}
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