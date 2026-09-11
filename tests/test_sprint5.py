import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

from fastapi.testclient import TestClient

from actions.router import router
from ai_brain.models import AIResponse, FinalOutput, Intent
from intake.main import app
from intake.models import NormalizedMessage


def test_router_uses_structured_intent_for_pricing(monkeypatch):
    monkeypatch.setattr("actions.router.integrator.create_crm_lead", lambda message: "LD-TEST")
    message = NormalizedMessage(
        session_id="session-1",
        user_id="user-1",
        channel="web_chat",
        original_text="pricing please",
        clean_text="pricing please",
        metadata={},
    )
    output = FinalOutput(
        response=AIResponse(text="Our plans start here.", reasoning="no keyword dependency"),
        intent=Intent(category="pricing", confidence=0.9),
        confidence_score=0.9,
        escalate_to_human=False,
    )
    result = router.route(message, output)
    assert result.action_taken == "crm_lead_created"
    assert result.internal_data["lead_id"] == "LD-TEST"


def test_feedback_and_quality_summary():
    user_id = "quality-user"
    with TestClient(app) as client:
        chat = client.post("/webhook/web", json={"channel": "web_chat", "user_id": user_id, "text": "hello", "metadata": {}})
        assert chat.status_code == 200
        conversation_id = chat.json()["session_id"]

        feedback = client.post("/feedback", json={"conversation_id": conversation_id, "user_id": user_id, "rating": 5, "comment": "helpful"})
        assert feedback.status_code == 201
        assert feedback.json()["rating"] == 5

        login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        quality = client.get("/admin/quality", headers=headers)
        assert quality.status_code == 200
        assert "avg_latency_ms" in quality.json()
        assert quality.json()["feedback_count"] >= 1
