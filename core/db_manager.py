import sqlite3

class MLBDbManager:
    def __init__(self, db_path="data/mlb_betting.db"):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert_pitcher(self, data: dict):
        sql = """
            INSERT INTO starting_pitchers (
                player_id, season, name, date_updated, stuff_plus, location_plus, 
                pitching_plus, xfip, siera, era, k_minus_bb_percent, iso, k_pct
            ) VALUES (
                :player_id, :season, :name, :date_updated, :stuff_plus, :location_plus, 
                :pitching_plus, :xfip, :siera, :era, :k_minus_bb_percent, :iso, :k_pct
            )
            ON CONFLICT(player_id, season) DO UPDATE SET
                name = excluded.name,
                date_updated = excluded.date_updated,
                stuff_plus = COALESCE(excluded.stuff_plus, starting_pitchers.stuff_plus),
                location_plus = COALESCE(excluded.location_plus, starting_pitchers.location_plus),
                pitching_plus = COALESCE(excluded.pitching_plus, starting_pitchers.pitching_plus),
                xfip = COALESCE(excluded.xfip, starting_pitchers.xfip),
                siera = COALESCE(excluded.siera, starting_pitchers.siera),
                era = COALESCE(excluded.era, starting_pitchers.era),
                k_minus_bb_percent = COALESCE(excluded.k_minus_bb_percent, starting_pitchers.k_minus_bb_percent),
                iso = COALESCE(excluded.iso, starting_pitchers.iso),
                k_pct = COALESCE(excluded.k_pct, starting_pitchers.k_pct)
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_hitting_lineup(self, data: dict):
        sql = """
            INSERT INTO hitting_lineups (
                team_id, season, team_name, date_updated, iso_vs_rhp, 
                iso_vs_lhp, woba, iso, k_percent
            ) VALUES (
                :team_id, :season, :team_name, :date_updated, :iso_vs_rhp, 
                :iso_vs_lhp, :woba, :iso, :k_percent
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = excluded.team_name,
                date_updated = excluded.date_updated,
                iso_vs_rhp = COALESCE(excluded.iso_vs_rhp, hitting_lineups.iso_vs_rhp),
                iso_vs_lhp = COALESCE(excluded.iso_vs_lhp, hitting_lineups.iso_vs_lhp),
                woba = COALESCE(excluded.woba, hitting_lineups.woba),
                iso = COALESCE(excluded.iso, hitting_lineups.iso),
                k_percent = COALESCE(excluded.k_percent, hitting_lineups.k_percent)
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_bullpen(self, data: dict):
        sql = """
            INSERT INTO bullpens (
                team_id, season, team_name, date_updated, bullpen_xfip, 
                bullpen_siera, top_relievers_rest_days, total_pitches_last_3_days
            ) VALUES (
                :team_id, :season, :team_name, :date_updated, :bullpen_xfip, 
                :bullpen_siera, :top_relievers_rest_days, :total_pitches_last_3_days
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = excluded.team_name,
                date_updated = excluded.date_updated,
                bullpen_xfip = COALESCE(excluded.bullpen_xfip, bullpens.bullpen_xfip),
                bullpen_siera = COALESCE(excluded.bullpen_siera, bullpens.bullpen_siera),
                top_relievers_rest_days = excluded.top_relievers_rest_days,
                total_pitches_last_3_days = excluded.total_pitches_last_3_days
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_betting_market(self, data: dict):
        """Live prediction table with full ML feature set."""
        sql = """
            INSERT INTO betting_markets (
                game_id, home_team_id, away_team_id, home_team, away_team, 
                home_pitcher, away_pitcher, home_sp_siera, away_sp_siera, 
                home_sp_k_minus_bb, away_sp_k_minus_bb, home_bullpen_siera, 
                away_bullpen_siera, home_lineup_iso_vs_pitcher_hand, 
                away_lineup_iso_vs_pitcher_hand, home_lineup_woba_vs_pitcher_hand, 
                away_lineup_woba_vs_pitcher_hand, park_factor_runs, temperature, 
                wind_speed, wind_direction, full_game_home_moneyline, 
                full_game_away_moneyline, full_game_total, implied_prob_home
            ) VALUES (
                :game_id, :home_team_id, :away_team_id, :home_team, :away_team, 
                :home_pitcher, :away_pitcher, :home_sp_siera, :away_sp_siera, 
                :home_sp_k_minus_bb, :away_sp_k_minus_bb, :home_bullpen_siera, 
                :away_bullpen_siera, :home_lineup_iso_vs_pitcher_hand, 
                :away_lineup_iso_vs_pitcher_hand, :home_lineup_woba_vs_pitcher_hand, 
                :away_lineup_woba_vs_pitcher_hand, :park_factor_runs, :temperature, 
                :wind_speed, :wind_direction, :full_game_home_moneyline, 
                :full_game_away_moneyline, :full_game_total, :implied_prob_home
            )
            ON CONFLICT(game_id) DO UPDATE SET
                full_game_home_moneyline = excluded.full_game_home_moneyline,
                full_game_away_moneyline = excluded.full_game_away_moneyline,
                full_game_total = excluded.full_game_total,
                implied_prob_home = excluded.implied_prob_home,
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_pitcher = COALESCE(excluded.home_pitcher, betting_markets.home_pitcher),
                away_pitcher = COALESCE(excluded.away_pitcher, betting_markets.away_pitcher),
                home_sp_siera = COALESCE(excluded.home_sp_siera, betting_markets.home_sp_siera),
                away_sp_siera = COALESCE(excluded.away_sp_siera, betting_markets.away_sp_siera),
                home_sp_k_minus_bb = COALESCE(excluded.home_sp_k_minus_bb, betting_markets.home_sp_k_minus_bb),
                away_sp_k_minus_bb = COALESCE(excluded.away_sp_k_minus_bb, betting_markets.away_sp_k_minus_bb),
                home_bullpen_siera = COALESCE(excluded.home_bullpen_siera, betting_markets.home_bullpen_siera),
                away_bullpen_siera = COALESCE(excluded.away_bullpen_siera, betting_markets.away_bullpen_siera),
                home_lineup_iso_vs_pitcher_hand = COALESCE(excluded.home_lineup_iso_vs_pitcher_hand, betting_markets.home_lineup_iso_vs_pitcher_hand),
                away_lineup_iso_vs_pitcher_hand = COALESCE(excluded.away_lineup_iso_vs_pitcher_hand, betting_markets.away_lineup_iso_vs_pitcher_hand),
                home_lineup_woba_vs_pitcher_hand = COALESCE(excluded.home_lineup_woba_vs_pitcher_hand, betting_markets.home_lineup_woba_vs_pitcher_hand),
                away_lineup_woba_vs_pitcher_hand = COALESCE(excluded.away_lineup_woba_vs_pitcher_hand, betting_markets.away_lineup_woba_vs_pitcher_hand),
                park_factor_runs = COALESCE(excluded.park_factor_runs, betting_markets.park_factor_runs),
                temperature = COALESCE(excluded.temperature, betting_markets.temperature),
                wind_speed = COALESCE(excluded.wind_speed, betting_markets.wind_speed),
                wind_direction = COALESCE(excluded.wind_direction, betting_markets.wind_direction)
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_historical_training_data(self, data: dict):
        """Historical training table - 1:1 mirror of live features + Target + Closing Lines."""
        sql = """
            INSERT INTO historical_training_data (
                game_id, game_date, home_team_id, away_team_id, home_team_won, 
                home_sp_siera, away_sp_siera, home_sp_k_minus_bb, away_sp_k_minus_bb, 
                home_bullpen_siera, away_bullpen_siera, home_lineup_iso_vs_pitcher_hand, 
                away_lineup_iso_vs_pitcher_hand, home_lineup_woba_vs_pitcher_hand, 
                away_lineup_woba_vs_pitcher_hand, park_factor_runs, temperature, 
                wind_speed, wind_direction, closing_home_moneyline, 
                closing_away_moneyline, closing_total
            ) VALUES (
                :game_id, :game_date, :home_team_id, :away_team_id, :home_team_won, 
                :home_sp_siera, :away_sp_siera, :home_sp_k_minus_bb, :away_sp_k_minus_bb, 
                :home_bullpen_siera, :away_bullpen_siera, :home_lineup_iso_vs_pitcher_hand, 
                :away_lineup_iso_vs_pitcher_hand, :home_lineup_woba_vs_pitcher_hand, 
                :away_lineup_woba_vs_pitcher_hand, :park_factor_runs, :temperature, 
                :wind_speed, :wind_direction, :closing_home_moneyline, 
                :closing_away_moneyline, :closing_total
            )
            ON CONFLICT(game_id) DO UPDATE SET
                home_team_won = excluded.home_team_won,
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_sp_siera = excluded.home_sp_siera,
                away_sp_siera = excluded.away_sp_siera,
                home_sp_k_minus_bb = excluded.home_sp_k_minus_bb,
                away_sp_k_minus_bb = excluded.away_sp_k_minus_bb,
                home_bullpen_siera = excluded.home_bullpen_siera,
                away_bullpen_siera = excluded.away_bullpen_siera,
                home_lineup_iso_vs_pitcher_hand = excluded.home_lineup_iso_vs_pitcher_hand,
                away_lineup_iso_vs_pitcher_hand = excluded.away_lineup_iso_vs_pitcher_hand,
                home_lineup_woba_vs_pitcher_hand = excluded.home_lineup_woba_vs_pitcher_hand,
                away_lineup_woba_vs_pitcher_hand = excluded.away_lineup_woba_vs_pitcher_hand,
                closing_home_moneyline = COALESCE(excluded.closing_home_moneyline, historical_training_data.closing_home_moneyline),
                closing_away_moneyline = COALESCE(excluded.closing_away_moneyline, historical_training_data.closing_away_moneyline),
                closing_total = COALESCE(excluded.closing_total, historical_training_data.closing_total)
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_sportsbook_odds(self, data: dict):
        """Inserts or updates detailed odds for a specific sportsbook."""
        sql = """
            INSERT INTO sportsbook_odds (
                game_id, book_name, home_team_id, away_team_id, home_ml, away_ml, home_rl, away_rl, 
                rl_price_home, rl_price_away, total, total_over_price, 
                total_under_price, last_updated
            ) VALUES (
                :game_id, :book_name, :home_team_id, :away_team_id, :home_ml, :away_ml, :home_rl, :away_rl, 
                :rl_price_home, :rl_price_away, :total, :total_over_price, 
                :total_under_price, :last_updated
            )
            ON CONFLICT(game_id, book_name) DO UPDATE SET
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_ml = excluded.home_ml,
                away_ml = excluded.away_ml,
                home_rl = excluded.home_rl,
                away_rl = excluded.away_rl,
                rl_price_home = excluded.rl_price_home,
                rl_price_away = excluded.rl_price_away,
                total = excluded.total,
                total_over_price = excluded.total_over_price,
                total_under_price = excluded.total_under_price,
                last_updated = excluded.last_updated
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def resolve_team_id(self, name: str) -> int:
        """Translates a team name into the canonical mlb_id."""
        sql = """
            SELECT mlb_id FROM team_mappings 
            WHERE team_name_short = ? OR team_full_name = ? OR odds_api_name = ? OR espn_name = ? OR fangraphs_abbr = ?
            LIMIT 1
        """
        with self._get_connection() as conn:
            res = conn.execute(sql, (name, name, name, name, name)).fetchone()
            return res['mlb_id'] if res else None

    def query_agent_data(self, sql_query: str):
        with self._get_connection() as conn:
            cursor = conn.execute(sql_query)
            return [dict(row) for row in cursor.fetchall()]
