import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import log_loss, mean_absolute_error
from sklearn.multioutput import MultiOutputRegressor
from scipy.stats import skellam
import joblib
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def optimize_xgboost():
    """
    Performs Grid Search to find the best hyperparameters for the MLB model.
    Includes Tweedie variance power for overdispersion tuning.
    """
    print("Starting Hyperparameter Optimization for Calibrated Run Estimator...")
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # 1. Define Search Space
    # Prefix with estimator__ for MultiOutputRegressor
    param_grid = {
        'estimator__max_depth': [3, 4, 5],
        'estimator__learning_rate': [0.01, 0.05, 0.1],
        'estimator__n_estimators': [100, 200],
        'estimator__tweedie_variance_power': [1.1, 1.5, 1.9],
        'estimator__subsample': [0.8, 1.0]
    }

    # 2. Initialize Grid Search
    # Tweedie objective is used for regression with overdispersion
    base_model = xgb.XGBRegressor(objective='reg:tweedie', random_state=42)
    grid_search = GridSearchCV(
        estimator=MultiOutputRegressor(base_model),
        param_grid=param_grid,
        scoring='neg_mean_absolute_error',
        cv=3,
        verbose=1
    )

    # 3. Fit Grid Search
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    print(f"\nBest Parameters Found: {grid_search.best_params_}")

    # 4. Final Evaluation
    y_test_pred = best_model.predict(X_test)
    
    # Calculate Raw Win Probability using Skellam
    prob_win_raw = skellam.sf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    prob_tie_raw = skellam.pmf(0, y_test_pred[:, 0], y_test_pred[:, 1])
    test_win_prob_raw = prob_win_raw / (1 - prob_tie_raw)
    
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)
    
    raw_loss = log_loss(y_test_won, test_win_prob_raw)
    mae = mean_absolute_error(y_test, y_test_pred)
    
    print(f"\nOptimized Results (Raw, 2022 Holdout):")
    print(f"  -> Best Win Log-Loss (Raw): {raw_loss:.4f}")
    print(f"  -> Mean Absolute Error (Runs): {mae:.4f}")

    # 5. Save Optimized Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/xgboost_optimized.joblib")
    print("Optimized model saved to models/xgboost_optimized.joblib")

if __name__ == "__main__":
    optimize_xgboost()
