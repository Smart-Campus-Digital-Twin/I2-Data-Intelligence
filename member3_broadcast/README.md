# Member 3 - Real-Time WebSocket & Data Broadcast Service

This project implements the Member 3 deliverable for the I2 Data Intelligence group.
It provides a FastAPI-based async broadcast server with Socket.IO namespaces for:

- `/forecast` for energy forecast updates
- `/occupancy` for live occupancy updates
- `/anomalies` for alert broadcasts

## What is included

- Async FastAPI application with Socket.IO integration
- JWT-based connection validation from query parameters
- Pydantic models for forecast, occupancy, anomaly, and audit payloads
- Health endpoint for service checks
- Service layer that can be wired to Kafka, Redis, PostgreSQL, and upstream APIs
- Test skeleton for core utility behavior

## Run locally

```bash
python -m uvicorn app.main:asgi_app --reload --port 8000
```

## Environment variables

- `JWT_SECRET`: secret used to validate socket connections
- `JWT_ALGORITHM`: signing algorithm, default `HS256`
- `FORECAST_UPSTREAM_URL`: optional Member 1 upstream API
- `REDIS_URL`: optional Redis connection string
- `KAFKA_BOOTSTRAP_SERVERS`: optional Kafka bootstrap servers

## Suggested next integration steps

1. Connect the forecast broadcaster to Member 1's REST API.
2. Wire occupancy and anomaly consumers to Kafka topics from Member 2.
3. Persist broadcast audit logs into PostgreSQL.
4. Add Redis replay buffers for reconnecting clients.
5. Add Docker Compose or Kubernetes manifests when the full group repo is ready.

## Viva summary: what your part is

If you are presenting Member 3, your part is the real-time broadcast layer. In viva, describe it like this:

- I built the WebSocket/Socket.IO service that pushes live campus events to the frontend.
- I separated traffic into three namespaces: forecasts, occupancy, and anomalies.
- I added JWT-based connection validation so only authenticated clients can subscribe.
- I added a health endpoint plus metrics/audit summaries for observability.
- I added replay-style message buffering so disconnected clients can recover recent events.

### What to emphasize in the viva

1. Problem solved: the frontend needs live updates without polling.
2. Architecture: upstream services send data to this broadcast layer, and clients subscribe by namespace.
3. Reliability: the hub keeps recent messages and audit data in memory so reconnects and debugging are possible.
4. Security: tokens are checked before a client is accepted.
5. Scalability: the service is async and ready to be wired to Redis, Kafka, and PostgreSQL.

### What to show if asked for a demo

- Run the service with `python -m uvicorn app.main:asgi_app --reload --port 8000`.
- Open `GET /health` to show service status.
- Open `GET /metrics` to show broadcast statistics.
- Call `POST /demo/seed` to generate sample forecast, occupancy, and anomaly payloads.
- Call `GET /demo/replay/forecast` to show cached recent forecast messages.

### Short viva script

"My module is Member 3, the real-time broadcast service. It sits between Members 1 and 2 and the frontend. It authenticates clients with JWT, exposes separate Socket.IO namespaces for forecast, occupancy, and anomalies, keeps recent messages for replay, and records broadcast metrics for observability. The goal is low-latency delivery of live campus data without polling."
