from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NHS Care Operations Copilot"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/nhs_copilot"
    sync_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/nhs_copilot"
    vector_store_dir: str = "./data/vectorstore"
    vector_store_backend: str = "sklearn"
    protocols_dir: str = "./data/protocols"
    default_site_id: str = "site_01"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_provider: str = "local"
    base_llm_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    extraction_adapter_path: str = "./artifacts/lora/extraction"
    triage_adapter_path: str = "./artifacts/lora/triage"
    hf_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def vector_store_path(self) -> Path:
        return Path(self.vector_store_dir)

    @property
    def protocols_path(self) -> Path:
        return Path(self.protocols_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
