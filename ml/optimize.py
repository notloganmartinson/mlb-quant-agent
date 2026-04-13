import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import log_loss
from sklearn.calibration import CalibratedClassifierCV
import joblib
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def optimize_xgboost():
    """
    Performs Grid Search to find the best hyperparameters for the MLB model.
    """
    print("Starting Hyperparameter Optimization...")
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # 1. Define Search Space
    param_grid = {
        'max_depth': [3, 4, 5],
        'learning_rate': [0.01, 0.05],
        'n_estimators': [100, 200],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0],
        'gamma': [0.1, 0.5, 1.0],
        'min_child_weight': [3, 5, 7]
    }

    # 2. Initialize Grid Search
    # Note: We use cv=3 for speed in this environment
    grid_search = GridSearchCV(
        estimator=xgb.XGBClassifier(objective='binary:logistic', random_state=42, eval_metric='logloss'),
        param_grid=param_grid,
        scoring='neg_log_loss',
        cv=3,
        verbose=1
    )

    # 3. Fit Grid Search
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    print(f"\nBest Parameters Found: {grid_search.best_params_}")

    # 4. Probability Calibration (Platt Scaling)
    print("Calibrating win probabilities (Platt Scaling)...")
    calibrated_model = CalibratedClassifierCV(estimator=best_model, method='sigmoid', cv=5)
    calibrated_model.fit(X_train, y_train)

    # 5. Final Evaluation
    y_prob = calibrated_model.predict_proba(X_test)[:, 1]
    optimized_loss = log_loss(y_test, y_prob)
    
    print(f"\nOptimized & Calibrated Results (2025 Holdout):")
    print(f"  -> Best Log-Loss: {optimized_loss:.4f}")

    # 6. Save Optimized & Calibrated Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(calibrated_model, "models/xgboost_calibrated.pkl")
    print("Calibrated model saved to models/xgboost_calibrated.pkl")

if __name__ == "__main__":
    optimize_xgboost()
