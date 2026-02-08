from __future__ import annotations


def evaluate_session(turn_evals: list[dict]) -> dict:
    if not turn_evals:
        return {
            "session_verdict": "warn",
            "session_score": 0.0,
            "turn_count": 0,
            "pass_count": 0,
            "warn_count": 0,
            "fail_count": 0,
            "avg_overall_score": 0.0,
            "avg_retrieval_top_similarity": 0.0,
            "avg_answer_coverage": 0.0,
            "flags": ["empty_session"],
        }

    pass_count = sum(1 for t in turn_evals if t.get("verdict") == "pass")
    warn_count = sum(1 for t in turn_evals if t.get("verdict") == "warn")
    fail_count = sum(1 for t in turn_evals if t.get("verdict") == "fail")

    avg_score = sum(float(t.get("overall_score", 0.0)) for t in turn_evals) / len(turn_evals)
    avg_top_similarity = (
        sum(float(t.get("retrieval", {}).get("top_similarity", 0.0)) for t in turn_evals) / len(turn_evals)
    )
    avg_coverage = (
        sum(float(t.get("grounding", {}).get("answer_coverage", 0.0)) for t in turn_evals) / len(turn_evals)
    )

    flag_set: set[str] = set()
    for turn in turn_evals:
        for flag in turn.get("flags", []):
            flag_set.add(str(flag))

    if fail_count > 0:
        session_verdict = "fail"
    elif warn_count > 0:
        session_verdict = "warn"
    else:
        session_verdict = "pass"

    return {
        "session_verdict": session_verdict,
        "session_score": round(avg_score, 4),
        "turn_count": len(turn_evals),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "avg_overall_score": round(avg_score, 4),
        "avg_retrieval_top_similarity": round(avg_top_similarity, 4),
        "avg_answer_coverage": round(avg_coverage, 4),
        "flags": sorted(flag_set),
    }
