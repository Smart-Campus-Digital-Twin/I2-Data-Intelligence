import sys
import os
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
import mlflow
import mlflow.sklearn

# Allow importing src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.data.features import prepare_anomaly_data

def train_anomaly_model():
    print("Loading prepared equipment telemetry data...")
    X_splits, y_splits, feature_names = prepare_anomaly_data()
    X_train, X_test = X_splits
    y_train, y_test = y_splits
    
    # Configure MLflow explicitly
    print("Notice: Tracking MLflow locally to ./mlruns")
    mlflow_dir = os.path.abspath("./mlruns").replace("\\", "/")
    mlflow.set_tracking_uri("file:///" + mlflow_dir)
    mlflow.set_experiment("Equipment_Anomaly_Detection")
    
    with mlflow.start_run() as run:
        print("Training Isolation Forest...")
        
        # Estimate of the proportion of outliers in the system
        params = {
            "n_estimators": 150,
            "max_samples": "auto",
            "contamination": 0.08,  # Approximate failure pattern density from our generator
            "random_state": 42
        }
        
        mlflow.log_params(params)
        
        # Train model
        model = IsolationForest(**params)
        model.fit(X_train)
        
        # Inference on test set
        print("Evaluating model...")
        predictions_raw = model.predict(X_test)
        
        # Isolation Forest mapping:
        # returns -1 for anomalies, 1 for normal
        # Our ground truth: 1 for anomalies, 0 for normal
        predictions = np.where(predictions_raw == -1, 1, 0)
        
        # Metrics calculation
        precision = precision_score(y_test, predictions, zero_division=0)
        recall = recall_score(y_test, predictions, zero_division=0)
        f1 = f1_score(y_test, predictions, zero_division=0)
        
        print(f"Test Metrics:")
        print(f"  - Precision: {precision:.4f}")
        print(f"  - Recall:    {recall:.4f}")
        print(f"  - F1 Score:  {f1:.4f}")
        
        if precision > 0.90:
            print("[SUCCESS] Precision target met (> 0.90)")
        else:
            print("[WARNING] Precision target failed (< 0.90). This happens if contamination parameter or synthetic degradation overlaps significantly with pure normal boundaries.")
            
        mlflow.log_metrics({
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        })
        
        from mlflow.models.signature import infer_signature
        signature = infer_signature(X_train, model.predict(X_train))
        
        mlflow.sklearn.log_model(
            sk_model=model, 
            artifact_path="model", 
            signature=signature,
            registered_model_name="anomaly_detector"
        )
        print("Anomaly model successfully trained, logged, and registered to MLflow.")

if __name__ == "__main__":
    if not os.path.exists('data/synthetic/equipment_telemetry.csv'):
        print("Error: Please run this script from the root of I2-Data-Intelligence/")
        sys.exit(1)
        
    train_anomaly_model()
