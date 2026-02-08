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

    meta = ingest_document(file_path=str(tmp_path), filename=file.filename, mime=file.content_type)
    return meta


@app.post("/ask")
def ask(req: AskRequest):
    return answer_question(req.document_id, req.question)


@app.post("/extract")
def extract(req: ExtractRequest):
    return extract_structured(req.document_id)
