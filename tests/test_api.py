import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("AGENT_USERNAME", "agent")
os.environ.setdefault("AGENT_PASSWORD", "agent123")

from fastapi.testclient import TestClient

from intake.main import app


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "4.0.0"


def test_browser_pages_are_available():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/dashboard").status_code == 200


def test_agent_routes_require_authentication():
    with TestClient(app) as client:
        response = client.get("/agent/conversations")
    assert response.status_code == 401


def test_agent_can_login_and_read_queue():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"username": "agent", "password": "agent123"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        response = client.get("/agent/conversations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_web_chat_runs_full_pipeline():
    payload = {"channel": "web_chat", "user_id": "test-web-user", "text": "What services do you offer?", "metadata": {}}
    with TestClient(app) as client:
        response = client.post("/webhook/web", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["reply"]
    assert body["action_taken"] in {"reply_only", "ticket_created", "sent_to_agent"}
    assert body["conversation_status"] in {"BOT_ACTIVE", "WAITING_FOR_AGENT"}


def test_support_message_enters_handoff_state():
    payload = {"channel": "web_chat", "user_id": "test-handoff-user", "text": "I have a problem and need help", "metadata": {}}
    with TestClient(app) as client:
        response = client.post("/webhook/web", json=payload)
    assert response.status_code == 200
    assert response.json()["conversation_status"] == "WAITING_FOR_AGENT"
    assert response.json()["action_taken"] == "sent_to_agent"


def test_meta_webhook_verification():
    with TestClient(app) as client:
        response = client.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "challenge-123"})
    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_meta_webhook_rejects_wrong_token():
    with TestClient(app) as client:
        response = client.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "wrong-token", "hub.challenge": "challenge-123"})
    assert response.status_code == 403
