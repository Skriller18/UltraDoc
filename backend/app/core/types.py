from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    page_num: int | None
    chunk_index: int
    meta: dict | None = None
