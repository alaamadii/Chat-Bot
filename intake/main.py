import hashlib
import hmac
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from core.logging import configure_logging
from db.database import init_db
from intake.models import IncomingMessage, NormalizedMessage
from intake.session_manager import session_manager
from services.chat_service import chat_service

configure_logging()
logger = logging.getLogger(__name__)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action_taken: str
    delivery_success: bool
    conversation_status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="NextTech AI Support Bot", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled request error", extra={"request_id": request_id, "event": "request_failed"})
        raise
    response.headers["X-Request-ID"] = request_id
    return response


def _verify_meta_signature(raw_body: bytes, signature: Optional[str]) -> None:
    app_secret = os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret:
        return
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing WhatsApp signature")
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp signature")


def _extract_whatsapp_messages(payload: dict) -> list[IncomingMessage]:
    result: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from")
                text = message.get("text", {}).get("body", "")
                if sender and text:
                    result.append(
                        IncomingMessage(
                            channel="whatsapp",
                            user_id=sender,
                            text=text,
                            timestamp=message.get("timestamp"),
                            metadata={"message_id": message.get("id"), "raw": message},
                        )
                    )
    return result


@app.get("/webhook/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    mode: str = Query(alias="hub.mode"),
    verify_token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
):
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and expected_token and hmac.compare_digest(verify_token, expected_token):
        return challenge
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(default=None)):
    raw_body = await request.body()
    _verify_meta_signature(raw_body, x_hub_signature_256)
    payload = await request.json()
    incoming_messages = _extract_whatsapp_messages(payload)

    results = []
    for incoming in incoming_messages:
        result = chat_service.process(incoming, deliver=True)
        results.append(
            ChatResponse(
                session_id=result.message.session_id,
                reply=result.reply,
                action_taken=result.action_taken,
                delivery_success=result.delivery_success,
                conversation_status=result.conversation_status,
            )
        )
    return {"processed": len(results), "results": [item.model_dump() for item in results]}


@app.post("/webhook/web", response_model=ChatResponse)
async def web_webhook(msg: IncomingMessage):
    msg.channel = "web_chat"
    result = chat_service.process(msg, deliver=False)
    return ChatResponse(
        session_id=result.message.session_id,
        reply=result.reply,
        action_taken=result.action_taken,
        delivery_success=result.delivery_success,
        conversation_status=result.conversation_status,
    )


@app.get("/session/{session_id}/history", response_model=List[NormalizedMessage])
async def get_session_history(session_id: str):
    history = session_manager.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return history


@app.get("/health")
async def health_check():
    return {"status": "ok"}
