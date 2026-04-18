import sqlite3
from datetime import datetime

class MLBDbManager:
    def __init__(self, db_path="data/mlb_betting.db"):
        self.db_path = db_path
        self._shared_conn = None

    def _get_connection(self):
        if self._shared_conn:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def __enter__(self):
        """Enable 'with MLBDbManager() as manager:' for bulk transactions."""
        self._shared_conn = sqlite3.connect(self.db_path)
        self._shared_conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._shared_conn:
            if exc_type is None:
                self._shared_conn.commit()
            else:
                self._shared_conn.rollback()
            self._shared_conn.close()
            self._shared_conn = None

    def upsert_player_stats(self, data: dict):
        sql = """
            INSERT INTO players (
                player_id, season, name, date_updated, stuff_plus, location_plus, 
                pitching_plus, xfip, siera, era, k_minus_bb_percent, iso, k_pct
            ) VALUES (
                :player_id, :season, :name, :date_updated, :stuff_plus, :location_plus, 
                :pitching_plus, :xfip, :siera, :era, :k_minus_bb_percent, :iso, :k_pct
            )
            ON CONFLICT(player_id, season) DO UPDATE SET
                name = excluded.name,
                date_updated = excluded.date_updated,
                stuff_plus = COALESCE(excluded.stuff_plus, players.stuff_plus),
                location_plus = COALESCE(excluded.location_plus, players.location_plus),
                pitching_plus = COALESCE(excluded.pitching_plus, players.pitching_plus),
                xfip = COALESCE(excluded.xfip, players.xfip),
                siera = COALESCE(excluded.siera, players.siera),
                era = COALESCE(excluded.era, players.era),
                k_minus_bb_percent = COALESCE(excluded.k_minus_bb_percent, players.k_minus_bb_percent),
                iso = COALESCE(excluded.iso, players.iso),
                k_pct = COALESCE(excluded.k_pct, players.k_pct)
        """
        conn = self._get_connection()
        try:
            conn.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_many_player_stats(self, data_list: list):
        """Optimized bulk upsert for player statistics."""
        if not data_list: return
        sql = """
            INSERT INTO players (
                player_id, season, name, date_updated, stuff_plus, location_plus, 
                pitching_plus, xfip, siera, era, k_minus_bb_percent, iso, k_pct
            ) VALUES (
                :player_id, :season, :name, :date_updated, :stuff_plus, :location_plus, 
                :pitching_plus, :xfip, :siera, :era, :k_minus_bb_percent, :iso, :k_pct
            )
            ON CONFLICT(player_id, season) DO UPDATE SET
                name = excluded.name,
                date_updated = excluded.date_updated,
                stuff_plus = COALESCE(excluded.stuff_plus, players.stuff_plus),
                location_plus = COALESCE(excluded.location_plus, players.location_plus),
                pitching_plus = COALESCE(excluded.pitching_plus, players.pitching_plus),
                xfip = COALESCE(excluded.xfip, players.xfip),
                siera = COALESCE(excluded.siera, players.siera),
                era = COALESCE(excluded.era, players.era),
                k_minus_bb_percent = COALESCE(excluded.k_minus_bb_percent, players.k_minus_bb_percent),
                iso = COALESCE(excluded.iso, players.iso),
                k_pct = COALESCE(excluded.k_pct, players.k_pct)
        """
        conn = self._get_connection()
        try:
            conn.executemany(sql, data_list)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

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
        conn = self._get_connection()
        try:
            conn.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_many_hitting_lineups(self, data_list: list):
        if not data_list: return
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
        conn = self._get_connection()
        try:
            conn.executemany(sql, data_list)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

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
        conn = self._get_connection()
        try:
            conn.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_many_bullpens(self, data_list: list):
        if not data_list: return
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
        conn = self._get_connection()
        try:
            conn.executemany(sql, data_list)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

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
                full_game_away_moneyline, full_game_total, implied_prob_home,
                home_sp_rolling_stuff, away_sp_rolling_stuff,
                home_lineup_pa, away_lineup_pa,
                home_sp_strikeouts, away_sp_strikeouts,
                home_lineup_k_pct, away_lineup_k_pct
            ) VALUES (
                :game_id, :home_team_id, :away_team_id, :home_team, :away_team, 
                :home_pitcher, :away_pitcher, :home_sp_siera, :away_sp_siera, 
                :home_sp_k_minus_bb, :away_sp_k_minus_bb, :home_bullpen_siera, 
                :away_bullpen_siera, :home_lineup_iso_vs_pitcher_hand, 
                :away_lineup_iso_vs_pitcher_hand, :home_lineup_woba_vs_pitcher_hand, 
                :away_lineup_woba_vs_pitcher_hand, :park_factor_runs, :temperature, 
                :wind_speed, :wind_direction, :full_game_home_moneyline, 
                :full_game_away_moneyline, :full_game_total, :implied_prob_home,
                :home_sp_rolling_stuff, :away_sp_rolling_stuff,
                :home_lineup_pa, :away_lineup_pa,
                :home_sp_strikeouts, :away_sp_strikeouts,
                :home_lineup_k_pct, :away_lineup_k_pct
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
                wind_direction = COALESCE(excluded.wind_direction, betting_markets.wind_direction),
                home_sp_rolling_stuff = COALESCE(excluded.home_sp_rolling_stuff, betting_markets.home_sp_rolling_stuff),
                away_sp_rolling_stuff = COALESCE(excluded.away_sp_rolling_stuff, betting_markets.away_sp_rolling_stuff),
                home_lineup_pa = COALESCE(excluded.home_lineup_pa, betting_markets.home_lineup_pa),
                away_lineup_pa = COALESCE(excluded.away_lineup_pa, betting_markets.away_lineup_pa),
                home_sp_strikeouts = COALESCE(excluded.home_sp_strikeouts, betting_markets.home_sp_strikeouts),
                away_sp_strikeouts = COALESCE(excluded.away_sp_strikeouts, betting_markets.away_sp_strikeouts),
                home_lineup_k_pct = COALESCE(excluded.home_lineup_k_pct, betting_markets.home_lineup_k_pct),
                away_lineup_k_pct = COALESCE(excluded.away_lineup_k_pct, betting_markets.away_lineup_k_pct)
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def upsert_historical_training_data(self, data: dict):
        """Historical training table - 1:1 mirror of live features + Target + Closing Lines."""
        sql = """
            INSERT INTO historical_training_data (
                game_id, game_date, home_team_id, away_team_id, home_team_won, 
                home_team_runs, away_team_runs,
                home_sp_siera, away_sp_siera, home_sp_k_minus_bb, away_sp_k_minus_bb, 
                home_bullpen_siera, away_bullpen_siera, home_lineup_iso_vs_pitcher_hand, 
                away_lineup_iso_vs_pitcher_hand, home_lineup_woba_vs_pitcher_hand, 
                away_lineup_woba_vs_pitcher_hand, park_factor_runs, temperature, 
                wind_speed, wind_direction, closing_home_moneyline, 
                closing_away_moneyline, closing_total,
                home_sp_rolling_stuff, away_sp_rolling_stuff,
                home_lineup_pa, away_lineup_pa,
                home_sp_strikeouts, away_sp_strikeouts,
                home_lineup_k_pct, away_lineup_k_pct
            ) VALUES (
                :game_id, :game_date, :home_team_id, :away_team_id, :home_team_won, 
                :home_team_runs, :away_team_runs,
                :home_sp_siera, :away_sp_siera, :home_sp_k_minus_bb, :away_sp_k_minus_bb, 
                :home_bullpen_siera, :away_bullpen_siera, :home_lineup_iso_vs_pitcher_hand, 
                :away_lineup_iso_vs_pitcher_hand, :home_lineup_woba_vs_pitcher_hand, 
                :away_lineup_woba_vs_pitcher_hand, :park_factor_runs, :temperature, 
                :wind_speed, :wind_direction, :closing_home_moneyline, 
                :closing_away_moneyline, :closing_total,
                :home_sp_rolling_stuff, :away_sp_rolling_stuff,
                :home_lineup_pa, :away_lineup_pa,
                :home_sp_strikeouts, :away_sp_strikeouts,
                :home_lineup_k_pct, :away_lineup_k_pct
            )
            ON CONFLICT(game_id) DO UPDATE SET
                home_team_won = excluded.home_team_won,
                home_team_runs = excluded.home_team_runs,
                away_team_runs = excluded.away_team_runs,
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
                closing_total = COALESCE(excluded.closing_total, historical_training_data.closing_total),
                home_sp_rolling_stuff = excluded.home_sp_rolling_stuff,
                away_sp_rolling_stuff = excluded.away_sp_rolling_stuff,
                home_lineup_pa = excluded.home_lineup_pa,
                away_lineup_pa = excluded.away_lineup_pa,
                home_sp_strikeouts = excluded.home_sp_strikeouts,
                away_sp_strikeouts = excluded.away_sp_strikeouts,
                home_lineup_k_pct = excluded.home_lineup_k_pct,
                away_lineup_k_pct = excluded.away_lineup_k_pct
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

    def upsert_raw_pitch(self, data: dict):
        """Inserts a raw Statcast pitch for training."""
        sql = """
            INSERT INTO raw_pitches (
                pitcher_id, game_date, pitch_type, release_speed, pfx_x, pfx_z, 
                release_spin_rate, release_extension, vx0, vy0, vz0, ax, ay, az, 
                sz_top, sz_bot, plate_x, plate_z, description, whiff
            ) VALUES (
                :pitcher_id, :game_date, :pitch_type, :release_speed, :pfx_x, :pfx_z, 
                :release_spin_rate, :release_extension, :vx0, :vy0, :vz0, :ax, :ay, :az, 
                :sz_top, :sz_bot, :plate_x, :plate_z, :description, :whiff
            )
        """
        with self._get_connection() as conn:
            conn.execute(sql, data)

    def update_player_stuff_plus(self, player_id, season, stuff_plus):
        """Surgically update Stuff+ for a player/season."""
        sql = """
            UPDATE players 
            SET stuff_plus = ?, date_updated = ?
            WHERE player_id = ? AND season = ?
        """
        with self._get_connection() as conn:
            conn.execute(sql, (stuff_plus, datetime.now().strftime("%Y-%m-%d"), player_id, season))

    def update_pitch_stuff_plus(self, pitch_id, stuff_plus):
        """Update individual pitch-level Stuff+."""
        sql = "UPDATE raw_pitches SET stuff_plus = ? WHERE pitch_id = ?"
        with self._get_connection() as conn:
            conn.execute(sql, (stuff_plus, pitch_id))

    def get_pitcher_prior_pitches(self, pitcher_id, game_date):
        """Fetches all Stuff+ values for a pitcher before a specific date."""
        sql = """
            SELECT stuff_plus FROM raw_pitches 
            WHERE pitcher_id = ? AND game_date < ? AND stuff_plus IS NOT NULL
            ORDER BY game_date ASC
        """
        with self._get_connection() as conn:
            rows = conn.execute(sql, (pitcher_id, game_date)).fetchall()
            return [row['stuff_plus'] for row in rows]

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
