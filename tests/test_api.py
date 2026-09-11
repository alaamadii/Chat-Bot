import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")

from fastapi.testclient import TestClient

from intake.main import app


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_web_chat_runs_full_pipeline():
    payload = {
        "channel": "web_chat",
        "user_id": "test-web-user",
        "text": "What services do you offer?",
        "metadata": {},
    }
    with TestClient(app) as client:
        response = client.post("/webhook/web", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["reply"]
    assert body["action_taken"] in {"reply_only", "ticket_created", "sent_to_agent"}
    assert body["conversation_status"] in {"BOT_ACTIVE", "WAITING_FOR_AGENT"}


def test_support_message_enters_handoff_state():
    payload = {
        "channel": "web_chat",
        "user_id": "test-handoff-user",
        "text": "I have a problem and need help",
        "metadata": {},
    }
    with TestClient(app) as client:
        response = client.post("/webhook/web", json=payload)

    assert response.status_code == 200
    assert response.json()["conversation_status"] == "WAITING_FOR_AGENT"
    assert response.json()["action_taken"] == "sent_to_agent"


def test_meta_webhook_verification():
    with TestClient(app) as client:
        response = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_meta_webhook_rejects_wrong_token():
    with TestClient(app) as client:
        response = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 403
