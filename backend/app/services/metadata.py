from __future__ import annotations

import re


def detect_document_type(text: str) -> str | None:
    t = (text or "").lower()
    # Very lightweight heuristics (POC). We'll improve with a classifier later.
    if "bill of lading" in t or re.search(r"\bbol\b", t):
        return "bol"
    if "rate confirmation" in t or "load confirmation" in t:
        return "rate_confirmation"
    if "commercial invoice" in t or re.search(r"\binvoice\b", t):
        return "invoice"
    if "packing list" in t:
        return "packing_list"
    if "manifest" in t:
        return "manifest"
    if "shipment instruction" in t or "shipping instructions" in t:
        return "shipment_instructions"
    return None


def extract_global_identifiers(text: str) -> dict:
    t = text or ""

    out: dict = {}

    # Reference / shipment id patterns
    m = re.search(r"\bReference\s*ID\s*[:#-]?\s*([A-Z0-9-]{4,})\b", t, re.IGNORECASE)
    if m:
        out["reference_id"] = m.group(1)

    m = re.search(r"\bShipment\s*(ID|#)\s*[:#-]?\s*([A-Z0-9-]{4,})\b", t, re.IGNORECASE)
    if m:
        out["shipment_id"] = m.group(2)

    m = re.search(r"\bBOL\s*(Number|No\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{6,})\b", t, re.IGNORECASE)
    if m:
        out["bol_number"] = m.group(2)

    m = re.search(r"\b(Purchase\s*Order|PO)\s*(Number|No\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{4,})\b", t, re.IGNORECASE)
    if m:
        out["po_number"] = m.group(3)

    m = re.search(r"\bContainer\s*(ID|No\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{6,})\b", t, re.IGNORECASE)
    if m:
        out["container_id"] = m.group(2)

    # Carrier MC
    m = re.search(r"\bMC\s*#?\s*([0-9]{5,10})\b", t, re.IGNORECASE)
    if m:
        out["carrier_mc"] = m.group(1)

    # Common date markers (keep raw; normalization can be added later)
    m = re.search(r"\bBooking\s*Date\s*[:#-]?\s*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})\b", t, re.IGNORECASE)
    if m:
        out["booking_date"] = m.group(1)

    m = re.search(r"\bIssue\s*Date\s*[:#-]?\s*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})\b", t, re.IGNORECASE)
    if m and "issue_date" not in out:
        out["issue_date"] = m.group(1)

    # Currency hint
    if re.search(r"\bUSD\b|\$", t):
        out["currency_hint"] = "USD"

    return out


def build_metadata_prefix(meta: dict) -> str:
    """Prefix injected into chunk text before embedding.

    This makes FAISS retrieval more robust even without metadata filtering.
    """

    lines = []
    for k in [
        "document_type",
        "reference_id",
        "shipment_id",
        "bol_number",
        "po_number",
        "container_id",
        "carrier_mc",
        "booking_date",
        "issue_date",
        "currency_hint",
    ]:
        v = meta.get(k)
        if v:
            lines.append(f"[{k}={v}]")

    if not lines:
        return ""

    return "\n".join(lines) + "\n---\n"
