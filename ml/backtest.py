import pandas as pd
import xgboost as xgb
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
    Simulates the 2025 season using the optimized XGBoost model 
    and calculates P&L using the Kelly Criterion.
    """
    print("Starting 2025 Historical Backtest...")
    
    # 1. Load Data & Model
    X_train, X_test, y_train, y_test = load_and_preprocess_data()
    model = xgb.XGBClassifier()
    model.load_model("models/xgboost_optimized.json")

    # 2. Get Predicted Probabilities (p)
    probs = model.predict_proba(X_test)[:, 1]
    
    # 3. Load Market Data (Closing Lines)
    # Since DB might be NULL, we simulate a 'Vegas Price' for research if missing
    # In a real run, this would pull directly from the DB.
    conn = sqlite3.connect("data/mlb_betting.db")
    df_market = pd.read_sql_query("SELECT game_id, closing_home_moneyline FROM historical_training_data WHERE game_date >= '2025-01-01'", conn)
    conn.close()

    results_df = pd.DataFrame({
        'our_p': probs,
        'actual_win': y_test.values,
        'vegas_ml': df_market['closing_home_moneyline']
    })

    # Fill missing market data with a standard -110 (1.91) for the simulation proof
    results_df['vegas_ml'] = results_df['vegas_ml'].fillna(-110)

    # 4. Convert American to Decimal Odds
    def am_to_dec(ml):
        if ml > 0: return (ml / 100) + 1
        else: return (100 / abs(ml)) + 1
    
    results_df['decimal_odds'] = results_df['vegas_ml'].apply(am_to_dec)

    # 5. Kelly Criterion Logic
    # Stake = (bp - q) / b  where b is net odds, p is prob, q is (1-p)
    # Fractional Kelly (0.25) is safer for sports
    fractional_kelly = 0.25
    
    results_df['kelly_stake'] = ((results_df['decimal_odds'] - 1) * results_df['our_p'] - (1 - results_df['our_p'])) / (results_df['decimal_odds'] - 1)
    
    # Only bet if edge is positive
    results_df['stake_pct'] = results_df['kelly_stake'].apply(lambda x: max(0, x) * fractional_kelly)
    
    # 6. Calculate P&L
    # Profit = stake * (decimal_odds - 1) if win, else -stake
    results_df['profit'] = np.where(
        results_df['actual_win'] == 1,
        results_df['stake_pct'] * (results_df['decimal_odds'] - 1),
        -results_df['stake_pct']
    )
    
    results_df['cumulative_pnl'] = results_df['profit'].cumsum()

    # 7. Metrics
    total_profit = results_df['profit'].sum()
    roi = (total_profit / results_df['stake_pct'].sum()) if results_df['stake_pct'].sum() > 0 else 0
    
    print("\n2025 Backtest Summary:")
    print(f"  -> Total Games Simulated: {len(results_df)}")
    print(f"  -> Total Profit (Units): {total_profit:.2f}")
    print(f"  -> Simulated ROI: {roi:.2%}")

    # 8. Plot P&L Graph
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
