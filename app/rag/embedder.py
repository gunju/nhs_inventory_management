"""
Embedding service — abstracts OpenAI and local/mock providers.
"""
from __future__ import annotations

import hashlib
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import log

settings = get_settings()


class EmbedderProtocol(Protocol):
    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


class MockEmbedder:
    """Deterministic mock — hash-based pseudo-embedding for dev/test."""
    dim = settings.embedding_dim

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        # Expand to required dim with repeating pattern
        raw = list(h) * (self.dim // 32 + 1)
        vec = [(b / 255.0) - 0.5 for b in raw[:self.dim]]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class OpenAIEmbedder:
    def __init__(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        except ImportError:
            raise RuntimeError("openai package not installed")
        self.model = settings.openai_embedding_model
        self.dim = settings.embedding_dim

    def embed(self, text: str) -> list[float]:
        result = self._client.embeddings.create(model=self.model, input=text)
        return result.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        result = self._client.embeddings.create(model=self.model, input=texts)
        return [r.embedding for r in result.data]


def get_embedder() -> MockEmbedder | OpenAIEmbedder:
    if settings.embedding_provider == "mock":
        return MockEmbedder()
    if settings.embedding_provider == "openai":
        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
