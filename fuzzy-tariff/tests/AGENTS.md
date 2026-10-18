# AGENTS.md: tests

- Use pytest. Session-scoped fixtures in `conftest.py` build engines and the synthetic year once.
- The golden example (`test_worked_example_from_docs`) mirrors `docs/flow.md` section 5. If it changes, update the docs.
- Prefer behaviour assertions (monotonicity, guardrails, completeness, no flicker) over brittle exact floats; use `pytest.approx` with a stated tolerance.
- Edge cases to keep covered: flat tariff, DST, NaN, missing inputs, omitted ENTSO-E points, impossible deadlines.
- No network. No writing outside `tmp_path`.
- Never delete or weaken a test to get green; explain and fix the cause.
