# I2-Data-Intelligence

Real-time analytics, ML serving, and live event streaming for Smart Campus Digital Twin.

**Tech Stack**: Python (Spark, FastAPI), Node.js (Socket.IO), Redis, TimescaleDB, Kafka, MLflow  
**Status**: 83% Complete (5/6 tasks)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      I1-IOT-Streaming                               │
│    (Raw sensor ingestion via MQTT, Kafka, InfluxDB)                 │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ Processed data
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    I2-Data-Intelligence                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ I2-T2: TimescaleDB Analytics Schema                         │   │
│  │   - sensor_readings (hypertable, compressed, 90d retention) │   │
│  │   - academic_calendar (terms, exam periods, holidays)       │   │
│  │   - alerts, rooms, buildings                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ I2-T3: Spark Structured Streaming                           │   │
│  │   - Reads from: Kafka topics (sensor.raw, sensor.processed) │   │
│  │   - Writes to: Redis (room state), TimescaleDB (analytics)  │   │
│  │   - Aggregates: 5-sec tumbling windows, anomaly detection   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ I2-T4: ML Service (Training + Inference)                    │   │
│  │   - Train: EnergyModel, OccupancyModel (XGBoost)           │   │
│  │   - Infer: FastAPI service, MLflow registry                │   │
│  │   - Output: Redis predictions, Kafka ml.predictions        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ I2-T5: FastAPI REST API (IB-6)                              │   │
│  │   - Auth: JWT HS256 (8h expiry)                            │   │
│  │   - Endpoints: rooms, predictions, history, alerts         │   │
│  │   - Storage: Redis cache, TimescaleDB analytics            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ I2-T6: Socket.IO Real-Time Relay (NEW)                      │   │
│  │   - Node.js/Express on port 4000                            │   │
│  │   - Namespaces: /twin (auth), /admin (admin-only)           │   │
│  │   - Subscribes: Redis Pub/Sub channels                      │   │
│  │   - Emits: room.update, alert.new, node.offline events     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     I3-Sys.Eng-Frontend                              │
│          (Next.js 16, React 19, 3D visualization)                   │
│          Connected via Socket.IO to real-time events                │
└─────────────────────────────────────────────────────────────────────┘
```


## Task Status

| Task | Title | Status | Location |
|------|-------|--------|----------|
| I2-T1 | Docker Compose Stack | ✅ Complete | `docker-compose.yml` |
| I2-T2 | TimescaleDB Schema | ✅ Complete | `schema/schema.sql` |
| I2-T3 | Spark Streaming | ✅ Complete | `streaming/spark/` |
| I2-T4 | ML Service | 📋  | — |
| I2-T5 | FastAPI REST API | ✅ Complete | `i2-t5-fastapi/` |
| I2-T6 | Socket.IO Relay | ✅ Complete | `realtime/` |

## Quick Start

```bash
# 1. Setup
cd I2-Data-Intelligence
cp .env.example .env
# Edit .env with your secrets

# 2. Start all services
docker compose up -d

# 3. Check status
docker compose ps

# 4. Verify services
psql -h localhost -U ctuser -d campustwin -c "SELECT * FROM rooms;"
redis-cli ping
curl http://localhost:8000/api/v1/health
curl http://localhost:4000/health
curl http://localhost:5000/  # MLflow UI
```

## Completed Tasks

### ✅ I2-T1: Docker Compose Infrastructure
All 9 services running with health checks and volumes:
- **Kafka** (9092): KRaft mode, auto-created topics
- **Schema Registry** (8081), **MQTT** (1883), **TimescaleDB** (5432)
- **Redis** (6379), **MLflow** (5000), **InfluxDB** (8086), **MinIO** (9000)

### ✅ I2-T2: TimescaleDB Schema
Core tables and functions:
- `sensor_readings` hypertable (1-day chunks, 7-day compression, 90-day retention)
- `rooms`, `buildings`, `alerts`, `academic_terms`, `calendar_events`
- Functions: `get_current_academic_term()`, `get_occupancy_factor_for_date()`
- Alembic migrations for versioning

### ✅ I2-T3: Spark Structured Streaming
Reads `sensor.raw` from Kafka, processes with 5-second windows:
- Filters null errors, detects anomalies
- Writes to: TimescaleDB (sensor_readings), Redis (room state), Kafka (sensor.processed)
- Metrics logged to stdout

### ✅ I2-T5: FastAPI REST API (Port 8000)
Secured with JWT HS256. Core endpoints:
- `POST /api/v1/auth/token` — Get JWT
- `GET /api/v1/rooms`, `/rooms/{id}`, `/rooms/{id}/history`, `/predictions`, `/alerts`, `/buildings`
- `GET /api/v1/health`, `/metrics` — Service health & Prometheus metrics

### ✅ I2-T6: Socket.IO Real-Time Relay (Port 4000)
Node.js + Express with JWT auth:
- Namespaces: `/twin` (authenticated), `/admin` (admin-only)
- Subscribes to Redis: `room-updates` → emits `room.update`, `alert-events` → emits `alert.new`
- Metrics: Connected clients, events emitted

### 📋 I2-T4: ML Service (TODO)
Not yet merged. 


## Services Reference

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **Kafka** | 9092 | Event streaming | `kafka-topics.sh --list ...` |
| **Schema Registry** | 8081 | Kafka schema management | `curl http://localhost:8081/subjects` |
| **MQTT Broker** | 1883 | IoT device communication | `mosquitto_sub -h localhost -t test` |
| **TimescaleDB** | 5432 | Analytics (I2-T2) | `psql -h localhost ...` |
| **Redis** | 6379 | Caching & Pub/Sub | `redis-cli ping` |
| **MinIO** | 9000 | S3-compatible storage | `curl http://localhost:9000` |
| **MLflow** | 5000 | Model tracking | `http://localhost:5000` |
| **MLflow Postgres** | 5433 | MLflow backend DB | `psql -p 5433 ...` |
| **InfluxDB** | 8086 | Metrics | `curl http://localhost:8086/health` |
| **FastAPI** | 8000 | REST API (I2-T5) | `curl http://localhost:8000/api/v1/health` |
| **Socket.IO** | 4000 | Real-time Relay (I2-T6) | `curl http://localhost:4000/health` |

## Project Structure

```
I2-Data-Intelligence/
├── docker-compose.yml       # All 9 services
├── schema/                  # TimescaleDB schema
├── alembic/                 # Schema migrations
├── i2-t5-fastapi/           # FastAPI REST API
├── realtime/                # Socket.IO relay
├── streaming/spark/         # Spark streaming job
└── infra/                   # Infrastructure configs
```

## Common Commands

```bash
# Start/Stop
docker compose up -d
docker compose down
docker compose ps

# Database
psql -h localhost -U ctuser -d campustwin
redis-cli

# Logs
docker compose logs -f i2-t5-fastapi
docker compose logs -f realtime

# Test API
curl -X GET http://localhost:8000/api/v1/health

# Check Kafka
docker exec i2-kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Containers not starting | `docker compose down -v && docker compose up -d` |
| Connection refused | Check `docker compose ps`, verify port not in use |
| JWT auth fails | Verify `JWT_SECRET` in `.env` matches all services |
| Kafka topics missing | Wait 60s for auto-creation, or check `docker compose logs kafka` |


---

**Last Updated**: May 5, 2026
