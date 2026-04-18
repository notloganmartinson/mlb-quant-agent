-- Migration: Add Advanced K-Prop Features (Sprint 4)
-- Added: 2026-04-18

-- Add columns to historical_training_data
ALTER TABLE historical_training_data ADD COLUMN umpire_k_pct REAL;
ALTER TABLE historical_training_data ADD COLUMN park_factor_k REAL;

-- Add columns to betting_markets for live predictions
ALTER TABLE betting_markets ADD COLUMN umpire_k_pct REAL;
ALTER TABLE betting_markets ADD COLUMN park_factor_k REAL;
