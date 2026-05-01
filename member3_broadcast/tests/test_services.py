from datetime import datetime, timezone

import pytest

from app.models import ForecastBroadcast, ForecastPoint
from app.services import BroadcastHub


@pytest.mark.asyncio
async def test_broadcast_hub_tracks_metrics_and_replay() -> None:
    hub = BroadcastHub()
    now = datetime.now(tz=timezone.utc)
    payload = ForecastBroadcast(
        building_id="B1",
        generated_at=now,
        model_version="v1",
        points=[ForecastPoint(timestamp=now, predicted_kw=10.0, lower_bound_kw=8.0, upper_bound_kw=12.0)],
        average_kw=10.0,
        peak_kw=10.0,
        peak_hour=12,
    )

    event = await hub.broadcast_forecast(payload)

    assert event["building_id"] == "B1"
    assert hub.client_count("/forecast") == 0
    assert hub.audit_summary()["events"] == 1
    assert hub.replay_messages("/forecast")[0]["payload"]["building_id"] == "B1"


def test_build_snapshot_reports_recent_messages() -> None:
    hub = BroadcastHub()
    snapshot = hub.build_snapshot()

    assert snapshot["connected_clients"] == 0
    assert snapshot["audit"]["events"] == 0
