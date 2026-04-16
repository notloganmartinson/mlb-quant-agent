import statsapi
from datetime import datetime
from core.db_manager import MLBDbManager
from core import stats_calculator

def ingest_mlb_official_stats(season=2026):
    """Fetches raw stats and computes metrics for 2026."""
    print(f"Fetching full universe of MLB {season} stats...")
    
    with MLBDbManager() as manager:
        # 1. Pitching (2026)
        print("Computing 2026 pitching metrics...")
        try:
            p_data = statsapi.get('stats_leaders', {'leaderCategories': 'strikeouts', 'season': season, 'statGroup': 'pitching', 'limit': 1500})
            leaders = p_data.get('leagueLeaders', [{}])[0].get('leaders', [])
            pitcher_batch = []
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
                    
                    pitcher_batch.append({
                        "player_id": player_id, "season": season, "name": name, 
                        "date_updated": datetime.now().strftime("%Y-%m-%d"), 
                        "xfip": None, "siera": siera, "era": era_val, 
                        "k_minus_bb_percent": k_bb, "stuff_plus": None, 
                        "location_plus": None, "pitching_plus": None, "iso": None, "k_pct": None
                    })
                except: continue
            
            manager.upsert_many_player_stats(pitcher_batch)
            print(f"Synced {len(pitcher_batch)} 2026 pitchers.")
        except Exception as e: print(f"Error: {e}")

        # 2. Individual Hitting (2026)
        print("Computing 2026 individual hitting metrics...")
        try:
            h_data = statsapi.get('stats', {'stats': 'season', 'group': 'hitting', 'season': season, 'playerPool': 'all'})
            splits = h_data.get('stats', [{}])[0].get('splits', [])
            hitter_batch = []
            for entry in splits:
                st = entry.get('stat', {})
                p = entry.get('player', {})
                iso = stats_calculator.calculate_iso(st.get('atBats', 0), st.get('doubles', 0), st.get('triples', 0), st.get('homeRuns', 0))
                k_pct = round(st.get('strikeOuts', 0) / st.get('plateAppearances', 1), 3) if st.get('plateAppearances') else 0.0
                hitter_batch.append({
                    "player_id": p['id'], "season": season, "name": p['fullName'], 
                    "date_updated": datetime.now().strftime("%Y-%m-%d"), 
                    "xfip": None, "siera": None, "era": None, "k_minus_bb_percent": None, 
                    "stuff_plus": None, "location_plus": None, "pitching_plus": None, 
                    "iso": iso, "k_pct": k_pct
                })
            
            manager.upsert_many_player_stats(hitter_batch)
            print(f"Synced {len(hitter_batch)} 2026 hitters.")
        except Exception as e: print(f"Error: {e}")

        # 3. Team Hitting (2026 with Splits)
        print("Computing 2026 team metrics and Platoon Splits...")
        teams_resp = statsapi.get('teams', {'sportId': 1})
        teams = teams_resp['teams']
        team_batch = []
        for team in teams:
            if team.get('active'):
                tid = team['id']
                try:
                    # Overall
                    o = statsapi.get('team_stats', {'teamId': tid, 'stats': 'season', 'group': 'hitting', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                    # Splits
                    vls = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vl', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                    vrs = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vr', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                    team_batch.append({
                        "team_id": tid, "season": season, "team_name": team['name'], "date_updated": datetime.now().strftime("%Y-%m-%d"),
                        "iso_vs_rhp": stats_calculator.calculate_iso(vrs.get('atBats', 0), vrs.get('doubles', 0), vrs.get('triples', 0), vrs.get('homeRuns', 0)),
                        "iso_vs_lhp": stats_calculator.calculate_iso(vls.get('atBats', 0), vls.get('doubles', 0), vls.get('triples', 0), vls.get('homeRuns', 0)),
                        "woba": o.get('obp', 0.0), "iso": stats_calculator.calculate_iso(o.get('atBats', 0), o.get('doubles', 0), o.get('triples', 0), o.get('homeRuns', 0)),
                        "k_percent": round(o.get('strikeOuts', 0) / o.get('plateAppearances', 1), 3) if o.get('plateAppearances') else 0.0
                    })
                except: continue
        
        manager.upsert_many_hitting_lineups(team_batch)
        print(f"Updated {len(team_batch)} 2026 team metrics.")

        # 4. Bullpens (2026)
        print("Computing 2026 Bullpen metrics...")
        bullpen_batch = []
        for team in teams:
            if team.get('active'):
                tid = team['id']
                try:
                    rps = statsapi.get('team_stats', {'teamId': tid, 'stats': 'statSplits', 'group': 'pitching', 'sitCodes': 'rp', 'season': season}).get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                    bp_siera = stats_calculator.calculate_siera(rps.get('strikeOuts', 0), rps.get('baseOnBalls', 0), rps.get('battersFaced', 0), rps.get('groundOuts', 0), rps.get('airOuts', 0), rps.get('popOuts', 0))
                    bullpen_batch.append({
                        "team_id": tid, "season": season, "team_name": team['name'], 
                        "date_updated": datetime.now().strftime("%Y-%m-%d"), 
                        "bullpen_xfip": None, "bullpen_siera": bp_siera, 
                        "top_relievers_rest_days": 0, "total_pitches_last_3_days": rps.get('numberOfPitches', 0)
                    })
                except: continue
        
        manager.upsert_many_bullpens(bullpen_batch)
        print(f"Updated {len(bullpen_batch)} 2026 bullpens.")

if __name__ == "__main__":
    ingest_mlb_official_stats()
