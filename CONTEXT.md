# CONTEXT.md - Sprint: Architectural Audit & Flaw Verification

## 1. Mission Objective
Conduct a targeted code audit of the MLB predictive pipeline. Recent backtest metrics (63% win rate, 4% ROI) are highly suspicious. The objective of this session is to investigate the codebase for specific data leaks, mathematical mismatches, and synthetic data generation that are artificially inflating model performance. 

## 2. Rules of Engagement
* **Read-Only Mode:** Do not attempt to refactor or rewrite the code yet. Your sole task right now is to locate, verify, and report on the flaws listed below.
* **Read-Before-Write Protocol:** Use the `GEMINI.md` AST map to locate functions, but you MUST read the full source file before confirming a flaw. Do not hallucinate logic.
* **Be Ruthlessly Objective:** Treat the codebase as hostile. Look for where the math breaks down.

## 3. The Audit Targets
Please investigate the following 5 specific vulnerabilities and report back confirming their existence and exact line locations:

### Target A: The Phantom Target (Data Generation)
* **Files to check:** `scripts/generate_training_data.py`, `core/db_manager.py`, `ml/preprocess.py`
* **Suspicion:** The ingestion script and DB manager never actually save `home_team_runs` or `away_team_runs`. This forces `ml/preprocess.py` to generate synthetic random noise, meaning the XGBoost model is training on fake data, not baseball games.

### Target B: The Calibration Leak
* **Files to check:** `ml/train_xgboost.py`
* **Suspicion:** The `IsotonicRegression` calibration layer is being `.fit()` directly on `test_win_prob_raw` (the holdout test set) rather than a dedicated validation split, guaranteeing an artificially perfect Log-Loss score.

### Target C: Mathematical Mismatch (Tweedie vs. Skellam)
* **Files to check:** `ml/train_xgboost.py`
* **Suspicion:** The XGBoost objective was updated to `reg:tweedie` (Compound Poisson-Gamma) to handle overdispersion, but the raw probabilities are still being calculated using `scipy.stats.skellam`. Skellam strictly requires Poisson distributions, making the current probability math invalid.

### Target D: The API Crash
* **Files to check:** `ml/backtest.py`
* **Suspicion:** The script calls `predict_proba(X_test)` on the loaded model. However, the model is saved as a `MultiOutputRegressor`, which does not possess a `predict_proba` method. This script should currently be crashing.

### Target E: The Median Future Leak
* **Files to check:** `ml/preprocess.py`
* **Suspicion:** Missing values are being filled using a global median (`X.fillna(X.median())`) *before* the time-series split (`train_mask` / `test_mask`). This leaks 2025 statistical data into the 2022-2024 training set.

## 4. Expected Output
Read the necessary files and provide a concise "Audit Report" confirming whether these flaws exist in the current implementation, explaining briefly how they manifest in the code.
