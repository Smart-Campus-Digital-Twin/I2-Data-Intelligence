import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def ensure_dirs():
    """Ensure that the data directories exist."""
    os.makedirs('data/synthetic', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)

def generate_occupancy_energy(days=30):
    """
    Generates synthetic data for room occupancy and building energy consumption.
    Reflects a typical university schedule:
    - 8AM-10AM: Classrooms peak
    - 1PM: Cafeteria peak
    - Energy correlates with occupancy and outside temperature.
    """
    # Start tracking from 30 days ago
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
    timestamps = [start_time + timedelta(hours=i) for i in range(days * 24)]
    
    data = []
    for ts in timestamps:
        hour = ts.hour
        is_weekend = ts.weekday() >= 5
        
        # Base outside temperature (sine wave over the day)
        base_temp = 15 + 10 * np.sin(np.pi * (hour - 6) / 12) + np.random.normal(0, 1)
        weather_noise = np.random.normal(0, 2)
        
        # Classroom Occupancy
        if is_weekend:
            classroom_occ = np.random.randint(0, 5)
        else:
            if 8 <= hour <= 10:
                classroom_occ = np.random.randint(40, 60)
            elif 14 <= hour <= 16:
                classroom_occ = np.random.randint(30, 50)
            elif 8 <= hour <= 18:
                classroom_occ = np.random.randint(10, 25)
            else:
                classroom_occ = np.random.randint(0, 5)
            
        # Cafeteria Occupancy
        if is_weekend:
            cafe_occ = np.random.randint(0, 20)
        else:
            if 12 <= hour <= 14:
                cafe_occ = np.random.randint(100, 200)
            elif 8 <= hour <= 18:
                cafe_occ = np.random.randint(20, 50)
            else:
                cafe_occ = max(0, np.random.randint(-5, 10))
            
        # Energy Calculation (Energy = Occupancy * hvac factor + weather impact)
        # Using a simulated campus block of 10 classrooms + 1 cafeteria
        total_occ = classroom_occ * 10 + cafe_occ 
        hvac_factor = 1.2
        
        # Cooling/Heating load based on temp deviation from comfortable 22C
        temp_load = abs(22 - base_temp) * 3 
        
        energy_kw = (total_occ * hvac_factor) + temp_load + weather_noise
        energy_kw = max(20, energy_kw) # Base operational load of 20kW
        
        # Predictor columns
        data.append({
            'timestamp': ts,
            'outside_temp': round(base_temp, 2),
            'classroom_occupancy_avg': classroom_occ,
            'cafeteria_occupancy': cafe_occ,
            'total_occupancy': total_occ,
            'energy_kw': round(energy_kw, 2)
        })
        
    df = pd.DataFrame(data)
    df.to_csv('data/synthetic/occupancy_energy.csv', index=False)
    print(f"Generated {len(df)} rows for Occupancy & Energy.")

def generate_equipment_telemetry(hours=1000):
    """
    Generates synthetic sensor telemetry for equipment failure detection.
    Introduces anomalies characterized by a gradual increase in vibration
    and temperature before an actual system anomaly occurs.
    """
    start_time = datetime.now() - timedelta(hours=hours)
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    data = []
    
    # Define a few specific intervals where anomalies will happen
    anomaly_starts = [int(hours * 0.3), int(hours * 0.7), int(hours * 0.9)]
    anomaly_duration = 24 # Hours the anomaly stays active
    
    for i, ts in enumerate(timestamps):
        # Normal baseline operation limits
        vibration = 0.5 + np.random.normal(0, 0.05)
        pressure = 100 + np.random.normal(0, 2)
        temp = 45 + np.random.normal(0, 1)
        is_anomaly = 0
        
        for ast in anomaly_starts:
            # Check if within the degradation window (48 hours prior)
            if ast - 48 <= i < ast:
                degradation_factor = (i - (ast - 48)) / 48.0
                vibration += degradation_factor * 0.8
                temp += degradation_factor * 8
                
            # Check if currently in failure/anomaly state
            elif ast <= i < ast + anomaly_duration:
                vibration += 2.5 + np.random.normal(0, 0.5)
                temp += 20 + np.random.normal(0, 3)
                pressure -= 15 + np.random.normal(0, 5)
                is_anomaly = 1
                    
        data.append({
            'timestamp': ts,
            'vibration': round(vibration, 3),
            'pressure': round(pressure, 2),
            'temperature': round(temp, 2),
            'is_anomaly': is_anomaly
        })
        
    df = pd.DataFrame(data)
    df.to_csv('data/synthetic/equipment_telemetry.csv', index=False)
    print(f"Generated {len(df)} rows for Equipment Telemetry with {anomaly_duration * len(anomaly_starts)} anomaly hours.")

if __name__ == '__main__':
    # Ensure current working directory is the base project directory
    if not os.path.exists('src'):
        print("Warning: Please run this script from the root of I2-Data-Intelligence/")
        
    ensure_dirs()
    print("Generating synthetic datasets...")
    generate_occupancy_energy()
    generate_equipment_telemetry()
    print("Synthetic data generation complete. Datasets saved in 'data/synthetic/'.")
