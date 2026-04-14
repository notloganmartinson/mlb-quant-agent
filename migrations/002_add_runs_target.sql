-- Migration: 002_add_runs_target.sql
-- Description: Add home_team_runs, away_team_runs, and stuff_plus columns to historical_training_data and betting_markets.

-- historical_training_data additions
ALTER TABLE historical_training_data ADD COLUMN home_team_runs INTEGER;
ALTER TABLE historical_training_data ADD COLUMN away_team_runs INTEGER;
ALTER TABLE historical_training_data ADD COLUMN home_sp_stuff_plus REAL;
ALTER TABLE historical_training_data ADD COLUMN away_sp_stuff_plus REAL;

-- betting_markets additions
ALTER TABLE betting_markets ADD COLUMN home_sp_stuff_plus REAL;
ALTER TABLE betting_markets ADD COLUMN away_sp_stuff_plus REAL;
