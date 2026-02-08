from __future__ import annotations

import json
import os

from openai import OpenAI

from app.core.config import settings
from app.services.rag import retrieve


SHIPMENT_SCHEMA = {
    "shipment_id": None,
    "shipper": None,
    "consignee": None,
    "pickup_datetime": None,
    "delivery_datetime": None,
    "equipment_type": None,
    "mode": None,
    "rate": None,
    "currency": None,
    "weight": None,
    "carrier_name": None,
}

RATE_CONFIRMATION_SCHEMA = {
    **SHIPMENT_SCHEMA,
    "reference_id": None,
    "po_number": None,
    "container_id": None,
    "booking_date": None,
    "agreed_amount": None,
}

INVOICE_SCHEMA = {
    "invoice_number": None,
    "invoice_date": None,
    "bill_to": None,
    "remit_to": None,
    "currency": None,
    "subtotal": None,
    "tax": None,
    "total": None,
    "due_date": None,
}

PACKING_LIST_SCHEMA = {
    "packing_list_number": None,
    "shipper": None,
    "consignee": None,
    "po_number": None,
    "container_id": None,
    "total_packages": None,
    "total_weight": None,
    "weight_unit": None,
}

SCHEMAS = {
    "rate_confirmation": RATE_CONFIRMATION_SCHEMA,
    "invoice": INVOICE_SCHEMA,
    "packing_list": PACKING_LIST_SCHEMA,
    # fallbacks
    "bol": SHIPMENT_SCHEMA,
    "manifest": SHIPMENT_SCHEMA,
    "shipment_instructions": SHIPMENT_SCHEMA,
}


def _load_doc_meta(document_id: str) -> dict:
    path = os.path.join(settings.storage_dir, "docs", document_id, "meta.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _schema_for_doc_type(doc_type: str | None) -> dict:
    if not doc_type:
        return SHIPMENT_SCHEMA
    return SCHEMAS.get(doc_type, SHIPMENT_SCHEMA)


def extract_structured(document_id: str, *, force: bool = False) -> dict:
    doc_meta = _load_doc_meta(document_id)
    doc_type = doc_meta.get("document_type")
    schema = _schema_for_doc_type(doc_type)

    # Cache: if extraction already computed for this doc+schema, reuse.
    doc_dir = os.path.join(settings.storage_dir, "docs", document_id)
    cache_path = os.path.join(doc_dir, "extract.json")
    schema_keys = list(schema.keys())

    if not force and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if (
                isinstance(cached, dict)
                and cached.get("_document_type") == doc_type
                and cached.get("_schema_keys") == schema_keys
            ):
                cached["_cached"] = True
                return cached
        except Exception:
            pass

    # Retrieve with a broad query to get likely relevant chunks.
    field_list = ", ".join(schema.keys())
    query = f"Extract the following fields: {field_list}"
    sources, sims = retrieve(document_id, query, top_k=10)

    if not settings.openai_api_key:
        # Return empty schema with some helpful debug for reviewers.
        out = {
            "_document_type": doc_type,
            "_schema_keys": schema_keys,
            "_cached": False,
            **{k: None for k in schema.keys()},
            "_note": "LLM not configured (set OPENAI_API_KEY). Returning nulls.",
            "_sources_preview": sources[:2],
        }
        # Cache the null-structure too (so UI doesn't keep re-running)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
        except Exception:
            pass
        return out

    client = OpenAI(api_key=settings.openai_api_key)

    context = "\n\n".join(
        [
            f"[Source {s['rank']} | page={s['page_num']}]\n{s['text']}"
            for s in sources[: min(8, len(sources))]
        ]
    )

    system = (
        "You are extracting structured shipment data from logistics documents. "
        "Return STRICT JSON only. "
        "Rules: If a field is not explicitly present in the sources, set it to null. "
        "Do not guess. Do not add extra keys."
    )

    user = (
        "Fill this JSON schema using ONLY the sources.\n\n"
        f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
        f"Sources:\n{context}"
    )

    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    # Enforce schema keys and nulls for missing
    out = {k: data.get(k, None) for k in schema.keys()}
    out["_document_type"] = doc_type
    out["_schema_keys"] = schema_keys
    out["_cached"] = False

    # Persist extraction result for reuse
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    except Exception:
        pass

    return out
