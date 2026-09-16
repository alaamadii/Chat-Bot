import hashlib
import math
import os
import re
from typing import Protocol

from openai import OpenAI


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


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self):
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        self.client = OpenAI(api_key=api_key)

    def embed(self, text: str, *, task: str = "document") -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        if not response.data:
            raise RuntimeError("Embedding provider returned no vectors")
        return list(response.data[0].embedding)


def get_embedding_provider() -> EmbeddingProvider:
    configured = os.getenv("EMBEDDING_PROVIDER", "auto").lower()
    if configured == "openai" or (configured == "auto" and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAIEmbeddingProvider()
        except Exception:
            if configured == "openai":
                raise
    return LocalHashEmbeddingProvider()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    if not denominator:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / denominator
