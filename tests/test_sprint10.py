import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("LLM_PROVIDER", "offline")

from ai_brain.providers import OfflineProvider, get_llm_provider
from knowledge.document_store import document_store
from knowledge.embeddings import LocalHashEmbeddingProvider, cosine_similarity
from knowledge.retriever import KnowledgeRetriever


def test_local_embeddings_are_deterministic_and_normalized():
    provider = LocalHashEmbeddingProvider(dimensions=64)
    first = provider.embed("pricing enterprise support")
    second = provider.embed("pricing enterprise support")
    assert first == second
    assert round(sum(value * value for value in first), 6) == 1.0


def test_cosine_similarity_prefers_related_vectors():
    provider = LocalHashEmbeddingProvider(dimensions=128)
    query = provider.embed("enterprise pricing plan", task="query")
    related = provider.embed("enterprise pricing plan for teams", task="document")
    unrelated = provider.embed("password reset technical support", task="document")
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_document_ingestion_persists_embeddings():
    result = document_store.ingest(
        title="Semantic pricing doc",
        content="Enterprise pricing includes dedicated support and custom integrations.",
        source="sprint10-test",
        content_type="text/plain",
        created_by="test",
    )
    assert result["embedded_chunks"] >= 1
    records = [record for record in document_store.retrieval_chunks() if record["document_id"] == result["id"]]
    assert records
    assert records[0]["embedding"]
    assert records[0]["embedding_provider"] == "local-hash"
    document_store.delete_document(result["id"])


def test_hybrid_retrieval_exposes_semantic_scores(monkeypatch):
    retriever = KnowledgeRetriever(path="does-not-exist.json")
    monkeypatch.setattr(
        retriever,
        "all_records",
        lambda: [
            {"text": "enterprise pricing plan with integrations", "source": "a", "title": "A", "document_id": None, "chunk_id": None, "chunk_index": 0},
            {"text": "reset password and login support", "source": "b", "title": "B", "document_id": None, "chunk_id": None, "chunk_index": 0},
        ],
    )
    results = retriever.retrieve_with_sources("enterprise pricing integrations", top_k=2)
    assert results[0]["source"] == "a"
    assert "semantic_score" in results[0]
    assert "lexical_score" in results[0]
    assert results[0]["query_embedding_provider"] == "local-hash"


def test_offline_llm_provider_can_be_selected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    provider = get_llm_provider()
    assert isinstance(provider, OfflineProvider)
