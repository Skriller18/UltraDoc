from __future__ import annotations
import pathlib
import asyncio
import mimetypes
import httpx
from docx import Document as DocxDocument
from app.core.config import settings


def extract_text_from_txt(path: str) -> list[tuple[int | None, str]]:
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")
    return [(None, text)]


def extract_text_from_docx(path: str) -> list[tuple[int | None, str]]:
    doc = DocxDocument(path)
    parts: list[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return [(None, "\n\n".join(parts))]


async def extract_text_from_pdf(path: str) -> list[tuple[int | None, str]]:
    """PDF extraction via Datalab API (direct HTTP, no SDK).

    We intentionally prefer Datalab for PDFs because it handles OCR + layout better
    than basic text extractors.

    Notes:
    - Datalab returns markdown/html/json; for now we use markdown and treat it as a
      single text stream (page_num=None) unless we later add reliable page splitting.
    """

    DATALAB_MARKER_URL = "https://www.datalab.to/api/v1/marker"

    if settings.datalab_api_key:
        # Guess content type for the file
        content_type, _ = mimetypes.guess_type(path)
        content_type = content_type or "application/pdf"

        data = {
            "output_format": "markdown",
            "paginate": "true" if settings.datalab_paginate else "false",
            "mode": settings.datalab_mode,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Submit the file
            with open(path, "rb") as f:
                files = {"file": (pathlib.Path(path).name, f, content_type)}
                submit_response = await client.post(
                    DATALAB_MARKER_URL,
                    headers={"X-API-Key": settings.datalab_api_key},
                    data=data,
                    files=files,
                )

            if submit_response.status_code >= 400:
                raise RuntimeError(f"Datalab submit failed: {submit_response.status_code} {submit_response.text}")

            submit_payload = submit_response.json()
            request_url = submit_payload.get("request_check_url")

            if not request_url:
                raise RuntimeError("Datalab response missing 'request_check_url'.")

            # Poll for completion
            start_time = asyncio.get_event_loop().time()
            timeout_seconds = 300
            poll_interval = 5.0

            while True:
                status_response = await client.get(
                    request_url,
                    headers={"X-API-Key": settings.datalab_api_key},
                )

                if status_response.status_code >= 400:
                    raise RuntimeError(f"Datalab status check failed: {status_response.status_code}")

                payload = status_response.json()
                status_value = str(payload.get("status", "")).lower()

                if payload.get("success") and status_value not in {"queued", "processing", "running"}:
                    break
                if status_value in {"completed", "complete", "success"} and payload.get("success") is not False:
                    break
                if status_value in {"failed", "error"} or payload.get("success") is False:
                    raise RuntimeError(f"Datalab processing failed: {payload.get('error') or payload}")

                if (asyncio.get_event_loop().time() - start_time) > timeout_seconds:
                    raise TimeoutError("Datalab processing timed out.")

                await asyncio.sleep(poll_interval)

            # Extract markdown from response
            markdown = payload.get("markdown")
            if isinstance(markdown, str) and markdown:
                return [(None, markdown)]

            # Handle list of markdown chunks
            if isinstance(markdown, list):
                chunks = []
                for chunk in markdown:
                    if isinstance(chunk, str):
                        chunks.append(chunk)
                    elif isinstance(chunk, dict) and chunk.get("content"):
                        chunks.append(chunk["content"])
                if chunks:
                    return [(None, "\n\n".join(chunks))]

            raise ValueError("Datalab conversion returned no usable markdown")

    # Fallback to PyMuPDF if no Datalab key
    import fitz  # PyMuPDF

    pages: list[tuple[int | None, str]] = []
    pdf = fitz.open(path)
    for i in range(pdf.page_count):
        page = pdf.load_page(i)
        text = page.get_text("text") or ""
        pages.append((i + 1, text))
    return pages


async def extract_text(path: str, mime: str) -> list[tuple[int | None, str]]:
    mime = (mime or "").lower()
    if mime in {"text/plain"} or path.lower().endswith(".txt"):
        return extract_text_from_txt(path)
    if mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or path.lower().endswith(".docx"):
        return extract_text_from_docx(path)
    if mime in {"application/pdf"} or path.lower().endswith(".pdf"):
        return await extract_text_from_pdf(path)

    # Best-effort fallback
    return extract_text_from_txt(path)
