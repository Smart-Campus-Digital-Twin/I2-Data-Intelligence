from datetime import datetime, timezone

from app.models import ForecastBroadcast, ForecastPoint, OccupancyBroadcast


def test_forecast_broadcast_schema() -> None:
    now = datetime.now(tz=timezone.utc)
    payload = ForecastBroadcast(
        building_id="B1",
        generated_at=now,
        model_version="v1",
        points=[ForecastPoint(timestamp=now, predicted_kw=12.5, lower_bound_kw=10.0, upper_bound_kw=15.0)],
        average_kw=12.5,
        peak_kw=12.5,
        peak_hour=9,
    )

    assert payload.points[0].predicted_kw == 12.5
    assert payload.peak_hour == 9


def test_occupancy_classification_schema() -> None:
    now = datetime.now(tz=timezone.utc)
    payload = OccupancyBroadcast(
        building_id="B1",
        room_id="R101",
        occupancy_count=15,
        capacity=30,
        classification="medium",
        confidence=50.0,
        timestamp=now,
    )

    assert payload.capacity == 30
    assert payload.confidence == 50.0
