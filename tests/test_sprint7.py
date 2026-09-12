import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

from fastapi.testclient import TestClient

from intake.main import app
from knowledge.document_store import chunk_text


def _admin_headers(client: TestClient) -> dict:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_chunk_text_has_overlap():
    content = " ".join(f"word-{i}" for i in range(20))
    chunks = chunk_text(content, max_words=10, overlap_words=2)
    assert len(chunks) == 3
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_document_ingestion_deduplicates_and_searches_with_sources():
    with TestClient(app) as client:
        headers = _admin_headers(client)
        payload = {
            "title": "Enterprise Support Policy",
            "source": "docs/support-policy.md",
            "content_type": "text/markdown",
            "content": "Enterprise customers receive priority onboarding, dedicated support, and annual security reviews. " * 40,
        }

        first = client.post("/admin/knowledge/documents", json=payload, headers=headers)
        assert first.status_code == 201
        assert first.json()["chunk_count"] > 1
        assert first.json()["duplicate"] is False

        duplicate = client.post("/admin/knowledge/documents", json=payload, headers=headers)
        assert duplicate.status_code == 201
        assert duplicate.json()["id"] == first.json()["id"]
        assert duplicate.json()["duplicate"] is True

        search = client.post(
            "/admin/knowledge/search",
            json={"query": "enterprise security reviews", "top_k": 3},
            headers=headers,
        )
        assert search.status_code == 200
        results = search.json()
        assert results
        assert results[0]["source"] == "docs/support-policy.md"
        assert results[0]["document_id"] == first.json()["id"]
        assert results[0]["score"] > 0

        listing = client.get("/admin/knowledge/documents", headers=headers)
        assert listing.status_code == 200
        assert any(item["id"] == first.json()["id"] for item in listing.json())

        deleted = client.delete(f"/admin/knowledge/documents/{first.json()['id']}", headers=headers)
        assert deleted.status_code == 204
