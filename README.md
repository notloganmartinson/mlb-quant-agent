# MLB Betting Agent: Professional Data Engine

A high-performance, modular data pipeline and calculation engine designed for quantitative MLB sports betting research. This system unifies disparate data sources (MLB StatsAPI, ESPN, The Odds API) into a relational SQLite database, providing a robust infrastructure for sabermetric modeling, backtesting, and autonomous market analysis.

## Core Features

- **Syndicate-Grade Predictive Engine:** Advanced XGBoost Binary Classifier (`binary:logistic`) optimized for log-loss, featuring strict non-parametric Isotonic Calibration for professional-grade $p$-value accuracy and Dynamic EV Thresholding.
- **Modular "Shattered" Pipeline:** Domain-specific ingestion modules (Stats, Odds, Environment) orchestrated for maximum reliability and ease of debugging.
- **Fail-Fast Mathematical Guardrails:** Strict `assert` statements in the statistical engine to prevent "Silent Failures" and ensure data integrity.
- **Schema Isolation:** Centralized `schema.sql` source of truth for all relational tables, separating definition from execution.
- **Proprietary Calculation Engine:** Local computation of advanced predictive metrics (SIERA, ISO, K-BB%, Stuff+) to identify market inefficiencies.
- **1:1 Mirrored ML Architecture:** Perfectly matched feature sets between live prediction tables and historical training data.
- **Unified Relational Mapping:** Centralized "Translator" architecture (`team_mappings`) resolving naming discrepancies across multiple providers.
- **Agentic Grounding:** ReAct-based AI analyst with Dependency Injection, grounded in structured SQL data.

## Project Architecture

```text
mlb-agent/
├── core/                   # Mathematical and Database Foundation
│   ├── schema.sql          # Centralized SQL schema (Source of Truth)
│   ├── database.py         # Schema execution and team seeding logic
│   ├── db_manager.py       # Object-oriented CRUD and connection management
│   └── stats_calculator.py # Vectorized sabermetric formulas with fail-fast assertions
├── scripts/                # Automated Ingestion Pipeline
│   ├── ingest/             # Shattered, domain-specific ingestion modules
│   │   ├── stats.py        # MLB official player/team stats
│   │   ├── odds.py         # ESPN market data and matchups
│   │   ├── environment.py  # Stadium coordinates and weather
│   │   └── statcast.py     # Pitch-by-pitch Statcast data (Velocity, Movement, VAA)
│   ├── ingest_historical.py# Automated season baseline ingestion
│   ├── fetch_live_odds.py  # Standalone The Odds API utility
│   ├── fetch_historical_odds.py # SBR JSON extraction for historical lines
│   ├── migrate.py          # Patch-based database migration system
│   └── generate_repo_map.py# AST-based project skeleton generator
├── ml/                     # Machine Learning Pipeline
│   ├── preprocess.py       # Data cleaning and true walk-forward splitting
│   ├── train_xgboost.py    # Calibrated model training (Tweedie + Isotonic)
│   ├── train_stuff_plus.py # Pitch-level "Stuff+" model (XGBoost)
│   ├── optimize.py         # Bayesian-style hyperparameter tuning
│   └── backtest.py         # 2025 season Kelly Criterion simulation
├── tools/                  # Analytical & Research Interfaces
│   ├── lineup_analyzer.py  # Real-time "Starting 9" offensive power analysis
│   ├── predict_games.py    # Live ML win-probability predictor
│   └── value_finder.py     # Multi-season weighted edge comparison engine
├── models/                 # Serialized Weights (XGBoost, Isotonic Calibration)
├── reports/                # Performance Plots and P&L Graphs
├── agent.py                # Class-based ReAct Agent with Dependency Injection
├── ingest_orchestrator.py  # Unified entry point for daily data ingestion
├── test_stats_calculator.py# Unit tests for statistical formulas
├── mlb_betting.db          # Local SQLite research database
├── requirements.txt        # System dependencies
├── .gitignore              # Multi-tier exclusion rules
├── GEMINI.md               # Token-optimized AST Repo Map for AI grounding
├── pitfalls.md             # Technical post-mortem and lessons learned
├── experiments.md          # Comparative research results
└── research-notes.md       # In-depth analysis of refactors, fixes, and validation
```

## Research Workflow

### 1. Relational Initialization
Build the database from the centralized SQL schema.
```bash
python3 core/db_builder.py
```

### 2. Sequential Data Generation
Populate the historical training table (2023-2025) using the vectorized rolling-stat engine.
```bash
PYTHONPATH=. python3 scripts/generate_training_data.py
```

### 3. Historical Market Enrichment
Populate the training set with real closing lines for accurate backtesting.
```bash
PYTHONPATH=. python3 scripts/fetch_historical_odds.py
```

### 4. Pitch-Level "Stuff+" Modeling (The Process Engine)
Generate proprietary pitch-quality metrics using high-frequency Statcast data to isolate physical talent from outcomes.
```bash
# Production-scale ingestion (2022-2025)
PYTHONPATH=. python3 scripts/ingest/statcast.py
# Train the pitch-level model and update starting_pitchers.stuff_plus
PYTHONPATH=. python3 ml/train_stuff_plus.py
```

### 5. Model Training & Optimization
Train the game-level XGBoost engine and simulate the 2025 season.
```bash
python3 ml/optimize.py
python3 ml/backtest.py
```


### 6. Production Synchronization
Execute the modular ingestion pipeline to sync real-time 2026 data.
```bash
python3 ingest_orchestrator.py
```

### 7. Agentic Analysis
Query the grounded AI analyst for market inefficiencies.
```bash
python3 agent.py
```

## Security & Design Principles
- **Fail-Fast Boundaries:** Mathematical formulas and API calls are wrapped in strict assertions and error handlers to halt execution before data corruption occurs.
- **Dependency Injection:** The AI agent and database managers accept configuration from the environment, decoupling logic from hardcoded paths.
- **Context Efficiency:** The repository uses a specialized `GEMINI.md` AST map to provide high-density grounding for AI-assisted development.
- **Factual Grounding:** All AI responses are derived via structured tool-use, ensuring mathematical rigor over probabilistic generation.
