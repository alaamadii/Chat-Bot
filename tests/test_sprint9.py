import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("WEB_SESSION_SECRET", "test-web-session-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

import pytest
from fastapi.testclient import TestClient

from auth.web_session import create_web_session, validate_production_secrets, verify_web_session
from core.rate_limit import rate_limiter
from intake.main import app


def test_web_session_token_is_scoped_to_user_and_conversation():
    token = create_web_session("web-user", "conversation-1")
    payload = verify_web_session(token, user_id="web-user", conversation_id="conversation-1")
    assert payload["sub"] == "web-user"

    with pytest.raises(Exception):
        verify_web_session(token, user_id="other-user", conversation_id="conversation-1")


def test_secure_web_chat_flow(monkeypatch):
    monkeypatch.setenv("WEB_SESSION_REQUIRED", "true")
    rate_limiter.reset()
    with TestClient(app) as client:
        session = client.post("/web/session")
        assert session.status_code == 200
        user_id = session.json()["user_id"]
        bootstrap_token = session.json()["session_token"]

        chat = client.post(
            "/webhook/web",
            headers={"X-Web-Session": bootstrap_token},
            json={"channel": "web_chat", "user_id": user_id, "text": "hello", "metadata": {}},
        )
        assert chat.status_code == 200
        conversation_id = chat.json()["session_id"]
        scoped_token = chat.json()["session_token"]
        assert scoped_token

        denied = client.get(
            f"/web/conversations/{conversation_id}/messages",
            params={"user_id": user_id},
        )
        assert denied.status_code == 401

        allowed = client.get(
            f"/web/conversations/{conversation_id}/messages",
            params={"user_id": user_id, "session_token": scoped_token},
        )
        assert allowed.status_code == 200
        assert isinstance(allowed.json(), list)


def test_public_rate_limit(monkeypatch):
    monkeypatch.setenv("PUBLIC_RATE_LIMIT", "1")
    monkeypatch.setenv("PUBLIC_RATE_WINDOW_SECONDS", "60")
    rate_limiter.reset()
    with TestClient(app) as client:
        assert client.post("/web/session").status_code == 200
        limited = client.post("/web/session")
        assert limited.status_code == 429
        assert limited.headers["retry-after"] == "60"
    rate_limiter.reset()


def test_production_rejects_weak_secrets(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "weak")
    monkeypatch.setenv("WEB_SESSION_SECRET", "also-weak")
    with pytest.raises(RuntimeError):
        validate_production_secrets()


def test_production_accepts_strong_secrets(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "j" * 40)
    monkeypatch.setenv("WEB_SESSION_SECRET", "w" * 40)
    validate_production_secrets()
