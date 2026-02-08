from __future__ import annotations

import json
import os
from dataclasses import asdict

import faiss
import numpy as np

from app.core.config import settings
from app.core.types import Chunk


def _doc_dir(document_id: str) -> str:
    return os.path.join(settings.storage_dir, "docs", document_id)


def _index_path(document_id: str) -> str:
    return os.path.join(_doc_dir(document_id), "index.faiss")


def _meta_path(document_id: str) -> str:
    return os.path.join(_doc_dir(document_id), "chunks_meta.jsonl")


def _normalize(v: np.ndarray) -> np.ndarray:
    # Normalize rows for cosine similarity via inner product
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    return v / norms


def persist(document_id: str, *, chunks: list[Chunk], embeddings: list[list[float]]):
    os.makedirs(_doc_dir(document_id), exist_ok=True)

    emb = np.asarray(embeddings, dtype=np.float32)
    if emb.ndim != 2 or emb.shape[0] != len(chunks):
        raise ValueError("Embeddings shape mismatch")

    emb = _normalize(emb)
    dim = emb.shape[1]

    # Flat index is plenty for POC. Swap to IVFFlat/HNSW later if needed.
    index = faiss.IndexFlatIP(dim)
    index.add(emb)
    faiss.write_index(index, _index_path(document_id))

    # Persist chunk metadata in the same order as vectors in the index.
    with open(_meta_path(document_id), "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def query(document_id: str, query_embedding: list[float], *, top_k: int):
    ipath = _index_path(document_id)
    mpath = _meta_path(document_id)
    if not os.path.exists(ipath) or not os.path.exists(mpath):
        return []

    index = faiss.read_index(ipath)

    q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
    q = _normalize(q)

    scores, idxs = index.search(q, top_k)
    scores = scores.reshape(-1).tolist()
    idxs = idxs.reshape(-1).tolist()

    # Load metadata lines into a list (POC). For huge docs, use sqlite/offsets.
    metas: list[dict] = []
    with open(mpath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                metas.append(json.loads(line))

    out = []
    rank = 1
    for sim, i in zip(scores, idxs):
        if i is None or i < 0 or i >= len(metas):
            continue
        m = metas[i]
        out.append(
            {
                "rank": rank,
                "similarity": float(sim),
                "page_num": m.get("page_num"),
                "chunk_index": m.get("chunk_index"),
                "text": m.get("text"),
                "chunk_id": m.get("id"),
            }
        )
        rank += 1

    return out
