from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Datalab
    datalab_api_key: str | None = None
    datalab_mode: str = "balanced"  # fast|balanced|accurate
    datalab_output_format: str = "markdown"  # markdown|html|json
    datalab_paginate: bool = True

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    storage_dir: str = "storage"

    min_similarity: float = 0.35
    top_k: int = 6


settings = Settings()
