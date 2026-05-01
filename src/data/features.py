import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

def ensure_dirs():
    """Ensure artifacts directory exists for saving scalers."""
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('src/models/artifacts', exist_ok=True)

def create_time_features(df, time_col='timestamp'):
    """Extract hour, day, and weekend features from timestamp."""
    df[time_col] = pd.to_datetime(df[time_col])
    df['hour'] = df[time_col].dt.hour
    df['day_of_week'] = df[time_col].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    return df

def create_lag_features(df, feature_cols, lags=[1, 2, 3]):
    """Shift features to create lagging parameters for time-series forecasting."""
    for col in feature_cols:
        for lag in lags:
            df[f'{col}_lag_{lag}'] = df[col].shift(lag)
    df.dropna(inplace=True)
    return df

def prepare_energy_data(test_size=0.2, val_size=0.1):
    """
    Preprocess data for Energy Prediction (XGBoost).
    Target: energy_kw
    """
    df = pd.read_csv('data/synthetic/occupancy_energy.csv')
    df = create_time_features(df)
    
    # Introduce lag features for energy prediction
    # Lags: 1 hour ago, and 24 hours ago (yesterday's pattern)
    df = create_lag_features(df, ['energy_kw', 'outside_temp', 'total_occupancy'], lags=[1, 24])
    
    # Features & Target
    features = [
        'outside_temp', 'total_occupancy', 'hour', 'day_of_week', 'is_weekend',
        'energy_kw_lag_1', 'energy_kw_lag_24',
        'outside_temp_lag_1', 'outside_temp_lag_24',
        'total_occupancy_lag_1', 'total_occupancy_lag_24'
    ]
    target = 'energy_kw'
    
    X = df[features]
    y = df[target]
    
    # Time-series aware split (shuffle=False)
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=test_size, random_state=42, shuffle=False)
    
    # Train/Validation Split from temp
    val_ratio = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=val_ratio, random_state=42, shuffle=False)
    
    # Scaling
    scaler = StandardScaler()
    # Ensure indices are kept as DataFrame for easier MLFlow signature logging later
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=features)
    X_val_scaled = pd.DataFrame(scaler.transform(X_val), columns=features)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=features)
    
    ensure_dirs()
    joblib.dump(scaler, 'src/models/artifacts/energy_scaler.joblib')
    
    return (X_train_scaled, X_val_scaled, X_test_scaled), (y_train, y_val, y_test), features

def prepare_occupancy_data(test_size=0.2):
    """
    Preprocess data for Occupancy Prediction (LightGBM).
    Target classification: Empty(0), Low(1), Medium(2), Full(3)
    """
    df = pd.read_csv('data/synthetic/occupancy_energy.csv')
    df = create_time_features(df)
    
    # Create target bins for classification
    def categorize_occupancy(occ):
        if occ < 10: return 0      # Empty
        elif occ < 50: return 1    # Low
        elif occ < 120: return 2   # Medium
        else: return 3             # Full
        
    df['occupancy_class'] = df['total_occupancy'].apply(categorize_occupancy)
    
    # Features & Target
    features = ['outside_temp', 'hour', 'day_of_week', 'is_weekend']
    target = 'occupancy_class'
    
    X = df[features]
    y = df[target]
    
    # Time-series aware split (shuffle=False)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42, shuffle=False)
    
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=features)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=features)
    
    ensure_dirs()
    joblib.dump(scaler, 'src/models/artifacts/occupancy_scaler.joblib')
    
    return (X_train_scaled, X_test_scaled), (y_train, y_test), features

def prepare_anomaly_data(test_size=0.2):
    """
    Preprocess data for Anomaly Detection (Isolation Forest).
    Unsupervised training on normal data.
    """
    df = pd.read_csv('data/synthetic/equipment_telemetry.csv')
    
    features = ['vibration', 'pressure', 'temperature']
    target = 'is_anomaly'
    
    X = df[features]
    y = df[target]
    
    # Random split is fine for generalized anomaly detection demonstration
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=features)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=features)
    
    ensure_dirs()
    joblib.dump(scaler, 'src/models/artifacts/anomaly_scaler.joblib')
    
    return (X_train_scaled, X_test_scaled), (y_train, y_test), features

if __name__ == '__main__':
    print("Testing Feature Factory...")
    
    try:
        X_splits, y_splits, feats = prepare_energy_data()
        print(f"[OK] Energy Prep | Train: {X_splits[0].shape[0]}, Val: {X_splits[1].shape[0]}, Test: {X_splits[2].shape[0]}")
        
        X_occ, y_occ, feat_occ = prepare_occupancy_data()
        print(f"[OK] Occupancy Prep | Train: {X_occ[0].shape[0]}, Test: {X_occ[1].shape[0]}")
        
        X_ano, y_ano, feat_ano = prepare_anomaly_data()
        print(f"[OK] Anomaly Prep | Train: {X_ano[0].shape[0]}, Test: {X_ano[1].shape[0]}")
        
        print("Feature engineering successful! Scalers exported to 'src/models/artifacts/'.")
    except Exception as e:
        print(f"Error during preprocessing: {e}")
