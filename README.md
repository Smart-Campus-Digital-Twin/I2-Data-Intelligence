# I2 Data & Intelligence Subsystem - Smart Campus Digital Twin

This project contains the machine learning core for the Smart Campus Digital Twin, designed for a university capstone project. 

## Features
- **Energy Consumption Predictor**: XGBoost Regressor for short-term facility energy forecasting.
- **Occupancy Predictor**: LightGBM Classifier to categorize room fullness.
- **Equipment Anomaly Detector**: Isolation Forest identifying anomalous vibrations/temperatures.
- **Real-Time Streaming**: Integrated Kafka processing and inference engine.
- **REST APIs**: FastAPI wrappers serving live prediction data to the I3 UI domain.

## Getting Started

1. Set up the local Python environment:
    ```bash
    python -m venv venv
    source venv/Scripts/activate # Windows
    pip install -r requirements.txt
    ```

2. Start the infrastructure (Kafka, DBs, MLflow, Prometheus, Grafana):
    ```bash
    docker-compose up -d
    ```

3. Run data generation:
    ```bash
    python src/data/synthetic_generator.py
    ```

## Folders
- `data/`: Raw, synthetic, and processed features.
- `src/data/`: Scripts for generation and extraction.
- `src/models/`: Training pipelines for estimators.
- `src/inference/`: Kafka consumers for real-time evaluations.
- `src/api/`: Outbound FastAPI service endpoints.
- `src/monitoring/`: Metrics exporters for Prometheus.
- `notebooks/`: Exporatory code and experiments.


