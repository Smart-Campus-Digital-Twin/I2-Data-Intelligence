# I2-T5: FastAPI REST API
Smart Campus Digital Twin — Data & Intelligence Layer

## What this does
REST API that reads from TimescaleDB and serves data to the I3 frontend and Socket.IO relay (T6).

## Endpoints

| Method | URL | Auth | What it does |
|--------|-----|------|-------------|
| GET | `/health` | No | Check API is alive |
| POST | `/api/auth/token` | No | Login, get JWT token |
| GET | `/api/auth/me` | Yes | Who am I |
| GET | `/api/buildings/` | Yes | All buildings |
| GET | `/api/buildings/{id}` | Yes | One building |
| GET | `/api/buildings/{id}/rooms` | Yes | Rooms in building |
| GET | `/api/rooms/` | Yes | All rooms |
| GET | `/api/rooms/{id}/status` | Yes | Live sensor status |
| GET | `/api/rooms/{id}/history` | Yes | Sensor history |
| GET | `/api/sensors/latest` | Yes | Latest reading all rooms |
| GET | `/api/sensors/building/{id}` | Yes | Building sensor summary |
| GET | `/api/sensors/anomalies` | Yes | Recent anomalies |
| GET | `/api/alerts/` | Yes | Active alerts |
| GET | `/api/alerts/all` | Yes | All alerts |
| PATCH | `/api/alerts/{id}/resolve` | Admin | Resolve alert |
| GET | `/api/predictions/{room_id}` | Yes | ML predictions |
| GET | `/api/predictions/{room_id}/energy` | Yes | Energy prediction |
| GET | `/api/predictions/{room_id}/occupancy` | Yes | Occupancy prediction |

## How to run locally

```bash
# 1. Install packages
pip install -r requirements.txt

# 2. Start the API
python -m uvicorn app.main:app --reload

# 3. Open browser
# Go to http://127.0.0.1:8000/docs
```

## Database connection (matches T1 exactly)
- Host: localhost
- Port: 5432
- Database: campustwin
- Username: ctuser
- Password: ctpass

## JWT (matches T6 Socket.IO relay)
Same JWT_SECRET shared with T6 so tokens work across both services.

1️⃣ ## Running With Full Stack

This API requires T1's Docker stack to be running first.

2️⃣ **Start T1 infrastructure (from I2-Data-Intelligence folder):**
```bash
git checkout docker_compose
docker compose up -d
```

3️⃣ **Then start this API (from i2-t5-fastapi folder):**
```bash
python -m uvicorn app.main:app --reload
```

## Verified Working Endpoints (with database running)

| Endpoint | Result | Status |
|---|---|---|
| `GET /health` | `{"status": "ok", "database": "ok"}` | ✅ |
| `POST /api/auth/token` | Returns valid JWT token | ✅ |
| `GET /api/auth/me` | Returns logged in user info | ✅ |
| `GET /api/buildings/` | Returns 3 campus buildings | ✅ |
| `GET /api/buildings/{id}` | Returns one building | ✅ |
| `GET /api/buildings/{id}/rooms` | Returns rooms in building | ✅ |
| `GET /api/rooms/` | Returns 5 campus rooms | ✅ |
| `GET /api/rooms/{id}` | Returns one room | ✅ |
| `GET /api/rooms/{id}/status` | Returns live sensor data (energy, humidity, occupancy, temperature) | ✅ |
| `GET /api/rooms/{id}/history` | Returns sensor history by type and time range | ✅ |
| `GET /api/sensors/latest` | Returns latest reading for all rooms | ✅ |
| `GET /api/sensors/building/{id}` | Returns building sensor summary | ✅ |
| `GET /api/sensors/anomalies` | Returns recent anomalies | ✅ |
| `GET /api/alerts/` | Returns active alerts (empty until T3 generates data) | ✅ |
| `GET /api/alerts/all` | Returns all alerts | ✅ |
| `PATCH /api/alerts/{id}/resolve` | Admin only — resolves an alert | ✅ |
| `GET /api/predictions/` | Returns all predictions (empty until T4 runs ML model) | ✅ |
| `GET /api/predictions/{room_id}/energy` | Returns energy prediction for room | ⏳ |
| `GET /api/predictions/{room_id}/occupancy` | Returns occupancy prediction for room | ⏳ |

> ✅ = Fully working and tested  
> ⏳ = Endpoint ready and correct — returns 404 until T4 ML model generates prediction data

---

## Prerequisites

Requires T1's Docker stack to be running first.

Start from the `docker_compose` branch of I2-Data-Intelligence:

```bash
git checkout docker_compose
docker compose up -d
```

Then start this API:
```bash
python -m uvicorn app.main:app --reload
```

---

## Author
**Member 5 — I2-T5: FastAPI REST API**  
Smart Campus Digital Twin — Group I, Subgroup I2
