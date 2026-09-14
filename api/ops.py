import os

from fastapi import APIRouter, HTTPException
from redis import RedisError
from sqlalchemy import text

from core.rate_limit import redis_rate_limiter
from db.database import SessionLocal

router = APIRouter(tags=["operations"])


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


@router.get("/ready")
async def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    redis_url = os.getenv("REDIS_URL", "").strip()
    redis_state = "disabled"
    if redis_url:
        try:
            redis_state = "ok" if redis_rate_limiter.ping() else "unavailable"
        except RedisError as exc:
            if _truthy("REDIS_REQUIRED"):
                raise HTTPException(status_code=503, detail="Redis unavailable") from exc
            redis_state = "degraded"

    return {
        "status": "ready",
        "database": "ok",
        "redis": redis_state,
        "distributed_runtime_required": _truthy("REDIS_REQUIRED"),
    }
