import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("AGENT_USERNAME", "agent")
os.environ.setdefault("AGENT_PASSWORD", "agent123")

from fastapi.testclient import TestClient

from intake.main import app


def _headers(client, username="agent", password="agent123"):
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _conversation(client, user_id):
    response = client.post(
        "/webhook/web",
        json={"channel": "web_chat", "user_id": user_id, "text": "I need support with a problem", "metadata": {}},
    )
    assert response.status_code == 200
    return response.json()["session_id"]


def test_agent_claim_reply_and_customer_polling():
    with TestClient(app) as client:
        conversation_id = _conversation(client, "sprint3-live-user")
        headers = _headers(client)
        claim = client.post(f"/agent/conversations/{conversation_id}/assign", headers=headers, json={})
        assert claim.status_code == 200
        assert claim.json()["status"] == "HUMAN_ACTIVE"

        reply = client.post(
            f"/agent/conversations/{conversation_id}/reply",
            headers=headers,
            json={"text": "A human agent is here to help."},
        )
        assert reply.status_code == 200
        assert reply.json()["delivered"] is True

        messages = client.get(
            f"/web/conversations/{conversation_id}/messages",
            params={"user_id": "sprint3-live-user"},
        )
        assert messages.status_code == 200
        assert any(m["role"] == "agent" for m in messages.json())


def test_customer_cannot_poll_another_users_conversation():
    with TestClient(app) as client:
        conversation_id = _conversation(client, "sprint3-owner")
        response = client.get(
            f"/web/conversations/{conversation_id}/messages",
            params={"user_id": "not-the-owner"},
        )
        assert response.status_code == 404


def test_human_active_conversation_bypasses_ai():
    with TestClient(app) as client:
        conversation_id = _conversation(client, "sprint3-human-route")
        headers = _headers(client)
        client.post(f"/agent/conversations/{conversation_id}/assign", headers=headers, json={})
        response = client.post(
            "/webhook/web",
            json={"channel": "web_chat", "user_id": "sprint3-human-route", "text": "One more detail", "metadata": {}},
        )
        assert response.status_code == 200
        assert response.json()["action_taken"] == "routed_to_agent"
        assert response.json()["conversation_status"] == "HUMAN_ACTIVE"


def test_agent_can_resolve_owned_conversation():
    with TestClient(app) as client:
        conversation_id = _conversation(client, "sprint3-resolve")
        headers = _headers(client)
        client.post(f"/agent/conversations/{conversation_id}/assign", headers=headers, json={})
        response = client.patch(
            f"/agent/conversations/{conversation_id}/status",
            headers=headers,
            json={"status": "RESOLVED"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"


def test_admin_manages_knowledge_and_agent_is_read_only():
    with TestClient(app) as client:
        agent_headers = _headers(client)
        forbidden = client.post(
            "/knowledge",
            headers=agent_headers,
            json={"title": "Private", "content": "Agents cannot create entries.", "category": "test"},
        )
        assert forbidden.status_code == 403

        admin_headers = _headers(client, "admin", "admin123")
        created = client.post(
            "/knowledge",
            headers=admin_headers,
            json={"title": "Refund policy", "content": "Refunds are reviewed within five business days.", "category": "policy"},
        )
        assert created.status_code == 201
        entry_id = created.json()["id"]

        listed = client.get("/knowledge", headers=agent_headers)
        assert listed.status_code == 200
        assert any(item["id"] == entry_id for item in listed.json())

        deleted = client.delete(f"/knowledge/{entry_id}", headers=admin_headers)
        assert deleted.status_code == 204


def test_agent_analytics_summary():
    with TestClient(app) as client:
        headers = _headers(client)
        response = client.get("/agent/analytics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_conversations" in data
        assert "waiting_for_agent" in data
        assert "resolved" in data
