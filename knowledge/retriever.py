import json
import math
import os
import re
from collections import Counter
from pathlib import Path

from db.repository import knowledge_repository
from knowledge.document_store import document_store
from knowledge.embeddings import cosine_similarity, get_embedding_provider


class KnowledgeRetriever:
    """Hybrid lexical + vector retriever over all knowledge sources."""

    def __init__(self, path: str = "knowledge_base.json"):
        self.path = Path(path)
        self.static_chunks = self._load_static_chunks()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\w\u0600-\u06FF]+", text.lower())

    def _load_static_chunks(self) -> list[dict]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        chunks: list[dict] = []
        company = data.get("company_info", {})
        if company:
            chunks.append({"text": "Company information: " + json.dumps(company, ensure_ascii=False), "source": "knowledge_base.json", "title": "Company information", "document_id": None, "chunk_id": None, "chunk_index": 0})
        for index, service in enumerate(data.get("services", [])):
            chunks.append({"text": "Service: " + json.dumps(service, ensure_ascii=False), "source": "knowledge_base.json", "title": service.get("name", f"Service {index + 1}"), "document_id": None, "chunk_id": None, "chunk_index": index})
        for index, faq in enumerate(data.get("faqs", [])):
            chunks.append({"text": f"FAQ: {faq.get('question', '')} Answer: {faq.get('answer', '')}", "source": "knowledge_base.json", "title": faq.get("question", f"FAQ {index + 1}"), "document_id": None, "chunk_id": None, "chunk_index": index})
        return chunks

    def all_records(self) -> list[dict]:
        records = list(self.static_chunks)
        try:
            records.extend({"text": text, "source": "knowledge_entry", "title": "Managed knowledge", "document_id": None, "chunk_id": None, "chunk_index": 0} for text in knowledge_repository.retrieval_chunks())
        except Exception:
            pass
        try:
            records.extend(document_store.retrieval_chunks())
        except Exception:
            pass
        return records

    def all_chunks(self) -> list[str]:
        return [record["text"] for record in self.all_records()]

    def retrieve_with_sources(self, query: str, top_k: int = 4) -> list[dict]:
        records = self.all_records()
        if not records:
            return []
        query_tokens = self._tokens(query)
        if not query_tokens:
            return records[:top_k]

        documents = [self._tokens(record["text"]) for record in records]
        avg_len = sum(len(doc) for doc in documents) / max(len(documents), 1)
        doc_freq = Counter()
        for doc in documents:
            doc_freq.update(set(doc))
        n_docs = len(documents)
        k1, b = 1.5, 0.75

        def bm25(doc: list[str]) -> float:
            tf = Counter(doc)
            score = 0.0
            for token in query_tokens:
                df = doc_freq.get(token, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                freq = tf.get(token, 0)
                denominator = freq + k1 * (1 - b + b * len(doc) / max(avg_len, 1))
                if denominator:
                    score += idf * (freq * (k1 + 1)) / denominator
            return score

        bm25_scores = [bm25(doc) for doc in documents]
        max_bm25 = max(bm25_scores) or 1.0
        provider = get_embedding_provider()
        query_vector = provider.embed(query, task="query")
        lexical_weight = float(os.getenv("RAG_LEXICAL_WEIGHT", "0.45"))
        lexical_weight = min(max(lexical_weight, 0.0), 1.0)
        vector_weight = 1.0 - lexical_weight

        ranked = []
        for record, lexical_score in zip(records, bm25_scores):
            document_vector = record.get("embedding")
            if not document_vector:
                document_vector = provider.embed(record["text"], task="document")
            semantic_score = max(0.0, cosine_similarity(query_vector, document_vector))
            lexical_normalized = lexical_score / max_bm25
            hybrid_score = lexical_weight * lexical_normalized + vector_weight * semantic_score
            ranked.append((hybrid_score, lexical_score, semantic_score, record))

        ranked.sort(key=lambda item: item[0], reverse=True)
        results = []
        for hybrid, lexical, semantic, record in ranked[:top_k]:
            results.append(dict(
                record,
                score=round(hybrid, 6),
                lexical_score=round(lexical, 6),
                semantic_score=round(semantic, 6),
                query_embedding_provider=provider.name,
                query_embedding_model=provider.model,
            ))
        return results

    def retrieve(self, query: str, top_k: int = 4) -> list[str]:
        return [record["text"] for record in self.retrieve_with_sources(query, top_k=top_k)]


retriever = KnowledgeRetriever()
