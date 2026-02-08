from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import AskRequest, ExtractRequest
from app.core.config import settings
from app.services.extract import extract_structured
from app.services.ingest import ingest_document
from app.services.rag import answer_question, rerank_hybrid, retrieve_raw

app = FastAPI(title="UltraDoc Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"ok": True, "service": "ultradoc-backend"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)

    tmp_path = Path(settings.storage_dir) / "uploads" / file.filename
    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    meta = await ingest_document(file_path=str(tmp_path), filename=file.filename, mime=file.content_type)
    return meta


@app.post("/ask")
def ask(req: AskRequest):
    return answer_question(req.document_id, req.question)


@app.get("/debug/retrieve")
def debug_retrieve(document_id: str, q: str, top_k: int = 6):
    """Debug endpoint: show raw FAISS retrieval vs hybrid reranked results.

    Query params:
    - document_id: uuid
    - q: question
    - top_k: final top_k (default 6)
    """

    doc_dir = Path(settings.storage_dir) / "docs" / document_id
    index_path = doc_dir / "index.faiss"
    meta_path = doc_dir / "chunks_meta.jsonl"

    missing = []
    if not doc_dir.exists():
        missing.append("doc_dir")
    if not index_path.exists():
        missing.append("index.faiss")
    if not meta_path.exists():
        missing.append("chunks_meta.jsonl")

    if missing:
        return {
            "document_id": document_id,
            "question": q,
            "top_k": top_k,
            "pre_k": max(top_k * 3, 12),
            "raw_top": [],
            "reranked_top": [],
            "error": {
                "message": "Document is not fully ingested (missing FAISS index/metadata). Re-upload the file to rebuild embeddings/index.",
                "missing": missing,
                "doc_dir": str(doc_dir),
            },
        }

    pre_k = max(top_k * 3, 12)
    raw, _ = retrieve_raw(document_id, q, pre_k=pre_k)
    reranked = rerank_hybrid(q, raw, alpha=0.25)

    def slim(s: dict) -> dict:
        # Keep payload readable
        return {
            "rank": s.get("rank"),
            "similarity": s.get("similarity"),
            "keyword_score": s.get("keyword_score"),
            "rerank_score": s.get("rerank_score"),
            "page_num": s.get("page_num"),
            "chunk_index": s.get("chunk_index"),
            "chunk_id": s.get("chunk_id"),
            "preview": (s.get("text") or "")[:240],
        }

    return {
        "document_id": document_id,
        "question": q,
        "top_k": top_k,
        "pre_k": pre_k,
        "raw_top": [slim(x) for x in raw[:top_k]],
        "reranked_top": [slim(x) for x in reranked[:top_k]],
    }


@app.post("/extract")
def extract(req: ExtractRequest):
    return extract_structured(req.document_id, force=req.force)


@app.get("/documents")
def list_documents():
    """List uploaded documents based on storage on disk."""
    import json

    docs_dir = Path(settings.storage_dir) / "docs"
    if not docs_dir.exists():
        return []

    out = []
    for d in docs_dir.iterdir():
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            out.append(meta)
        except Exception:
            continue

    # newest first when created_at exists
    out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return out


@app.get("/documents/{document_id}")
def get_document_meta(document_id: str):
    import json

    meta_path = Path(settings.storage_dir) / "docs" / document_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return json.loads(meta_path.read_text(encoding="utf-8"))


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Delete a stored document and its FAISS index/caches."""
    import shutil

    doc_dir = Path(settings.storage_dir) / "docs" / document_id
    if not doc_dir.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    shutil.rmtree(doc_dir)
    return {"ok": True, "deleted": document_id}


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: str):
    """Serve the original uploaded document file."""
    import json
    from fastapi.responses import FileResponse

    doc_dir = Path(settings.storage_dir) / "docs" / document_id
    meta_path = doc_dir / "meta.json"

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    filename = meta.get("filename", "document")
    file_path = doc_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=meta.get("mime", "application/octet-stream"),
    )
