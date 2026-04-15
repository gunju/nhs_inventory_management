"""
Central application configuration via Pydantic Settings / twelve-factor env vars.
All secrets must be injected via environment — never hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Identity ─────────────────────────────────────────────────────────────
    app_name: str = "NHS Inventory Intelligence Copilot"
    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/nhs_inventory"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_pre_ping: bool = True

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    secret_key: SecretStr = Field(
        default=SecretStr("CHANGE_ME_IN_PRODUCTION_USE_256_BIT_RANDOM_KEY"),
        description="JWT signing key — override in production",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── LLM / AI ──────────────────────────────────────────────────────────────
    openai_api_key: SecretStr | None = Field(default=None)
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_provider: Literal["openai", "azure_openai", "mock"] = "mock"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # Azure OpenAI overrides (optional)
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment: str | None = None

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_provider: Literal["openai", "local", "mock"] = "mock"
    embedding_dim: int = 1536

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_top_k: int = 5
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64

    # ── Object storage ────────────────────────────────────────────────────────
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./data/uploads"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_chat_per_minute: int = 20
    rate_limit_api_per_minute: int = 200

    # ── Feature flags ─────────────────────────────────────────────────────────
    enable_pgvector: bool = True
    enable_celery: bool = True
    enable_otel: bool = False
    otel_endpoint: str = "http://localhost:4317"

    # ── Seed / dev ────────────────────────────────────────────────────────────
    seed_on_startup: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
