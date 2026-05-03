from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_db
from app.auth import require_auth

router = APIRouter()


@router.get("/")
async def get_all_rooms(db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT room_id, name, building_id, floor, capacity, room_type FROM rooms ORDER BY building_id, floor, name")
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{room_id}")
async def get_room(room_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT room_id, name, building_id, floor, capacity, room_type FROM rooms WHERE room_id = %s", (room_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")
    return {"success": True, "data": row}


@router.get("/{room_id}/status")
async def get_room_status(room_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT room_id, name, building_id, capacity FROM rooms WHERE room_id = %s", (room_id,))
        room = await cur.fetchone()
    if not room:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    async with db.cursor() as cur:
        await cur.execute("""
            SELECT DISTINCT ON (sensor_type)
                sensor_type, avg_value, min_value, max_value, ts, anomaly_flag, anomaly_type
            FROM sensor_readings
            WHERE room_id = %s
            ORDER BY sensor_type, ts DESC
        """, (room_id,))
        rows = await cur.fetchall()

    readings = {}
    anomaly = False
    anomaly_type = None
    last_ts = None

    for r in rows:
        readings[r["sensor_type"]] = {
            "value": r["avg_value"],
            "min":   r["min_value"],
            "max":   r["max_value"],
            "ts":    str(r["ts"]),
        }
        if r["anomaly_flag"]:
            anomaly = True
            anomaly_type = r["anomaly_type"]
        if last_ts is None or r["ts"] > last_ts:
            last_ts = r["ts"]

    return {
        "success": True,
        "data": {
            "room_id":      room_id,
            "room_name":    room["name"],
            "building_id":  room["building_id"],
            "capacity":     room["capacity"],
            "sensors":      readings,
            "anomaly_flag": anomaly,
            "anomaly_type": anomaly_type,
            "last_updated": str(last_ts),
            "status":       "CRITICAL" if anomaly else "OK",
        },
    }


@router.get("/{room_id}/history")
async def get_room_history(
    room_id: str,
    sensor_type: str = Query(default="occupancy"),
    hours: int = Query(default=24),
    db=Depends(get_db),
    user=Depends(require_auth),
):
    async with db.cursor() as cur:
        await cur.execute("""
            SELECT ts, sensor_type, avg_value, min_value, max_value, anomaly_flag
            FROM sensor_readings
            WHERE room_id = %s AND sensor_type = %s
              AND ts >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY ts ASC
        """, (room_id, sensor_type, hours))
        rows = await cur.fetchall()
    return {"success": True, "room_id": room_id, "sensor_type": sensor_type, "hours": hours, "count": len(rows), "data": rows}
