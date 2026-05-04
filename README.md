# I2-Data-Intelligence: Smart Campus Analytics Layer

Data & intelligence layer for the Smart Campus Digital Twin system. Provides real-time data analytics, ML model serving, and live event streaming.

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

## Quick Start

### 1. Setup Environment

```bash
cd I2-Data-Intelligence
cp .env.example .env
# Edit .env with your secrets (JWT_SECRET, passwords, etc.)
```

### 2. Start All Services

```bash
docker compose up -d
```

> The `spark-processor` service is now included as part of the I2 T3 analytics pipeline.

### 3. Verify Services

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
curl http://localhost:4000/health
curl http://localhost:4000/metrics | grep socket_io
```

**MLflow**:
Open http://localhost:5000 in browser

## Completed Tasks

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
  - Graceful shutdown with signal handlers

## Services

### TimescaleDB (I2-T2)

- **Port**: 5432
- **Database**: `campustwin`
- **Tables**: sensor_readings, academic_terms, calendar_events, alerts, rooms, buildings
- **Compression**: 7 days
- **Retention**: 90 days

### Redis

- **Port**: 6379
- **Features**: Keyspace notifications enabled, Pub/Sub channels for real-time events

### Socket.IO Real-Time Relay (I2-T6)

- **Port**: 4000
- **Namespaces**: `/twin` (auth), `/admin` (admin)
- **Events**: room.update, alert.new, node.offline
- **Metrics**: Prometheus-compatible endpoint

### Other Services

- **Kafka**: Port 9092 (KRaft mode)
- **Schema Registry**: Port 8081
- **MQTT**: Port 1883
- **MLflow**: Port 5000
- **InfluxDB**: Port 8086

## File Structure

```
I2-Data-Intelligence/
├── schema/
│   └── schema.sql                    # Full TimescaleDB schema with academic calendar
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py    # Versioned migration
├── db/
│   └── migrations.py                 # Programmatic migration runner
├── realtime/
│   ├── src/
│   │   ├── index.js                  # Socket.IO main server
│   │   └── services/
│   │       ├── jwt.js                # JWT validation
│   │       └── redis.js              # Redis Pub/Sub
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── infra/
│   └── mosquitto/
│       └── mosquitto.conf
├── docker-compose.yml                # Full I2 stack
├── .env.example                      # Environment template
└── README.md                         # This file
```

## Socket.IO Client Example

```javascript
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
```

## Academic Calendar Features

The schema supports flexible academic calendar management:

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
- **I3**: Integrate Socket.IO client in Next.js frontend

---

**Team**: I2 — Data & Intelligence  
**Status**: ✅ I2-T2 & I2-T6 Complete  
**Last Updated**: May 2, 2026
