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

<<<<<<< HEAD

## Task Status

| Task  | Title                | Status      | Location             |
| ----- | -------------------- | ----------- | -------------------- |
| I2-T1 | Docker Compose Stack | ✅ Complete | `docker-compose.yml` |
| I2-T2 | TimescaleDB Schema   | ✅ Complete | `schema/schema.sql`  |
| I2-T3 | Spark Streaming      | ✅ Complete | `streaming/spark/`   |
| I2-T4 | ML Service           | 📋          | —                    |
| I2-T5 | FastAPI REST API     | ✅ Complete | `i2-t5-fastapi/`     |
| I2-T6 | Socket.IO Relay      | ✅ Complete | `realtime/`          |

## Quick Start

### 1. Setup Environment

````bash
=======

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
>>>>>>> main
# 1. Setup
cd I2-Data-Intelligence
cp .env.example .env
# Edit .env with your secrets

# 2. Start all services
docker compose up -d
<<<<<<< HEAD
````

# 3. Check status

docker compose ps

**TimescaleDB**:

```bash
psql -h localhost -U ctuser -d campustwin -c "SELECT * FROM rooms;"
psql -h localhost -U ctuser -d campustwin -c "SELECT * FROM timescaledb_information.hypertables;"
```

**Redis**:

```bash
redis-cli ping
redis-cli KEYS '*'
```

**Kafka**:

```bash
docker exec i2-kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

**Socket.IO**:

```bash
=======

# 3. Check status
docker compose ps

# 4. Verify services
psql -h localhost -U ctuser -d campustwin -c "SELECT * FROM rooms;"
redis-cli ping
curl http://localhost:8000/api/v1/health
>>>>>>> main
curl http://localhost:4000/health
curl http://localhost:5000/  # MLflow UI
```

## Completed Tasks

<<<<<<< HEAD

### ✅ I2-T2: TimescaleDB Schema + Migrations

- **Location**: `schema/schema.sql`, `alembic/versions/001_initial_schema.py`, `db/migrations.py`
- **Features**:
  - `sensor_readings` hypertable (1-day chunks, 7-day compression, 90-day retention)
  - **Academic Calendar Tables** (NEW):
    - `academic_terms`: Semester/term definitions with date ranges
    - `calendar_events`: Holidays, exam periods, reading weeks, special events
    - `occupancy_factor`: Configurable multiplier for each event type
  - Master data: `buildings`, `rooms`, `alerts`
  - Functions: `get_current_academic_term()`, `get_occupancy_factor_for_date(date)`
  - Materialized views: `mv_latest_occupancy`, `mv_recent_anomalies`
  - Alembic migrations for versioning and rollback

### ✅ I2-T6: Socket.IO Real-Time Relay Server

- **Location**: `realtime/src/index.js`, `realtime/src/services/jwt.js`, `realtime/src/services/redis.js`
- **Features**:
  - Node.js/Express on port 4000
  - Two namespaces: `/twin` (authenticated), `/admin` (admin-only)
  - JWT HS256 authentication middleware
  - Redis Pub/Sub subscriptions:
    - `room-updates` → emit `room.update` events
    - `alert-events` → emit `alert.new` events
    - Keyspace notifications for node heartbeat expiration
  - Prometheus metrics: connected clients, event counters
  - Health check endpoints: `/health`, `/metrics`, `/info`
  - # Graceful shutdown with signal handlers

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
  > > > > > > > main

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

| Service             | Port | Purpose                  | Health Check                               |
| ------------------- | ---- | ------------------------ | ------------------------------------------ |
| **Kafka**           | 9092 | Event streaming          | `kafka-topics.sh --list ...`               |
| **Schema Registry** | 8081 | Kafka schema management  | `curl http://localhost:8081/subjects`      |
| **MQTT Broker**     | 1883 | IoT device communication | `mosquitto_sub -h localhost -t test`       |
| **TimescaleDB**     | 5432 | Analytics (I2-T2)        | `psql -h localhost ...`                    |
| **Redis**           | 6379 | Caching & Pub/Sub        | `redis-cli ping`                           |
| **MinIO**           | 9000 | S3-compatible storage    | `curl http://localhost:9000`               |
| **MLflow**          | 5000 | Model tracking           | `http://localhost:5000`                    |
| **MLflow Postgres** | 5433 | MLflow backend DB        | `psql -p 5433 ...`                         |
| **InfluxDB**        | 8086 | Metrics                  | `curl http://localhost:8086/health`        |
| **FastAPI**         | 8000 | REST API (I2-T5)         | `curl http://localhost:8000/api/v1/health` |
| **Socket.IO**       | 4000 | Real-time Relay (I2-T6)  | `curl http://localhost:4000/health`        |

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

<<<<<<< HEAD

````javascript
const socket = io("http://localhost:4000/twin", {
  auth: {
    token: "eyJhbGc...", // JWT from FastAPI
  },
});

socket.emit("subscribe.room", { roomId: "room-101" });

socket.on("room.update", (roomState) => {
  console.log("Room updated:", roomState);
});

socket.on("alert.new", (alert) => {
  console.log("New alert:", alert);
});
=======
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
>>>>>>> main
````

## Troubleshooting

| Issue                   | Fix                                                              |
| ----------------------- | ---------------------------------------------------------------- |
| Containers not starting | `docker compose down -v && docker compose up -d`                 |
| Connection refused      | Check `docker compose ps`, verify port not in use                |
| JWT auth fails          | Verify `JWT_SECRET` in `.env` matches all services               |
| Kafka topics missing    | Wait 60s for auto-creation, or check `docker compose logs kafka` |

<<<<<<< HEAD
**Supported Event Types**:

- `holiday`: Campus holidays (low/no occupancy)
- `exam_period`: Exam periods (higher library occupancy)
- `reading_week`: Reading weeks (reduced teaching)
- `break`: Mid-semester breaks
- `special_event`: Custom campus events

**Occupancy Factors**:

- `1.0`: Normal operations
- `0.5`: 50% of normal occupancy
- `0.0`: Campus closed
- `1.2`: Elevated occupancy (e.g., exam period in libraries)

Query current academic context:

```sql
SELECT * FROM get_current_academic_term();
SELECT get_occupancy_factor_for_date('2025-12-25'::DATE);
```

## Verification Checkpoints

### I2-T2

- [ ] `docker compose up timescaledb -d` → healthy
- [ ] `psql ... -c "SELECT * FROM rooms;"` → 5 rows
- [ ] `psql ... -c "SELECT * FROM timescaledb_information.hypertables;"` → sensor_readings present
- [ ] Alembic: `alembic upgrade head` → success

### I2-T6

- [ ] `docker compose up realtime -d` → healthy
- [ ] `curl http://localhost:4000/health` → 200 OK
- [ ] Valid JWT client connects without error
- [ ] Invalid JWT → `connect_error("AUTH_FAILED")`
- [ ] Redis pub/sub events → Socket.IO emissions

## Next Steps

- **I2-T1**: Refine docker-compose with Kafka topic auto-creation and health checks
- **I2-T3**: Implement Spark Structured Streaming job (populates Redis & TimescaleDB)
- **I2-T5**: Build FastAPI REST API (uses TimescaleDB & Redis)
- # **I3**: Integrate Socket.IO client in Next.js frontend
  > > > > > > > main

---

**Last Updated**: May 5, 2026
