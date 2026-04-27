ALTER TABLE betting_markets ADD COLUMN IF NOT EXISTS model_prob_home REAL;
ALTER TABLE betting_markets ADD COLUMN IF NOT EXISTS model_prob_away REAL;
