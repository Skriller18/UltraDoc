from __future__ import annotations

import pathlib

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


def extract_text_from_pdf(path: str) -> list[tuple[int | None, str]]:
    """PDF extraction via Datalab.

    We intentionally prefer Datalab for PDFs because it handles OCR + layout better
    than basic text extractors.

    Notes:
    - Datalab returns markdown/html/json; for now we use markdown and treat it as a
      single text stream (page_num=None) unless we later add reliable page splitting.
    """

    if settings.datalab_api_key:
        from datalab_sdk import ConvertOptions, DatalabClient

        client = DatalabClient(api_key=settings.datalab_api_key)
        options = ConvertOptions(
            output_format=settings.datalab_output_format,
            mode=settings.datalab_mode,
            paginate=settings.datalab_paginate,
        )
        result = client.convert(path, options=options)

        # Prefer markdown output (most RAG-friendly); fall back if configured otherwise.
        if getattr(result, "markdown", None):
            return [(None, result.markdown)]
        if getattr(result, "html", None):
            return [(None, result.html)]
        if getattr(result, "json", None):
            return [(None, str(result.json))]

        raise ValueError("Datalab conversion returned no usable text")

    # Optional fallback (kept so local dev isn't blocked if Datalab key isn't set)
    import fitz  # PyMuPDF

    pages: list[tuple[int | None, str]] = []
    pdf = fitz.open(path)
    for i in range(pdf.page_count):
        page = pdf.load_page(i)
        text = page.get_text("text") or ""
        pages.append((i + 1, text))
    return pages


def extract_text(path: str, mime: str) -> list[tuple[int | None, str]]:
    mime = (mime or "").lower()
    if mime in {"text/plain"} or path.lower().endswith(".txt"):
        return extract_text_from_txt(path)
    if mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or path.lower().endswith(".docx"):
        return extract_text_from_docx(path)
    if mime in {"application/pdf"} or path.lower().endswith(".pdf"):
        return extract_text_from_pdf(path)

    # Best-effort fallback
    return extract_text_from_txt(path)
