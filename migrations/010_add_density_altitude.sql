-- Migration: Add Density Altitude Feature (Sprint 6)
-- Added: 2026-04-18

-- Add columns to historical_training_data
ALTER TABLE historical_training_data ADD COLUMN density_altitude REAL;

-- Add columns to betting_markets for live predictions
ALTER TABLE betting_markets ADD COLUMN density_altitude REAL;
