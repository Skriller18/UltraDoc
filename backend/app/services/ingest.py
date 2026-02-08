from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.services.chunking import chunk_pages
from app.services.embeddings import get_embedding_client
from app.services.metadata import build_metadata_prefix, detect_document_type, extract_global_identifiers
from app.services.text_extract import extract_text
from app.services.faiss_store import persist


def _ensure_dirs():
    os.makedirs(settings.storage_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "docs"), exist_ok=True)


def ingest_document(*, file_path: str, filename: str, mime: str | None) -> dict:
    _ensure_dirs()

    document_id = str(uuid.uuid4())
    doc_dir = os.path.join(settings.storage_dir, "docs", document_id)
    os.makedirs(doc_dir, exist_ok=True)

    original_path = os.path.join(doc_dir, filename)
    shutil.copyfile(file_path, original_path)

    pages = extract_text(original_path, mime or "")

    # Global metadata detection (POC heuristics)
    full_text = "\n\n".join([(t or "") for _, t in pages])
    doc_type = detect_document_type(full_text)
    identifiers = extract_global_identifiers(full_text)

    global_meta = {
        "document_type": doc_type,
        **identifiers,
    }
    prefix = build_metadata_prefix(global_meta)

    chunks = chunk_pages(document_id, pages)
    if not chunks:
        raise ValueError("No text found in document")

    # Metadata injection into chunk text (improves retrieval even without DB filters)
    for c in chunks:
        c.meta = global_meta
        if prefix:
            c.text = prefix + c.text

    embedder = get_embedding_client()
    embeddings = embedder.embed([c.text for c in chunks])

    # FAISS per-document index + chunk metadata.
    persist(document_id, chunks=chunks, embeddings=embeddings)

    meta = {
        "document_id": document_id,
        "filename": filename,
        "mime": mime,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "num_pages": len(pages),
        "num_chunks": len(chunks),
        "document_type": doc_type,
        **identifiers,
    }

    with open(os.path.join(doc_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta
