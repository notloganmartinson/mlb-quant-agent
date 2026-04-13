import statsapi
from core.db_manager import MLBDbManager
from core import stats_calculator
from datetime import datetime

def ingest_2025_baseline():
    """
    Automated ingestion of full 2025 season stats to provide a stable baseline.
    """
    season = 2025
    print(f"Fetching full 2025 season baseline (No CSV needed)...")
    manager = MLBDbManager()

    # 1. Pitching Baseline
    print("Ingesting 2025 Pitching...")
    try:
        p_data = statsapi.get('stats', {'stats': 'season', 'group': 'pitching', 'season': season, 'playerPool': 'all'})
        all_pitchers = p_data.get('stats', [{}])[0].get('splits', [])
        for p_entry in all_pitchers:
            st = p_entry.get('stat', {})
            player = p_entry.get('player', {})
            player_id = player.get('id')
            name = player.get('fullName')
            if not player_id: continue
            
            siera = stats_calculator.calculate_siera(st.get('strikeOuts', 0), st.get('baseOnBalls', 0), st.get('battersFaced', 0), st.get('groundOuts', 0), st.get('airOuts', 0), st.get('popOuts', 0))
            k_bb_pct = stats_calculator.calculate_k_minus_bb_percent(st.get('strikeOuts', 0), st.get('baseOnBalls', 0), st.get('battersFaced', 0))
            
            pitcher_stats = {
                "player_id": player_id, "season": season, "name": name, "date_updated": "2025-12-31",
                "xfip": None, "siera": siera, "era": st.get('era'), "k_minus_bb_percent": k_bb_pct,
                "stuff_plus": None, "location_plus": None, "pitching_plus": None,
                "iso": None, "k_pct": None
            }
            manager.upsert_pitcher(pitcher_stats)
        print(f"Successfully synced {len(all_pitchers)} historical pitchers.")
    except Exception as e:
        print(f"Error fetching 2025 pitchers: {e}")

    # 2. Team Hitting Baseline
    print("Ingesting 2025 Team Hitting...")
    try:
        teams_data = statsapi.get('teams', {'sportId': 1})['teams']
        for team in teams_data:
            if team.get('active'):
                team_id = team['id']
                team_name = team['name']
                # Overall
                o_raw = statsapi.get('team_stats', {'teamId': team_id, 'stats': 'season', 'group': 'hitting', 'season': season})
                o_st = o_raw.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                # ISO vs LHP
                vl_raw = statsapi.get('team_stats', {'teamId': team_id, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vl', 'season': season})
                vls = vl_raw.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
                # ISO vs RHP
                vr_raw = statsapi.get('team_stats', {'teamId': team_id, 'stats': 'statSplits', 'group': 'hitting', 'sitCodes': 'vr', 'season': season})
                vrs = vr_raw.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})

                lineup_stats = {
                    "team_id": team_id, "season": season, "team_name": team_name, "date_updated": "2025-12-31",
                    "iso_vs_rhp": stats_calculator.calculate_iso(vrs.get('atBats', 0), vrs.get('doubles', 0), vrs.get('triples', 0), vrs.get('homeRuns', 0)),
                    "iso_vs_lhp": stats_calculator.calculate_iso(vls.get('atBats', 0), vls.get('doubles', 0), vls.get('triples', 0), vls.get('homeRuns', 0)),
                    "woba": o_st.get('obp', 0.0), 
                    "iso": stats_calculator.calculate_iso(o_st.get('atBats', 0), o_st.get('doubles', 0), o_st.get('triples', 0), o_st.get('homeRuns', 0)),
                    "k_percent": round(o_st.get('strikeOuts', 0) / o_st.get('plateAppearances', 1), 3) if o_st.get('plateAppearances') else 0.0
                }
                manager.upsert_hitting_lineup(lineup_stats)
        print("Updated 2025 team metrics.")
    except Exception as e:
        print(f"Error fetching 2025 team stats: {e}")

if __name__ == "__main__":
    ingest_2025_baseline()
