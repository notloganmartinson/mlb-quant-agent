import os
import sys
import sqlite3
import pandas as pd
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import statsapi
from thefuzz import process

# Add project root to path
sys.path.append(os.getcwd())
from core.db_manager import MLBDbManager

def fetch_vi_k_props_playwright(date_str):
    """
    Fetches strikeout prop lines from VegasInsider for a specific date using Playwright DOM scraping.
    """
    extracted_props = {} # Keyed by pitcher name
    
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".playwright_session_vi")
        context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=True)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        
        # URL format: 2025-04-10
        url = f"https://www.vegasinsider.com/mlb/odds/player-props/?date={date_str}"
        print(f"  [VI] Scraping Strikeout Props for {date_str}...")
        
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Scrape the table directly from the DOM
            props_data = page.evaluate('''() => {
                const results = [];
                // Look for the section specifically for Strikeouts
                const allTables = Array.from(document.querySelectorAll('table.odds-widget-table'));
                let kTable = null;
                
                // Find table whose preceding header contains STRIKEOUTS
                for (const table of allTables) {
                    let prev = table.previousElementSibling;
                    while (prev) {
                        if (prev.innerText && prev.innerText.includes('STRIKEOUTS')) {
                            kTable = table;
                            break;
                        }
                        prev = prev.previousElementSibling;
                    }
                    if (kTable) break;
                }
                
                if (!kTable) {
                    // Fallback: just look for the first table that has "data-name" rows if only one table exists
                    kTable = document.querySelector('table.odds-widget-table');
                }
                
                if (!kTable) return [];
                
                const rows = Array.from(kTable.querySelectorAll('tr[data-name]'));
                for (const tr of rows) {
                    const name = tr.getAttribute('data-name');
                    const oddsCells = Array.from(tr.querySelectorAll('td.game-odds'));
                    
                    for (const cell of oddsCells) {
                        const spans = Array.from(cell.querySelectorAll('.data-value'));
                        if (spans.length >= 2) {
                            const lineStr = spans[0].innerText.trim();
                            const priceStr = spans[1].innerText.trim();
                            if (lineStr && priceStr && priceStr !== 'OFF') {
                                results.push({ name, lineStr, priceStr });
                                break; 
                            }
                        }
                    }
                }
                return results;
            }''')
            
            for p_val in props_data:
                name = p_val['name']
                line_str = p_val['lineStr'].lower()
                price_str = p_val['priceStr']
                
                side = 'over' if 'o' in line_str else 'under'
                try:
                    line = float(line_str.replace('o', '').replace('u', '').strip())
                    price = int(price_str.replace('+', '').strip())
                    
                    if name not in extracted_props:
                        extracted_props[name] = {'line': line}
                    extracted_props[name][f'odds_{side}'] = price
                except:
                    continue
                
        except Exception as e:
            print(f"    [!] VI Error for {date_str}: {e}")
        finally:
            context.close()
            
    return extracted_props

def update_historical_k_props(date_limit=None):
    manager = MLBDbManager()
    
    # Identify 2025 games with synthetic lines (-115/-115) or missing lines
    query = """
        SELECT DISTINCT game_date 
        FROM historical_training_data 
        WHERE strftime('%Y', game_date) = '2025'
        AND (
            (home_sp_k_odds_over = -115 AND home_sp_k_odds_under = -115)
            OR home_sp_k_line IS NULL
        )
        ORDER BY game_date DESC
    """
    dates = [row['game_date'] for row in manager.query_agent_data(query)]
    
    if date_limit:
        dates = [d for d in dates if date_limit in d]
    
    print(f"Syncing Real K-Props from VegasInsider for {len(dates)} dates...")
    
    for date in dates:
        vi_props = fetch_vi_k_props_playwright(date)
        if not vi_props:
            print(f"  -> {date}: No props extracted. Skipping.")
            continue
            
        games_query = f"""
            SELECT game_id, home_team_id, away_team_id 
            FROM historical_training_data 
            WHERE game_date = '{date}'
        """
        games = manager.query_agent_data(games_query)
        
        # Use statsapi to get probable pitchers for matching
        try:
            schedule = statsapi.schedule(date=date)
        except Exception as e:
            print(f"  [!] statsapi error for {date}: {e}")
            continue
            
        updated_count = 0
        prop_names = list(vi_props.keys())
        
        for g in games:
            match = next((s for s in schedule if s['game_id'] == g['game_id']), None)
            if not match: continue
            
            h_name = match.get('home_probable_pitcher')
            a_name = match.get('away_probable_pitcher')
            
            h_data, a_data = None, None
            
            if h_name:
                best_match, score = process.extractOne(h_name, prop_names) or (None, 0)
                if score > 85: h_data = vi_props[best_match]
            
            if a_name:
                best_match, score = process.extractOne(a_name, prop_names) or (None, 0)
                if score > 85: a_data = vi_props[best_match]
                
            if h_data or a_data:
                sql = """
                    UPDATE historical_training_data 
                    SET home_sp_k_line = ?, home_sp_k_odds_over = ?, home_sp_k_odds_under = ?,
                        away_sp_k_line = ?, away_sp_k_odds_over = ?, away_sp_k_odds_under = ?
                    WHERE game_id = ?
                """
                
                h_line = h_data.get('line') if h_data else None
                h_over = h_data.get('odds_over') if h_data else None
                h_under = h_data.get('odds_under') if h_data else None
                
                # If only one side is found, default the other to -115 as a conservative estimate
                # although real props usually have both.
                if h_data:
                    if h_over is not None and h_under is None: h_under = -115
                    if h_under is not None and h_over is None: h_over = -115
                
                a_line = a_data.get('line') if a_data else None
                a_over = a_data.get('odds_over') if a_data else None
                a_under = a_data.get('odds_under') if a_data else None
                
                if a_data:
                    if a_over is not None and a_under is None: a_under = -115
                    if a_under is not None and a_over is None: a_over = -115
                
                with manager._get_connection() as conn:
                    cursor = conn.execute(sql, (h_line, h_over, h_under, a_line, a_over, a_under, g['game_id']))
                    if cursor.rowcount > 0: updated_count += 1
                    
        print(f"  -> {date}: Patched {updated_count} pitchers with real market lines.")
        time.sleep(1)

if __name__ == "__main__":
    # If a date is passed as arg, only fetch that month or day
    target = sys.argv[1] if len(sys.argv) > 1 else None
    update_historical_k_props(target)
