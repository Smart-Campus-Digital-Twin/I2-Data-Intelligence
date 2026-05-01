from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_kw: float = Field(ge=0)
    lower_bound_kw: float = Field(ge=0)
    upper_bound_kw: float = Field(ge=0)


class ForecastBroadcast(BaseModel):
    building_id: str
    generated_at: datetime
    model_version: str
    points: list[ForecastPoint]
    average_kw: float = Field(ge=0)
    peak_kw: float = Field(ge=0)
    peak_hour: int = Field(ge=0, le=23)


class OccupancyBroadcast(BaseModel):
    building_id: str
    room_id: str
    occupancy_count: int = Field(ge=0)
    capacity: int = Field(gt=0)
    classification: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=100)
    timestamp: datetime


class AnomalyBroadcast(BaseModel):
    anomaly_id: str
    building_id: str
    room_id: str | None = None
    severity: Literal["low", "medium", "high"]
    anomaly_type: str
    expected_count: int = Field(ge=0)
    actual_count: int = Field(ge=0)
    divergence: int = Field(ge=0)
    divergence_ratio: float = Field(ge=0)
    confidence: float = Field(ge=0, le=100)
    message: str
    timestamp: datetime


class AuditLogRecord(BaseModel):
    event_type: str
    namespace: str
    client_count: int = Field(ge=0)
    data_size: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    timestamp: datetime
