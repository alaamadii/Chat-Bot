import hashlib
import math
import os
import re
from typing import Protocol

from google import genai


class EmbeddingProvider(Protocol):
    name: str
    model: str

    def embed(self, text: str, *, task: str = "document") -> list[float]: ...


class LocalHashEmbeddingProvider:
    """Deterministic offline vector fallback for tests/local development."""

    name = "local-hash"
    model = "hashed-token-v1"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def embed(self, text: str, *, task: str = "document") -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\w\u0600-\u06FF]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class GeminiEmbeddingProvider:
    name = "gemini"

    def __init__(self):
        self.model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def embed(self, text: str, *, task: str = "document") -> list[float]:
        task_type = "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config={"task_type": task_type},
        )
        embeddings = getattr(response, "embeddings", None) or []
        if not embeddings:
            raise RuntimeError("Embedding provider returned no vectors")
        return list(embeddings[0].values)


def get_embedding_provider() -> EmbeddingProvider:
    configured = os.getenv("EMBEDDING_PROVIDER", "auto").lower()
    if configured == "gemini" or (configured == "auto" and os.getenv("GEMINI_API_KEY")):
        try:
            return GeminiEmbeddingProvider()
        except Exception:
            if configured == "gemini":
                raise
    return LocalHashEmbeddingProvider()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    if not denominator:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / denominator
