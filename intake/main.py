import hashlib
import hmac
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from api.admin import router as admin_router
from api.ops import router as ops_router
from api.quality import router as quality_router
from auth.security import authenticate, create_access_token, require_roles
from core.logging import configure_logging
from db.database import init_db
from db.models import ConversationStatus
from db.repository import conversation_repository, knowledge_repository
from delivery.engine import engine as delivery_engine
from delivery.models import FormattedMessage
from intake.models import IncomingMessage, NormalizedMessage
from intake.session_manager import session_manager
from services.audit import record_audit
from services.chat_service import chat_service
from services.idempotency import webhook_idempotency

configure_logging()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action_taken: str
    delivery_success: bool
    conversation_status: str


class LoginRequest(BaseModel):
    username: str
    password: str


class StatusRequest(BaseModel):
    status: ConversationStatus


class AssignmentRequest(BaseModel):
    agent_username: Optional[str] = None


class AgentReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class KnowledgeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=20000)
    category: str = Field(default="general", max_length=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="NextTech AI Support Bot", version="6.0.0", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(ops_router)
app.include_router(quality_router)


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
                    result.append(IncomingMessage(
                        channel="whatsapp",
                        user_id=sender,
                        text=text,
                        timestamp=message.get("timestamp"),
                        metadata={"message_id": message.get("id"), "raw": message},
                    ))
    return result


@app.get("/", include_in_schema=False)
async def web_chat_page():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse(ROOT / "dashboard" / "index.html")


@app.post("/auth/login")
async def login(payload: LoginRequest):
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token(user), "token_type": "bearer", "role": user["role"], "username": user["username"]}


@app.get("/agent/conversations")
async def agent_conversations(user: dict = Depends(require_roles("agent", "admin"))):
    return conversation_repository.list_conversations()


@app.get("/agent/conversations/{conversation_id}/messages")
async def agent_messages(conversation_id: str, user: dict = Depends(require_roles("agent", "admin"))):
    if not conversation_repository.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_repository.list_messages(conversation_id)


@app.post("/agent/conversations/{conversation_id}/assign")
async def assign_conversation(conversation_id: str, payload: AssignmentRequest, user: dict = Depends(require_roles("agent", "admin"))):
    target = payload.agent_username or user["username"]
    if user["role"] != "admin" and target != user["username"]:
        raise HTTPException(status_code=403, detail="Agents may only claim conversations for themselves")
    try:
        if user["role"] == "admin" and payload.agent_username and conversation_repository.get_assignment(conversation_id):
            assignment = conversation_repository.transfer_agent(conversation_id, target)
            action = "conversation.transferred"
        else:
            assignment = conversation_repository.claim_agent(conversation_id, target)
            action = "conversation.claimed"
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "already assigned" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail) from exc
    record_audit(user["username"], action, "conversation", conversation_id, {"agent": target})
    return assignment


@app.delete("/agent/conversations/{conversation_id}/assignment")
async def unassign_conversation(conversation_id: str, user: dict = Depends(require_roles("agent", "admin"))):
    assigned_agent = conversation_repository.get_assignment(conversation_id)
    if assigned_agent and assigned_agent != user["username"] and user["role"] != "admin":
        raise HTTPException(status_code=409, detail=f"Conversation is assigned to {assigned_agent}")
    try:
        result = conversation_repository.unassign_agent(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(user["username"], "conversation.unassigned", "conversation", conversation_id)
    return result


@app.post("/agent/conversations/{conversation_id}/reply")
async def agent_reply(conversation_id: str, payload: AgentReplyRequest, user: dict = Depends(require_roles("agent", "admin"))):
    conversation = conversation_repository.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    assigned_agent = conversation_repository.get_assignment(conversation_id)
    if assigned_agent and assigned_agent != user["username"] and user["role"] != "admin":
        raise HTTPException(status_code=409, detail=f"Conversation is assigned to {assigned_agent}")
    if not assigned_agent:
        try:
            conversation_repository.claim_agent(conversation_id, user["username"])
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    message_id = conversation_repository.add_text_message(
        conversation_id=conversation_id,
        role="agent",
        user_id=user["username"],
        channel=conversation.channel,
        text=payload.text,
        metadata={"agent_username": user["username"], "delivery_status": "pending"},
    )

    delivery = delivery_engine.send(
        FormattedMessage(text=payload.text),
        conversation.channel,
        conversation.user_id,
        send_network=conversation.channel == "whatsapp",
    )
    if not delivery.success:
        conversation_repository.update_message_metadata(message_id, {
            "delivery_status": "failed",
            "delivery_error": delivery.error_details or "Delivery failed",
        })
        raise HTTPException(status_code=502, detail=delivery.error_details or "Delivery failed")

    conversation_repository.update_message_metadata(message_id, {"delivery_status": "sent"})
    conversation_repository.set_status(conversation_id, ConversationStatus.HUMAN_ACTIVE)
    record_audit(user["username"], "conversation.replied", "conversation", conversation_id, {"channel": conversation.channel, "message_id": message_id})
    return {"conversation_id": conversation_id, "message_id": message_id, "delivered": True, "channel": conversation.channel, "status": ConversationStatus.HUMAN_ACTIVE.value}


@app.patch("/agent/conversations/{conversation_id}/status")
async def update_conversation_status(conversation_id: str, payload: StatusRequest, user: dict = Depends(require_roles("agent", "admin"))):
    if not conversation_repository.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    assigned_agent = conversation_repository.get_assignment(conversation_id)
    if assigned_agent and assigned_agent != user["username"] and user["role"] != "admin":
        raise HTTPException(status_code=409, detail=f"Conversation is assigned to {assigned_agent}")
    conversation_repository.set_status(conversation_id, payload.status)
    record_audit(user["username"], "conversation.status_changed", "conversation", conversation_id, {"status": payload.status.value})
    return {"id": conversation_id, "status": payload.status.value}


@app.get("/agent/analytics")
async def agent_analytics(user: dict = Depends(require_roles("agent", "admin"))):
    return conversation_repository.analytics_summary()


@app.get("/knowledge")
async def list_knowledge(user: dict = Depends(require_roles("agent", "admin"))):
    return knowledge_repository.list_entries()


@app.post("/knowledge", status_code=201)
async def create_knowledge(payload: KnowledgeRequest, user: dict = Depends(require_roles("admin"))):
    created = knowledge_repository.create_entry(title=payload.title, content=payload.content, category=payload.category, created_by=user["username"])
    record_audit(user["username"], "knowledge.created", "knowledge", created["id"], {"title": payload.title})
    return created


@app.delete("/knowledge/{entry_id}", status_code=204)
async def delete_knowledge(entry_id: str, user: dict = Depends(require_roles("admin"))):
    if not knowledge_repository.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    record_audit(user["username"], "knowledge.deleted", "knowledge", entry_id)
    return None


@app.get("/web/conversations/{conversation_id}/messages")
async def web_conversation_messages(conversation_id: str, user_id: str = Query(min_length=1)):
    conversation = conversation_repository.get_conversation(conversation_id)
    if not conversation or conversation.channel != "web_chat" or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_repository.list_messages(conversation_id)


@app.get("/webhook/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(mode: str = Query(alias="hub.mode"), verify_token: str = Query(alias="hub.verify_token"), challenge: str = Query(alias="hub.challenge")):
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and expected_token and hmac.compare_digest(verify_token, expected_token):
        return challenge
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(default=None)):
    raw_body = await request.body()
    _verify_meta_signature(raw_body, x_hub_signature_256)
    payload = await request.json()
    results = []
    duplicates = 0
    for incoming in _extract_whatsapp_messages(payload):
        event_id = str(incoming.metadata.get("message_id") or "")
        if event_id and not webhook_idempotency.begin("whatsapp", event_id):
            duplicates += 1
            continue
        try:
            result = chat_service.process(incoming, deliver=True)
            if event_id:
                webhook_idempotency.complete("whatsapp", event_id)
        except Exception:
            if event_id:
                webhook_idempotency.fail("whatsapp", event_id)
            raise
        results.append(ChatResponse(
            session_id=result.message.session_id,
            reply=result.reply,
            action_taken=result.action_taken,
            delivery_success=result.delivery_success,
            conversation_status=result.conversation_status,
        ))
    return {"processed": len(results), "duplicates": duplicates, "results": [item.model_dump() for item in results]}


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
async def get_session_history(session_id: str, user: dict = Depends(require_roles("agent", "admin"))):
    history = session_manager.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return history


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "6.0.0"}
