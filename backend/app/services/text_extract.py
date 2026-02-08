from __future__ import annotations

import pathlib

import fitz  # PyMuPDF
from docx import Document as DocxDocument


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
