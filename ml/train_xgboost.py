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
from tools.experiment_logger import logger

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
    params = {
        'n_estimators': 200,
        'max_depth': 3,
        'learning_rate': 0.01,
        'objective': 'binary:logistic',
        'subsample': 0.8,
        'random_state': 42,
        'eval_metric': 'logloss'
    }
    model = xgb.XGBClassifier(**params)

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

    metrics = {
        'log_loss_raw': round(float(test_loss_raw), 4),
        'log_loss_calibrated': round(float(test_loss_calibrated), 4),
        'brier_score_raw': round(float(test_brier_raw), 4),
        'brier_score_calibrated': round(float(test_brier_calibrated), 4),
        'accuracy': round(float(test_acc), 4)
    }

    print("\nWin Probability Estimator Calibrated Results (Isotonic Regression):")
    print(f"  -> Test Log-Loss (Raw): {test_loss_raw:.4f}")
    print(f"  -> Test Log-Loss (Isotonic): {test_loss_calibrated:.4f}")
    print(f"  -> Test Brier Score (Raw): {test_brier_raw:.4f}")
    print(f"  -> Test Brier Score (Isotonic): {test_brier_calibrated:.4f}")
    print(f"  -> Test Win Accuracy: {test_acc:.2%}")

    # 5. Save Model & Calibration
    os.makedirs("models", exist_ok=True)
    model_path = "models/xgboost_baseline.joblib"
    calib_path = "models/calibration_model.joblib"
    joblib.dump(model, model_path)
    joblib.dump(iso_reg, calib_path)
    print(f"\nModel and Calibration saved to models/")

    # 6. Log to Experiment Registry
    logger.log_run(
        label="Baseline XGBoost - Isotonic Calibration",
        model_type="XGBClassifier",
        features=X_train.columns.tolist(),
        parameters=params,
        metrics=metrics,
        artifacts=[model_path, calib_path]
    )

    return model

if __name__ == "__main__":
    train_baseline_xgboost()