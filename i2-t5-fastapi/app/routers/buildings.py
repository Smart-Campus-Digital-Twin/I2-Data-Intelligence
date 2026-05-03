from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import require_auth

router = APIRouter()


@router.get("/")
async def get_all_buildings(db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT building_id, name, floors, address FROM buildings ORDER BY name")
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{building_id}")
async def get_building(building_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute("SELECT building_id, name, floors, address FROM buildings WHERE building_id = %s", (building_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Building '{building_id}' not found")
    return {"success": True, "data": row}


@router.get("/{building_id}/rooms")
async def get_rooms_in_building(building_id: str, db=Depends(get_db), user=Depends(require_auth)):
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT room_id, name, building_id, floor, capacity, room_type FROM rooms WHERE building_id = %s ORDER BY floor, name",
            (building_id,)
        )
        rows = await cur.fetchall()
    return {"success": True, "count": len(rows), "data": rows}
