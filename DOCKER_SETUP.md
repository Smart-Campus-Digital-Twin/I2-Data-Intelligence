# I2-T1: Docker Compose — Full Local Dev Stack

## Overview

This is the complete local development infrastructure for the Smart Campus Digital Twin project. It includes all services required for the I2 (Data & Intelligence) group to function independently.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        dev-tools Network (Bridge)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Kafka 9092   │  │ Schema Reg   │  │ MQTT 1883    │  │ TimescaleDB  │  │
│  │ (KRaft)      │  │ 8081         │  │ WebSocket    │  │ 5432         │  │
│  │              │  │              │  │ 9001         │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Redis 6379   │  │ InfluxDB     │  │ MinIO        │  │ MLflow       │  │
│  │ Cache & Pub  │  │ 8086         │  │ 9000/9001    │  │ 5000         │  │
│  │              │  │              │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ MLflow PostgreSQL 5433 (Backend)                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Services

### Core Data Pipeline
- **Kafka** (9092) — Message broker, KRaft mode, auto-creates topics:
  - `sensor.raw` (12 partitions)
  - `sensor.processed` (6 partitions)
  - `sensor.anomaly` (3 partitions)
  - `ml.predictions` (3 partitions)
  - `node.heartbeat` (3 partitions)
  - `sensor.dlq` (3 partitions)
  
- **Schema Registry** (8081) — Avro/JSON schema management
- **MQTT Broker** (1883, 9001) — IoT message protocol
- **TimescaleDB** (5432) — Time-series analytics database
- **Redis** (6379) — Cache, Pub/Sub, session store

### ML & Tracking
- **MLflow** (5000) — ML experiment tracking and model registry
- **MLflow PostgreSQL** (5433) — Backend for MLflow metadata
- **MinIO** (9000/9001) — S3-compatible artifact storage

### Monitoring & Analytics
- **InfluxDB** (8086) — Time-series metrics database

## Quick Start

### Prerequisites
- Docker & Docker Compose v2.0+
- 8+ GB RAM available
- 20 GB disk space

### 1. Start All Services

```bash
# From project root directory
docker compose up -d

# Wait for all services to be healthy (~30-60 seconds)
docker compose ps

# Watch startup logs
docker compose logs -f
```

### 2. Verify Services

```bash
# Check all containers are healthy
docker compose ps

# Expected output: all services should show "healthy" or "running"
```

### 3. Test Database Connection

```bash
# Connect to TimescaleDB
psql -h localhost -U ctuser -d campustwin -c "SELECT version();"

# Credentials: user=ctuser, password=ctpass, db=campustwin
```

### 4. Verify Kafka Topics

```bash
# List all Kafka topics (may take a few seconds to appear)
docker exec i2-kafka kafka-topics.sh --list --bootstrap-server kafka:9092

# Should show: sensor.raw, sensor.processed, sensor.anomaly, ml.predictions, node.heartbeat, sensor.dlq
```

### 5. Access Web Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| MLflow | http://localhost:5000 | (no auth for dev) |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| InfluxDB | http://localhost:8086 | admin / adminpass |
| Kafka UI | (optional, install separately) | — |

## Database Schema

### Tables (created automatically via init.sql)

**buildings** — Campus building metadata
- building_id, name, floors, address

**rooms** — Room/space metadata
- room_id, name, building_id, floor, capacity, room_type

**sensor_readings** (hypertable) — Time-series sensor data
- ts (timestamp), room_id, building_id, sensor_type, avg_value, min_value, max_value, anomaly_flag, anomaly_type

**alerts** — Anomaly & system alerts
- alert_id, room_id, severity, anomaly_type, message, triggered_at, resolved

**node_status** — ESP32 sensor node status
- node_id, room_id, last_heartbeat, is_online, firmware_version, signal_strength, uptime_seconds

**ml_predictions** — ML model predictions
- prediction_id, room_id, prediction_type, predicted_value, confidence, model_version, valid_until

### Hypertable Configuration

**sensor_readings** is configured with:
- **Chunk interval**: 1 day
- **Compression**: Enabled after 7 days
- **Retention**: 90 days
- **Indexes**: On (room_id, ts), (sensor_type, ts), anomaly_flag

### Sample Data

The init.sql automatically populates:
- 3 buildings
- 5 sample rooms across buildings
- 24 hours of synthetic sensor readings

## Configuration

### Environment Variables

All configuration is set in `docker-compose.yml`. Key variables:

```yaml
# TimescaleDB
POSTGRES_DB: campustwin
POSTGRES_USER: ctuser
POSTGRES_PASSWORD: ctpass

# MLflow
MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:mlflow@mlflow-postgres:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://mlflow-artifacts

# MinIO (S3)
MINIO_ROOT_USER: minioadmin
MINIO_ROOT_PASSWORD: minioadmin

# InfluxDB
DOCKER_INFLUXDB_INIT_ORG: campus-org
DOCKER_INFLUXDB_INIT_BUCKET: campustwin
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: campus-token-secret-key

# Redis
# Keyspace notifications enabled (Kex) for monitoring
# Max memory: 512MB with LRU eviction
```

## Health Checks

Each service has a health check that runs every 10 seconds:

```bash
# View health status
docker compose ps

# Check specific service
docker inspect i2-kafka | grep -A 5 "State"

# View health check logs
docker compose exec kafka kafka-broker-api-versions.sh --bootstrap-server kafka:9092
```

## Stopping & Cleanup

```bash
# Stop all services (keep volumes)
docker compose stop

# Stop and remove containers (keep volumes)
docker compose down

# Full cleanup (remove volumes too - CAUTION: loses all data)
docker compose down -v

# Remove only specific volume
docker volume rm i2-data-intelligence_timescaledb-data
```

## Troubleshooting

### Services not starting

```bash
# Check logs
docker compose logs <service-name>

# Example
docker compose logs kafka
docker compose logs timescaledb
```

### Database connection refused

```bash
# Wait a bit longer for TimescaleDB to initialize (~20-30 seconds)
# Check if port is in use
lsof -i :5432

# Restart just the database
docker compose restart timescaledb
```

### Out of memory

```bash
# Check Docker memory allocation
docker stats

# Reduce Redis max memory in docker-compose.yml
# Adjust Kafka broker memory settings
```

### Kafka topics not auto-created

```bash
# Manually create topics
docker exec i2-kafka kafka-topics.sh --create \
  --bootstrap-server kafka:9092 \
  --topic sensor.raw \
  --partitions 12 \
  --replication-factor 1

# List created topics
docker exec i2-kafka kafka-topics.sh --list --bootstrap-server kafka:9092
```

### Redis Pub/Sub not working

```bash
# Test Redis Pub/Sub
docker exec i2-redis redis-cli PING
docker exec i2-redis redis-cli INFO replication

# Check keyspace notifications enabled
docker exec i2-redis redis-cli CONFIG GET notify-keyspace-events
```

## Testing the Pipeline

### Test 1: Publish MQTT Message

```bash
# From another terminal, publish a test message
docker exec i2-mqtt-broker mosquitto_pub \
  -h localhost \
  -t "campus/eng-block-a/room-101/temperature" \
  -m '{"schema":"SensorReading/v1","readingId":"550e8400-e29b-41d4-a716-446655440000","nodeId":"sensor-101","buildingId":"eng-block-a","roomId":"room-101","type":"temperature","value":22.5,"unit":"°C","ts":'$(date +%s000)',"error":null}'
```

### Test 2: Query TimescaleDB

```bash
# Connect to database
psql -h localhost -U ctuser -d campustwin

# View sample data
SELECT * FROM sensor_readings LIMIT 5;
SELECT * FROM rooms;
SELECT * FROM alerts;

# View hypertable info
SELECT hypertable_name, owner, schema_name FROM timescaledb_information.hypertables;
```

### Test 3: Check Redis

```bash
# Connect to Redis
docker exec i2-redis redis-cli

# In Redis CLI:
PING
INFO stats
KEYS *
```

### Test 4: MLflow

```bash
# Check MLflow
curl http://localhost:5000/api/2.0/mlflow/version

# View in browser
open http://localhost:5000
```

## Performance Notes

- **Kafka**: Configuration tuned for dev (single broker, 1 replication factor)
- **TimescaleDB**: 256MB shared buffers, up to 100 connections
- **Redis**: 512MB max memory with LRU eviction
- **All services**: Health checks every 10s, start period 10-30s

For production, increase replicas, memory, and implement clustering.

## Next Steps

After verifying this stack is healthy:

1. **I1-T3**: Start sensor simulator to publish MQTT messages
2. **I2-T3**: Deploy Spark streaming job to consume from Kafka
3. **I2-T5**: Deploy FastAPI REST API
4. **I2-T6**: Deploy Node.js Socket.IO relay server
5. **I3-T1**: Build React dashboard

## Support

For issues or questions:
1. Check `docker compose logs <service>`
2. Verify all containers are healthy: `docker compose ps`
3. Check port availability: `netstat -tulpn | grep -E '9092|8081|1883|5432|6379|5000'`

---

**Created**: I2-T1 Docker Compose Implementation  
**Last Updated**: 2026-05-02  
**Status**: Ready for development
