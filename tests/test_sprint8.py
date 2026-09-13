import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("AGENT_USERNAME", "agent")
os.environ.setdefault("AGENT_PASSWORD", "agent123")

from fastapi.testclient import TestClient

from auth.security import create_user
from db.models import ConversationStatus
from db.repository import conversation_repository
from intake.main import app
from services.idempotency import webhook_idempotency


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_webhook_idempotency_blocks_completed_duplicate_and_retries_failed():
    event_id = _unique("wamid")
    assert webhook_idempotency.begin("whatsapp", event_id) is True
    webhook_idempotency.complete("whatsapp", event_id)
    assert webhook_idempotency.begin("whatsapp", event_id) is False

    retry_id = _unique("wamid-retry")
    assert webhook_idempotency.begin("whatsapp", retry_id) is True
    webhook_idempotency.fail("whatsapp", retry_id)
    assert webhook_idempotency.begin("whatsapp", retry_id) is True


def test_claim_does_not_overwrite_existing_owner_and_admin_can_transfer():
    first = _unique("agent")
    second = _unique("agent")
    create_user(first, "password-123", "agent")
    create_user(second, "password-123", "agent")
    conversation = conversation_repository.get_or_create_conversation(_unique("customer"), "web_chat")

    claimed = conversation_repository.claim_agent(conversation.id, first)
    assert claimed["agent_username"] == first

    try:
        conversation_repository.claim_agent(conversation.id, second)
        assert False, "second claim should fail"
    except ValueError as exc:
        assert "already assigned" in str(exc)

    transferred = conversation_repository.transfer_agent(conversation.id, second)
    assert transferred["agent_username"] == second
    assert conversation_repository.get_assignment(conversation.id) == second


def test_unassign_returns_conversation_to_waiting_queue():
    username = _unique("agent")
    create_user(username, "password-123", "agent")
    conversation = conversation_repository.get_or_create_conversation(_unique("customer"), "web_chat")
    conversation_repository.claim_agent(conversation.id, username)

    result = conversation_repository.unassign_agent(conversation.id)
    assert result["agent_username"] is None
    assert result["status"] == ConversationStatus.WAITING_FOR_AGENT.value
    assert conversation_repository.get_assignment(conversation.id) is None


def test_duplicate_whatsapp_message_is_processed_once(monkeypatch):
    message_id = _unique("wamid-api")
    calls = {"count": 0}

    class Result:
        class Message:
            session_id = "session-test"
        message = Message()
        reply = "ok"
        action_taken = "reply"
        delivery_success = True
        conversation_status = "BOT_ACTIVE"

    def fake_process(incoming, deliver=True):
        calls["count"] += 1
        return Result()

    monkeypatch.setattr("intake.main.chat_service.process", fake_process)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": message_id,
                        "from": "15550001111",
                        "timestamp": "1700000000",
                        "type": "text",
                        "text": {"body": "hello"},
                    }]
                }
            }]
        }]
    }

    with TestClient(app) as client:
        first = client.post("/webhook/whatsapp", json=payload)
        second = client.post("/webhook/whatsapp", json=payload)

    assert first.status_code == 200
    assert first.json()["processed"] == 1
    assert second.status_code == 200
    assert second.json()["processed"] == 0
    assert second.json()["duplicates"] == 1
    assert calls["count"] == 1
