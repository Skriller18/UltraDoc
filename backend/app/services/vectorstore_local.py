from __future__ import annotations

import json
import os
from dataclasses import asdict

import numpy as np

from app.core.config import settings
from app.core.types import Chunk


def _doc_dir(document_id: str) -> str:
    return os.path.join(settings.storage_dir, "docs", document_id)


def persist_chunks(document_id: str, *, chunks: list[Chunk], embeddings: list[list[float]]):
    os.makedirs(_doc_dir(document_id), exist_ok=True)
    path = os.path.join(_doc_dir(document_id), "chunks.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for c, e in zip(chunks, embeddings):
            row = {
                **asdict(c),
                "embedding": e,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def query(document_id: str, query_embedding: list[float], *, top_k: int):
    path = os.path.join(_doc_dir(document_id), "chunks.jsonl")
    if not os.path.exists(path):
        return []

    q = np.asarray(query_embedding, dtype=np.float32)
    qn = np.linalg.norm(q) + 1e-9

    scored: list[tuple[float, dict]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            emb = np.asarray(row.get("embedding", []), dtype=np.float32)
            en = np.linalg.norm(emb) + 1e-9
            sim = float(np.dot(q, emb) / (qn * en)) if emb.size else 0.0
            scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for rank, (sim, row) in enumerate(scored[:top_k], start=1):
        out.append(
            {
                "rank": rank,
                "similarity": sim,
                "page_num": row.get("page_num"),
                "chunk_index": row.get("chunk_index"),
                "text": row.get("text"),
                "chunk_id": row.get("id"),
            }
        )
    return out
