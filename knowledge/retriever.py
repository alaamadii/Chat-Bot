import json
import math
import re
from collections import Counter
from pathlib import Path

from db.repository import knowledge_repository


class KnowledgeRetriever:
    """Query retriever over static and managed knowledge using BM25 ranking."""

    def __init__(self, path: str = "knowledge_base.json"):
        self.path = Path(path)
        self.static_chunks = self._load_static_chunks()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\w\u0600-\u06FF]+", text.lower())

    def _load_static_chunks(self) -> list[str]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        chunks: list[str] = []
        company = data.get("company_info", {})
        if company:
            chunks.append("Company information: " + json.dumps(company, ensure_ascii=False))
        for service in data.get("services", []):
            chunks.append("Service: " + json.dumps(service, ensure_ascii=False))
        for faq in data.get("faqs", []):
            chunks.append(f"FAQ: {faq.get('question', '')} Answer: {faq.get('answer', '')}")
        return chunks

    def all_chunks(self) -> list[str]:
        try:
            managed = knowledge_repository.retrieval_chunks()
        except Exception:
            managed = []
        return self.static_chunks + managed

    def retrieve(self, query: str, top_k: int = 4) -> list[str]:
        chunks = self.all_chunks()
        if not chunks:
            return []
        query_tokens = self._tokens(query)
        if not query_tokens:
            return chunks[:top_k]

        documents = [self._tokens(chunk) for chunk in chunks]
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

        ranked = sorted(
            ((bm25(doc), chunk) for doc, chunk in zip(documents, chunks)),
            key=lambda item: item[0],
            reverse=True,
        )
        relevant = [chunk for score, chunk in ranked if score > 0][:top_k]
        return relevant or chunks[: min(2, top_k)]


retriever = KnowledgeRetriever()
