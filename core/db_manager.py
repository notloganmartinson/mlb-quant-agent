import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MLBDbManager:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.dbname = os.getenv("DB_NAME")
        self._shared_conn = None

    def _get_connection(self):
        if self._shared_conn:
            return self._shared_conn
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname,
            cursor_factory=RealDictCursor
        )
        return conn

    def __enter__(self):
        """Enable 'with MLBDbManager() as manager:' for bulk transactions."""
        self._shared_conn = self._get_connection()
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
                %(player_id)s, %(season)s, %(name)s, %(date_updated)s, %(stuff_plus)s, %(location_plus)s, 
                %(pitching_plus)s, %(xfip)s, %(siera)s, %(era)s, %(k_minus_bb_percent)s, %(iso)s, %(k_pct)s
            )
            ON CONFLICT(player_id, season) DO UPDATE SET
                name = EXCLUDED.name,
                date_updated = EXCLUDED.date_updated,
                stuff_plus = COALESCE(EXCLUDED.stuff_plus, players.stuff_plus),
                location_plus = COALESCE(EXCLUDED.location_plus, players.location_plus),
                pitching_plus = COALESCE(EXCLUDED.pitching_plus, players.pitching_plus),
                xfip = COALESCE(EXCLUDED.xfip, players.xfip),
                siera = COALESCE(EXCLUDED.siera, players.siera),
                era = COALESCE(EXCLUDED.era, players.era),
                k_minus_bb_percent = COALESCE(EXCLUDED.k_minus_bb_percent, players.k_minus_bb_percent),
                iso = COALESCE(EXCLUDED.iso, players.iso),
                k_pct = COALESCE(EXCLUDED.k_pct, players.k_pct)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
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
                %(player_id)s, %(season)s, %(name)s, %(date_updated)s, %(stuff_plus)s, %(location_plus)s, 
                %(pitching_plus)s, %(xfip)s, %(siera)s, %(era)s, %(k_minus_bb_percent)s, %(iso)s, %(k_pct)s
            )
            ON CONFLICT(player_id, season) DO UPDATE SET
                name = EXCLUDED.name,
                date_updated = EXCLUDED.date_updated,
                stuff_plus = COALESCE(EXCLUDED.stuff_plus, players.stuff_plus),
                location_plus = COALESCE(EXCLUDED.location_plus, players.location_plus),
                pitching_plus = COALESCE(EXCLUDED.pitching_plus, players.pitching_plus),
                xfip = COALESCE(EXCLUDED.xfip, players.xfip),
                siera = COALESCE(EXCLUDED.siera, players.siera),
                era = COALESCE(EXCLUDED.era, players.era),
                k_minus_bb_percent = COALESCE(EXCLUDED.k_minus_bb_percent, players.k_minus_bb_percent),
                iso = COALESCE(EXCLUDED.iso, players.iso),
                k_pct = COALESCE(EXCLUDED.k_pct, players.k_pct)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                execute_batch(cursor, sql, data_list)
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
                %(team_id)s, %(season)s, %(team_name)s, %(date_updated)s, %(iso_vs_rhp)s, 
                %(iso_vs_lhp)s, %(woba)s, %(iso)s, %(k_percent)s
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = EXCLUDED.team_name,
                date_updated = EXCLUDED.date_updated,
                iso_vs_rhp = COALESCE(EXCLUDED.iso_vs_rhp, hitting_lineups.iso_vs_rhp),
                iso_vs_lhp = COALESCE(EXCLUDED.iso_vs_lhp, hitting_lineups.iso_vs_lhp),
                woba = COALESCE(EXCLUDED.woba, hitting_lineups.woba),
                iso = COALESCE(EXCLUDED.iso, hitting_lineups.iso),
                k_percent = COALESCE(EXCLUDED.k_percent, hitting_lineups.k_percent)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
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
                %(team_id)s, %(season)s, %(team_name)s, %(date_updated)s, %(iso_vs_rhp)s, 
                %(iso_vs_lhp)s, %(woba)s, %(iso)s, %(k_percent)s
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = EXCLUDED.team_name,
                date_updated = EXCLUDED.date_updated,
                iso_vs_rhp = COALESCE(EXCLUDED.iso_vs_rhp, hitting_lineups.iso_vs_rhp),
                iso_vs_lhp = COALESCE(EXCLUDED.iso_vs_lhp, hitting_lineups.iso_vs_lhp),
                woba = COALESCE(EXCLUDED.woba, hitting_lineups.woba),
                iso = COALESCE(EXCLUDED.iso, hitting_lineups.iso),
                k_percent = COALESCE(EXCLUDED.k_percent, hitting_lineups.k_percent)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                execute_batch(cursor, sql, data_list)
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
                %(team_id)s, %(season)s, %(team_name)s, %(date_updated)s, %(bullpen_xfip)s, 
                %(bullpen_siera)s, %(top_relievers_rest_days)s, %(total_pitches_last_3_days)s
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = EXCLUDED.team_name,
                date_updated = EXCLUDED.date_updated,
                bullpen_xfip = COALESCE(EXCLUDED.bullpen_xfip, bullpens.bullpen_xfip),
                bullpen_siera = COALESCE(EXCLUDED.bullpen_siera, bullpens.bullpen_siera),
                top_relievers_rest_days = EXCLUDED.top_relievers_rest_days,
                total_pitches_last_3_days = EXCLUDED.total_pitches_last_3_days
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
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
                %(team_id)s, %(season)s, %(team_name)s, %(date_updated)s, %(bullpen_xfip)s, 
                %(bullpen_siera)s, %(top_relievers_rest_days)s, %(total_pitches_last_3_days)s
            )
            ON CONFLICT(team_id, season) DO UPDATE SET
                team_name = EXCLUDED.team_name,
                date_updated = EXCLUDED.date_updated,
                bullpen_xfip = COALESCE(EXCLUDED.bullpen_xfip, bullpens.bullpen_xfip),
                bullpen_siera = COALESCE(EXCLUDED.bullpen_siera, bullpens.bullpen_siera),
                top_relievers_rest_days = EXCLUDED.top_relievers_rest_days,
                total_pitches_last_3_days = EXCLUDED.total_pitches_last_3_days
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                execute_batch(cursor, sql, data_list)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_betting_market(self, data: dict):
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
                %(game_id)s, %(home_team_id)s, %(away_team_id)s, %(home_team)s, %(away_team)s, 
                %(home_pitcher)s, %(away_pitcher)s, %(home_sp_siera)s, %(away_sp_siera)s, 
                %(home_sp_k_minus_bb)s, %(away_sp_k_minus_bb)s, %(home_bullpen_siera)s, 
                %(away_bullpen_siera)s, %(home_lineup_iso_vs_pitcher_hand)s, 
                %(away_lineup_iso_vs_pitcher_hand)s, %(home_lineup_woba_vs_pitcher_hand)s, 
                %(away_lineup_woba_vs_pitcher_hand)s, %(park_factor_runs)s, %(temperature)s, 
                %(wind_speed)s, %(wind_direction)s, %(full_game_home_moneyline)s, 
                %(full_game_away_moneyline)s, %(full_game_total)s, %(implied_prob_home)s,
                %(home_sp_rolling_stuff)s, %(away_sp_rolling_stuff)s,
                %(home_lineup_pa)s, %(away_lineup_pa)s,
                %(home_sp_strikeouts)s, %(away_sp_strikeouts)s,
                %(home_lineup_k_pct)s, %(away_lineup_k_pct)s
            )
            ON CONFLICT(game_id) DO UPDATE SET
                full_game_home_moneyline = EXCLUDED.full_game_home_moneyline,
                full_game_away_moneyline = EXCLUDED.full_game_away_moneyline,
                full_game_total = EXCLUDED.full_game_total,
                implied_prob_home = EXCLUDED.implied_prob_home,
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                home_pitcher = COALESCE(EXCLUDED.home_pitcher, betting_markets.home_pitcher),
                away_pitcher = COALESCE(EXCLUDED.away_pitcher, betting_markets.away_pitcher),
                home_sp_siera = COALESCE(EXCLUDED.home_sp_siera, betting_markets.home_sp_siera),
                away_sp_siera = COALESCE(EXCLUDED.away_sp_siera, betting_markets.away_sp_siera),
                home_sp_k_minus_bb = COALESCE(EXCLUDED.home_sp_k_minus_bb, betting_markets.home_sp_k_minus_bb),
                away_sp_k_minus_bb = COALESCE(EXCLUDED.away_sp_k_minus_bb, betting_markets.away_sp_k_minus_bb),
                home_bullpen_siera = COALESCE(EXCLUDED.home_bullpen_siera, betting_markets.home_bullpen_siera),
                away_bullpen_siera = COALESCE(EXCLUDED.away_bullpen_siera, betting_markets.away_bullpen_siera),
                home_lineup_iso_vs_pitcher_hand = COALESCE(EXCLUDED.home_lineup_iso_vs_pitcher_hand, betting_markets.home_lineup_iso_vs_pitcher_hand),
                away_lineup_iso_vs_pitcher_hand = COALESCE(EXCLUDED.away_lineup_iso_vs_pitcher_hand, betting_markets.away_lineup_iso_vs_pitcher_hand),
                home_lineup_woba_vs_pitcher_hand = COALESCE(EXCLUDED.home_lineup_woba_vs_pitcher_hand, betting_markets.home_lineup_woba_vs_pitcher_hand),
                away_lineup_woba_vs_pitcher_hand = COALESCE(EXCLUDED.away_lineup_woba_vs_pitcher_hand, betting_markets.away_lineup_woba_vs_pitcher_hand),
                park_factor_runs = COALESCE(EXCLUDED.park_factor_runs, betting_markets.park_factor_runs),
                temperature = COALESCE(EXCLUDED.temperature, betting_markets.temperature),
                wind_speed = COALESCE(EXCLUDED.wind_speed, betting_markets.wind_speed),
                wind_direction = COALESCE(EXCLUDED.wind_direction, betting_markets.wind_direction),
                home_sp_rolling_stuff = COALESCE(EXCLUDED.home_sp_rolling_stuff, betting_markets.home_sp_rolling_stuff),
                away_sp_rolling_stuff = COALESCE(EXCLUDED.away_sp_rolling_stuff, betting_markets.away_sp_rolling_stuff),
                home_lineup_pa = COALESCE(EXCLUDED.home_lineup_pa, betting_markets.home_lineup_pa),
                away_lineup_pa = COALESCE(EXCLUDED.away_lineup_pa, betting_markets.away_lineup_pa),
                home_sp_strikeouts = COALESCE(EXCLUDED.home_sp_strikeouts, betting_markets.home_sp_strikeouts),
                away_sp_strikeouts = COALESCE(EXCLUDED.away_sp_strikeouts, betting_markets.away_sp_strikeouts),
                home_lineup_k_pct = COALESCE(EXCLUDED.home_lineup_k_pct, betting_markets.home_lineup_k_pct),
                away_lineup_k_pct = COALESCE(EXCLUDED.away_lineup_k_pct, betting_markets.away_lineup_k_pct),
                model_prob_home = COALESCE(EXCLUDED.model_prob_home, betting_markets.model_prob_home),
                model_prob_away = COALESCE(EXCLUDED.model_prob_away, betting_markets.model_prob_away)
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_historical_training_data(self, data: dict):
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
                %(game_id)s, %(game_date)s, %(home_team_id)s, %(away_team_id)s, %(home_team_won)s, 
                %(home_team_runs)s, %(away_team_runs)s,
                %(home_sp_siera)s, %(away_sp_siera)s, %(home_sp_k_minus_bb)s, %(away_sp_k_minus_bb)s, 
                %(home_bullpen_siera)s, %(away_bullpen_siera)s, %(home_lineup_iso_vs_pitcher_hand)s, 
                %(away_lineup_iso_vs_pitcher_hand)s, %(home_lineup_woba_vs_pitcher_hand)s, 
                %(away_lineup_woba_vs_pitcher_hand)s, %(park_factor_runs)s, %(temperature)s, 
                %(wind_speed)s, %(wind_direction)s, %(closing_home_moneyline)s, 
                %(closing_away_moneyline)s, %(closing_total)s,
                %(home_sp_rolling_stuff)s, %(away_sp_rolling_stuff)s,
                %(home_lineup_pa)s, %(away_lineup_pa)s,
                %(home_sp_strikeouts)s, %(away_sp_strikeouts)s,
                %(home_lineup_k_pct)s, %(away_lineup_k_pct)s
            )
            ON CONFLICT(game_id) DO UPDATE SET
                home_team_won = EXCLUDED.home_team_won,
                home_team_runs = EXCLUDED.home_team_runs,
                away_team_runs = EXCLUDED.away_team_runs,
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                home_sp_siera = EXCLUDED.home_sp_siera,
                away_sp_siera = EXCLUDED.away_sp_siera,
                home_sp_k_minus_bb = EXCLUDED.home_sp_k_minus_bb,
                away_sp_k_minus_bb = EXCLUDED.away_sp_k_minus_bb,
                home_bullpen_siera = EXCLUDED.home_bullpen_siera,
                away_bullpen_siera = EXCLUDED.away_bullpen_siera,
                home_lineup_iso_vs_pitcher_hand = EXCLUDED.home_lineup_iso_vs_pitcher_hand,
                away_lineup_iso_vs_pitcher_hand = EXCLUDED.away_lineup_iso_vs_pitcher_hand,
                home_lineup_woba_vs_pitcher_hand = EXCLUDED.home_lineup_woba_vs_pitcher_hand,
                away_lineup_woba_vs_pitcher_hand = EXCLUDED.away_lineup_woba_vs_pitcher_hand,
                closing_home_moneyline = COALESCE(EXCLUDED.closing_home_moneyline, historical_training_data.closing_home_moneyline),
                closing_away_moneyline = COALESCE(EXCLUDED.closing_away_moneyline, historical_training_data.closing_away_moneyline),
                closing_total = COALESCE(EXCLUDED.closing_total, historical_training_data.closing_total),
                home_sp_rolling_stuff = EXCLUDED.home_sp_rolling_stuff,
                away_sp_rolling_stuff = EXCLUDED.away_sp_rolling_stuff,
                home_lineup_pa = EXCLUDED.home_lineup_pa,
                away_lineup_pa = EXCLUDED.away_lineup_pa,
                home_sp_strikeouts = EXCLUDED.home_sp_strikeouts,
                away_sp_strikeouts = EXCLUDED.away_sp_strikeouts,
                home_lineup_k_pct = EXCLUDED.home_lineup_k_pct,
                away_lineup_k_pct = EXCLUDED.away_lineup_k_pct
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_sportsbook_odds(self, data: dict):
        sql = """
            INSERT INTO sportsbook_odds (
                game_id, book_name, home_team_id, away_team_id, closing_home_ml, closing_away_ml, 
                opening_home_ml, opening_away_ml, home_rl, away_rl, 
                rl_price_home, rl_price_away, closing_total, opening_total, total_over_price, 
                total_under_price, last_updated
            ) VALUES (
                %(game_id)s, %(book_name)s, %(home_team_id)s, %(away_team_id)s, %(closing_home_ml)s, %(closing_away_ml)s, 
                %(opening_home_ml)s, %(opening_away_ml)s, %(home_rl)s, %(away_rl)s, 
                %(rl_price_home)s, %(rl_price_away)s, %(closing_total)s, %(opening_total)s, %(total_over_price)s, 
                %(total_under_price)s, %(last_updated)s
            )
            ON CONFLICT(game_id, book_name) DO UPDATE SET
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                closing_home_ml = EXCLUDED.closing_home_ml,
                closing_away_ml = EXCLUDED.closing_away_ml,
                opening_home_ml = COALESCE(sportsbook_odds.opening_home_ml, EXCLUDED.opening_home_ml),
                opening_away_ml = COALESCE(sportsbook_odds.opening_away_ml, EXCLUDED.opening_away_ml),
                home_rl = EXCLUDED.home_rl,
                away_rl = EXCLUDED.away_rl,
                rl_price_home = EXCLUDED.rl_price_home,
                rl_price_away = EXCLUDED.rl_price_away,
                closing_total = EXCLUDED.closing_total,
                opening_total = COALESCE(sportsbook_odds.opening_total, EXCLUDED.opening_total),
                total_over_price = EXCLUDED.total_over_price,
                total_under_price = EXCLUDED.total_under_price,
                last_updated = EXCLUDED.last_updated
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def upsert_raw_pitch(self, data: dict):
        sql = """
            INSERT INTO raw_pitches (
                pitcher_id, game_date, pitch_type, release_speed, pfx_x, pfx_z, 
                release_spin_rate, release_extension, vx0, vy0, vz0, ax, ay, az, 
                sz_top, sz_bot, plate_x, plate_z, description, whiff
            ) VALUES (
                %(pitcher_id)s, %(game_date)s, %(pitch_type)s, %(release_speed)s, %(pfx_x)s, %(pfx_z)s, 
                %(release_spin_rate)s, %(release_extension)s, %(vx0)s, %(vy0)s, %(vz0)s, %(ax)s, %(ay)s, %(az)s, 
                %(sz_top)s, %(sz_bot)s, %(plate_x)s, %(plate_z)s, %(description)s, %(whiff)s
            )
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def update_player_stuff_plus(self, player_id, season, stuff_plus):
        sql = """
            UPDATE players 
            SET stuff_plus = %s, date_updated = %s
            WHERE player_id = %s AND season = %s
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (stuff_plus, datetime.now().strftime("%Y-%m-%d"), player_id, season))
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def update_pitch_stuff_plus(self, pitch_id, stuff_plus):
        sql = "UPDATE raw_pitches SET stuff_plus = %s WHERE pitch_id = %s"
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (stuff_plus, pitch_id))
            if not self._shared_conn:
                conn.commit()
        finally:
            if not self._shared_conn:
                conn.close()

    def get_pitcher_prior_pitches(self, pitcher_id, game_date):
        sql = """
            SELECT stuff_plus FROM raw_pitches 
            WHERE pitcher_id = %s AND game_date < %s AND stuff_plus IS NOT NULL
            ORDER BY game_date ASC
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (pitcher_id, game_date))
                rows = cursor.fetchall()
                return [row['stuff_plus'] for row in rows]
        finally:
            if not self._shared_conn:
                conn.close()

    def resolve_team_id(self, name: str) -> int:
        sql = """
            SELECT mlb_id FROM team_mappings 
            WHERE team_name_short = %s OR team_full_name = %s OR odds_api_name = %s OR espn_name = %s OR fangraphs_abbr = %s
            LIMIT 1
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (name, name, name, name, name))
                res = cursor.fetchone()
                return res['mlb_id'] if res else None
        finally:
            if not self._shared_conn:
                conn.close()

    def query_agent_data(self, sql_query: str):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                # RealDictCursor means these will already behave like dicts
                return [dict(row) for row in cursor.fetchall()]
        finally:
            if not self._shared_conn:
                conn.close()

if __name__ == "__main__":
    print("Testing PostgreSQL connection...")
    try:
        manager = MLBDbManager()
        result = manager.query_agent_data("SELECT 1 AS connection_test;")
        print(f"Connection successful: {result}")
    except Exception as e:
        print(f"Connection failed: {e}")
