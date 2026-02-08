from __future__ import annotations

import math

from openai import OpenAI

from app.core.config import settings
from app.services.embeddings import get_embedding_client
from app.services.vectorstore_local import query as local_query


def _confidence_from_similarities(sims: list[float]) -> dict:
    if not sims:
        return {"confidence": 0.0, "details": {"reason": "no_retrieval"}}

    top1 = sims[0]
    top3 = sims[:3]
    agreement = 0.0
    if len(top3) >= 2:
        # lower variance => higher agreement
        mean = sum(top3) / len(top3)
        var = sum((x - mean) ** 2 for x in top3) / len(top3)
        agreement = max(0.0, 1.0 - math.sqrt(var) * 3)

    # No deep coverage scoring yet; keep it honest.
    coverage = 0.6 if top1 > 0.5 else 0.3

    conf = 0.6 * top1 + 0.2 * agreement + 0.2 * coverage
    conf = float(max(0.0, min(1.0, conf)))
    return {
        "confidence": conf,
        "details": {"top1": top1, "agreement": agreement, "coverage": coverage},
    }


def retrieve(document_id: str, question: str, *, top_k: int | None = None):
    top_k = top_k or settings.top_k
    embedder = get_embedding_client()
    q_emb = embedder.embed([question])[0]

    sources = local_query(document_id, q_emb, top_k=top_k)
    sims = [float(s["similarity"]) for s in sources]
    return sources, sims


def answer_question(document_id: str, question: str) -> dict:
    sources, sims = retrieve(document_id, question)

    if not sources or sims[0] < settings.min_similarity:
        conf = _confidence_from_similarities(sims)
        return {
            "answer": "Not found in document.",
            "sources": sources[:2],
            "confidence": conf["confidence"],
            "confidence_details": conf["details"],
            "guardrail": {
                "triggered": True,
                "reason": "low_retrieval_similarity" if sources else "no_sources",
                "min_similarity": settings.min_similarity,
                "top_similarity": sims[0] if sims else None,
            },
        }

    if not settings.openai_api_key:
        conf = _confidence_from_similarities(sims)
        return {
            "answer": "LLM not configured (set OPENAI_API_KEY). Top matching text is returned as source.",
            "sources": sources[:3],
            "confidence": conf["confidence"],
            "confidence_details": conf["details"],
            "guardrail": {"triggered": False, "reason": None},
        }

    client = OpenAI(api_key=settings.openai_api_key)

    context = "\n\n".join(
        [
            f"[Source {s['rank']} | page={s['page_num']} | sim={s['similarity']:.3f}]\n{s['text']}"
            for s in sources[: min(6, len(sources))]
        ]
    )

    system = (
        "You are an AI assistant inside a Transportation Management System. "
        "Answer ONLY using the provided sources. "
        "If the answer is not explicitly present, respond exactly with: Not found in document. "
        "Keep the answer short and specific."
    )

    user = f"Question: {question}\n\nSources:\n{context}"

    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )

    answer = (completion.choices[0].message.content or "").strip()
    if not answer:
        answer = "Not found in document."

    # Guardrail #2: require answer to be grounded; if model says it isn't found, accept.
    if answer.lower() != "not found in document." and sims[0] < settings.min_similarity:
        answer = "Not found in document."

    conf = _confidence_from_similarities(sims)
    return {
        "answer": answer,
        "sources": sources[:3],
        "confidence": conf["confidence"],
        "confidence_details": conf["details"],
        "guardrail": {"triggered": False, "reason": None},
    }
