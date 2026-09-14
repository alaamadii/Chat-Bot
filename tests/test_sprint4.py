import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("AGENT_USERNAME", "agent")
os.environ.setdefault("AGENT_PASSWORD", "agent123")

from fastapi.testclient import TestClient

from intake.main import app


def _admin_headers(client: TestClient) -> dict:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_readiness_checks_database():
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["redis"] in {"disabled", "ok", "degraded"}
    assert isinstance(body["distributed_runtime_required"], bool)


def test_admin_can_create_persistent_user_and_audit_event():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        username = "sprint4-agent"
        create = client.post(
            "/admin/users",
            json={"username": username, "password": "securepass123", "role": "agent"},
            headers=headers,
        )
        if create.status_code == 409:
            assert create.json()["detail"] == "username already exists"
        else:
            assert create.status_code == 201
            assert create.json()["username"] == username

        users = client.get("/admin/users", headers=headers)
        assert users.status_code == 200
        assert any(item["username"] == username for item in users.json())

        audit = client.get("/admin/audit", headers=headers)
        assert audit.status_code == 200
        assert isinstance(audit.json(), list)


def test_agent_cannot_access_admin_users():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"username": "agent", "password": "agent123"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = client.get("/admin/users", headers=headers)
    assert response.status_code == 403
