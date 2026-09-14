import asyncio
import json
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from redis import RedisError
from sqlalchemy import text

from auth.web_session import verify_web_session
from core.rate_limit import redis_rate_limiter
from db.database import SessionLocal
from db.repository import conversation_repository
from services.realtime import subscribe

router = APIRouter(tags=["operations"])
WEB_SESSION_COOKIE = "web_session"


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _web_session_required() -> bool:
    return _truthy("WEB_SESSION_REQUIRED") or os.getenv("ENVIRONMENT", "development").lower() == "production"


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


def _authorize_web_conversation(request: Request, conversation_id: str, user_id: str) -> None:
    token = request.cookies.get(WEB_SESSION_COOKIE)
    if token:
        verify_web_session(token, user_id=user_id, conversation_id=conversation_id)
    elif _web_session_required():
        raise HTTPException(status_code=401, detail="Signed web session required")

    conversation = conversation_repository.get_conversation(conversation_id)
    if not conversation or conversation.channel != "web_chat" or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")


def _event_payload(message: dict) -> str:
    return f"event: message\ndata: {json.dumps(message)}\n\n"


@router.get("/web/conversations/{conversation_id}/events", include_in_schema=False)
async def distributed_web_conversation_events(
    request: Request,
    conversation_id: str,
    user_id: str = Query(min_length=1),
):
    """SSE backed by Redis pub/sub with database reconciliation/fallback."""
    _authorize_web_conversation(request, conversation_id, user_id)

    async def stream():
        seen: set[str] = set()

        def unseen_messages() -> list[dict]:
            rows = conversation_repository.list_messages(conversation_id)
            fresh = [message for message in rows if message["id"] not in seen]
            for message in fresh:
                seen.add(message["id"])
            return fresh

        for message in unseen_messages():
            yield _event_payload(message)

        redis_url = os.getenv("REDIS_URL", "").strip()
        if redis_url:
            try:
                async for message in subscribe(conversation_id):
                    if await request.is_disconnected():
                        return
                    if message is None:
                        for recovered in unseen_messages():
                            yield _event_payload(recovered)
                        yield ": keepalive\n\n"
                        continue
                    message_id = str(message.get("id") or "")
                    if message_id and message_id in seen:
                        continue
                    if message_id:
                        seen.add(message_id)
                    yield _event_payload(message)
            except RedisError:
                if _truthy("REDIS_REQUIRED"):
                    yield "event: error\ndata: {\"detail\":\"realtime backend unavailable\"}\n\n"
                    return

        # Safe fallback for local/single-replica deployments or a non-required Redis outage.
        for _ in range(55):
            if await request.is_disconnected():
                return
            for message in unseen_messages():
                yield _event_payload(message)
            yield ": keepalive\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
