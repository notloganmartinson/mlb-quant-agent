# MISSION CONTROL: Strikeout Prop Model Sprint
**Objective:** Build an XGBoost model to predict Starting Pitcher Strikeouts (K's).
**Rules of Engagement:**
1. Avoid "Context Saturation". We are doing this in atomic steps.
2. Read `core/schema.sql` and `core/db_manager.py` before modifying DB logic.
3. Strict Forward-Only features. No data leakage (Look-Ahead Bias).
4. Use `XGBRegressor` with `objective='count:poisson'` since strikeouts are count data.
