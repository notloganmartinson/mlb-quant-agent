import sqlite3
import pandas as pd
import numpy as np

def test():
    conn = sqlite3.connect('data/mlb_betting.db')
    query = """
        SELECT game_id, game_date, home_sp_k_minus_bb, away_lineup_k_pct, 
               away_sp_k_minus_bb, home_lineup_k_pct, home_sp_strikeouts, away_sp_strikeouts
        FROM historical_training_data
        WHERE home_sp_k_minus_bb IS NOT NULL AND away_lineup_k_pct IS NOT NULL
        LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    
    for _, row in df.iterrows():
        # Home SP calculation
        h_k_pct = row['home_sp_k_minus_bb'] + 0.08
        a_lineup_mult = row['away_lineup_k_pct'] / 0.22
        h_exp_k = 23 * h_k_pct * a_lineup_mult
        # Snap to nearest 0.5
        h_line = round(h_exp_k * 2) / 2
        # Ensure it ends in .5
        if h_line % 1 == 0:
            h_line -= 0.5
            
        print(f"Date: {row['game_date']}, Home SP: {h_k_pct:.3f} K% vs Lineup {row['away_lineup_k_pct']:.3f} K% -> Raw: {h_exp_k:.2f} -> Line: {h_line}, Actual: {row['home_sp_strikeouts']}")

if __name__ == "__main__":
    test()
