-- Migration: 003_add_rolling_stuff.sql
-- Description: Add rolling stuff columns to training data and betting markets, and add stuff_plus to raw_pitches.

-- historical_training_data additions
ALTER TABLE historical_training_data ADD COLUMN home_sp_rolling_stuff REAL;
ALTER TABLE historical_training_data ADD COLUMN away_sp_rolling_stuff REAL;

-- betting_markets additions
ALTER TABLE betting_markets ADD COLUMN home_sp_rolling_stuff REAL;
ALTER TABLE betting_markets ADD COLUMN away_sp_rolling_stuff REAL;

-- raw_pitches addition (to store pitch-level Stuff+ values)
ALTER TABLE raw_pitches ADD COLUMN stuff_plus REAL;
