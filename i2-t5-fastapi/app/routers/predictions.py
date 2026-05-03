from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_db
from app.auth import require_auth

router = APIRouter()


@router.get("/")
async def get_all_predictions(prediction_type: str = Query(default=None), limit: int = Query(default=50, le=200), db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        if prediction_type:
            await cur.execute("SELECT prediction_id, ts, room_id, prediction_type, predicted_value, confidence, model_version, valid_until FROM ml_predictions WHERE valid_until >= NOW() AND prediction_type = %s ORDER BY ts DESC LIMIT %s", (prediction_type, limit))
        else:
            await cur.execute("SELECT prediction_id, ts, room_id, prediction_type, predicted_value, confidence, model_version, valid_until FROM ml_predictions WHERE valid_until >= NOW() ORDER BY ts DESC LIMIT %s", (limit,))
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{room_id}/energy")
async def get_energy_prediction(room_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT * FROM ml_predictions WHERE room_id = %s AND prediction_type = 'energy' AND valid_until >= NOW() ORDER BY ts DESC LIMIT 1", (room_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"No energy prediction for room '{room_id}'")
    return {"success": True, "data": row}


@router.get("/{room_id}/occupancy")
async def get_occupancy_prediction(room_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT * FROM ml_predictions WHERE room_id = %s AND prediction_type = 'occupancy' AND valid_until >= NOW() ORDER BY ts DESC LIMIT 1", (room_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"No occupancy prediction for room '{room_id}'")
    return {"success": True, "data": row}


@router.get("/{room_id}")
async def get_room_predictions(room_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT prediction_id, ts, room_id, prediction_type, predicted_value, confidence, model_version, valid_until FROM ml_predictions WHERE room_id = %s AND valid_until >= NOW() ORDER BY ts DESC", (room_id,))
        rows = await cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No predictions for room '{room_id}'")
    return {"success": True, "room_id": room_id, "count": len(rows), "data": rows}
