from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from .models import AnomalyBroadcast, AuditLogRecord, ForecastBroadcast, OccupancyBroadcast


class BroadcastHub:
    def __init__(self) -> None:
        self.connected_clients: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
        self.recent_messages: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=1000))
        self.audit_log: list[AuditLogRecord] = []

    def register_client(self, namespace: str, sid: str, claims: dict[str, object]) -> None:
        self.connected_clients[namespace][sid] = claims

    def unregister_client(self, namespace: str, sid: str) -> None:
        self.connected_clients[namespace].pop(sid, None)

    def client_count(self, namespace: str | None = None) -> int:
        if namespace is None:
            return sum(len(clients) for clients in self.connected_clients.values())
        return len(self.connected_clients[namespace])

    def record_audit(self, event_type: str, namespace: str, payload_size: int, latency_ms: float) -> AuditLogRecord:
        record = AuditLogRecord(
            event_type=event_type,
            namespace=namespace,
            client_count=self.client_count(namespace),
            data_size=payload_size,
            latency_ms=latency_ms,
            timestamp=datetime.now(tz=timezone.utc),
        )
        self.audit_log.append(record)
        return record

    def cache_message(self, namespace: str, payload: dict[str, Any]) -> None:
        self.recent_messages[namespace].append({"id": str(uuid4()), "payload": payload, "timestamp": datetime.now(tz=timezone.utc).isoformat()})

    def replay_messages(self, namespace: str) -> list[dict[str, Any]]:
        return list(self.recent_messages[namespace])

    def audit_summary(self) -> dict[str, Any]:
        if not self.audit_log:
            return {"events": 0, "average_latency_ms": 0.0, "max_latency_ms": 0.0}

        latencies = [record.latency_ms for record in self.audit_log]
        return {
            "events": len(self.audit_log),
            "average_latency_ms": sum(latencies) / len(latencies),
            "max_latency_ms": max(latencies),
        }

    async def broadcast_forecast(self, payload: ForecastBroadcast) -> dict[str, Any]:
        started = perf_counter()
        event = payload.model_dump(mode="json")
        self.cache_message("/forecast", event)
        latency_ms = (perf_counter() - started) * 1000
        self.record_audit("forecast.broadcast", "/forecast", len(str(event).encode("utf-8")), latency_ms)
        return event

    async def broadcast_occupancy(self, payload: OccupancyBroadcast) -> dict[str, Any]:
        started = perf_counter()
        event = payload.model_dump(mode="json")
        self.cache_message("/occupancy", event)
        latency_ms = (perf_counter() - started) * 1000
        self.record_audit("occupancy.broadcast", "/occupancy", len(str(event).encode("utf-8")), latency_ms)
        return event

    async def broadcast_anomaly(self, payload: AnomalyBroadcast) -> dict[str, Any]:
        started = perf_counter()
        event = payload.model_dump(mode="json")
        self.cache_message("/anomalies", event)
        latency_ms = (perf_counter() - started) * 1000
        self.record_audit("anomaly.broadcast", "/anomalies", len(str(event).encode("utf-8")), latency_ms)
        return event

    def build_snapshot(self) -> dict[str, Any]:
        return {
            "connected_clients": self.client_count(),
            "audit": self.audit_summary(),
            "recent_messages": {namespace: len(messages) for namespace, messages in self.recent_messages.items()},
        }
