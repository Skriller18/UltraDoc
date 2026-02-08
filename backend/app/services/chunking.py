from __future__ import annotations

import re

from app.core.types import Chunk
from app.services.parsing.markdown_blocks import parse_markdown_blocks


def _split_by_blank_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b and b.strip()]


def _chunk_block_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []

    out: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end >= n:
            break
        start = max(end - overlap_chars, end)
    return out


def chunk_pages(
    document_id: str,
    pages: list[tuple[int | None, str]],
    *,
    max_chars: int = 2400,
    overlap_chars: int = 250,
) -> list[Chunk]:
    """Structure-aware chunker.

    If the input looks like Markdown (Datalab output), we parse headings/tables/kvs
    and chunk by block boundaries first.

    Otherwise we fall back to paragraph packing.
    """

    chunks: list[Chunk] = []
    chunk_index = 0

    for page_num, text in pages:
        t = text or ""

        looks_markdown = ("|" in t and "\n" in t) or ("#" in t and "\n" in t)

        if looks_markdown:
            blocks = parse_markdown_blocks(t)
            # Pack blocks into chunks, but never split a table unless it is huge.
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

            for b in blocks:
                b_text = b.text.strip()
                if not b_text:
                    continue

                # If it's a huge table, split it by chars but keep it isolated.
                if b.kind == "table" and len(b_text) > max_chars:
                    flush()
                    for piece in _chunk_block_text(b_text, max_chars=max_chars, overlap_chars=overlap_chars):
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
                    continue

                # headings should stick with the next block when possible
                if b.kind == "heading" and buf_len + len(b_text) + 2 > max_chars:
                    flush()

                if buf_len + len(b_text) + 2 <= max_chars:
                    buf.append(b_text)
                    buf_len += len(b_text) + 2
                else:
                    flush()
                    # block still too large -> split
                    for piece in _chunk_block_text(b_text, max_chars=max_chars, overlap_chars=overlap_chars):
                        buf = [piece]
                        buf_len = len(piece)
                        flush()

            flush()
            continue

        # Fallback: paragraph packing
        paras = _split_by_blank_lines(t)
        if not paras:
            continue

        buf: list[str] = []
        buf_len = 0

        def flush2():
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
            if buf_len + len(p) + 2 <= max_chars:
                buf.append(p)
                buf_len += len(p) + 2
            else:
                flush2()
                for piece in _chunk_block_text(p, max_chars=max_chars, overlap_chars=overlap_chars):
                    buf = [piece]
                    buf_len = len(piece)
                    flush2()

        flush2()

    return chunks
