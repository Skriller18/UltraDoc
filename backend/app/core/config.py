from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_storage_dir() -> str:
    """Use /tmp for serverless (Vercel/Lambda), otherwise local storage."""
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/storage"
    return "storage"


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

    storage_dir: str = get_default_storage_dir()

    min_similarity: float = 0.35
    top_k: int = 6


settings = Settings()
