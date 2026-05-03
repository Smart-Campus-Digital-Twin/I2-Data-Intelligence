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
