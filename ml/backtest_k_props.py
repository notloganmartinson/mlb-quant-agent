import pandas as pd
import joblib
import numpy as np
import os
import json
from scipy.stats import poisson, nbinom
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import argparse
from tools.experiment_logger import logger
from core.db_manager import MLBDbManager

def american_to_decimal(american):
    """Converts American odds to Decimal odds."""
    if pd.isna(american):
        return 1.87 # Default to -115
    if american < 0:
        return 1 - (100 / american)
    else:
        return 1 + (american / 100)

def calculate_kelly(p, dec_odds, fraction=0.25):
    """Calculates Fractional Kelly Criterion bet size."""
    b = dec_odds - 1
    q = 1 - p
    k = (p * b - q) / b
    return max(0, k) * fraction

def run_k_prop_backtest(label="K-Prop Backtest"):
    """
    Evaluates the strikeout model on 2025 data.
    Simulates a betting bankroll using Negative Binomial CDF and Kelly Criterion.
    """
    model_path = "models/xgboost_k_props.joblib"
    config_path = "models/k_prop_config.json"
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}. Please run ml/train_k_props.py first.")
        return

    # Load Model and Dispersion Config
    print(f"Loading model and configuration for backtest: {label}...")
    model = joblib.load(model_path)
    
    phi = 1.0
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            phi = config.get('dispersion_phi', 1.0)
            print(f"  -> Loaded Dispersion Factor (phi): {phi:.4f}")
    else:
        print("  -> Warning: k_prop_config.json not found. Falling back to Poisson (phi=1.0).")

    manager = MLBDbManager()
    conn = manager._get_connection()
    
    query = """
    SELECT 
        game_date,
        home_sp_rolling_stuff, home_sp_k_minus_bb, away_lineup_k_pct, 
        away_sp_rolling_stuff, away_sp_k_minus_bb, home_lineup_k_pct,
        park_factor_runs, park_factor_k, umpire_k_pct, home_bullpen_k_bb, away_bullpen_k_bb,
        home_sp_strikeouts, away_sp_strikeouts,
        home_sp_k_line, home_sp_k_odds_over, home_sp_k_odds_under,
        away_sp_k_line, away_sp_k_odds_over, away_sp_k_odds_under
    FROM historical_training_data 
    WHERE strftime('%Y', game_date) = '2025'
    AND home_sp_k_line IS NOT NULL
    AND (home_sp_strikeouts > 0 OR away_sp_strikeouts > 0)
    ORDER BY game_date ASC
    """
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("No patched 2025 data found. Wait for the patch script to finish.")
        return

    # Extract Home
    home_df = df[['game_date', 'home_sp_rolling_stuff', 'home_sp_k_minus_bb', 'away_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'home_bullpen_k_bb', 'home_sp_strikeouts', 'home_sp_k_line', 'home_sp_k_odds_over', 'home_sp_k_odds_under']].copy()
    home_df.columns = ['game_date', 'sp_rolling_stuff', 'sp_k_minus_bb', 'opposing_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'bullpen_k_bb', 'actual_k', 'line', 'odds_over', 'odds_under']
    
    # Extract Away
    away_df = df[['game_date', 'away_sp_rolling_stuff', 'away_sp_k_minus_bb', 'home_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'away_bullpen_k_bb', 'away_sp_strikeouts', 'away_sp_k_line', 'away_sp_k_odds_over', 'away_sp_k_odds_under']].copy()
    away_df.columns = ['game_date', 'sp_rolling_stuff', 'sp_k_minus_bb', 'opposing_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'bullpen_k_bb', 'actual_k', 'line', 'odds_over', 'odds_under']

    # Combine into one dataset of pitcher appearances
    test_df = pd.concat([home_df, away_df], ignore_index=True)
    test_df = test_df.dropna(subset=['sp_rolling_stuff', 'sp_k_minus_bb', 'opposing_lineup_k_pct']).copy()
    test_df = test_df.sort_values('game_date')
    
    features = ['sp_rolling_stuff', 'sp_k_minus_bb', 'opposing_lineup_k_pct', 'park_factor_runs', 'park_factor_k', 'umpire_k_pct', 'bullpen_k_bb']
    X_test = test_df[features].apply(pd.to_numeric, errors='coerce')
    
    print(f"Backtesting {len(test_df)} pitcher appearances using {'Negative Binomial' if phi > 1.01 else 'Poisson'} CDF & Kelly Criterion...")

    # 1. Model Prediction (Lambda / Expected Mean)
    test_df['pred_lambda'] = model.predict(X_test)
    
    # 2. Probability Engine (Negative Binomial or Poisson)
    if phi > 1.01:
        # Negative Binomial parameters (Scipy nbinom uses n, p): 
        # Scipy 'p' is probability of success, 'n' is number of successes.
        # Our phi = Variance / Mean. 
        # Relationship: Mean = n(1-p)/p, Var = n(1-p)/p^2
        # Solving for p and n:
        # p = Mean / Var = 1 / phi
        # n = Mean^2 / (Var - Mean) = Mean / (phi - 1)
        p_param = 1.0 / phi
        n_param = test_df['pred_lambda'] / (phi - 1.0)
        test_df['prob_under'] = nbinom.cdf(np.floor(test_df['line']), n_param, p_param)
    else:
        test_df['prob_under'] = poisson.cdf(np.floor(test_df['line']), test_df['pred_lambda'])
        
    test_df['prob_over'] = 1 - test_df['prob_under']
    
    # 3. Implied Odds
    test_df['dec_over'] = test_df['odds_over'].apply(american_to_decimal)
    test_df['dec_under'] = test_df['odds_under'].apply(american_to_decimal)
    test_df['implied_over'] = 1 / test_df['dec_over']
    test_df['implied_under'] = 1 / test_df['dec_under']
    
    # 4. Bankroll Simulation (Simultaneous Daily Kelly)
    initial_bankroll = 1000
    current_bankroll = initial_bankroll
    max_daily_risk = 0.10  # Never risk more than 10% of total bankroll per day
    kelly_fraction = 0.25
    min_edge = 0.02

    total_staked = 0
    total_profit = 0
    bets_placed = 0
    wins = 0
    
    # Sort for sequential day-by-day processing
    test_df = test_df.sort_values('game_date')
    
    print(f"Running simulation with {max_daily_risk*100}% Max Daily Risk and {kelly_fraction} Fractional Kelly...")

    for date, day_df in test_df.groupby('game_date'):
        day_bets = []
        
        # Identify all potential bets for the day
        for idx, row in day_df.iterrows():
            edge_over = row['prob_over'] - row['implied_over']
            edge_under = row['prob_under'] - row['implied_under']
            
            if edge_over > min_edge and edge_over > edge_under:
                k_pct = calculate_kelly(row['prob_over'], row['dec_over'], kelly_fraction)
                if k_pct > 0:
                    day_bets.append({
                        'side': 'OVER',
                        'k_pct': k_pct,
                        'dec_odds': row['dec_over'],
                        'actual_k': row['actual_k'],
                        'line': row['line']
                    })
            elif edge_under > min_edge and edge_under > edge_over:
                k_pct = calculate_kelly(row['prob_under'], row['dec_under'], kelly_fraction)
                if k_pct > 0:
                    day_bets.append({
                        'side': 'UNDER',
                        'k_pct': k_pct,
                        'dec_odds': row['dec_under'],
                        'actual_k': row['actual_k'],
                        'line': row['line']
                    })

        if not day_bets:
            continue

        # Calculate Simultaneous Scaling
        total_raw_fractions = sum(b['k_pct'] for b in day_bets)
        scaling_factor = 1.0
        if total_raw_fractions > max_daily_risk:
            scaling_factor = max_daily_risk / total_raw_fractions
        
        day_pnl = 0
        for bet in day_bets:
            actual_stake = current_bankroll * bet['k_pct'] * scaling_factor
            
            # Resolve Bet
            won = False
            if bet['side'] == 'OVER' and bet['actual_k'] > bet['line']:
                won = True
            elif bet['side'] == 'UNDER' and bet['actual_k'] < bet['line']:
                won = True
            
            if won:
                profit = actual_stake * (bet['dec_odds'] - 1)
                wins += 1
            else:
                profit = -actual_stake
            
            day_pnl += profit
            total_staked += actual_stake
            bets_placed += 1

        # End of day bankroll update
        current_bankroll += day_pnl
        total_profit += day_pnl

    roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0
    hit_rate = (wins / bets_placed) * 100 if bets_placed > 0 else 0
    
    metrics = {
        'roi': round(float(roi), 2),
        'hit_rate': round(float(hit_rate), 2),
        'bets_placed': bets_placed,
        'final_bankroll': round(float(current_bankroll), 2)
    }

    print("\n" + "="*40)
    print(f"      2025 K-PROP KELLY SIMULATION: {label}")
    print("="*40)
    print(f"Total Model Edges Found: {bets_placed} Bets")
    print(f"Hit Rate:                {hit_rate:.1f}% ({wins}/{bets_placed})")
    print(f"Starting Bankroll:       ${initial_bankroll:,.2f}")
    print(f"Final Bankroll:          ${current_bankroll:,.2f}")
    print(f"Total Staked:            ${total_staked:,.2f}")
    print(f"Total Profit:            ${total_profit:,.2f}")
    print(f"Return on Investment:    {roi:+.2f}%")
    print("="*40)

    # 5. Log to Experiment Registry
    logger.log_run(
        label=label,
        model_type="Backtest_K_Props",
        features=features,
        parameters={'kelly_fraction': 0.25, 'min_edge': 0.02},
        metrics=metrics
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=str, default="Manual Backtest Run")
    args = parser.parse_args()
    
    run_k_prop_backtest(label=args.label)
