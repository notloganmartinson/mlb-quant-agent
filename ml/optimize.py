import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import log_loss
import joblib
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def optimize_xgboost():
    """
    Performs Grid Search to find the best hyperparameters for the MLB binary classifier.
    Optimizes directly for Log-Loss.
    """
    print("Starting Hyperparameter Optimization for Binary Classifier...")
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # Convert target to binary
    y_train_won = (y_train.iloc[:, 0] > y_train.iloc[:, 1]).astype(int)
    y_test_won = (y_test.iloc[:, 0] > y_test.iloc[:, 1]).astype(int)

    # 1. Define Search Space
    param_grid = {
        'max_depth': [3, 4, 5],
        'learning_rate': [0.01, 0.05, 0.1],
        'n_estimators': [100, 200, 300],
        'subsample': [0.8, 1.0]
    }

    # 2. Initialize Grid Search
    base_model = xgb.XGBClassifier(objective='binary:logistic', random_state=42, eval_metric='logloss')
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        scoring='neg_log_loss',
        cv=3,
        verbose=1
    )

    # 3. Fit Grid Search
    grid_search.fit(X_train, y_train_won)

    best_model = grid_search.best_estimator_
    print(f"\nBest Parameters Found: {grid_search.best_params_}")

    # 4. Final Evaluation
    raw_probs_test = best_model.predict_proba(X_test)[:, 1]
    
    raw_loss = log_loss(y_test_won, raw_probs_test)
    
    print(f"\nOptimized Results (Raw, 2025 Holdout):")
    print(f"  -> Best Win Log-Loss (Raw): {raw_loss:.4f}")

    # 5. Save Optimized Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/xgboost_optimized.joblib")
    print("Optimized model saved to models/xgboost_optimized.joblib")

if __name__ == "__main__":
    optimize_xgboost()