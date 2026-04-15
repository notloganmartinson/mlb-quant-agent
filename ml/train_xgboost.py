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

def train_baseline_xgboost():
    """
    Trains an initial XGBoost model and establishes a baseline Log-Loss.
    Now uses Tweedie regression for overdispersion and Isotonic Calibration.
    """
    print("Establishing Calibrated Run Estimator (Tweedie XGBoost)...")
    
    # 1. Load Data
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # Split training data for a dedicated calibration holdout (80/20 split)
    # This prevents data leakage from the test set into the calibration model.
    from sklearn.model_selection import train_test_split
    X_base, X_calib, y_base, y_calib = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, shuffle=False
    )

    # 2. Initialize Model
    # Tweedie handles overdispersion better than Poisson.
    # Updated to optimal hyperparameters found during optimization.
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

    # 4. Evaluation & Calibration
    # A. Generate Calibration Probabilities from the Calibration Holdout
    y_calib_pred = model.predict(X_calib)
    calib_prob_win_raw = skellam.sf(0, y_calib_pred[:, 0], y_calib_pred[:, 1])
    calib_prob_tie_raw = skellam.pmf(0, y_calib_pred[:, 0], y_calib_pred[:, 1])
    calib_win_prob_raw = calib_prob_win_raw / (1 - calib_prob_tie_raw)
    y_calib_won = (y_calib.iloc[:, 0] > y_calib.iloc[:, 1]).astype(int)

    # B. Fit Calibration Engine on the Calibration Holdout
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(calib_win_prob_raw, y_calib_won)
    
    # C. Generate predictions for Test set
    y_test_pred = model.predict(X_test)
    test_prob_win_raw = skellam.sf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_prob_tie_raw = skellam.pmf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_win_prob_raw = test_prob_win_raw / (1 - test_prob_tie_raw)
    
    # D. Generate predictions for full Training set (for logging metrics)
    y_train_pred = model.predict(X_train)
    train_prob_win_raw = skellam.sf(0, y_train_pred[:, 0], y_train_pred[:, 1])
    train_prob_tie_raw = skellam.pmf(0, y_train_pred[:, 0], y_train_pred[:, 1])
    train_win_prob_raw = train_prob_win_raw / (1 - train_prob_tie_raw)
    
    # Actual Outcomes
    y_train_won = (y_train.iloc[:, 0] > y_train.iloc[:, 1]).astype(int)
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)

    # Calibrated Probabilities
    test_win_prob_calibrated = iso_reg.transform(test_win_prob_raw)
    train_win_prob_calibrated = iso_reg.transform(train_win_prob_raw) # Approximated calibration

    # Metrics
    test_loss_raw = log_loss(y_test_won, test_win_prob_raw)
    test_loss_calibrated = log_loss(y_test_won, test_win_prob_calibrated)
    test_brier_raw = brier_score_loss(y_test_won, test_win_prob_raw)
    test_brier_calibrated = brier_score_loss(y_test_won, test_win_prob_calibrated)
    
    test_acc = accuracy_score(y_test_won, (test_win_prob_calibrated > 0.5).astype(int))
    home_mae = mean_absolute_error(y_test.iloc[:, 0], y_test_pred[:, 0])
    away_mae = mean_absolute_error(y_test.iloc[:, 1], y_test_pred[:, 1])

    print("\nRun Estimator Calibrated Results:")
    print(f"  -> Test Log-Loss (Raw): {test_loss_raw:.4f}")
    print(f"  -> Test Log-Loss (Calibrated): {test_loss_calibrated:.4f}")
    print(f"  -> Test Brier Score (Raw): {test_brier_raw:.4f}")
    print(f"  -> Test Brier Score (Calibrated): {test_brier_calibrated:.4f}")
    print(f"  -> Test Win Accuracy: {test_acc:.2%}")
    print(f"  -> Home Run MAE: {home_mae:.2f}")
    print(f"  -> Away Run MAE: {away_mae:.2f}")

    # 5. Verification Check
    sample_idx = 0
    sample_home_exp = y_test_pred[sample_idx, 0]
    sample_away_exp = y_test_pred[sample_idx, 1]
    sample_prob_raw = test_win_prob_raw[sample_idx]
    sample_prob_calibrated = test_win_prob_calibrated[sample_idx]
    print(f"\nVerification Sample:")
    print(f"  Predicted Home Runs: {sample_home_exp:.1f}, Predicted Away Runs: {sample_away_exp:.1f}")
    print(f"  Raw Win Prob: {sample_prob_raw:.1%}")
    print(f"  Calibrated Win Prob: {sample_prob_calibrated:.1%}")

    # 6. Save Model & Calibration
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/xgboost_baseline.joblib")
    joblib.dump(iso_reg, "models/calibration_model.joblib")
    print(f"\nModel and Calibration saved to models/")

    return model

if __name__ == "__main__":
    train_baseline_xgboost()
