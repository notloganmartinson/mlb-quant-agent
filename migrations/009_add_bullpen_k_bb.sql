-- Migration: Add Granular Bullpen Features (Sprint 5)
-- Added: 2026-04-18

-- Add columns to historical_training_data
ALTER TABLE historical_training_data ADD COLUMN home_bullpen_k_bb REAL;
ALTER TABLE historical_training_data ADD COLUMN away_bullpen_k_bb REAL;

-- Add columns to betting_markets for live predictions
ALTER TABLE betting_markets ADD COLUMN home_bullpen_k_bb REAL;
ALTER TABLE betting_markets ADD COLUMN away_bullpen_k_bb REAL;
