# MLB Betting Agent: Professional Data Engine

A high-performance, modular data pipeline and calculation engine designed for quantitative MLB sports betting research. This system unifies disparate data sources (MLB StatsAPI, ESPN, The Odds API) into a relational SQLite database, providing a robust infrastructure for sabermetric modeling, backtesting, and autonomous market analysis.

## Core Features

- **Dual-Market Isotonic Calibration:** Symmetrical probability calibration using two independent non-parametric models (Home and Away), eliminating directional bias and ensuring professional-grade $p$-value accuracy for both sides of the moneyline.
- **Multi-Factor Environmental Integration:** Professional feature engineering including dynamic Umpire K-tendencies, Park K-factors (strikeout-specific), Lineup K-susceptibility, and Market Consensus (Closing Totals), providing the model with critical atmospheric and officiating context.
- **Closing Line Value (CLV) Tracking:** Sophisticated market monitoring that captures both "Opening" and "Closing" lines for Moneylines and Totals, enabling precise measurement of model edge against market movement.
- **Advanced K-Prop Engine:** Discrete strikeout prediction using an XGBRegressor (Poisson objective) with dynamic dispersion modeling. Predictions are converted into betting probabilities via a **Negative Binomial CDF** (addressing over-dispersion) and sized via the Fractional Kelly Criterion.
- **Background Orchestration:** Continuous, credit-aware scheduling system that manages daily heavy-stats ingestion and high-frequency odds polling.
- **Proprietary Calculation Engine:** Local computation of advanced predictive metrics (SIERA, ISO, K-BB%, Stuff+) to identify market inefficiencies.
- **Agentic Grounding:** ReAct-based AI analyst with Dependency Injection, grounded in structured SQL data.

## Project Architecture

```text
mlb-agent/
├── core/                   # Mathematical and Database Foundation
│   ├── schema.sql          # Centralized SQL schema (Source of Truth)
│   ├── db_manager.py       # Object-oriented CRUD and connection management (CLV Aware)
│   └── stats_calculator.py # Vectorized sabermetric formulas with fail-fast assertions
├── scripts/                # Automated Ingestion & Patching
│   ├── ingest/             # Shattered, domain-specific ingestion modules
│   │   ├── stats.py        # MLB official player/team stats
│   │   ├── odds.py         # ESPN market data and matchups
│   │   ├── environment.py  # Stadium coordinates and Density Altitude physics
│   │   └── statcast.py     # Pitch-by-pitch Statcast data (Velocity, Movement, VAA)
│   ├── fetch_live_odds.py  # High-frequency market data scraper (The Odds API)
│   ├── fetch_historical_odds.py # Playwright-based historical odds harvester (SBR)
│   ├── archive_daily_props.py # Daily proprietary odds archiver
│   ├── generate_training_data.py # Vectorized rolling-stat & bullpen engine
│   ├── migrate.py          # Patch-based database migration system
├── ml/                     # Machine Learning Pipeline
│   ├── preprocess.py       # Data cleaning and true walk-forward splitting
│   ├── train_k_props.py    # Poisson strikeout model with registry logging
│   ├── train_xgboost.py    # Binary win-probability model with Isotonic Calibration
│   ├── backtest_k_props.py # Poisson CDF & Kelly Criterion simulation
│   └── backtest.py         # Moneyline Kelly Criterion simulation (CLV Integrated)
├── tools/                  # Analytical & Research Interfaces
│   ├── experiment_logger.py # Quant Experiment Registry utility
│   ├── lineup_analyzer.py  # Real-time "Starting 9" offensive power analysis
│   └── value_finder.py     # Multi-season weighted edge comparison engine
├── models/                 # Serialized Weights (XGBoost, Isotonic Calibration)
├── reports/                # Performance Registry and Artifacts
│   ├── registry.db         # Immutable ledger of all model/backtest runs
│   └── runs/               # Archived artifacts (PNGs, Models) for every run
├── agent.py                # Class-based ReAct Agent with Dependency Injection
├── ingest_orchestrator.py  # Background scheduler for automated ingestion
├── mlb_betting.db          # Local SQLite research database
├── requirements.txt        # System dependencies
└── GEMINI.md               # Token-optimized AST Repo Map for AI grounding
```

## Research Workflow

### 1. The Data Foundation (Ingestion)
Start the background scheduler to keep the database fresh with live odds and official stats.
```bash
python3 ingest_orchestrator.py
```

### 2. Historical Harvesting (Backfilling)
Populate real market lines for 2025 to enable non-biased backtesting.
```bash
PYTHONPATH=. python3 scripts/fetch_historical_odds.py
```

### 3. The Truth Test (Backtesting)
Evaluate the model against 2025 holdout data using real market lines and Kelly Criterion.
```bash
PYTHONPATH=. python3 ml/backtest.py
```

### 4. Reviewing Progress
Compare metrics across multiple runs via the registry.
```bash
sqlite3 reports/registry.db "SELECT run_id, label, metrics FROM experiment_runs;"
```

## Security & Design Principles
- **Strict Idempotency:** All ingestion and migration scripts are designed to safely resume after interruptions.
- **Market Integrity:** CLV tracking protects "Opening" lines to ensure backtests reflect real-world execution.
- **Strict Forward-Only Math:** All rolling features utilize `.shift(1)` to eliminate Look-Ahead Bias.
- **Atmospheric Grounding:** Models incorporate Density Altitude to account for the physical environment of each game.
- **Factual Grounding:** All AI responses are derived via structured tool-use, ensuring mathematical rigor over probabilistic generation.
