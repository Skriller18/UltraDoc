# UltraDoc — Ultra Doc-Intelligence (POC)

UltraDoc is a POC AI system that lets a user upload a logistics document (Rate Confirmation, BOL, Shipment Instructions, Invoice, Packing List, etc.) and interact with it using natural language.

It is designed to simulate an AI assistant inside a Transportation Management System (TMS):
- Upload a document
- Ask questions grounded in the document (RAG)
- See supporting sources + a confidence score
- Run structured extraction (schema varies by document type)
- Apply guardrails to reduce hallucinations

---

## 1) Setup / Run Locally

### Prerequisites
- Python 3.11+ (recommended)
- Node.js 18+
- API keys (recommended):
  - **DATALAB_API_KEY** (best PDF parsing + OCR)
  - **OPENAI_API_KEY** (embeddings + Q&A + extraction)

> Notes
> - PDF parsing uses Datalab (OCR + layout → Markdown). Without DATALAB_API_KEY it will fall back to PyMuPDF.
> - Vector indexing uses FAISS. No external vector DB required for this POC.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set DATALAB_API_KEY and OPENAI_API_KEY in .env

uvicorn app.main:app --reload --port 8000
```

Backend docs:
- http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default:
- http://localhost:5173

### Debug mode (optional)
Append `?debug` to the frontend URL:
- `http://localhost:5173/?debug`

This enables a debug panel that shows:
- raw FAISS retrieval
- reranked (hybrid) retrieval

---

## 2) Architecture & End-to-End Flow

### High-level architecture diagram

```mermaid
flowchart LR
  U[User] -->|Upload / Ask / Extract| UI[Frontend (Vite/React)]
  UI -->|HTTP JSON| API[Backend (FastAPI)]

  subgraph Backend
    API --> UP[/POST /upload/]
    API --> ASK[/POST /ask/]
    API --> EXT[/POST /extract/]

    UP --> PARSE[Parse & normalize text\n(PDF via Datalab → Markdown; DOCX/TXT native)]
    PARSE --> CHUNK[Structure-aware chunking\n(markdown blocks + overlap)]
    CHUNK --> META[Metadata enrichment + injection\n(reference/load/PO/container/etc.)]
    META --> EMB[Embeddings\n(OpenAI embeddings)]
    EMB --> FAISS[(FAISS per-doc index\nindex.faiss)]
    CHUNK --> CHMETA[(Chunk store\nchunks_meta.jsonl)]
    META --> DOCMETA[(meta.json)]

    ASK --> RET[Retrieve candidates (FAISS)]
    RET --> HYB[Hybrid rerank\n(vector + keyword boost)]
    HYB --> GUARD[Guardrail\n(similarity threshold)]
    GUARD --> LLM[LLM grounded answer\n(OpenAI chat)]
    LLM --> RESP1[answer + sources + confidence]

    EXT --> CACHE{extract.json cache?}
    CACHE -- hit --> RESP2[cached extraction]
    CACHE -- miss --> EXTLLM[LLM fills schema\n(doc-type dependent)]
    EXTLLM --> SAVE[(extract.json)]
    SAVE --> RESP2
  end

  API -->|Serves PDF| FILE[/GET /documents/{id}/file/]
  FILE --> UI

  API -->|Reads/writes| STORE[(storage/ on disk)]
  STORE --> API

  UI --> U
```

### What’s persisted (storage layout)

Each uploaded document has a folder:

```text
backend/storage/
  docs/
    <document_id>/
      <original_filename>
      meta.json
      index.faiss
      chunks_meta.jsonl
      extract.json           # created after /extract (cached)
  uploads/
    <filename>               # temp file during upload
```

---

## 3) Methodology & Design Decisions

This project optimizes for **grounded retrieval quality** and **practical AI engineering** over framework complexity.

### 3.1 Parsing
- **PDF → Datalab → Markdown**
  - Rationale: logistics documents are layout-heavy (tables, key/value fields, fixed forms). Datalab produces OCR + layout-aware output that is more RAG-friendly than raw text extraction.
- DOCX/TXT use direct text extraction.

### 3.2 Chunking (structure-aware)
Logistics docs often contain:
- tables (stops, rate breakdown, line items)
- key-value fields (Reference ID, Load ID, PO/Container)
- instruction paragraphs

Naive char-based chunking breaks these relationships.

What we do:
- If text looks like Markdown (typical Datalab output):
  - parse into blocks: `heading`, `table`, `kvs`, `text`
  - pack blocks into chunks while avoiding splitting tables/key-value runs
  - apply overlap for continuity
- Otherwise (plain text):
  - split by blank lines → pack into size-bounded chunks

### 3.3 Metadata enrichment + injection
Shipping docs are template-like and can look similar. We extract global identifiers (best-effort heuristics) and inject them into every chunk before embedding.

Examples of metadata:
- `document_type`
- `reference_id`, `load_id`, `po_number`, `container_id`, `carrier_mc`
- dispatcher: `dispatcher_name`, `dispatcher_phone`, `dispatcher_email`

Why injection:
- In this POC, FAISS is used per-document and doesn’t do metadata filtering.
- Injecting metadata into chunk text improves retrieval for identifier-heavy queries (PO numbers, load IDs, etc.).

### 3.4 Vector index + retrieval (FAISS)
- Per-document FAISS index (`IndexFlatIP`) with **L2-normalized vectors** so inner product == cosine similarity.
- This is simple, fast, and reliable for a POC.

### 3.5 Hybrid reranking (vector + keyword)
Embeddings are weak at exact identifiers (LD53657, PO numbers, emails, phone numbers).

Retrieval strategy:
1) FAISS retrieves a broader candidate set (`pre_k = max(top_k*3, 12)`)
2) We compute a keyword match score per chunk for tokens from the question (IDs/emails/$ patterns)
3) Rerank:

```text
rerank_score = similarity + 0.25 * keyword_score
```

Result:
- identifier-containing chunks rise to the top
- LLM receives better evidence → fewer misses/hallucinations

### 3.6 Guardrails
At minimum:
- If top similarity < `MIN_SIMILARITY` → return: **“Not found in document.”**

This prevents answering when retrieval evidence is weak.

### 3.7 Structured extraction (dynamic schema)
`/extract` selects a schema based on detected `document_type` (rate confirmation vs invoice vs packing list vs fallback).

Caching:
- Results stored in `extract.json`
- Repeated calls return cached output unless `force=true`

---

## 4) Message Metrics (Confidence) — What You See in the UI

Every assistant answer includes:
- `confidence` (0–1)
- `confidence_details` (breakdown)

### 4.1 Confidence formula (current)
We separate:
- **Guardrail threshold** (hard safety): `MIN_SIMILARITY`
- **Confidence** (user-facing): calibrated + hybrid-aware

Confidence is computed (conceptually) as:

```text
base = 0.62 * top1_calibrated
     + 0.23 * agreement_rerank
     + 0.15 * coverage

confidence = clamp(base + keyword_boost, 0, 1)
```

Additionally:
- If we passed guardrails and produced an answer (not “Not found”), we apply a floor of **0.55** for UX consistency.

### 4.2 Breakdown fields returned to the frontend
You’ll see these in `confidence_details`:
- `top1_raw` — raw cosine similarity of the top chunk
- `top1_calibrated` — similarity mapped to a more human-usable scale
- `agreement_rerank` — agreement among top-3 **rerank_score** values
- `agreement_similarity` — agreement among top-3 raw similarities (debug)
- `coverage` — heuristic placeholder (will be upgraded to quote/attribution scoring)
- `keyword_top1` — keyword score for the top chunk
- `keyword_boost` — boost applied from keyword match (up to +0.12)
- `floor_applied` — present when the confidence floor is applied

### 4.3 Why the confidence is designed this way
- Cosine similarity in OCR/table-heavy docs often clusters around 0.35–0.50 even when retrieval is correct.
- Hybrid reranking is a real signal for identifier-heavy questions, so agreement is computed on rerank scores.
- Keyword boost reflects cases where exact matches strongly indicate grounding.

---

## More details
For implementation-level flowcharts and file-by-file dataflow, see:
- `backend/README.md`
