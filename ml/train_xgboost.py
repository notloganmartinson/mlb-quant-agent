import xgboost as xgb
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split
import joblib
import numpy as np
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def train_baseline_xgboost():
    """
    Trains an XGBoost binary classifier to predict home team win probability directly.
    Uses Isotonic Regression for rigorous non-parametric calibration.
    """
    print("Establishing Calibrated Win Probability Estimator (Binary XGBoost)...")
    
    # 1. Load Data
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # Convert targets to binary (1 = Home Win, 0 = Away Win/Tie)
    y_train_won = (y_train.iloc[:, 0] > y_train.iloc[:, 1]).astype(int)
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)

    # Split training data for a dedicated calibration holdout (80/20 split)
    X_base, X_calib, y_base, y_calib = train_test_split(
        X_train, y_train_won, test_size=0.2, random_state=42, shuffle=False
    )

    # 2. Initialize Model (Binary Classification)
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.01,
        objective='binary:logistic',
        subsample=0.8,
        random_state=42,
        eval_metric='logloss'
    )

    # 3. Train Model on the base training split
    model.fit(X_base, y_base)

    # 4. Evaluation & Calibration (Isotonic Regression)
    # Get uncalibrated probabilities for the calibration set
    raw_probs_calib = model.predict_proba(X_calib)[:, 1]
    
    # Fit strictly monotonic Isotonic Regression (out_of_bounds='clip' prevents extrapolation errors)
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(raw_probs_calib, y_calib)
    
    # Generate predictions for Test set
    raw_probs_test = model.predict_proba(X_test)[:, 1]
    test_probs_calibrated = iso_reg.predict(raw_probs_test)
    
    # Metrics
    test_loss_raw = log_loss(y_test_won, raw_probs_test)
    test_loss_calibrated = log_loss(y_test_won, test_probs_calibrated)
    test_brier_raw = brier_score_loss(y_test_won, raw_probs_test)
    test_brier_calibrated = brier_score_loss(y_test_won, test_probs_calibrated)
    
    test_acc = accuracy_score(y_test_won, (test_probs_calibrated > 0.5).astype(int))

    print("\nWin Probability Estimator Calibrated Results (Isotonic Regression):")
    print(f"  -> Test Log-Loss (Raw): {test_loss_raw:.4f}")
    print(f"  -> Test Log-Loss (Isotonic): {test_loss_calibrated:.4f}")
    print(f"  -> Test Brier Score (Raw): {test_brier_raw:.4f}")
    print(f"  -> Test Brier Score (Isotonic): {test_brier_calibrated:.4f}")
    print(f"  -> Test Win Accuracy: {test_acc:.2%}")

    # 5. Save Model & Calibration
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/xgboost_baseline.joblib")
    joblib.dump(iso_reg, "models/calibration_model.joblib")
    print(f"\nModel and Calibration saved to models/")

    return model

if __name__ == "__main__":
    train_baseline_xgboost()