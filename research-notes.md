# Research Notes: The ReAct Pattern in Autonomous Agents

## Case Study: Self-Correction in the MLB Betting Agent
**Date:** April 12, 2026
**Subject:** Observational analysis of a multi-turn ReAct (Reasoning + Acting) loop.

### 1. The Observation
During a query regarding "Pitchers with high ERA-SIERA differentials and their K-BB%," the agent provided two distinct text outputs. 
- **Output A:** A list of pitchers meeting the ERA/SIERA criteria.
- **Output B:** The same list, but enriched with the requested K-BB% metrics.

### 2. The Mechanics of the ReAct Loop
The agent follows the **ReAct (Reason + Act)** framework. This is implemented in `agent.py` via a `while response.function_calls` loop. The cycle functions as follows:

1.  **Reasoning:** The LLM analyzes the user prompt and determines what data is missing.
2.  **Acting:** The LLM generates a tool call (SQL query).
3.  **Observation:** The Python script executes the SQL and feeds the results back to the LLM.
4.  **Refinement:** The LLM compares the "Observation" with the original "Goal."

### 3. Deep Dive: The "Self-Correction" Phenomenon
In this specific instance, the agent demonstrated **Autonomous Recovery**. 

*   **The Initial Failure:** In the first "Action" phase, the agent generated a SQL query that selected `name`, `era`, and `siera`, but omitted `k_minus_bb_percent`. 
*   **The Mid-Loop Realization:** Upon receiving the results of Query 1 (the Observation), the agent's internal reasoning recognized a **Gap in Fulfillment**. It realized it had the list of pitchers but could not yet provide the K-BB% statistics requested by the user.
*   **The Second Action:** Instead of terminating the loop or asking the user for help, the agent immediately generated a second Tool Call to fetch the missing `k_minus_bb_percent` for that specific list of players.
*   **The Final Response:** Only once the "Observation" matched the "Goal" (having all three metrics) did the agent exit the tool-calling loop and provide the final synthesis.

### 4. Significance for Research
This behavior highlights the superiority of **Stateful Agentic Loops** over simple "one-shot" prompting. 

- **Reliability:** In a one-shot system, the missing K-BB% would simply be a failed requirement. In a ReAct system, the agent has the "agency" to recognize its own mistake and fix it dynamically.
- **Explainability:** The "Double Output" seen in the terminal is a window into the agent's "Chain of Thought." It allows the developer to see exactly where the agent pivoted from a partial answer to a complete one.

### 5. Technical Implementation Details
The loop is sustained by the following Python logic:
```python
while response.function_calls:
    # 1. Capture the 'Action' (Function Call)
    # 2. Execute the 'Observation' (SQL Execution)
    # 3. Feed back to the LLM
    response = chat.send_message(types.Part.from_function_response(...))
    # Loop repeats if the LLM decides it needs more data
```
This ensures the agent remains in a "Thinking" state until it explicitly decides it has sufficient information to respond to the user.

---

## Machine Learning Pipeline: Feature Engineering & Model Selection

### 1. The Training Dataset
A specialized repository, `historical_training_data`, was constructed to facilitate supervised learning. 
- **Sample Size:** 8,551 games (comprising the full 2023, 2024, and 2025 MLB regular seasons).
- **Ingestion Methodology:** Data was fetched sequentially via the MLB StatsAPI using a monthly chunking strategy to ensure 100% uptime and bypass API timeout restrictions.

### 2. Feature Architecture (Independent Variables)
The dataset utilizes a "Mirrored Feature Set," where every training column has a corresponding live equivalent in the `betting_markets` table. Key features include:
- **Pitching Stability:** Rolling SIERA and K-BB% for both starting pitchers and relief corps.
- **Offensive Variance:** Team-level ISO and wOBA, filtered by pitcher-handedness (LHP/RHP platoon splits).
- **Environmental Anchors:** Stadium-specific park factors, real-time temperature, and wind velocity.

### 3. Avoiding Temporal Data Leakage
A critical component of this research was the implementation of a **Rolling cumulative feature store**. By utilizing the vectorized Pandas `.shift(1)` operation during dataset generation, the system ensures that every game’s features represent the "Current State" of player skill *prior* to the first pitch. This eliminates "Look-Ahead Bias," ensuring that end-of-season results do not pollute early-season predictions.

### 4. Future Research: Model Comparison
The next phase of research will involve a head-to-head performance comparison between two distinct architectural approaches to calculate the Win Probability ($p$):

1.  **Gradient Boosted Decision Trees (XGBoost):**
    - **Hypothesis:** XGBoost will excel at handling the non-linear relationships between environmental variables (Wind/Temp) and proprietary skill metrics (SIERA).
    - **Optimization:** Hyperparameter tuning using Bayesian Optimization.

2.  **Deep Learning (Neural Network):**
    - **Hypothesis:** A multi-layer perceptron (MLP) architecture may identify subtle, latent interactions between platoon splits and bullpen fatigue that traditional tree-based models might overlook.
    - **Architecture:** Dense layers with Dropout for regularization and a Softmax output for binary classification (Win/Loss).

### 5. Evaluation Framework
Both models will be evaluated using **Log-Loss** (to measure the accuracy of the probability estimates) and **Kelly ROI**. The ultimate goal is to determine which architecture provides the most accurate $p$ value for the Kelly Criterion tool, thereby maximizing long-term bankroll growth.

---

## Codebase Refactor: Architecting for AI-Assisted Development (April 2026)

### 1. Objective: Efficiency & Context Management
The project underwent a significant architectural refactor to optimize for AI-assisted development. The primary goals were to reduce **context bloat** (preventing large, monolithic files from exhausting the LLM's context window) and eliminate **logic leaking** (ensuring clear boundaries between data, math, and execution).

### 2. Step-by-Step Refactor & Reasoning

#### Phase 1: Mathematical Bulletproofing (`core/stats_calculator.py`)
- **Change:** Added fail-fast `assert` statements to all statistical formulas (SIERA, ISO, K-BB%).
- **Reasoning:** To prevent "Silent Failures" and divide-by-zero errors. By enforcing strict assertions at the function level, we ensure the agent or developer is immediately alerted to data quality issues (e.g., a player with 0 Plate Appearances) before incorrect stats are saved to the database.
- **Verification:** Created `test_stats_calculator.py` to serve as a 100% verified baseline for all future math changes.

#### Phase 2: Schema Isolation (`core/schema.sql`)
- **Change:** Extracted all SQL `CREATE TABLE` and `DROP TABLE` statements from `core/database.py` into a standalone `core/schema.sql` file.
- **Reasoning:** This centralizes the "Source of Truth" for the database structure. It allows the agent to read the schema directly from a clean SQL file rather than parsing Python strings, reducing the potential for hallucination and making schema-aware prompts more efficient.

#### Phase 3: Script Atomicity (`scripts/ingest/`)
- **Change:** Shattered the monolithic `scripts/ingest_daily.py` into three single-responsibility modules:
  - `stats.py`: MLB official player/team stats.
  - `odds.py`: ESPN market data and matchups.
  - `environment.py`: Stadium coordinates and weather.
- **Reasoning:** Monolithic scripts are prone to "Context Poisoning," where unrelated logic (e.g., weather API calls) distracts the AI from debugging a stats ingestion issue. Atomicity ensures that each module is small, testable, and focused on one domain.
- **Verification:** Implemented a **Snapshot Verification** tool to confirm that the new orchestrator produced 100% identical data output to the original script.

#### Phase 4: Dependency Injection (`agent.py`)
- **Change:** Refactored the `MLBAgent` into a class-based structure that accepts a `db_path` during initialization.
- **Reasoning:** This decouples the agent's core reasoning from the physical environment. By injecting the database connection rather than hardcoding `data/mlb_betting.db`, we enable the agent to run against "Sandboxed" or "Backtest" databases without modifying the source code, making the system much more portable and secure.

### 3. Outcome: A Modular & Verifiable System
This refactor transformed the codebase from a "Script-Heavy" prototype into a "Modular-First" architecture. The system is now:
- **Easier to Maintain:** Bug fixes are isolated to specific domain modules.
- **Faster for AI:** The agent can read smaller files and has a clear SQL schema to reference.
- **Secure:** Assertions and Dependency Injection provide robust guardrails against data corruption and environmental coupling.

### 4. Specialized Tooling: The AST Repo Map (`scripts/generate_repo_map.py`)
To further optimize the agent's performance, a specialized `generate_repo_map.py` script was created. This script produces a non-traditional `GEMINI.md` file that functions as a "High-Resolution Skeleton" of the entire codebase.

#### Why an AST Map instead of a standard `GEMINI.md`?
Traditional `GEMINI.md` files are often prose-heavy, describing project goals or setup steps. While useful for humans, they are **token-expensive** and often lack the **structural precision** an agent needs for complex refactoring.

The AST (Abstract Syntax Tree) Repo Map approach provides several key advantages:
1.  **Context Density:** By extracting only class/function signatures and the first line of docstrings, the map provides a 30,000-foot view of the project's logic using less than 5% of the tokens required to read the full source code.
2.  **Hallucination Prevention:** The map includes explicit **SYSTEM INSTRUCTIONS** that command the agent to never assume logic exists and to always request the full file path before attempting a modification. This "Read-Before-Write" protocol is critical for maintaining codebase integrity.
3.  **Architectural Grounding:** It allows the agent to see cross-file dependencies (e.g., ensuring `agent.py` uses the exact signature from `core/db_manager.py`) without having to manually grep the entire repository.
4.  **Automatic Synchronization:** The script can be run after any major refactor to ensure the agent's "Internal Map" is instantly updated to reflect the new modular architecture.

## Phase V: Quantitative Backtesting & Model Evolution (2025 Season)

Following the validation of the tool-grounded architecture, the research shifted toward the longitudinal evaluation of the XGBoost predictive engine. The 2025 MLB season was utilized as a primary holdout set to simulate real-market performance across three distinct iterations of model logic.

### Iteration 1: The Baseline (Static Expanding Features)
**Configuration:**
- **Training Set:** 2023-2024 (Full Seasons).
- **Feature Engineering:** `expanding().sum()` cumulative rolling statistics with $N-1$ shift.
- **Wager Logic:** Single-side Kelly Criterion (0.25 fractional) on Home Moneyline only.
- **Market Data:** SBR Closing Lines (dropped $NULL$ values).

**Results:**
- **Total Games Simulated:** 2,601
- **Total Profit (Units):** 0.48
- **Simulated ROI:** 3.14%

**Analysis:**
The baseline iteration demonstrated structural alpha, suggesting that even a simplified cumulative feature set can identify market inefficiencies. However, the reliance on expanding windows created a "dilution effect," where early-season performance carried equal weight to late-season form, potentially ignoring the high-variance nature of player development and mechanical adjustments.

---

### Iteration 2: Temporal Reactivity (EWMA & Two-Way Exploitation)
**Motivation:** 
To enhance the model's sensitivity to "recent form" and expand the exploitable market universe to include visitor value.

**Configuration:**
- **Feature Engineering:** Exponentially Weighted Moving Averages (EWMA) replaced static expanding sums. 
    - Pitching Span: 25 games (~5-start rotation cycle).
    - Hitting Span: 30 games (~1 calendar month).
- **Wager Logic:** Two-way market exploitation. The system evaluated both Home and Away Expected Value (EV) and selected the side with the highest positive edge.

**Results:**
- **Total Games Simulated:** 2,601
- **Total Profit (Units):** 0.22
- **Simulated ROI:** 0.42%

**Analysis:**
The significant degradation in ROI (from 3.14% to 0.42%) revealed a critical failure in the reactivity-precision tradeoff. The EWMA features, while capturing recent trends, introduced "feature noise" that the XGBoost model overfit during the 2023-2024 training phase. Furthermore, the two-way logic forced the model to chase marginal edges. In a high-juice environment (Vegas Vigorish), betting on low-conviction edges resulted in a "death by a thousand cuts," where the cost of the spread outweighed the model's predictive advantage.

---

### Iteration 3: Structural Regularization & Decision Filtering
**Motivation:**
To counteract the volatility and "Vig Erosion" introduced in Iteration 2, a strict decision filter was applied to the uncalibrated model.

**Configuration:**
- **Decision Filter:** Mandatory minimum Expected Value (EV) of **2.0%** required to authorize a wager.
- **Goal:** To convert from a "High-Frequency" to a "High-Conviction" engine.

**Results:**
- **Total Games Simulated:** 2,601
- **Total Profit (Units):** 0.34
- **Simulated ROI:** 0.68%

**Analysis:**
The slight recovery (from 0.42% to 0.68%) confirmed that decision filtering is effective at mitigating losses from marginal, low-conviction wagers. However, the system remained prone to "Kelly Over-Staking" due to the uncalibrated nature of the raw XGBoost probability outputs.

---

### Iteration 4: Probability Calibration (Platt Scaling)
**Motivation:**
To align the model's win-probability estimates with real-world outcomes, ensuring the Kelly Criterion stakes capital proportionally to the true mathematical edge.

**Configuration:**
- **Method:** `CalibratedClassifierCV` (Sigmoid/Platt Scaling) with 5-fold cross-validation.
- **Threshold:** Maintained the 2.0% EV Decision Filter.

**Results:**
- **Total Games Simulated:** 2,601
- **Total Bets Placed:** 1,854
- **Total Profit (Units):** 0.54
- **Simulated ROI:** 1.07%

**Analysis:**
The recovery to a **1.07% ROI** represents the most significant breakthrough since the baseline. By calibrating the probabilities, the model reduced "bankroll churn" on overconfident estimates. The 1,854 bets placed (out of 2,601 possible) indicate that the 2% EV filter is actively removing the noisest ~30% of the market. While still below the 3.14% baseline, Iteration 4 provides a statistically stable foundation for professional two-way market exploitation.

---

### Iteration 5: The Simplicity Alpha (A/B Test: Breakthrough Stack)
**Motivation:**
A final A/B test to determine if the modern risk-management constraints (Calibration + Filtering) perform better on the original, stable feature set.

**The Breakthrough Stack:**
1.  **Feature Set:** Cumulative Expanding Sums (Iteration 1).
2.  **Probability Engine:** Platt Scaling (Iteration 4).
3.  **Market Focus:** Home-Side Only.
4.  **Risk Filter:** Strict 5.0% EV Threshold.

**Results:**
- **Total Games Simulated:** 2,601
- **Total Bets Placed:** 512
- **Total Bets Won:** 239
- **Win Rate:** 46.68%
- **Total Profit (Units):** 0.61
- **Simulated ROI:** 4.07%

**Analysis:**
The 4.07% ROI achieved here is the highest recorded in the 2025 backtest suite. 

**The Quant "Holy Grail":**
The win rate of **46.68%** is perhaps the most telling metric. The system is losing more bets than it wins, yet it is generating substantial profit. This is the "Holy Grail" of sports quant modeling; it indicates the model is not just predicting winners, but specifically **identifying heavy underdogs (e.g., +140 or higher) that have a much better chance of winning than the market price suggests.** The profit is derived from consistently exploiting these mispriced "Longshots" rather than chasing high-probability favorites.

---

### Iteration 6: Dynamic EV Thresholding (Volatility Guardrails)
**Motivation:**
To improve the win rate and protect the bankroll from high-variance "Longshots" (+150 or higher) that may possess a high theoretical edge but a low absolute probability of success.

**Configuration:**
- **Feature Set:** Stable Baseline (Iteration 5).
- **Decision Logic:** Sliding EV Threshold based on Vegas Implied Probability.
    - Implied Prob >= 40% (Odds <= +150): **5.0% EV Threshold**.
    - Implied Prob < 40% (Odds > +150): **8.0% EV Threshold**.
- **Market Focus:** Home-Side Only.

**Results:**
- **Total Games Simulated:** 2,601
- **Total Bets Placed:** 512
- **Total Bets Won:** 239
- **Win Rate:** 46.68%
- **Total Profit (Units):** 0.61
- **Simulated ROI:** 4.07%

Analysis:
The results matched Iteration 5 exactly, indicating that the current model's authorized wagers were already concentrated in the "Slight Underdog/Favorite" zone, or that the "Heavy Underdog" edges did not exceed the new 8.0% barrier. While the ROI did not increase in this specific simulation, the implementation of **Dynamic EV Thresholding** is a critical architectural upgrade for live deployment. It provides a "Volatility Safety Net," ensuring the system only attacks heavy underdogs when the conviction is exceptionally high, thereby protecting the win rate from the noise of low-probability longshots.

---

### Iteration 7: The Pristine Holdout (2022 Validation)
**Motivation:**
To verify if the 4.07% ROI from Iteration 5 was a legitimate market discovery or a result of "Strategy Snooping" (Human Overfitting). The model was tested on the 2022 season—a dataset it had never seen and that was not used during the A/B testing phase.

**Configuration:**
- **Training Set:** 2023-2024.
- **Test Set:** 2022 (Pristine Holdout).
- **The Stack:** Baseline Features + Platt Scaling + Dynamic EV Thresholding.

**Results:**
- **Total Games Simulated:** 2,672
- **Total Bets Placed:** 607
- **Total Bets Won:** 248
- **Win Rate:** 40.86%
- **Total Profit (Units):** -0.40
- **Simulated ROI:** -2.24%

**Analysis: The "Fluke" Confirmed**
The complete reversal of ROI (from +4.07% to -2.24%) provides a critical research lesson: **The "Breakthrough Stack" was overfit to the specific variance of the 2025 season.** 

By iterating on the strategy *after* observing the 2025 results, the research accidentally engaged in "Backtest Overfitting." The model didn't find a universal edge; it found a strategy that happened to work well in 2025. The drop in win rate (nearly 6%) indicates that the "Underdog Identification" logic was not robust enough to survive the different market conditions of 2022.

---

## Future Research Directions: Beyond the Fluke

The failure of Iteration 7 necessitates a shift from **Strategy Optimization** to **Signal Reconstruction**. To achieve a robust, multi-season ROI, the following vectors must be pursued:

1.  **Technical Debt (The Median Leak):** 
    The preprocessing logic currently calculates medians across the entire dataset before splitting. This minor "future leak" must be resolved to ensure the model is 100% temporally honest.

2.  **Higher-Density Features (Situational Math):**
    The "Expanding Sum" features are too blunt. The model needs to transition from "Season-Level Talent" to "Game-Level Tactics":
    - **Platoon Splits:** Calculating ISO/wOBA specifically against the hand of the starting pitcher.
    - **Bullpen Fatigue:** Integrating rolling 3-day pitch counts to identify vulnerable underdogs in late innings.

3.  **K-Fold Walk-Forward Validation:**
    Future iterations must be validated using a "Walk-Forward" approach (e.g., Train '22 -> Test '23; Train '22-'23 -> Test '24) to ensure that alpha is persistent across varying seasonal environments.

---

## Pitch-Level Modeling: The "Stuff+" Breakthrough (April 2026)

### 1. Abstract
The transition from game-level aggregation to pitch-level modeling represents a fundamental shift from **Outcome-Based Analysis** to **Process-Grounded Prediction**. By isolating the physical components of a pitch (velocity, movement, release point, and approach angle) from the result (strike, out, hit), we can derive a "Pure Talent" metric that is significantly more stable and predictive of long-term success than traditional sabermetrics like ERA or SIERA.

### 2. Methodology: Feature Engineering & The Physics of the Whiff
The model, developed in `ml/train_stuff_plus.py`, utilizes an XGBoost binary classifier to predict the **Probability of a Whiff ($pWhiff$)** for every pitch in the Statcast universe. The features are derived exclusively from biomechanical and physics-based data, ensuring zero leakage from the defense or stadium:

- **Velocity & Extension:** Raw release speed and the distance toward the plate at release, which determines "Perceived Velocity."
- **Movement (pfx_x, pfx_z):** Horizontal and vertical break, normalized to capture the "Shape" of the pitch.
- **Vertical Approach Angle (VAA):** Calculated in `core/stats_calculator.py`, this represents the angle at which the ball enters the strike zone. High-VAA fastballs at the top of the zone are a primary driver of modern whiffs.
- **Break Magnitude:** The Pythagorean sum of horizontal and vertical movement, capturing the total deviation from a straight line.

### 3. Normalization: The "Plus" Notation
To ensure the metric is intuitive for analytical use, the raw $pWhiff$ is normalized against the league-average $pWhiff$ for that specific pitch type. 

$$Stuff+ = \left( \frac{pWhiff_{Pitcher}}{pWhiff_{League\_Avg\_by\_Type}} \right) \times 100$$

- **100:** Represents league-average "Stuff" for that pitch type.
- **120:** Represents a pitch that generates whiffs at a rate 20% higher than the league average.
- **80:** Represents a pitch that is 20% less likely to generate a whiff than the league average.

### 4. Aggregation and Integration
The pitch-level results are averaged across all pitches thrown by a pitcher within a specific season and stored in the `starting_pitchers.stuff_plus` column. This creates a "Process Anchor" for the game-level master model. By providing the master XGBoost engine with a stable read on a pitcher's raw physical capability, the system can better distinguish between a "Good Pitcher with Bad Luck" and a "Poor Pitcher with Good Results."

### 5. Research Significance
Stuff+ serves as the ultimate "Talent Floor." While outcomes like SIERA can be noisy in small samples (especially early in the season), a pitcher's velocity and movement stabilize almost immediately (often within 50-100 pitches). This allows the betting engine to identify undervalued pitchers in April—before the market has fully adjusted to their physical growth or mechanical improvements.

---

## Phase VI: Probability Calibration & 2025 Walk-Forward Validation (April 2026)

### 1. The Skellam Correction (Math Integrity)
**The Bug:** The initial model used `1 - skellam.cdf(0, ...)` which failed to account for ties (impossible in MLB) and resulted in physically inconsistent win probabilities (e.g., a team projected for more runs receiving < 50% win probability).
**The Fix:** Updated the win probability calculation to strictly isolate the "Home Win" case and redistribute the probability of a tie:
- `prob_home_win = skellam.sf(0, home_runs, away_runs)`
- `prob_tie = skellam.pmf(0, home_runs, away_runs)`
- `final_p = prob_home_win / (1 - prob_tie)`

### 2. Overdispersion Upgrade (Tweedie Regression)
**Motivation:** Run scoring in baseball is overdispersed (variance > mean), which the standard Poisson distribution (`count:poisson`) cannot fully capture, leading to "thin tails" in blowout scenarios.
**Implementation:** Migrated the XGBoost objective to `reg:tweedie`.
- **Tuning:** Integrated `tweedie_variance_power` (1.1 to 1.9) into the hyperparameter search space.
- **Result:** Improved MAE and Log-Loss by better modeling the variance in high-scoring games.

### 3. The Calibration Engine (Isotonic Regression)
**Motivation:** Raw probabilities derived from the Skellam distribution often exhibit systematic bias. A "60% model projection" may only win 55% of the time in reality.
**Implementation:** Added a post-processing `IsotonicRegression` layer fitted on the holdout set's predicted probabilities vs. actual outcomes.
**Impact:**
- **Brier Score Improvement:** Reduced from 0.2407 to **0.2328**.
- **Log-Loss Improvement:** Reduced from 0.6723 to **0.6583**.
- This ensures the model's $p$ values are "Strictly Calibrated" to empirical frequencies before being passed to the Kelly Criterion.

### 4. 2025 Walk-Forward Validation (The Reality Check)
**The Test:** To eliminate data leakage and "Strategy Snooping," the model was trained strictly on 2022-2024 data and tested on the entirely unseen 2025 season.
**Results:**
- **Test Win Accuracy:** **63.03%**
- **Calibrated Log-Loss:** **0.6583**
- **Calibrated Brier Score:** **0.2328**

**Conclusion:** The 63% accuracy is a robust, persistent signal. The combination of Tweedie overdispersion handling and Isotonic calibration has created a syndicate-grade predictive engine ready for live 2026 deployment.

---

## Phase VII: Leakage Resolution & Stuff+ Integration (Mid-April 2026)

### 1. Abstract
Despite high initial reported performance (63% accuracy and 4% ROI), the codebase was discovered to suffer from critical structural integrity issues, specifically target data corruption, Look-Ahead Bias, and mathematical mismatches. This sprint overhauled the pipeline to enforce strict honesty, patched missing feature data using high-efficiency SQL querying, and ultimately integrated pitch-level `Stuff+` metrics into the primary predictive model.

### 2. Structural Pipeline Fixes
A systematic audit revealed and resolved four major flaws:
1.  **The "Phantom Target":** The initial ingestion scripts failed to capture actual run totals, forcing the preprocessor to generate synthetic noise (`4.7 +/- 1.0`). We updated ingestion and database ops to pass and persist actual `home_team_runs` and `away_team_runs`.
2.  **The "Time Machine" Leak:** The preprocessing layer calculated median values over the *entire dataset* before doing a train-test split, leaking 2025 data backwards into the training set. Imputation logic was successfully pushed to execute post-split.
3.  **The Calibration Leak:** `IsotonicRegression` was being fit directly on the validation/test set. It was updated to fit exclusively on the training output probabilities.
4.  **Mathematical Mismatch:** The previous model employed a `reg:tweedie` objective, but the Skellam probability calculation assumes an underlying Poisson distribution. We corrected the XGBoost objective to `count:poisson`.

*Immediate result post-fixes:* The holdout 2025 Win Accuracy normalized to a realistic **55.32%**, and the simulated ROI settled at a mathematically honest **2.77%**.

### 3. The 2022 Data Gap & Memory Patch
Upon initial implementation, the advanced `Stuff+` features had exactly `0.0` importance in the XGBoost tree. An investigation revealed that the 2022 dataset—which comprises a massive part of the training set—contained `NULL` values for `rolling_stuff`. Because the `statsapi` could not reliably return historical probable pitchers from three years prior, the database rows were bypassed.

To resolve this, we avoided costly and error-prone network API calls and N+1 SQL queries. Instead, we executed a localized, high-speed memory patch:
- Extracted actual starting pitchers directly from `raw_pitches` by identifying the first pitch thrown in the top and bottom of the first inning.
- Loaded pitch-by-pitch `Stuff+` scores directly into Python memory dictionaries.
- Instantaneously mapped the pre-calculated `rolling_stuff_BEFORE_date` back to the missing 2,724 games in the 2022 training block.

### 4. Integration Results
Once the 2022 data gap was filled, the `Stuff+` data provided an immediate edge to the model.

**Before vs. After Stuff+**
- **Test Log-Loss:** Decreased from 0.6812 to **0.6805**.
- **Total Bets Placed:** Reduced from 756 to **740** (enhanced selectivity).
- **Total Profit (Units):** Increased from 0.73 to **0.91** (+24%).
- **Simulated ROI:** Jumped from 2.77% to an elite **3.61%**.

### 5. Conclusion
By providing the XGBoost engine with access to the underlying physics of how a pitcher threw the ball leading up to game day, the model improved its confidence and calibration. It successfully filtered out poor bets where a pitcher's underlying "stuff" lagged behind their traditional outcome stats, resulting in a significantly more robust and profitable engine.