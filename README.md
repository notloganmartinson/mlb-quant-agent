# MLB Betting Agent: Professional Data Engine

A high-performance, modular data pipeline and calculation engine designed for quantitative MLB sports betting research. This system unifies disparate data sources (MLB StatsAPI, ESPN, The Odds API) into a relational SQLite database, providing a robust infrastructure for sabermetric modeling, backtesting, and autonomous market analysis.

## 🚀 Core Features

- **Automated Data Pipeline:** 100% automated ingestion using official REST APIs, ensuring high data availability and reliability.
- **Proprietary Calculation Engine:** Local computation of advanced predictive metrics (SIERA, ISO, K-BB%) to identify market inefficiencies independent of third-party providers.
- **1:1 Mirrored ML Architecture:** Perfectly matched feature sets between live prediction tables and historical training data, enabling seamless machine learning model deployment.
- **Unified Relational Mapping:** Centralized "Translator" architecture (`team_mappings`) resolving naming discrepancies across multiple providers to canonical MLB IDs.
- **Sequential Feature Engineering:** Chronological data ingestion pipeline designed to eliminate "Look-Ahead Bias" (data leakage) in historical training sets.
- **Agentic Grounding:** Implementation of a ReAct-based AI analyst grounded in structured SQL data, mitigating the risks of generative hallucination in financial modeling.

## 🛠 Project Architecture

```text
mlb-agent/
├── core/                   # Mathematical and Database Foundation
│   ├── database.py         # Relational schema definitions and team seeding
│   ├── db_manager.py       # Object-oriented CRUD and team ID resolution
│   └── stats_calculator.py # Vectorized sabermetric regression formulas
├── data/                   # Persistent Storage
│   ├── raw/                # Manual data backups and external CSVs
│   └── mlb_betting.db      # Multi-season relational SQLite database
├── scripts/                # Automated Ingestion Pipeline
│   ├── ingest_historical.py# Automated 2025 season baseline ingestion
│   ├── ingest_daily.py     # Main 2026 stats, ESPN, and weather synchronizer
│   ├── fetch_live_odds.py  # Standalone The Odds API utility
│   ├── fetch_historical_odds.py # SBR JSON extraction for historical lines
│   └── generate_training_data.py # Sequential ML feature store generator
├── ml/                     # Machine Learning Pipeline
│   ├── preprocess.py       # Data cleaning and time-series splitting
│   ├── train_xgboost.py    # Baseline model training and serialization
│   ├── optimize.py         # Hyperparameter tuning (Grid Search)
│   └── backtest.py         # 2025 season Kelly Criterion simulation
├── tools/                  # Analytical & Research Interfaces
│   ├── lineup_analyzer.py  # Real-time "Starting 9" offensive power analysis
│   ├── predict_games.py    # Live ML win-probability predictor
│   └── value_finder.py     # Multi-season weighted edge comparison engine
├── models/                 # Serialized ML Model Weights (Ignored by Git)
├── reports/                # Performance Plots and P&L Graphs
├── agent.py                # ReAct-based AI Analytical Agent
├── requirements.txt        # System dependencies
├── .gitignore              # Multi-tier exclusion rules
├── PITFALLS.md             # Technical post-mortem and lessons learned
├── EXPERIMENTS.md          # Comparative research results (Agent vs. Web App)
└── RESEARCH_NOTES.md       # In-depth analysis of autonomous self-correction
```

## 📈 Research Workflow

### 1. Relational Initialization
Establish the schema and canonical mappings required for multi-source joins.
```bash
python3 core/database.py
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

### 4. Model Training & Optimization
Train the XGBoost engine and simulate the 2025 season.
```bash
PYTHONPATH=. python3 ml/optimize.py
PYTHONPATH=. python3 ml/backtest.py
```

### 5. Production Synchronization
Sync real-time 2026 metrics, market prices, and environmental variables.
```bash
PYTHONPATH=. python3 scripts/ingest_daily.py
```

### 6. Agentic Analysis
Query the grounded AI analyst for market inefficiencies and sabermetric insights.
```bash
python3 agent.py
```

## 📊 Database Schema Highlights

- **`starting_pitchers`**: Multi-season repository of individual ERA, SIERA, and K-BB% metrics.
- **`hitting_lineups`**: Tracks team-level power (ISO) and discipline (K%) with LHP/RHP platoon splits.
- **`bullpens`**: Stores aggregate relief-corps metrics to monitor late-inning performance risk.
- **`betting_markets`**: Live prediction table containing real-time features mirrored for ML model execution.
- **`historical_training_data`**: Chronological repository of 8,500+ games (2023-2025) for model training.
- **`sportsbook_odds`**: Granular, multi-bookmaker tracking of ML, Run Line, and Totals.
- **`team_mappings`**: Relational "Translator" anchor used for name-to-ID resolution across all APIs.
- **`park_factors_and_weather`**: Environmental variables (Temp/Wind) for game-total modeling.

## 📊 Analytical Indicators
- **SIERA (Skill-Interactive ERA):** Advanced ERA estimator used to identify lucky/unlucky pitcher variance.
- **K-BB%:** Primary indicator of pitcher plate-discipline dominance.
- **Lineup ISO:** Weighted offensive power based on confirmed pre-game rosters.
- **Platoon Edge:** Differential performance metrics vs. LHP and RHP.

## 🛡 Security & Design Principles
- **Relational Integrity:** Uses composite Primary Keys and `ON CONFLICT` resolution to maintain a clean state.
- **Environment Agnostic:** Fully optimized for headless server deployment and automated task scheduling (Cron).
- **Factual Grounding:** All AI responses are derived via structured tool-use, ensuring mathematical rigor over probabilistic generation.
