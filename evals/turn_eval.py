from __future__ import annotations

from dataclasses import dataclass
import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


@dataclass(frozen=True)
class EvalThresholds:
    min_similarity: float = 0.35
    min_coverage: float = 0.45
    fail_coverage: float = 0.30


def _tokens(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", text.lower())


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokens(text) if t not in STOPWORDS and len(t) > 1]


def _coverage_ratio(answer: str, source_texts: list[str]) -> float:
    answer_tokens = _content_tokens(answer)
    if not answer_tokens:
        return 0.0
    src_tokens = set(_content_tokens(" ".join(source_texts)))
    overlap = sum(1 for tok in answer_tokens if tok in src_tokens)
    return max(0.0, min(1.0, overlap / max(1, len(answer_tokens))))


def evaluate_turn(
    *,
    question: str,
    answer: str,
    sources: list[dict],
    confidence: float,
    guardrail: dict | None = None,
    thresholds: EvalThresholds = EvalThresholds(),
) -> dict:
    similarities = [float(s.get("similarity", 0.0)) for s in sources]
    top_similarity = similarities[0] if similarities else 0.0
    mean_similarity = sum(similarities) / len(similarities) if similarities else 0.0

    source_texts = [str(s.get("text", "")) for s in sources]
    answer_coverage = _coverage_ratio(answer, source_texts)
    not_found = answer.strip().lower() == "not found in document."

    retrieval_pass = top_similarity >= thresholds.min_similarity
    grounding_pass = not_found or answer_coverage >= thresholds.min_coverage

    flags: list[str] = []
    if not retrieval_pass:
        flags.append("low_similarity")
    if guardrail and guardrail.get("triggered"):
        reason = guardrail.get("reason") or "unknown"
        flags.append(f"guardrail:{reason}")
    if not not_found and answer_coverage < thresholds.min_coverage:
        flags.append("weak_source_coverage")

    score = 0.50 * float(confidence) + 0.35 * float(answer_coverage) + 0.15 * (1.0 if retrieval_pass else 0.0)
    score = max(0.0, min(1.0, score))

    if flags:
        if not retrieval_pass or (not not_found and answer_coverage < thresholds.fail_coverage):
            verdict = "fail"
        else:
            verdict = "warn"
    else:
        verdict = "pass"

    return {
        "verdict": verdict,
        "overall_score": score,
        "retrieval": {
            "top_similarity": top_similarity,
            "mean_similarity": mean_similarity,
            "min_similarity_required": thresholds.min_similarity,
            "retrieved_chunks": len(sources),
            "passed": retrieval_pass,
        },
        "grounding": {
            "answer_coverage": answer_coverage,
            "answer_is_not_found": not_found,
            "min_coverage_required": thresholds.min_coverage,
            "passed": grounding_pass,
        },
        "guardrail": {
            "triggered": bool(guardrail and guardrail.get("triggered")),
            "reason": (guardrail or {}).get("reason"),
        },
        "flags": flags,
        "meta": {
            "question_length_chars": len(question or ""),
            "answer_length_chars": len(answer or ""),
        },
    }
