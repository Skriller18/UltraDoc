from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MdBlock:
    kind: str  # heading|table|kvs|text
    text: str


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_KV_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /\-_.()]{1,40})\s*[:\-]\s*(.+?)\s*$")


def _is_table_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # Markdown tables usually have pipes.
    return s.count("|") >= 2


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    # e.g. | --- | --- | or ---|---
    return bool(re.match(r"^\s*\|?\s*:?[-]{2,}\s*\|", s)) or bool(re.match(r"^\s*[-:| ]{6,}\s*$", s))


def parse_markdown_blocks(md: str) -> list[MdBlock]:
    """Best-effort markdown block parser for structure-aware chunking.

    We detect:
    - headings: lines starting with #
    - tables: consecutive lines with | and a separator row
    - key-value runs: consecutive lines like "Label: Value"
    - text: everything else, grouped by blank-line paragraphs
    """

    md = (md or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = md.split("\n")

    blocks: list[MdBlock] = []
    i = 0
    n = len(lines)

    def consume_blank(j: int) -> int:
        while j < n and not lines[j].strip():
            j += 1
        return j

    while i < n:
        i = consume_blank(i)
        if i >= n:
            break

        line = lines[i]

        # Heading
        m = _HEADING_RE.match(line.strip())
        if m:
            blocks.append(MdBlock(kind="heading", text=line.strip()))
            i += 1
            continue

        # Table block: header line with pipes + separator line
        if _is_table_line(line) and i + 1 < n and (_is_table_line(lines[i + 1]) or _is_table_sep(lines[i + 1])):
            start = i
            i += 1
            while i < n and (_is_table_line(lines[i]) or _is_table_sep(lines[i])):
                i += 1
            table_txt = "\n".join(lines[start:i]).strip()
            blocks.append(MdBlock(kind="table", text=table_txt))
            continue

        # Key-value run
        if _KV_RE.match(line):
            start = i
            i += 1
            while i < n and _KV_RE.match(lines[i]):
                i += 1
            kv_txt = "\n".join(lines[start:i]).strip()
            blocks.append(MdBlock(kind="kvs", text=kv_txt))
            continue

        # Paragraph text until blank line or structural token
        start = i
        i += 1
        while i < n and lines[i].strip():
            # stop if next line starts a new structure
            if _HEADING_RE.match(lines[i].strip()):
                break
            if _KV_RE.match(lines[i]):
                break
            if _is_table_line(lines[i]) and i + 1 < n and (_is_table_line(lines[i + 1]) or _is_table_sep(lines[i + 1])):
                break
            i += 1
        para = "\n".join(lines[start:i]).strip()
        if para:
            blocks.append(MdBlock(kind="text", text=para))

    return blocks
