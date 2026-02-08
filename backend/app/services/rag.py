from __future__ import annotations

import math
import re

from openai import OpenAI

from app.core.config import settings
from app.services.embeddings import get_embedding_client
from app.services.faiss_store import query as faiss_query


def _calibrate_similarity(sim: float) -> float:
    """Map cosine similarity into a more human-usable confidence-like scale.

    Similarity values from embeddings in messy documents often cluster around 0.30–0.55.
    We keep the guardrail threshold separate; this is only for *display confidence*.
    """

    # piecewise linear calibration
    if sim <= 0.25:
        return max(0.0, sim / 0.25 * 0.20)  # 0..0.20
    if sim <= 0.35:
        # 0.25..0.35 -> 0.20..0.45
        return 0.20 + (sim - 0.25) / 0.10 * 0.25
    if sim <= 0.45:
        # 0.35..0.45 -> 0.45..0.75
        return 0.45 + (sim - 0.35) / 0.10 * 0.30
    if sim <= 0.60:
        # 0.45..0.60 -> 0.75..0.92
        return 0.75 + (sim - 0.45) / 0.15 * 0.17
    # 0.60+ -> asymptote to 0.98
    return min(0.98, 0.92 + (sim - 0.60) / 0.40 * 0.06)


def _agreement_from_scores(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    var = sum((x - mean) ** 2 for x in scores) / len(scores)
    return max(0.0, 1.0 - math.sqrt(var) * 3)


def _confidence_from_sources(sources: list[dict]) -> dict:
    if not sources:
        return {"confidence": 0.0, "details": {"reason": "no_retrieval"}}

    raw_top1 = float(sources[0].get("similarity") or 0.0)
    top1_cal = _calibrate_similarity(raw_top1)

    # Option A: agreement based on the *final ranking score* (rerank_score), not raw similarity.
    rr_scores = [float(s.get("rerank_score") or 0.0) for s in sources[:3]]
    agreement_rerank = _agreement_from_scores(rr_scores)

    # Also keep similarity agreement for debugging.
    sim_scores = [float(s.get("similarity") or 0.0) for s in sources[:3]]
    agreement_similarity = _agreement_from_scores(sim_scores)

    # Option B: keyword-based boost (IDs/PO/Load/MC/email etc.).
    kw_top1 = float(sources[0].get("keyword_score") or 0.0)
    # up to +0.12 boost when kw_top1 is strong
    kw_boost = min(0.12, 0.12 * kw_top1)

    # Still a placeholder; later we can score answer support/quotes.
    coverage = 0.70 if raw_top1 >= 0.45 else (0.55 if raw_top1 >= 0.35 else 0.35)

    base = 0.62 * top1_cal + 0.23 * agreement_rerank + 0.15 * coverage
    conf = base + kw_boost
    conf = float(max(0.0, min(1.0, conf)))

    return {
        "confidence": conf,
        "details": {
            "top1_raw": raw_top1,
            "top1_calibrated": top1_cal,
            "agreement_rerank": agreement_rerank,
            "agreement_similarity": agreement_similarity,
            "coverage": coverage,
            "keyword_top1": kw_top1,
            "keyword_boost": kw_boost,
        },
    }


def _keyword_tokens(question: str) -> list[str]:
    q = (question or "").strip()
    if not q:
        return []

    tokens: set[str] = set()

    # IDs like LD53657, MC1685682, PO12345
    stop_upper = {"WHAT", "WHEN", "WHERE", "WHO", "WHICH", "TELL", "SHOW", "GIVE", "PLEASE", "RATE", "PICKUP", "DELIVERY"}
    for t in re.findall(r"\b[A-Z0-9-]{4,}\b", q.upper()):
        if t.isdigit():
            continue
        if t in stop_upper:
            continue
        tokens.add(t)

    # Emails
    for t in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", q.upper()):
        tokens.add(t)

    # Money patterns
    for t in re.findall(r"\$\s*\d+(?:\.\d+)?", q):
        tokens.add(t.replace(" ", ""))

    # Longer words (helps for things like consignee names/locations)
    stop = {"what", "when", "where", "who", "which", "tell", "show", "give", "please", "about", "from", "into", "with", "rate", "pickup", "delivery"}
    for t in re.findall(r"\b[a-zA-Z]{4,}\b", q.lower()):
        if t in stop:
            continue
        tokens.add(t)

    return list(tokens)


def _keyword_score(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    t = (text or "")
    t_upper = t.upper()
    t_lower = t.lower()

    score = 0.0
    for tok in tokens:
        if not tok:
            continue
        # exact-ish contains
        if tok.isupper() and tok in t_upper:
            score += 1.5
        elif tok in t_lower:
            score += 0.6

    # normalize to 0..1-ish
    return min(1.0, score / max(3.0, len(tokens)))


def retrieve_raw(document_id: str, question: str, *, pre_k: int):
    embedder = get_embedding_client()
    q_emb = embedder.embed([question])[0]
    sources = faiss_query(document_id, q_emb, top_k=pre_k)
    for i, s in enumerate(sources, start=1):
        s["rank"] = i
    sims = [float(s["similarity"]) for s in sources]
    return sources, sims


def rerank_hybrid(question: str, sources: list[dict], *, alpha: float = 0.25) -> list[dict]:
    tokens = _keyword_tokens(question)

    out = []
    for s in sources:
        s2 = dict(s)
        kw = _keyword_score(s2.get("text", ""), tokens)
        s2["keyword_score"] = kw
        s2["rerank_score"] = float(s2.get("similarity", 0.0)) + alpha * kw
        out.append(s2)

    out.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    for i, s in enumerate(out, start=1):
        s["rank"] = i
    return out


def retrieve(document_id: str, question: str, *, top_k: int | None = None):
    top_k = top_k or settings.top_k
    pre_k = max(top_k * 3, 12)

    raw_sources, _ = retrieve_raw(document_id, question, pre_k=pre_k)
    reranked = rerank_hybrid(question, raw_sources, alpha=0.25)

    final = reranked[:top_k]
    sims = [float(s["similarity"]) for s in final]
    return final, sims


def answer_question(document_id: str, question: str) -> dict:
    sources, sims = retrieve(document_id, question)

    if not sources or sims[0] < settings.min_similarity:
        conf = _confidence_from_sources(sources)
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
        conf = _confidence_from_sources(sources)
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

    conf = _confidence_from_sources(sources)

    # Optional floor when we passed guardrails and produced an answer.
    if answer.lower() != "not found in document." and sources and sims and sims[0] >= settings.min_similarity:
        conf_val = max(conf["confidence"], 0.55)
        if conf_val != conf["confidence"]:
            conf["details"]["floor_applied"] = 0.55
            conf["confidence"] = conf_val

    return {
        "answer": answer,
        "sources": sources[:3],
        "confidence": conf["confidence"],
        "confidence_details": conf["details"],
        "guardrail": {"triggered": False, "reason": None},
    }
