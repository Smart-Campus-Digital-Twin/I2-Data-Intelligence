from fastapi import APIRouter, Depends
from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db=Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "ok",
        "database": db_status,
        "service": "I2-T5 FastAPI",
        "version": "1.0.0",
    }
