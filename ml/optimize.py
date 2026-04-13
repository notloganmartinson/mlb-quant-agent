import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import log_loss
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
    X_train, X_test, y_train, y_test = load_and_preprocess_data()

    # 1. Define Search Space
    param_grid = {
        'max_depth': [3, 5, 6],
        'learning_rate': [0.01, 0.05, 0.1],
        'n_estimators': [100, 200],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0]
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

    # 4. Final Evaluation
    y_prob = best_model.predict_proba(X_test)[:, 1]
    optimized_loss = log_loss(y_test, y_prob)
    
    print(f"\nOptimized Results (2025 Holdout):")
    print(f"  -> Best Log-Loss: {optimized_loss:.4f}")

    # 5. Save Optimized Model
    os.makedirs("models", exist_ok=True)
    best_model.save_model("models/xgboost_optimized.json")
    print("Optimized model saved to models/xgboost_optimized.json")

if __name__ == "__main__":
    optimize_xgboost()
