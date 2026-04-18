# MLB Betting Agent: Professional Data Engine

A high-performance, modular data pipeline and calculation engine designed for quantitative MLB sports betting research. This system unifies disparate data sources (MLB StatsAPI, ESPN, The Odds API) into a relational SQLite database, providing a robust infrastructure for sabermetric modeling, backtesting, and autonomous market analysis.

## Core Features

- **Advanced K-Prop Engine:** Discrete strikeout prediction using an XGBRegressor (Poisson objective), converted into betting probabilities via the Poisson CDF and sized via the Fractional Kelly Criterion.
- **Professional Feature Set:** Multi-dimensional feature engineering including dynamic Umpire K-tendencies, Park K-factors, Granular Bullpen Skill (Top 5 relievers), and Atmospheric Physics (Density Altitude).
- **Quant Experiment Registry:** A centralized SQLite ledger (`registry.db`) that tracks every model iteration, parameter set, and ROI metric to ensure research reproducibility.
- **Syndicate-Grade Win Probability:** Master XGBoost Binary Classifier optimized for log-loss, featuring strict non-parametric Isotonic Calibration for professional-grade $p$-value accuracy.
- **Modular "Shattered" Pipeline:** Domain-specific ingestion modules (Stats, Odds, Environment) orchestrated for maximum reliability and ease of debugging.
- **Proprietary Calculation Engine:** Local computation of advanced predictive metrics (SIERA, ISO, K-BB%, Stuff+) to identify market inefficiencies.
- **Agentic Grounding:** ReAct-based AI analyst with Dependency Injection, grounded in structured SQL data.

## Project Architecture

```text
mlb-agent/
├── core/                   # Mathematical and Database Foundation
│   ├── schema.sql          # Centralized SQL schema (Source of Truth)
│   ├── db_manager.py       # Object-oriented CRUD and connection management
│   └── stats_calculator.py # Vectorized sabermetric formulas with fail-fast assertions
├── scripts/                # Automated Ingestion & Patching
│   ├── ingest/             # Shattered, domain-specific ingestion modules
│   │   ├── stats.py        # MLB official player/team stats
│   │   ├── odds.py         # ESPN market data and matchups
│   │   ├── environment.py  # Stadium coordinates and Density Altitude physics
│   │   └── statcast.py     # Pitch-by-pitch Statcast data (Velocity, Movement, VAA)
│   ├── archive_daily_props.py # Daily proprietary odds archiver
│   ├── patch_advanced_k_features.py # Dynamic Umpire/Park feature generation
│   ├── generate_training_data.py # Vectorized rolling-stat & bullpen engine
│   ├── migrate.py          # Patch-based database migration system
│   └── generate_repo_map.py# AST-based project skeleton generator
├── ml/                     # Machine Learning Pipeline
│   ├── preprocess.py       # Data cleaning and true walk-forward splitting
│   ├── train_k_props.py    # Poisson strikeout model with registry logging
│   ├── train_xgboost.py    # Binary win-probability model with Isotonic Calibration
│   ├── train_stuff_plus.py # Pitch-level "Stuff+" model (XGBoost)
│   ├── backtest_k_props.py # Poisson CDF & Kelly Criterion simulation
│   └── backtest.py         # Moneyline Kelly Criterion simulation
├── tools/                  # Analytical & Research Interfaces
│   ├── experiment_logger.py # Quant Experiment Registry utility
│   ├── lineup_analyzer.py  # Real-time "Starting 9" offensive power analysis
│   └── value_finder.py     # Multi-season weighted edge comparison engine
├── models/                 # Serialized Weights (XGBoost, Isotonic Calibration)
├── reports/                # Performance Registry and Artifacts
│   ├── registry.db         # Immutable ledger of all model/backtest runs
│   └── runs/               # Archived artifacts (PNGs, Models) for every run
├── agent.py                # Class-based ReAct Agent with Dependency Injection
├── ingest_orchestrator.py  # Unified entry point for daily data ingestion
├── mlb_betting.db          # Local SQLite research database
├── requirements.txt        # System dependencies
├── GEMINI.md               # Token-optimized AST Repo Map for AI grounding
├── pitfalls.md             # Technical post-mortem and lessons learned
├── experiments.md          # Comparative research results
└── research-notes.md       # In-depth analysis of refactors, fixes, and validation
```

## Research Workflow

### 1. The Quant Lab (Training & Logging)
Train the "Professional" strikeout model and log it to the registry.
```bash
PYTHONPATH=. python3 ml/train_k_props.py --label "Sprint 6: Physics + Bullpens"
```

### 2. The Truth Test (Backtesting)
Evaluate the model against 2025 holdout data using the Poisson EV engine.
```bash
PYTHONPATH=. python3 ml/backtest_k_props.py --label "Backtest Physics v1"
```

### 3. Reviewing Progress
Compare metrics across multiple runs via the registry.
```bash
sqlite3 reports/registry.db "SELECT run_id, label, metrics FROM experiment_runs;"
```

### 4. Data Archival
Build a proprietary historical dataset of real player prop lines for free.
```bash
python3 scripts/archive_daily_props.py
```

## Security & Design Principles
- **Strict Forward-Only Math:** All rolling features utilize `.shift(1)` to eliminate Look-Ahead Bias.
- **Bayesian Normalization:** Small-sample stats are anchored with league-average priors to prevent early-season noise.
- **Atmospheric Grounding:** Models incorporate Density Altitude to account for the physical environment of each game.
- **Factual Grounding:** All AI responses are derived via structured tool-use, ensuring mathematical rigor over probabilistic generation.
