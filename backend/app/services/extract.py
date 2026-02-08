from __future__ import annotations

import json

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


def extract_structured(document_id: str) -> dict:
    # Retrieve with a broad query to get likely relevant chunks.
    query = (
        "Extract shipment details: shipment id, shipper, consignee, pickup datetime, delivery datetime, "
        "equipment type, mode, rate, currency, weight, carrier name"
    )
    sources, sims = retrieve(document_id, query, top_k=8)

    if not settings.openai_api_key:
        # Return empty schema with some helpful debug for reviewers.
        return {
            **SHIPMENT_SCHEMA,
            "_note": "LLM not configured (set OPENAI_API_KEY). Returning nulls.",
            "_sources_preview": sources[:2],
        }

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
        f"Schema:\n{json.dumps(SHIPMENT_SCHEMA, indent=2)}\n\n"
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
    out = {k: data.get(k, None) for k in SHIPMENT_SCHEMA.keys()}
    return out
