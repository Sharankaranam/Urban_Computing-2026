# AGENTS.md: fuzzy core

Scope: `membership.py`, `variables.py`, `rules.py`, `engine.py`, `config.py`, `default.yaml`.

- This package must stay **pure**: only numpy, pydantic, yaml, stdlib. No pandas, no httpx, no FastAPI, no imports from other project packages (except within `fuzzy/`).
- `MamdaniFIS` semantics are fixed: min for AND, min implication, max aggregation, centroid. Changing them needs an ADR (see 0001).
- Shoulders: a membership function with `a == b` or `c == d` is a vertical edge and must give 1.0 at the edge. Keep the property tests green.
- `default.yaml` changes follow the rules in the root `AGENTS.md`: golden test, completeness test, docs, ADR.
- Inference must remain vectorised (`infer_many`). `infer` is a convenience wrapper; do not add per-row Python loops in hot paths.
- When adding a new engine (Sugeno, type-2), keep the same `infer` / `infer_many` interface so `labeler.py` and `evaluation/` can swap it.
- Always return explanations: fired rules with strengths.
