# UltraDoc Frontend

Lightweight reviewer UI for UltraDoc (upload a document, ask questions, view grounded answers + confidence, run structured extraction).

## Run locally

```bash
cd frontend
npm install

# Optional: point UI to a different backend
# export VITE_API_URL=http://localhost:8000

npm run dev
```

Open:
- http://localhost:5173

## Configure backend URL

The frontend reads:
- `VITE_API_URL` (defaults to `http://localhost:8000`)

Example:

```bash
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

## Features

- **Upload**: sends multipart file to `POST /upload`
- **Chat Q&A**: sends question to `POST /ask` and displays:
  - answer
  - sources (supporting text)
  - confidence + breakdown (tooltip)
- **Structured extraction**: calls `POST /extract` and renders dynamic fields
- **PDF viewer**: loads `GET /documents/{document_id}/file`

## Debug mode: retrieval inspection

Append `?debug` to the frontend URL:
- `http://localhost:5173/?debug`

When enabled, after each question the UI will call:
- `GET /debug/retrieve?document_id=...&q=...&top_k=6`

and show:
- **Raw (FAISS)** vs **Reranked (hybrid)** retrieval side-by-side.

## Notes

- Sessions/doc list are loaded from backend storage via `GET /documents`.
- If backend storage is cleared, the UI will show no sessions (expected).
