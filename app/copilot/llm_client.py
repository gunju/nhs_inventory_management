"""
Abstracted LLM client — supports OpenAI, Azure OpenAI, and mock.
Provider is selected from config and never hardcoded.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.logging import log

settings = get_settings()


@dataclass
class LLMMessage:
    role: str  # system / user / assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]
    raw: Any = None


class MockLLMClient:
    """Deterministic mock — safe for testing and offline dev."""
    model = "mock-gpt"

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        # Return a structured, grounded-looking answer for testing
        user_msg = next((m.content for m in messages if m.role == "user"), "")
        answer = (
            "Based on the structured inventory data provided, I can see the following:\n\n"
            "This is a mock response. In production, real inventory facts from the database "
            "will be injected as context and the LLM will answer grounded only on those facts.\n\n"
            "**Decision support only — requires human review before action.**"
        )
        return LLMResponse(content=answer, model=self.model, usage={"prompt_tokens": 0, "completion_tokens": 0})

    def embed(self, text: str) -> list[float]:
        """Return a zero vector for mock mode."""
        return [0.0] * settings.embedding_dim


class OpenAILLMClient:
    """Real OpenAI client — requires OPENAI_API_KEY in environment."""

    def __init__(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        except ImportError:
            raise RuntimeError("openai package not installed. pip install openai")
        self.model = settings.openai_model

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            **kwargs,
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            raw=response,
        )

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding


def get_llm_client() -> MockLLMClient | OpenAILLMClient:
    provider = settings.llm_provider
    if provider == "mock":
        return MockLLMClient()
    if provider in ("openai", "azure_openai"):
        return OpenAILLMClient()
    raise ValueError(f"Unknown LLM provider: {provider}")
