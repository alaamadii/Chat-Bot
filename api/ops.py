from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from db.database import SessionLocal

router = APIRouter(tags=["operations"])


@router.get("/ready")
async def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
