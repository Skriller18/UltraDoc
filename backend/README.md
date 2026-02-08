# UltraDoc Backend

FastAPI backend for the Ultra Doc-Intelligence POC.

## Architecture (at a glance)

```text
                ┌──────────────────────────┐
                │        Frontend UI        │
                │  Upload / Ask / Extract   │
                └─────────────┬────────────┘
                              │ HTTP
                              v
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                            │
│  /upload                 /ask                     /extract         │
│    │                      │                         │              │
│    v                      v                         v              │
│ Parse -> Chunk -> Embed -> FAISS retrieve -> LLM answer   LLM JSON  │
│    │                      │                         │              │
│    v                      v                         v              │
│ Persist: meta.json, index.faiss, chunks_meta.jsonl  extract.json    │
└──────────────────────────────────────────────────────────────────┘

PDF parsing: Datalab (OCR + layout → Markdown) with optional PyMuPDF fallback
Embeddings + LLM: OpenAI (configurable)
Vector index: FAISS (per-document)
```

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set DATALAB_API_KEY for best PDF parsing
# set OPENAI_API_KEY for Q&A + extraction

uvicorn app.main:app --reload --port 8000
```

Open:
- http://127.0.0.1:8000/docs

---

## Endpoints

- `POST /upload` (multipart file)
  - returns: `document_id`, `document_type`, identifiers, chunk/page counts
- `POST /ask` `{ document_id, question }`
  - returns: `answer`, `sources[]`, `confidence`, `confidence_details`, `guardrail`
- `POST /extract` `{ document_id, force? }`
  - returns: extracted JSON (schema depends on detected `document_type`)
  - caches to disk; set `force=true` to recompute

Also:
- `GET /documents` list stored documents
- `GET /documents/{document_id}` get metadata
- `DELETE /documents/{document_id}` delete document + indexes + caches
- `GET /documents/{document_id}/file` serve original file

---

## What happens after parsing (end-to-end flow)

### 1) Storage layout (per document)

After upload we create a folder:

```text
storage/
  docs/
    <document_id>/
      <original_filename>
      meta.json
      index.faiss
      chunks_meta.jsonl
      extract.json           # created after /extract (cached)
  uploads/
    <filename>               # temp copy during upload
```

### 2) Parsing

- **PDF**: converted via **Datalab Marker API** into Markdown (better OCR + layout retention)
- **DOCX**: text extracted from paragraphs
- **TXT**: plain text read

Output is normalized into:
- `pages: list[(page_num | None, text)]`

### 3) Chunking strategy (structure-aware)

File: `app/services/chunking.py`

We prefer *structure-aware* chunking when the extracted text looks like Markdown (typical for Datalab output):

- Parse Markdown into blocks (`heading`, `table`, `kvs`, `text`) using `app/services/parsing/markdown_blocks.py`
- Chunk by block boundaries to avoid breaking tables and key-value groups
- Tables are kept intact unless extremely large (then split, but kept isolated)

Fallback for non-Markdown text:
- split by blank lines (paragraph-ish)
- pack paragraphs into chunks up to ~2400 chars with ~250 char overlap

Why this matters for logistics docs:
- tables (stops, rate breakdown) remain coherent
- key/value fields (Reference ID, PO, Load ID) stay together

### 4) Metadata enrichment + injection

File: `app/services/metadata.py`

At ingest time, we scan the full document text for global identifiers and tags:
- `document_type`
- `reference_id`, `load_id`, `shipment_id`, `bol_number`, `po_number`, `container_id`
- `dispatcher_name`, `dispatcher_phone`, `dispatcher_email`
- `carrier_mc`, `booking_date`, `issue_date`, `currency_hint`

We then **inject a compact metadata prefix into every chunk text** before embedding:

```text
[document_type=rate_confirmation]
[reference_id=LD53657]
[load_id=L1234]
[po_number=112233ABC]
---
<chunk text>
```

This improves retrieval even with FAISS (which doesn’t do metadata filtering in this POC).

### 5) Embedding + indexing (FAISS)

- Each chunk is embedded using OpenAI embeddings.
- Vectors are L2-normalized.
- A **per-document FAISS index** is built using `IndexFlatIP`.
  - inner-product on normalized vectors == cosine similarity

Persisted files:
- `index.faiss`: the vector index
- `chunks_meta.jsonl`: chunk records in the same order as vectors in FAISS

---

## Retrieval + ranking strategy (RAG)

File: `app/services/rag.py`

### Step A: retrieve candidates (vector)
- Embed the user question
- Query FAISS for **pre_k** candidates (`max(top_k*3, 12)`) to get a wider net

### Step B: hybrid rerank (vector + keyword)
Logistics documents contain many identifiers where semantic embeddings are weak.
So we rerank FAISS candidates using a **keyword boost**:

- Extract keyword tokens from the question (IDs like `LD53657`, `112233ABC`, emails, money patterns)
- Compute a lightweight `keyword_score` per chunk based on token presence
- Rerank using:

```text
rerank_score = vector_similarity + 0.25 * keyword_score
```

Return top_k after reranking.
Each returned source includes:
- `similarity` (raw cosine)
- `keyword_score`
- `rerank_score`
- chunk text + page number (when available)

### Step C: guardrails
- If no sources or top similarity < `MIN_SIMILARITY`:
  - answer is forced to: `Not found in document.`
  - guardrail triggers with reason

### Step D: answer synthesis
- If OpenAI is configured:
  - We send the question + top sources to the LLM with strict instruction: **answer only from sources**.
- If not configured:
  - We return a message that LLM isn’t configured and still return sources for debugging.

---

## How quality is calculated (confidence scoring)

We keep two concepts separate:

1) **Guardrail threshold**: hard safety gate (`MIN_SIMILARITY`)
2) **Confidence score**: a user-facing score that’s calibrated for typical similarity ranges

### Confidence components
- `top1_raw`: raw cosine similarity from FAISS
- `top1_calibrated`: mapped into a more human-usable scale (piecewise)
- `agreement`: measures stability/consensus among top-3 similarities (low variance = higher)
- `coverage`: heuristic placeholder (will later be upgraded to quote/attribution scoring)

The final confidence is a weighted blend:
- `0.65 * top1_calibrated + 0.20 * agreement + 0.15 * coverage`

Returned in `/ask` response as:
- `confidence`
- `confidence_details`

---

## Extraction strategy + caching

File: `app/services/extract.py`

- Determine `document_type` from `meta.json`
- Select schema dynamically (rate confirmation vs invoice vs packing list vs fallback)
- Retrieve likely relevant chunks
- Ask LLM to fill schema with strict rules: missing => `null`

Caching:
- results stored in `storage/docs/<document_id>/extract.json`
- repeated calls return cached result unless `force=true`

---

## Improvement ideas (next)
- Add true token-based chunk sizing (tiktoken) instead of char length
- Add table row-aware chunking (repeat header per N rows)
- Add a reranker (cross-encoder or LLM re-rank) for better top-1 selection
- Add quote-based answer support scoring to make confidence more meaningful
