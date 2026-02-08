# UltraDoc Evals

This folder contains standalone evaluation logic for UltraDoc chat sessions.

## Goals
- Score each Q&A turn for retrieval quality and grounding.
- Emit a stable payload that frontend can render per turn.
- Aggregate turn metrics into a session summary.

## Files
- `evals/turn_eval.py`: Turn-level evaluator and payload schema.
- `evals/session_eval.py`: Session-level rollups across turns.
- `evals/example_payloads.json`: Example objects for frontend wiring.

## Turn Eval Output Contract
Each evaluated turn returns:
- `verdict`: `pass | warn | fail`
- `overall_score`: float `0..1`
- `retrieval`: top similarity, average similarity, thresholds, pass/fail
- `grounding`: lexical answer coverage and pass/fail
- `guardrail`: triggered flag and reason
- `flags`: list of warning/error flags

## Session Eval Output Contract
Session output includes:
- `session_verdict`
- `session_score`
- counts (`turn_count`, `pass_count`, `warn_count`, `fail_count`)
- averaged metrics (`avg_overall_score`, `avg_retrieval_top_similarity`, `avg_answer_coverage`)
- collected `flags`

## Notes
- This is heuristic scoring for a POC and should be calibrated with real docs.
- The evaluator is deterministic and does not call an LLM.
