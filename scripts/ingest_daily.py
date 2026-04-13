import os
import requests
import statsapi
import pandas as pd
import json
from datetime import datetime
from core.db_manager import MLBDbManager
from core import stats_calculator
from scripts.fetch_live_odds import fetch_odds_api

# --- STADIUM MAPPING (LAT/LON) ---
STADIUM_COORDS = {
    "Yankees": {"lat": 40.8296, "lon": -73.9262},
    "Dodgers": {"lat": 34.0739, "lon": -118.2400},
    "Braves": {"lat": 33.8907, "lon": -84.4678},
    "Red Sox": {"lat": 42.3467, "lon": -71.0972},
    "Mets": {"lat": 40.7571, "lon": -73.8458},
    "Cubs": {"lat": 41.9484, "lon": -87.6553},
}

def ingest_mlb_official_stats(season=2026):
    """Fetches raw stats and computes metrics for 2026."""
    print(f"Fetching full universe of MLB {season} stats...")
    manager = MLBDbManager()

    # 1. Pitching (2026)
    print("Computing 2026 pitching metrics...")
    try:
        p_data = statsapi.get('stats_leaders', {'leaderCategories': 'strikeouts', 'season': season, 'statGroup': 'pitching', 'limit': 1500})
        leaders = p_data.get('leagueLeaders', [{}])[0].get('leaders', [])
        for entry in leaders:
            player_id = entry.get('person', {}).get('id')
            name = entry.get('person', {}).get('fullName')
            try:
                p_stats = statsapi.player_stat_data(player_id, group='pitching', type='season')
                st = p_stats.get('stats', [{}])[0].get('stats', {})
                siera = stats_calculator.calculate_siera(st.get('strikeOuts', 0), st.get('baseOnBalls', 0), st.get('battersFaced', 0), st.get('groundOuts', 0), st.get('airOuts', 0), st.get('popOuts', 0))
                k_bb = stats_calculator.calculate_k_minus_bb_percent(st.get('strikeOuts', 0), st.get('baseOnBalls', 0), st.get('battersFaced', 0))
                era_val = st.get('era')
                if isinstance(era_val, str) and era_val != '-.--': era_val = float(era_val)
                elif era_val == '-.--': era_val = None
                manager.upsert_pitcher({"player_id": player_id, "season": season, "name": name, "date_updated": datetime.now().strftime("%Y-%m-%d"), "xfip": None, "siera": siera, "era": era_val, "k_minus_bb_percent": k_bb, "stuff_plus": None, "location_plus": None, "pitching_plus": None, "iso": None, "k_pct": None})
            except: continue
        print(f"Synced {len(leaders)} 2026 pitchers.")
    except Exception as e: print(f"Error: {e}")

    # 2. Individual Hitting (2026)
    print("Computing 2026 individual hitting metrics...")
    try:
        h_data = statsapi.get('stats', {'stats': 'season', 'group': 'hitting', 'season': season, 'playerPool': 'all'})
        splits = h_data.get('stats', [{}])[0].get('splits', [])
        for entry in splits:
            st = entry.get('stat', {})
            p = entry.get('player', {})
            iso = stats_calculator.calculate_iso(st.get('atBats', 0), st.get('doubles', 0), st.get('triples', 0), st.get('homeRuns', 0))
            k_pct = round(st.get('strikeOuts', 0) / st.get('plateAppearances', 1), 3) if st.get('plateAppearances') else 0.0
            manager.upsert_pitcher({"player_id": p['id'], "season": season, "name": p['fullName'], "date_updated": datetime.now().strftime("%Y-%m-%d"), "xfip": None, "siera": None, "era": None, "k_minus_bb_percent": None, "stuff_plus": None, "location_plus": None, "pitching_plus": None, "iso": iso, "k_pct": k_pct})
        print(f"Synced {len(splits)} 2026 hitters.")
    except Exception as e: print(f"Error: {e}")

    # 3. Team Hitting (2026 with Splits)
    print("Computing 2026 team metrics and Platoon Splits...")
    teams = statsapi.get('teams', {'sportId': 1})['teams']
    for team in teams:
        if team.get('active'):
            tid = team['id']
            try:
                # Overall
                o = statsapi.get('team_stats', {'teamId': tid, 'stats': 'season', 'group': 'hitting', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                # Splits
                vls = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vl', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                vrs = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vr', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                manager.upsert_hitting_lineup({
                    "team_id": tid, "season": season, "team_name": team['name'], "date_updated": datetime.now().strftime("%Y-%m-%d"),
                    "iso_vs_rhp": stats_calculator.calculate_iso(vrs.get('atBats', 0), vrs.get('doubles', 0), vrs.get('triples', 0), vrs.get('homeRuns', 0)),
                    "iso_vs_lhp": stats_calculator.calculate_iso(vls.get('atBats', 0), vls.get('doubles', 0), vls.get('triples', 0), vls.get('homeRuns', 0)),
                    "woba": o.get('obp', 0.0), "iso": stats_calculator.calculate_iso(o.get('atBats', 0), o.get('doubles', 0), o.get('triples', 0), o.get('homeRuns', 0)),
                    "k_percent": round(o.get('strikeOuts', 0) / o.get('plateAppearances', 1), 3) if o.get('plateAppearances') else 0.0
                })
            except: continue
    print("Updated 2026 team metrics.")

    # 4. Bullpens (2026)
    print("Computing 2026 Bullpen metrics...")
    for team in teams:
        if team.get('active'):
            tid = team['id']
            try:
                rps = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'pitching', 'sitCodes': 'rp', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                bp_siera = stats_calculator.calculate_siera(rps.get('strikeOuts', 0), rps.get('baseOnBalls', 0), rps.get('battersFaced', 0), rps.get('groundOuts', 0), rps.get('airOuts', 0), rps.get('popOuts', 0))
                manager.upsert_bullpen({"team_id": tid, "season": season, "team_name": team['name'], "date_updated": datetime.now().strftime("%Y-%m-%d"), "bullpen_xfip": None, "bullpen_siera": bp_siera, "top_relievers_rest_days": 0, "total_pitches_last_3_days": rps.get('numberOfPitches', 0)})
            except: continue
    print("Updated 2026 bullpens.")

def fetch_odds_espn():
    print("Fetching live MLB odds and probable pitchers...")
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            events = response.json().get('events', [])
            manager = MLBDbManager()
            matchups = []
            
            for event in events:
                comp = event['competitions'][0]
                home_team_name = comp['competitors'][0]['team']['shortDisplayName']
                away_team_name = comp['competitors'][1]['team']['shortDisplayName']
                
                # Resolve IDs
                home_id = manager.resolve_team_id(home_team_name)
                away_id = manager.resolve_team_id(away_team_name)
                
                odds_list = comp.get('odds', [])
                total, hml, aml = 0.0, 0, 0
                if odds_list:
                    o = odds_list[0]
                    total, hml, aml = o.get('overUnder', 0.0), o.get('homeTeamOdds', {}).get('value', 0), o.get('awayTeamOdds', {}).get('value', 0)
                
                gid = int(event['id'])
                iprob = abs(hml)/(abs(hml)+100) if hml < 0 else 100/(hml+100) if hml > 0 else 0.5
                
                manager.upsert_betting_market({
                    "game_id": gid, "home_team": home_team_name, "away_team": away_team_name, 
                    "home_team_id": home_id, "away_team_id": away_id,
                    "home_sp_siera": 4.20, "away_sp_siera": 4.20,
                    "home_sp_k_minus_bb": 0.14, "away_sp_k_minus_bb": 0.14,
                    "home_bullpen_siera": 3.80, "away_bullpen_siera": 3.80,
                    "home_lineup_iso_vs_pitcher_hand": 0.160, "away_lineup_iso_vs_pitcher_hand": 0.160,
                    "home_lineup_woba_vs_pitcher_hand": 0.315, "away_lineup_woba_vs_pitcher_hand": 0.315,
                    "park_factor_runs": 1.0, "temperature": 72.0, "wind_speed": 4.0, "wind_direction": "Neutral",
                    "home_pitcher": None, "away_pitcher": None,
                    "full_game_home_moneyline": int(hml), "full_game_away_moneyline": int(aml), 
                    "full_game_total": float(total), "implied_prob_home": iprob
                })
                matchups.append({"game_id": gid, "home_team": home_team_name})
            print(f"Updated odds and pitchers for {len(events)} games.")
            return matchups
    except Exception as e:
        print(f"Error fetching odds: {e}")
        return []

def fetch_weather(matchups):
    manager = MLBDbManager()
    for g in matchups:
        stadium = g['home_team']
        coords = STADIUM_COORDS.get(stadium)
        if coords:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=temperature_2m,wind_speed_10m,wind_direction_10m"
            try:
                w = requests.get(url).json()['current']
                sql = "INSERT INTO park_factors_and_weather (game_id, home_team, stadium_name, temperature, wind_speed_mph, wind_direction) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(game_id) DO UPDATE SET temperature=excluded.temperature"
                with manager._get_connection() as conn: conn.execute(sql, (g['game_id'], stadium, f"{stadium} Stadium", w['temperature_2m'], w['wind_speed_10m'], str(w['wind_direction_10m'])))
            except: continue

if __name__ == "__main__":
    ingest_mlb_official_stats(season=2026)
    fetch_odds_api()
    matchups = fetch_odds_espn()
    if matchups: fetch_weather(matchups)
    print("\n--- 2026 Daily Ingestion Complete ---")
