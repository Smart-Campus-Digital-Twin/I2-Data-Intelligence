from __future__ import annotations

from datetime import datetime, timedelta, timezone

import socketio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import get_settings
from .models import AnomalyBroadcast, ForecastBroadcast, ForecastPoint, OccupancyBroadcast
from .security import TokenError, validate_socket_token
from .services import BroadcastHub

settings = get_settings()
app = FastAPI(title=settings.app_name)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
hub = BroadcastHub()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": settings.app_name,
            "namespaces": ["/forecast", "/occupancy", "/anomalies"],
            "connected_clients": hub.client_count(),
        }
    )


@app.exception_handler(TokenError)
async def token_error_handler(_: Request, exc: TokenError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def _authenticate(environ: dict[str, object]) -> dict[str, object]:
    query_string = environ.get("QUERY_STRING", "")
    token_value = ""
    if isinstance(query_string, str):
        for item in query_string.split("&"):
            if item.startswith("token="):
                token_value = item.split("=", 1)[1]
                break
    return validate_socket_token(token_value, settings.jwt_secret, settings.jwt_algorithm)


@sio.event(namespace="/forecast")
async def connect_forecast(sid: str, environ: dict[str, object]) -> bool:
    claims = await _authenticate(environ)
    hub.register_client("/forecast", sid, claims)
    return True


@sio.event(namespace="/forecast")
async def disconnect_forecast(sid: str) -> None:
    hub.unregister_client("/forecast", sid)


@sio.event(namespace="/occupancy")
async def connect_occupancy(sid: str, environ: dict[str, object]) -> bool:
    claims = await _authenticate(environ)
    hub.register_client("/occupancy", sid, claims)
    return True


@sio.event(namespace="/occupancy")
async def disconnect_occupancy(sid: str) -> None:
    hub.unregister_client("/occupancy", sid)


@sio.event(namespace="/anomalies")
async def connect_anomalies(sid: str, environ: dict[str, object]) -> bool:
    claims = await _authenticate(environ)
    hub.register_client("/anomalies", sid, claims)
    return True


@sio.event(namespace="/anomalies")
async def disconnect_anomalies(sid: str) -> None:
    hub.unregister_client("/anomalies", sid)


@app.get("/metrics")
async def metrics() -> dict[str, object]:
    return hub.build_snapshot()


@app.get("/demo/replay/{namespace}")
async def demo_replay(namespace: str) -> dict[str, object]:
    namespaced = f"/{namespace.lstrip('/')}"
    if namespaced not in {"/forecast", "/occupancy", "/anomalies"}:
        raise HTTPException(status_code=404, detail="Unknown namespace")
    return {"namespace": namespaced, "messages": hub.replay_messages(namespaced)}


@app.post("/demo/seed")
async def demo_seed() -> dict[str, object]:
    now = datetime.now(tz=timezone.utc)
    forecast = ForecastBroadcast(
        building_id="B1",
        generated_at=now,
        model_version="v1",
        points=[
            ForecastPoint(timestamp=now + timedelta(hours=offset), predicted_kw=25.0 + offset, lower_bound_kw=20.0 + offset, upper_bound_kw=30.0 + offset)
            for offset in range(24)
        ],
        average_kw=36.5,
        peak_kw=48.0,
        peak_hour=18,
    )
    occupancy = OccupancyBroadcast(
        building_id="B1",
        room_id="R101",
        occupancy_count=32,
        capacity=50,
        classification="medium",
        confidence=64.0,
        timestamp=now,
    )
    anomaly = AnomalyBroadcast(
        anomaly_id="A-1001",
        building_id="B1",
        room_id="R101",
        severity="medium",
        anomaly_type="proxy_attendance",
        expected_count=30,
        actual_count=18,
        divergence=12,
        divergence_ratio=40.0,
        confidence=72.0,
        message="Occupancy deviates from expected range.",
        timestamp=now,
    )

    return {
        "forecast": await hub.broadcast_forecast(forecast),
        "occupancy": await hub.broadcast_occupancy(occupancy),
        "anomaly": await hub.broadcast_anomaly(anomaly),
    }


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
