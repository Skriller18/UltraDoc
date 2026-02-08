# UltraDoc Backend

FastAPI backend for the Ultra Doc-Intelligence POC.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# (optional) set OPENAI_API_KEY in .env

uvicorn app.main:app --reload --port 8000
```

Open:
- http://127.0.0.1:8000/docs

## Endpoints
- `POST /upload` (multipart file)
- `POST /ask` `{ document_id, question }`
- `POST /extract` `{ document_id }`

## Storage
- `storage/docs/<document_id>/meta.json`
- `storage/docs/<document_id>/index.faiss` (FAISS index; cosine via inner-product on normalized vectors)
- `storage/docs/<document_id>/chunks_meta.jsonl` (chunk text + metadata in index order)

## Notes
- Retrieval uses **FAISS** per document (IndexFlatIP). Good for POC; can swap to IVF/HNSW later.
- If `OPENAI_API_KEY` is not set, `/ask` returns guardrailed “LLM not configured…” and `/extract` returns nulls.
