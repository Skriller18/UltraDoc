# Ultra Doc-Intelligence (POC)

POC: upload a logistics document (PDF/DOCX/TXT), ask grounded questions over it (RAG), get sources + confidence, run structured extraction.

## System design (high level)

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

## Repo layout
- `backend/` – API + document processing + retrieval + extraction
- `frontend/` – UI for document upload and Q&A
- `evaluation/` – evaluation scripts and metrics
- `data/` – sample documents and extracted data

## Backend architecture
See `backend/README.md` for:
- storage layout
- chunking strategy
- retrieval + hybrid ranking
- confidence scoring
- flowchart diagram

## Next