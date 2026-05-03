from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_db
from app.auth import require_auth, require_admin

router = APIRouter()


@router.get("/")
async def get_active_alerts(db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT alert_id, room_id, severity, anomaly_type, message, triggered_at, resolved FROM alerts WHERE resolved = FALSE ORDER BY triggered_at DESC")
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/all")
async def get_all_alerts(severity: str = Query(default=None), limit: int = Query(default=50, le=200), db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        if severity:
            await cur.execute("SELECT alert_id, room_id, severity, anomaly_type, message, triggered_at, resolved FROM alerts WHERE severity = %s ORDER BY triggered_at DESC LIMIT %s", (severity.upper(), limit))
        else:
            await cur.execute("SELECT alert_id, room_id, severity, anomaly_type, message, triggered_at, resolved FROM alerts ORDER BY triggered_at DESC LIMIT %s", (limit,))
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{alert_id}")
async def get_alert(alert_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT * FROM alerts WHERE alert_id = %s::uuid", (alert_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "data": row}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, note: str = Query(default=None), db=Depends(get_db), admin=Depends(require_admin)):
    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE alerts SET resolved = TRUE, resolved_at = NOW(), resolution_note = %s WHERE alert_id = %s::uuid AND resolved = FALSE",
            (note, alert_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
    await db.commit()
    return {"success": True, "message": "Alert resolved"}
