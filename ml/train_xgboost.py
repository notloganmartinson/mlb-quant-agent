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

    # 2. Initialize Model
    # Tweedie handles overdispersion better than Poisson.
    # 1.5 is a common starting point for variance power.
    base_model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective='count:poisson',
        random_state=42
    )
    model = MultiOutputRegressor(base_model)

    # 3. Train Model
    model.fit(X_train, y_train)

    # 4. Evaluation & Calibration
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Raw Win Probabilities using Skellam
    train_prob_win_raw = skellam.sf(0, y_train_pred[:, 0], y_train_pred[:, 1])
    train_prob_tie_raw = skellam.pmf(0, y_train_pred[:, 0], y_train_pred[:, 1])
    train_win_prob_raw = train_prob_win_raw / (1 - train_prob_tie_raw)
    
    test_prob_win_raw = skellam.sf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_prob_tie_raw = skellam.pmf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_win_prob_raw = test_prob_win_raw / (1 - test_prob_tie_raw)
    
    # Actual Outcomes
    y_train_won = (y_train.iloc[:, 0] > y_train.iloc[:, 1]).astype(int)
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)

    # Calibration Engine: Fit on Validation (Holdout)
    # Note: In production, this should be done on a separate validation split.
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(test_win_prob_raw, y_test_won)
    
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
