from fastapi import APIRouter, Depends, Query
from app.database import get_db
from app.auth import require_auth

router = APIRouter()


@router.get("/latest")
async def get_latest_all_rooms(sensor_type: str = Query(default="occupancy"), db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("""
            SELECT DISTINCT ON (room_id)
                room_id, building_id, sensor_type, avg_value, ts, anomaly_flag, anomaly_type
            FROM sensor_readings WHERE sensor_type = %s
            ORDER BY room_id, ts DESC
        """, (sensor_type,))
        rows = await cur.fetchall()
    return {"success": True, "sensor_type": sensor_type, "count": len(rows), "data": rows}


@router.get("/building/{building_id}")
async def get_building_sensors(building_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("""
            SELECT sr.room_id, sr.sensor_type,
                   AVG(sr.avg_value) AS avg_value, MAX(sr.avg_value) AS max_value,
                   MIN(sr.avg_value) AS min_value, MAX(sr.ts) AS last_updated,
                   BOOL_OR(sr.anomaly_flag) AS has_anomaly
            FROM sensor_readings sr
            JOIN rooms r ON sr.room_id = r.room_id
            WHERE r.building_id = %s AND sr.ts >= NOW() - INTERVAL '1 hour'
            GROUP BY sr.room_id, sr.sensor_type ORDER BY sr.room_id, sr.sensor_type
        """, (building_id,))
        rows = await cur.fetchall()
    return {"success": True, "building_id": building_id, "count": len(rows), "data": rows}


@router.get("/anomalies")
async def get_anomalies(hours: int = Query(default=1), db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("""
            SELECT ts, room_id, building_id, sensor_type, avg_value, anomaly_type
            FROM sensor_readings
            WHERE anomaly_flag = TRUE AND ts >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY ts DESC
        """, (hours,))
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}
