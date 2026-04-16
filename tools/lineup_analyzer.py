import statsapi
from core.db_manager import MLBDbManager
from datetime import datetime

class LineupAnalyzer:
    def __init__(self):
        self.manager = MLBDbManager()

    def get_todays_games(self):
        """Fetches today's game schedule and gamePks."""
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"Fetching game schedule for {today}...")
        sched = statsapi.schedule(date=today)
        return sched

    def analyze_lineup(self, game_pk, team_type='home'):
        """
        Fetches the starting lineup for a game and calculates weighted metrics.
        team_type: 'home' or 'away'
        """
        try:
            box = statsapi.boxscore_data(game_pk)
            team_info = box.get(team_type, {})
            team_name = team_info.get('team', {}).get('name')
            batters = team_info.get('batters', []) # List of player IDs in order
            
            if not batters:
                return None

            total_iso = 0.0
            total_k_pct = 0.0
            count = 0

            # We only look at the starting 9 (first 9 IDs in the 'batters' list)
            starting_9 = batters[:9]
            
            for player_id in starting_9:
                # Query our DB for this player's metrics (ISO, K%)
                query = f"SELECT name, iso, k_pct FROM players WHERE player_id = {player_id}"
                res = self.manager.query_agent_data(query)
                
                if res:
                    p = res[0]
                    total_iso += (p['iso'] or 0.0)
                    total_k_pct += (p['k_pct'] or 0.0)
                    count += 1
            
            if count > 0:
                avg_iso = round(total_iso / count, 3)
                avg_k = round(total_k_pct / count, 3)
                return {
                    "team": team_name,
                    "lineup_iso": avg_iso,
                    "lineup_k_pct": avg_k,
                    "players_tracked": count
                }
            return None

        except Exception as e:
            print(f"Error analyzing lineup for game {game_pk}: {e}")
            return None

    def run_daily_analysis(self):
        """Iterates through all today's games and prints the lineup strength."""
        games = self.get_todays_games()
        print(f"\n--- LIVE LINEUP ANALYSIS ({len(games)} Games) ---")
        print(f"{'Matchup':<40} | {'Team':<20} | {'ISO':<6} | {'K%':<6}")
        print("-" * 85)

        for g in games:
            game_pk = g['game_id']
            summary = f"{g['away_name']} @ {g['home_name']}"
            
            home_analysis = self.analyze_lineup(game_pk, 'home')
            away_analysis = self.analyze_lineup(game_pk, 'away')

            if home_analysis:
                print(f"{summary:<40} | {home_analysis['team']:<20} | {home_analysis['lineup_iso']:<6} | {home_analysis['lineup_k_pct']:<6}")
            if away_analysis:
                print(f"{'':<40} | {away_analysis['team']:<20} | {away_analysis['lineup_iso']:<6} | {away_analysis['lineup_k_pct']:<6}")
            print("-" * 85)

if __name__ == "__main__":
    analyzer = LineupAnalyzer()
    analyzer.run_daily_analysis()
