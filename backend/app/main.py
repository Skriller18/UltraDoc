from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import AskRequest, ExtractRequest
from app.core.config import settings
from app.services.extract import extract_structured
from app.services.ingest import ingest_document
from app.services.rag import answer_question

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


@app.post("/extract")
def extract(req: ExtractRequest):
    return extract_structured(req.document_id)


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: str):
    """Serve the original uploaded document file."""
    import json
    from fastapi.responses import FileResponse
    
    doc_dir = Path(settings.storage_dir) / "docs" / document_id
    meta_path = doc_dir / "meta.json"
    
    if not meta_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    filename = meta.get("filename", "document")
    file_path = doc_dir / filename
    
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=meta.get("mime", "application/octet-stream")
    )
