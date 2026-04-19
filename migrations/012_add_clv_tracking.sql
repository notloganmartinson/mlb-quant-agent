-- Migration 012: Add CLV Tracking Columns

-- Update sportsbook_odds table
ALTER TABLE sportsbook_odds RENAME COLUMN home_ml TO closing_home_ml;
ALTER TABLE sportsbook_odds RENAME COLUMN away_ml TO closing_away_ml;
ALTER TABLE sportsbook_odds RENAME COLUMN total TO closing_total;

ALTER TABLE sportsbook_odds ADD COLUMN opening_home_ml INTEGER;
ALTER TABLE sportsbook_odds ADD COLUMN opening_away_ml INTEGER;
ALTER TABLE sportsbook_odds ADD COLUMN opening_total REAL;

-- Update betting_markets table
ALTER TABLE betting_markets RENAME COLUMN full_game_home_moneyline TO closing_home_moneyline;
ALTER TABLE betting_markets RENAME COLUMN full_game_away_moneyline TO closing_away_moneyline;
ALTER TABLE betting_markets RENAME COLUMN full_game_total TO closing_total;

ALTER TABLE betting_markets ADD COLUMN opening_home_moneyline INTEGER;
ALTER TABLE betting_markets ADD COLUMN opening_away_moneyline INTEGER;
ALTER TABLE betting_markets ADD COLUMN opening_total REAL;
