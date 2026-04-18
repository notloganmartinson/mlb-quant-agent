-- Migration: Add Historical Prop Archive Table
-- Added: 2026-04-18

CREATE TABLE IF NOT EXISTS historical_prop_archive (
    player_id INTEGER,
    player_name TEXT,
    game_date TEXT,
    game_id INTEGER,
    market_key TEXT, -- e.g. 'pitcher_strikeouts'
    line REAL,
    odds_over INTEGER,
    odds_under INTEGER,
    source TEXT, -- e.g. 'draftkings', 'fanduel'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, game_date, market_key, source)
);
