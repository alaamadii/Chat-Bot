import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

from fastapi.testclient import TestClient

from intake.main import app
from knowledge.retriever import KnowledgeRetriever


def test_bm25_retrieval_prefers_matching_content(monkeypatch):
    retriever = KnowledgeRetriever(path="missing-test-kb.json")
    monkeypatch.setattr(
        "knowledge.retriever.knowledge_repository.retrieval_chunks",
        lambda: [
            "support: Password Reset\nReset your password from account settings.",
            "pricing: Enterprise Plan\nEnterprise pricing includes custom integrations.",
        ],
    )
    result = retriever.retrieve("enterprise pricing integrations", top_k=1)
    assert len(result) == 1
    assert "Enterprise Plan" in result[0]


def test_readiness_endpoint_checks_database():
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
