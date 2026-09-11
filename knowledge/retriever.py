import json
import math
import re
from collections import Counter
from pathlib import Path


class KnowledgeRetriever:
    """Lightweight RAG retriever over the project knowledge base.

    Documents are flattened into chunks and ranked with cosine similarity over
    normalized term-frequency vectors. This keeps local development dependency
    free while providing actual query-based retrieval instead of intent-only
    hard-coded selection.
    """

    def __init__(self, path: str = "knowledge_base.json"):
        self.path = Path(path)
        self.chunks = self._load_chunks()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\w\u0600-\u06FF]+", text.lower())

    def _load_chunks(self) -> list[str]:
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

    def retrieve(self, query: str, top_k: int = 4) -> list[str]:
        q = Counter(self._tokens(query))
        if not q:
            return self.chunks[:top_k]

        def score(chunk: str) -> float:
            d = Counter(self._tokens(chunk))
            dot = sum(q[t] * d.get(t, 0) for t in q)
            q_norm = math.sqrt(sum(v * v for v in q.values()))
            d_norm = math.sqrt(sum(v * v for v in d.values()))
            return dot / (q_norm * d_norm) if q_norm and d_norm else 0.0

        ranked = sorted(((score(c), c) for c in self.chunks), reverse=True)
        relevant = [chunk for similarity, chunk in ranked if similarity > 0][:top_k]
        return relevant or self.chunks[: min(2, top_k)]


retriever = KnowledgeRetriever()
