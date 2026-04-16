import xgboost as xgb
from sklearn.metrics import log_loss, accuracy_score, mean_absolute_error, brier_score_loss
from sklearn.multioutput import MultiOutputRegressor
from sklearn.isotonic import IsotonicRegression
from scipy.stats import skellam
import joblib
import numpy as np
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

from sklearn.linear_model import LogisticRegression

def train_baseline_xgboost():
    """
    Trains an initial XGBoost model and establishes a baseline Log-Loss.
    Uses Poisson regression for runs and Platt Scaling (Logistic) for win prob.
    """
    print("Establishing Calibrated Run Estimator (Poisson XGBoost)...")
    
    # 1. Load Data
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # Split training data for a dedicated calibration holdout (80/20 split)
    from sklearn.model_selection import train_test_split
    X_base, X_calib, y_base, y_calib = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, shuffle=False
    )

    # 2. Initialize Model
    base_model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.01,
        objective='count:poisson',
        subsample=0.8,
        random_state=42
    )
    model = MultiOutputRegressor(base_model)

    # 3. Train Model on the base training split
    model.fit(X_base, y_base)

    # 4. Evaluation & Calibration (Manual Platt Scaling)
    def get_raw_probs(mod, X):
        y_p = mod.predict(X)
        prob_win_raw = skellam.sf(0, y_p[:, 0], y_p[:, 1])
        prob_tie_raw = skellam.pmf(0, y_p[:, 0], y_p[:, 1])
        return (prob_win_raw / (1.0 - prob_tie_raw)).reshape(-1, 1)

    y_calib_won = (y_calib.iloc[:, 0] > y_calib.iloc[:, 1]).astype(int)
    raw_probs_calib = get_raw_probs(model, X_calib)
    
    # Platt Scaling: Logistic regression on the raw probabilities
    lr = LogisticRegression(penalty=None) # Pure Platt Scaling doesn't use penalty
    lr.fit(raw_probs_calib, y_calib_won)
    
    # Actual Outcomes
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)

    # Generate predictions for Test set
    raw_probs_test = get_raw_probs(model, X_test)
    test_probs = lr.predict_proba(raw_probs_test)[:, 1]
    
    # Metrics
    test_loss_raw = log_loss(y_test_won, raw_probs_test)
    test_loss_calibrated = log_loss(y_test_won, test_probs)
    test_brier_raw = brier_score_loss(y_test_won, raw_probs_test)
    test_brier_calibrated = brier_score_loss(y_test_won, test_probs)
    
    test_acc = accuracy_score(y_test_won, (test_probs > 0.5).astype(int))
    y_test_pred = model.predict(X_test)
    home_mae = mean_absolute_error(y_test.iloc[:, 0], y_test_pred[:, 0])
    away_mae = mean_absolute_error(y_test.iloc[:, 1], y_test_pred[:, 1])

    print("\nRun Estimator Calibrated Results (Platt Scaling):")
    print(f"  -> Test Log-Loss (Raw): {test_loss_raw:.4f}")
    print(f"  -> Test Log-Loss (Platt): {test_loss_calibrated:.4f}")
    print(f"  -> Test Brier Score (Raw): {test_brier_raw:.4f}")
    print(f"  -> Test Brier Score (Platt): {test_brier_calibrated:.4f}")
    print(f"  -> Test Win Accuracy: {test_acc:.2%}")
    print(f"  -> Home Run MAE: {home_mae:.2f}")
    print(f"  -> Away Run MAE: {away_mae:.2f}")

    # 5. Save Model & Calibration
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/xgboost_baseline.joblib")
    joblib.dump(lr, "models/calibration_model.joblib")
    print(f"\nModel and Calibration saved to models/")

    return model

if __name__ == "__main__":
    train_baseline_xgboost()
