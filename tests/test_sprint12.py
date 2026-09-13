import os
import uuid
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("WEB_SESSION_SECRET", "test-web-session-secret")

from db.database import SessionLocal, init_db
from db.models import ConversationStatus
from db.reliability_models import WebhookEvent
from db.repository import conversation_repository
from delivery.models import DeliveryStatus
from services.idempotency import webhook_idempotency
from services.outbox import outbox


def test_stale_processing_webhook_can_be_reclaimed(monkeypatch):
    init_db()
    monkeypatch.setenv("WEBHOOK_PROCESSING_LEASE_SECONDS", "30")
    event_id = "evt-" + str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(WebhookEvent(
            provider="whatsapp",
            external_event_id=event_id,
            status="processing",
            received_at=datetime.utcnow() - timedelta(minutes=5),
        ))
        db.commit()

    assert webhook_idempotency.begin("whatsapp", event_id) is True
    assert webhook_idempotency.begin("whatsapp", event_id) is False


def test_outbox_persists_failure_then_retries(monkeypatch):
    init_db()
    monkeypatch.setenv("OUTBOX_RETRY_BASE_SECONDS", "0")
    calls = {"count": 0}

    def fake_send(msg, channel, recipient, send_network=True):
        calls["count"] += 1
        if calls["count"] == 1:
            return DeliveryStatus(success=False, channel=channel, timestamp=datetime.utcnow().isoformat(), error_details="temporary")
        return DeliveryStatus(success=True, channel=channel, timestamp=datetime.utcnow().isoformat())

    monkeypatch.setattr("services.outbox.engine.send", fake_send)
    item = outbox.enqueue(channel="whatsapp", recipient="15550001111", text="hello", max_attempts=3)
    first = outbox.deliver_now(item.id)
    assert first.success is False
    state = outbox.get(item.id)
    assert state["status"] == "pending"
    assert state["attempt_count"] == 1

    second = outbox.deliver_now(item.id)
    assert second.success is True
    state = outbox.get(item.id)
    assert state["status"] == "sent"
    assert state["attempt_count"] == 2


def test_resolve_clears_assignment():
    init_db()
    user = "user-" + str(uuid.uuid4())
    conversation = conversation_repository.get_or_create_conversation(user, "web_chat")

    # Seed an active agent already created by the test environment.
    conversation_repository.claim_agent(conversation.id, "agent")
    assert conversation_repository.get_assignment(conversation.id) == "agent"

    conversation_repository.set_status(conversation.id, ConversationStatus.RESOLVED)
    assert conversation_repository.get_assignment(conversation.id) is None
    assert conversation_repository.get_conversation(conversation.id).status == ConversationStatus.RESOLVED
