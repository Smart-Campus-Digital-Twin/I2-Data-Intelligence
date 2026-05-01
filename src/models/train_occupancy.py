import sys
import os
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
from sklearn.metrics import f1_score, accuracy_score

# Allow importing src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.data.features import prepare_occupancy_data

def train_occupancy_model():
    print("Loading prepared occupancy data...")
    X_splits, y_splits, feature_names = prepare_occupancy_data()
    X_train, X_test = X_splits
    y_train, y_test = y_splits
    
    # Configure MLflow safely for local student usage
    print("Notice: Tracking MLflow locally to ./mlruns")
    mlflow_dir = os.path.abspath("./mlruns").replace("\\", "/")
    mlflow.set_tracking_uri("file:///" + mlflow_dir)
    mlflow.set_experiment("Occupancy_Prediction")
    
    with mlflow.start_run() as run:
        print("Training LightGBM Classifier...")
        
        # Hyperparameters for 4-class categorization (Empty, Low, Medium, Full)
        params = {
            "objective": "multiclass",
            "num_class": 4,
            "n_estimators": 150,
            "learning_rate": 0.05,
            "max_depth": 5,
            "random_state": 42
        }
        
        mlflow.log_params(params)
        
        # Train model
        model = lgb.LGBMClassifier(**params)
        
        # Early stopping requires a list of callbacks in newer LightGBM versions
        # Using a direct fit to maintain simplicity for the script without pulling deep callbacks
        model.fit(
            X_train, y_train, 
            eval_set=[(X_test, y_test)]
        )
        
        # Inference on test set
        print("Evaluating model...")
        predictions = model.predict(X_test)
        
        # Calculate macro F1-score across all 4 classes
        f1_macro = f1_score(y_test, predictions, average='macro')
        acc = accuracy_score(y_test, predictions)
        
        print(f"Test Metrics:")
        print(f"  - Accuracy: {acc:.2%}")
        print(f"  - F1 Score (Macro): {f1_macro:.4f}")
        
        if f1_macro > 0.85:
            print("[SUCCESS] F1-Score target met (> 0.85)")
        else:
            print("[WARNING] F1-Score target failed (< 0.85)")
            
        mlflow.log_metrics({
            "f1_score_macro": f1_macro,
            "accuracy": acc
        })
        
        from mlflow.models.signature import infer_signature
        signature = infer_signature(X_train, model.predict(X_train))
        
        mlflow.lightgbm.log_model(
            lgb_model=model, 
            artifact_path="model", 
            signature=signature,
            registered_model_name="occupancy_predictor"
        )
        print("Occupancy model successfully trained, logged, and registered to MLflow.")

if __name__ == "__main__":
    if not os.path.exists('data/synthetic/occupancy_energy.csv'):
        print("Error: Please run this script from the root of I2-Data-Intelligence/")
        sys.exit(1)
        
    train_occupancy_model()
