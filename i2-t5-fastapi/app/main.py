from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, auth, buildings, rooms, sensors, alerts, predictions

app = FastAPI(
    title="Smart Campus Digital Twin — I2-T5 REST API",
    description="REST API for the Smart Campus Digital Twin. Reads from TimescaleDB.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public — no login needed
app.include_router(health.router,                          tags=["Health"])
app.include_router(auth.router,    prefix="/api/auth",     tags=["Auth"])

# Protected — need JWT token
app.include_router(buildings.router,    prefix="/api/buildings",    tags=["Buildings"])
app.include_router(rooms.router,        prefix="/api/rooms",        tags=["Rooms"])
app.include_router(sensors.router,      prefix="/api/sensors",      tags=["Sensors"])
app.include_router(alerts.router,       prefix="/api/alerts",       tags=["Alerts"])
app.include_router(predictions.router,  prefix="/api/predictions",  tags=["Predictions"])
