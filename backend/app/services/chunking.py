from __future__ import annotations

import re

from app.core.types import Chunk


def _split_by_blank_lines(text: str) -> list[str]:
    # Normalize whitespace but keep paragraph boundaries
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b and b.strip()]


def chunk_pages(
    document_id: str,
    pages: list[tuple[int | None, str]],
    *,
    max_chars: int = 2200,
    overlap_chars: int = 200,
) -> list[Chunk]:
    """Simple but effective chunker for POC.

    Strategy:
    1) split by blank lines (paragraph-ish)
    2) pack paragraphs into chunks up to max_chars
    3) add small overlap for continuity

    We keep page_num in metadata when available.
    """

    chunks: list[Chunk] = []
    chunk_index = 0

    for page_num, text in pages:
        paras = _split_by_blank_lines(text or "")
        if not paras:
            continue

        buf: list[str] = []
        buf_len = 0

        def flush():
            nonlocal chunk_index, buf, buf_len
            if not buf:
                return
            joined = "\n\n".join(buf).strip()
            if not joined:
                buf, buf_len = [], 0
                return
            cid = f"{document_id}:{page_num or 0}:{chunk_index}"
            chunks.append(
                Chunk(
                    id=cid,
                    document_id=document_id,
                    text=joined,
                    page_num=page_num,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
            buf, buf_len = [], 0

        for p in paras:
            p_len = len(p)
            if buf_len + p_len + 2 <= max_chars:
                buf.append(p)
                buf_len += p_len + 2
                continue

            # flush current chunk
            flush()

            # if paragraph itself is huge, hard-split
            if p_len > max_chars:
                start = 0
                while start < p_len:
                    end = min(start + max_chars, p_len)
                    piece = p[start:end].strip()
                    if piece:
                        cid = f"{document_id}:{page_num or 0}:{chunk_index}"
                        chunks.append(
                            Chunk(
                                id=cid,
                                document_id=document_id,
                                text=piece,
                                page_num=page_num,
                                chunk_index=chunk_index,
                            )
                        )
                        chunk_index += 1
                    start = max(end - overlap_chars, end)
                continue

            # start new chunk with this paragraph
            buf.append(p)
            buf_len = p_len

        flush()

    return chunks
