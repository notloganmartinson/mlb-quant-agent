from core.db_manager import MLBDbManager
import statsapi
from datetime import datetime

class ValueFinder:
    def __init__(self):
        self.manager = MLBDbManager()

    def get_weighted_stat(self, player_id, stat_name):
        """
        Calculates a weighted average of 2025 (70%) and 2026 (30%) stats
        to stabilize early-season volatility.
        """
        query_2025 = f"SELECT {stat_name} FROM starting_pitchers WHERE player_id = {player_id} AND season = 2025"
        query_2026 = f"SELECT {stat_name} FROM starting_pitchers WHERE player_id = {player_id} AND season = 2026"
        
        res_2025 = self.manager.query_agent_data(query_2025)
        res_2026 = self.manager.query_agent_data(query_2026)
        
        val_2025 = res_2025[0][stat_name] if res_2025 and res_2025[0][stat_name] else None
        val_2026 = res_2026[0][stat_name] if res_2026 and res_2026[0][stat_name] else None
        
        if val_2025 and val_2026:
            return round((val_2025 * 0.7) + (val_2026 * 0.3), 3)
        return val_2026 or val_2025 or 0.0

    def find_value_today(self):
        print(f"--- PRO VALUE FINDER (April 11, 2026) ---")
        print(f"{'Matchup':<40} | {'Vegas Prob':<10} | {'Our Prob':<10} | {'Edge'}")
        print("-" * 80)
        
        # 1. Get Today's Market Odds from DB
        market_query = "SELECT * FROM betting_markets"
        games = self.manager.query_agent_data(market_query)
        
        for g in games:
            # For this MVP, we use a simple projection: 
            # Compare Home Team overall ISO vs Away Team overall ISO (Weighted)
            # In a full model, you'd include SIERA and Bullpens.
            
            # Simple placeholder logic for 'Our Prob'
            our_prob = 0.52 # Baseline
            vegas_prob = g['implied_prob_home'] or 0.5
            edge = our_prob - vegas_prob
            
            summary = f"{g['away_team']} @ {g['home_team']}"
            if abs(edge) > 0.02: # Show games with > 2% edge
                print(f"{summary:<40} | {vegas_prob:<10.1%} | {our_prob:<10.1%} | {edge:+.1%}")

if __name__ == "__main__":
    finder = ValueFinder()
    finder.find_value_today()
