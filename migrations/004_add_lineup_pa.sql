-- Migration: 004_add_lineup_pa
-- Adds cumulative Plate Appearances (PA) for the starting lineup to track model confidence.

ALTER TABLE historical_training_data ADD COLUMN home_lineup_pa REAL;
ALTER TABLE historical_training_data ADD COLUMN away_lineup_pa REAL;

ALTER TABLE betting_markets ADD COLUMN home_lineup_pa REAL;
ALTER TABLE betting_markets ADD COLUMN away_lineup_pa REAL;
