# AGENTS.md: API

Scope: `main.py`, `schemas.py`.

- The API is a thin layer: validate, call services, serialise. No fuzzy logic here.
- Schemas are a public contract under `/v1`. Additive changes only; breaking changes need `/v2` and approval.
- Every inference response includes `fired_rules` (explainability requirement NFR-4).
- Use `Depends(get_services)`; tests may override dependencies.
- Validate ranges with pydantic `Field(ge=, le=)`; cap list lengths.
- Errors: 422 for bad input, 500 only for internal invariants (e.g. rule-base gap) with a clear message.
- Add a test in `tests/test_api.py` for every new endpoint, including an error path.
