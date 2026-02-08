# UltraDoc Backend

FastAPI backend for the Ultra Doc-Intelligence POC.

This backend provides:
- document upload + ingestion (parse → chunk → embed → index)
- grounded Q&A (RAG) with guardrails + confidence scoring
- structured extraction (dynamic schema by doc type) with caching
- debug retrieval inspection endpoint

---

## 1) Setup / Run Locally

### Prerequisites
- Python 3.11+ recommended
- API keys:
  - `DATALAB_API_KEY` (recommended for PDF OCR/layout → Markdown)
  - `OPENAI_API_KEY` (required for embeddings; also used for Q&A + extraction)

### Install + run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set DATALAB_API_KEY + OPENAI_API_KEY

uvicorn app.main:app --reload --port 8000
```

Swagger:
- http://127.0.0.1:8000/docs

---

## 2) API Endpoints

### Core
- `POST /upload` (multipart file)
  - Ingests document and builds per-document FAISS index
- `POST /ask` `{ document_id, question }`
  - Returns: `answer`, `sources[]`, `confidence`, `confidence_details`, `guardrail`
- `POST /extract` `{ document_id, force?: boolean }`
  - Returns structured JSON (schema depends on `document_type`)
  - Cached to disk; set `force=true` to recompute

### Document management
- `GET /documents` → list stored documents (from `storage/docs/*/meta.json`)
- `GET /documents/{document_id}` → return metadata
- `DELETE /documents/{document_id}` → delete doc + indexes + caches
- `GET /documents/{document_id}/file` → serve original file

### Debug
- `GET /debug/retrieve?document_id=...&q=...&top_k=6`
  - Returns both:
    - raw FAISS top-k (vector only)
    - reranked top-k (hybrid vector + keyword)

---

## 3) Architecture & Dataflow

### High-level flow

```mermaid
flowchart TD
  UP[/POST /upload/] --> PARSE[Parse (PDF via Datalab → Markdown)]
  PARSE --> CHUNK[Structure-aware chunking\n(markdown blocks: heading/table/kvs/text)]
  CHUNK --> META[Metadata enrichment + injection]
  META --> EMB[Embeddings (OpenAI)]
  EMB --> IDX[FAISS per-document index (IndexFlatIP, cosine)]
  IDX --> DISK[(index.faiss + chunks_meta.jsonl + meta.json)]

  ASK[/POST /ask/] --> RET[FAISS retrieve pre_k]
  RET --> RR[Hybrid rerank\n(similarity + 0.25*keyword_score)]
  RR --> GUARD{Guardrail: min similarity?}
  GUARD -->|fail| NF["Not found in document"]
  GUARD -->|pass| LLM[LLM answer from sources]

  EXT[/POST /extract/] --> CACHE{extract.json cache?}
  CACHE -->|hit| CACHED[Return cached]
  CACHE -->|miss| EXTLLM[LLM fills schema]\n
  EXTLLM --> SAVE[(extract.json)]
```

### What is persisted (per document)

```text
storage/
  docs/
    <document_id>/
      <original_filename>
      meta.json
      index.faiss
      chunks_meta.jsonl
      extract.json           # created after /extract
  uploads/
    <filename>               # temp
```

---

## 4) Methodology (why these choices)

### PDF parsing: Datalab
Logistics documents are layout- and table-heavy. Datalab provides OCR + layout-preserving Markdown, which tends to improve chunking and retrieval grounding.

### Chunking: structure-aware
Instead of naive character chunking, we chunk by Markdown blocks:
- headings, tables, key/value runs, paragraphs
This helps keep:
- table rows coherent
- key identifiers near their values

### Vector store: FAISS (per document)
- Simple and fast for a POC
- No external DB needed
- Uses `IndexFlatIP` with L2-normalized vectors (inner product == cosine similarity)

### Retrieval: hybrid ranking
- FAISS (semantic) retrieves a candidate set
- Keyword boost improves exact matching for identifiers (Reference ID, PO, Load ID, emails)

### Guardrails
- If retrieval similarity is too low, the system refuses and returns “Not found in document.”

### Extraction caching
- Extraction results are persisted to `extract.json` per document
- Repeated extracts return cached output (unless `force=true`)

---

## 5) Confidence & metrics returned by `/ask`

The backend returns:
- `confidence` (0..1)
- `confidence_details` (breakdown)

Current confidence components:
- `top1_raw`: raw cosine similarity of top chunk
- `top1_calibrated`: similarity mapped to a more human-friendly scale
- `agreement_rerank`: agreement among top-3 rerank scores
- `agreement_similarity`: agreement among top-3 raw similarities (debug)
- `keyword_top1`: keyword match score for top chunk
- `keyword_boost`: boost applied from keyword matching
- `coverage`: heuristic placeholder (future: quote-based support scoring)
- optional: `floor_applied`

See root `README.md` for the full confidence formula explanation.
