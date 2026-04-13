import xgboost as xgb
from sklearn.metrics import log_loss, accuracy_score
import joblib
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())
from ml.preprocess import load_and_preprocess_data

def train_baseline_xgboost():
    """
    Trains an initial XGBoost model and establishes a baseline Log-Loss.
    """
    print("Establishing Baseline XGBoost Model...")
    
    # 1. Load Data
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data()

    # 2. Initialize Model
    # We use conservative default parameters for the baseline
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective='binary:logistic',
        random_state=42,
        eval_metric='logloss'
    )

    # 3. Train Model
    model.fit(X_train, y_train)

    # 4. In-Sample Evaluation (Train)
    y_train_prob = model.predict_proba(X_train)[:, 1]
    train_loss = log_loss(y_train, y_train_prob)
    
    # 5. Out-of-Sample Evaluation (Test - 2025)
    y_test_prob = model.predict_proba(X_test)[:, 1]
    y_test_pred = model.predict(X_test)
    
    test_loss = log_loss(y_test, y_test_prob)
    test_acc = accuracy_score(y_test, y_test_pred)

    print("\nBaseline Results:")
    print(f"  -> Train Log-Loss: {train_loss:.4f}")
    print(f"  -> Test Log-Loss (2025): {test_loss:.4f}")
    print(f"  -> Test Accuracy: {test_acc:.2%}")

    # 6. Save Model
    os.makedirs("models", exist_ok=True)
    model_path = "models/xgboost_baseline.json"
    model.save_model(model_path)
    print(f"\nModel saved to {model_path}")

    return model

if __name__ == "__main__":
    train_baseline_xgboost()
