# Development Pitfalls & Lessons Learned

Technical and strategic hurdles encountered while building the MLB Betting Engine.

### 1. The Scraping Wall (Cloudflare)
- **Pitfall:** Initial attempts to scrape FanGraphs via `pybaseball` and `Playwright` were blocked by Cloudflare 403 errors and persistent "Verify Human" captchas.
- **Lesson:** Web scraping is too fragile for production. Official APIs are mandatory for stability.
- **Fix:** Switched to the **Official MLB StatsAPI**, which is unblockable and requires no keys.

### 2. The Proprietary Data Trap
- **Pitfall:** Highly predictive stats (SIERA, Stuff+, wRC+) are private IP and not available in free APIs.
- **Lesson:** To scale for free, you must own the math.
- **Fix:** Built a local **Calculation Engine** (`stats_calculator.py`) to derive proprietary metrics from raw counting stats (K, BB, GB, FB).

### 3. Early Season Volatility
- **Pitfall:** On April 11th, 2026 data is too "noisy" (~2 week sample size) to be reliable for betting.
- **Lesson:** Never bet on early-season samples in isolation.
- **Fix:** Refactored for **Multi-Season Support**, using a **70/30 Weighted Average** (2025 baseline + 2026 current) to stabilize performance reads.

### 4. Matchup Blindness
- **Pitfall:** Season averages hide daily reality (Platoon Splits and Benched Stars).
- **Lesson:** Handedness (L/R) and the "Starting 9" are the true drivers of daily value.
- **Fix:** Implemented **Platoon Split Ingestion** and a **Lineup Analyzer** to compute power based on the actual players taking the field.

### 5. Automated Data Interception Failure
- **Pitfall:** Initial attempts to automate odds ingestion relied on intercepting "internal" JSON payloads from Action Network via Playwright. High-security sites frequently utilize "Heuristic Bot Detection" that suppresses API calls when a headless browser fingerprint is detected, resulting in empty datasets despite successful page navigation.
- **Lesson:** Undocumented internal APIs are unreliable for production infrastructure.
- **Fix:** Migrated to **The Odds API (v4)**, a documented, RESTful service. This transition yielded 100% data reliability and enabled granular tracking of specific bookmakers (DraftKings, FanDuel, BetMGM).

### 6. Relational Integrity and Naming Discrepancies
- **Pitfall:** Aggregating data from multiple providers (MLB, ESPN, The Odds API) introduced critical "Linkage Errors" due to inconsistent team naming (e.g., "NYY" vs "New York Yankees"). This rendered the AI agent unable to perform SQL JOINs between stats and market prices.
- **Lesson:** A relational database requires a centralized "Source of Truth" for identifiers.
- **Fix:** Implemented a **Team Mapping Architecture** (`team_mappings` table) that resolves all source-specific strings to a canonical MLB ID, ensuring seamless analytical joins.

**Commentary on ID Mapping vs. Fuzzy Matching:**
While "Fuzzy Matching" (Levenstein distance or string similarity) is often proposed for name resolution, it was rejected for this architecture for three professional reasons:
1. **Elimination of Ambiguity:** Fuzzy logic creates "False Positives" in MLB data (e.g., incorrectly matching "Chicago Sox" to "Chicago Cubs" during low-confidence runs). Canonical IDs ensure 100% deterministic accuracy.
2. **Computational Efficiency:** Performing fuzzy string comparisons within every SQL query significantly increases "Compute Latency" and complexity. A Join on an Integer Primary Key is the most efficient operation in relational databases.
3. Agentic Reliability: AI agents perform better when given a clear "Translation Map." Fuzzy matching requires the agent to "guess" or "approximate" the linkage, whereas ID mapping allows the agent to generate strict, high-confidence SQL JOINS that are immune to generative hallucination.

### 7. Static Baseline Inflation (Model "Cheating")
- **Pitfall:** Initial training sets were populated with static league-average placeholders (e.g., 4.20 SIERA) rather than varying daily metrics. This resulted in an artificially inflated 22% ROI, as the model learned to rely solely on Home Field Advantage bias while assuming player skill was constant.
- **Lesson:** Machine learning models are only as valid as the variance in their features. Static baselines create "False Positives" that fail in production.
- **Fix:** Implemented a **Chronological Feature Store** that calculates and injects unique, daily-calculated skill metrics for every row in the historical dataset.

### 8. Temporal Data Leakage (Look-Ahead Bias)
- **Pitfall:** Utilizing full-season statistics to predict individual games occurring early in the year. 
- **Lesson:** Predictive models must strictly simulate the information available *prior* to the event. 
- **Fix:** Implemented vectorized **Pandas `.shift(1)` operations** within the ingestion pipeline. This ensures that the features for Game $N$ are derived exclusively from the cumulative results of Games $1$ through $N-1$.

### 9. Small Sample Size Instability
- **Pitfall:** Rate-based metrics (SIERA, K-BB%, ISO) exhibit extreme mathematical volatility in the early weeks of a season (e.g., a 10.00+ SIERA after a single poor outing).
- **Lesson:** Raw early-season data is statistically "noisy" and can destabilize gradient-boosted models (XGBoost).
- **Fix:** Integrated a **Bayesian Prior (Padding)** strategy. Artificially injecting ~100 league-average counting stats into every player's Opening Day baseline anchors early-season performance to reality and naturally dilutes as the true sample size expands.

### 11. Model Calibration and Backtest "Cheating"
- **Pitfall:** Initial backtest simulations yielded an implausible 22% ROI. This was traced to two forms of unintentional "cheating":
    1. **Feature Stasis:** Populating historical rows with static league-average placeholders rather than daily-varying rolling metrics. The model "learned" the bias of the sample (Home Field Advantage) rather than player skill.
    2. **The "-110 Baseline" Bias:** Assuming a flat market price of -110 for all historical games. In reality, the "Juice" (Vig) and lopsided lines for heavy favorites significantly erode profit. Assuming a flat price artificially inflates the performance of high-probability favorites.
- **Lesson:** A backtest is only a valid research instrument if it mirrors the friction and variance of the live market.
- **Fix:** Refactored the ingestion pipeline to fetch **Real Closing Lines** via SBR/The Odds API and replaced placeholders with **Strict Rolling Metrics**. This collapsed the ROI to a realistic professional range (2-5%), validating the model's integrity for the final research paper.

