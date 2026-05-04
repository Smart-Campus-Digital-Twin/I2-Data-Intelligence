# I2-Data-Intelligence: Smart Campus Digital Twin Backend

This repository contains the complete backend infrastructure for the Smart Campus Digital Twin project, orchestrated with Docker Compose. It provides a full local development environment with all necessary data services.

## Services

The following 9 services are included in this stack:

1.  **Kafka (Confluent)**: A production-grade distributed event streaming platform running in KRaft mode with optimized Schema Registry integration.
2.  **Schema Registry**: Manages schemas for Kafka topics with reliable coordination.
3.  **MQTT Broker**: For IoT device communication.
4.  **TimescaleDB**: A PostgreSQL database with time-series superpowers for sensor data.
5.  **Redis**: In-memory data store for caching and real-time analytics.
6.  **MinIO**: S3-compatible object storage for large files and ML artifacts.
7.  **MLflow**: An open-source platform to manage the ML lifecycle.
8.  **PostgreSQL (for MLflow)**: Backend database for MLflow tracking.
9.  **InfluxDB**: A time-series database for monitoring and metrics.

## Getting Started

### Prerequisites

-   Docker Desktop (version 4.10+ is recommended).
-   An internet connection to pull Docker images.
-   Approximately 2GB of free disk space for images and volumes.

### 1. Clone the Repository

Ensure you have the project files in your local directory.

### 2. Start the Stack

Navigate to the project root (`I2-Data-Intelligence`) and run the following command to start all services in detached mode:

```bash
docker compose up -d
```

It may take 60-90 seconds for all services to initialize and become healthy.

### 3. Verify the Deployment

You can check the status of all containers with:

```bash
docker compose ps
```

All services should show a `running` or `healthy` status.

For a comprehensive check, run the verification script:

```bash
bash verify.sh
```

This script runs over 40 automated checks to ensure every component of the stack is functioning correctly.

## Service Endpoints and Credentials

| Service           | URL                       | Username     | Password  | Notes                               |
| ----------------- | ------------------------- | ------------ | --------- | ----------------------------------- |
| **Kafka**         | `localhost:9092`          | -            | -         | Broker for producers/consumers      |
| **Schema Registry** | `http://localhost:8081`   | -            | -         | Avro/JSON Schema management         |
| **MQTT Broker**   | `localhost:1883`          | -            | -         | Anonymous access enabled            |
| **TimescaleDB**   | `localhost:5432`          | `ctuser`     | `ctpass`  | Database: `campustwin`              |
| **Redis**         | `localhost:6379`          | -            | -         | In-memory cache and pub/sub         |
| **MinIO API**     | `http://localhost:9000`   | `minioadmin` | `minioadmin`| S3-compatible API endpoint          |
| **MinIO Console** | `http://localhost:9002`   | `minioadmin` | `minioadmin`| Web UI for object storage           |
| **MLflow Server** | `http://localhost:5000`   | -            | -         | ML experiment tracking UI           |
| **MLflow Postgres** | `localhost:5433`          | `mlflow`     | `mlflow`  | Backend DB for MLflow               |
| **InfluxDB**      | `http://localhost:8086`   | `admin`      | `adminpass` | Org: `campus-org`, Bucket: `campustwin` |

## Design & Implementation Notes

*   **Kafka Image**: We use `confluentinc/cp-kafka:7.6.0` (Confluent's production-grade Kafka distribution) instead of alternatives:
    - **Not `bitnami/kafka`**: This image is no longer publicly available as Bitnami has transitioned its main `bitnami/kafka` repository to a commercial model without public tags.
    - **Not `apache/kafka`**: While available, the official Apache image lacks optimized integration with Schema Registry, causing consumer group coordination timeouts during initialization.
    - **Why Confluent**: Provides better integration and reliability with Schema Registry coordination, is production-tested, and includes optimized Kafka broker binaries for seamless group coordination and leader election.
*   **KRaft Mode**: The Kafka broker runs in the modern, Zookeeper-less KRaft mode for simplified architecture and better resource efficiency.

## Stopping the Environment

To stop all running services, run:

```bash
docker compose down
```

To stop services and remove all persistent data (volumes), use:

```bash
docker compose down -v
```
