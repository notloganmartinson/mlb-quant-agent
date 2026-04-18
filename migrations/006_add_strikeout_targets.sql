-- Migration: Add Strikeout Targets and Lineup K%
-- Added: 2026-04-16

-- Add columns to historical_training_data
ALTER TABLE historical_training_data ADD COLUMN home_sp_strikeouts INTEGER;
ALTER TABLE historical_training_data ADD COLUMN away_sp_strikeouts INTEGER;
ALTER TABLE historical_training_data ADD COLUMN home_lineup_k_pct REAL;
ALTER TABLE historical_training_data ADD COLUMN away_lineup_k_pct REAL;

-- Add columns to betting_markets
ALTER TABLE betting_markets ADD COLUMN home_sp_strikeouts INTEGER;
ALTER TABLE betting_markets ADD COLUMN away_sp_strikeouts INTEGER;
ALTER TABLE betting_markets ADD COLUMN home_lineup_k_pct REAL;
ALTER TABLE betting_markets ADD COLUMN away_lineup_k_pct REAL;
