-- Migration: Add Strikeout Prop Odds
-- Added: 2026-04-18

-- Add columns to historical_training_data for the over/under prices (juice)
ALTER TABLE historical_training_data ADD COLUMN home_sp_k_odds_over INTEGER;
ALTER TABLE historical_training_data ADD COLUMN home_sp_k_odds_under INTEGER;
ALTER TABLE historical_training_data ADD COLUMN away_sp_k_odds_over INTEGER;
ALTER TABLE historical_training_data ADD COLUMN away_sp_k_odds_under INTEGER;

-- Add columns to betting_markets for future live support
ALTER TABLE betting_markets ADD COLUMN home_sp_k_odds_over INTEGER;
ALTER TABLE betting_markets ADD COLUMN home_sp_k_odds_under INTEGER;
ALTER TABLE betting_markets ADD COLUMN away_sp_k_odds_over INTEGER;
ALTER TABLE betting_markets ADD COLUMN away_sp_k_odds_under INTEGER;
