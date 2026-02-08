from __future__ import annotations

from typing import Sequence

from openai import OpenAI

from app.core.config import settings


class EmbeddingClient:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        # OpenAI embeddings API returns data in order.
        res = self._client.embeddings.create(
            model=settings.openai_embedding_model,
            input=list(texts),
        )
        return [d.embedding for d in res.data]


def get_embedding_client() -> EmbeddingClient:
    # For the POC we keep it simple: OpenAI embeddings when configured.
    return OpenAIEmbeddingClient()
