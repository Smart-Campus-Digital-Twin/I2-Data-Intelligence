import sys
import os
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, mean_absolute_error

# Allow importing src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.data.features import prepare_energy_data

def train_energy_model():
    print("Loading prepared energy data...")
    X_splits, y_splits, feature_names = prepare_energy_data()
    X_train, X_val, X_test = X_splits
    y_train, y_val, y_test = y_splits
    
    # Configure MLflow
    print("Notice: Tracking MLflow locally to ./mlruns")
    mlflow_dir = os.path.abspath("./mlruns").replace("\\", "/")
    mlflow.set_tracking_uri("file:///" + mlflow_dir)
    mlflow.set_experiment("Energy_Consumption_Prediction")
    
    with mlflow.start_run() as run:
        print("Training XGBoost Regressor...")
        
        # Hyperparameters (realistic priorities: simple but effective)
        params = {
            "objective": "reg:squarederror",
            "n_estimators": 150,
            "learning_rate": 0.05,
            "max_depth": 5,
            "random_state": 42
        }
        
        mlflow.log_params(params)
        
        # Initialize and Train model
        model = xgb.XGBRegressor(**params)
        
        # XGBoost early stopping requires the eval set format matching the training features
        # Note: XGBoost >= 1.3 uses `early_stopping_rounds` directly, but in fit() for newer versions
        model.fit(
            X_train, y_train, 
            eval_set=[(X_val, y_val)], 
            verbose=False
        )
        
        # Inference on test set
        print("Evaluating model...")
        predictions = model.predict(X_test)
        
        # Metrics calculation
        mape = mean_absolute_percentage_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        mae = mean_absolute_error(y_test, predictions)
        
        print(f"Test Metrics:")
        print(f"  - MAPE: {mape:.2%}")
        print(f"  - RMSE: {rmse:.2f} kW")
        print(f"  - MAE:  {mae:.2f} kW")
        
        # Check objective threshold
        if mape < 0.10:
            print("[SUCCESS] MAPE targets met (< 10%)")
        else:
            print("[WARNING] MAPE target failed (> 10%). Consider hyperparameter tuning.")
            
        # Log metrics to MLflow
        mlflow.log_metrics({
            "mape": mape,
            "rmse": rmse,
            "mae": mae
        })
        
        # Log model context via MLFlow
        # Using a dummy input signature
        from mlflow.models.signature import infer_signature
        signature = infer_signature(X_train, model.predict(X_train))
        
        mlflow.xgboost.log_model(
            xgb_model=model, 
            artifact_path="model", 
            signature=signature,
            registered_model_name="energy_predictor"
        )
        print("Model successfully trained, logged, and registered to MLflow.")

if __name__ == "__main__":
    if not os.path.exists('data/synthetic/occupancy_energy.csv'):
        print("Error: Please run this script from the root of I2-Data-Intelligence/")
        sys.exit(1)
        
    train_energy_model()
