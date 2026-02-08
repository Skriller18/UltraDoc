from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
    confidence_details: dict | None = None
    guardrail: dict | None = None


class ExtractRequest(BaseModel):
    document_id: str
    force: bool = False
