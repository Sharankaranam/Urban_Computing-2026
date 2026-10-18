# Contributing

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
make install
make check
```

## Workflow
1. Branch from `main`: `feat/...`, `fix/...`, `docs/...`, `exp/...` (experiments).
2. Keep PRs small and focused; one behavioural change per PR.
3. Use Conventional Commits: `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `refactor: ...`, `chore: ...`.
4. Run `make check` before pushing. CI runs ruff, mypy, pytest (3.11, 3.12), a backtest smoke test and a Docker build.
5. Request review; address comments with new commits, squash on merge.

## Changing fuzzy behaviour
Edits to `src/fuzzy_tariff/fuzzy/default.yaml` need: tests (golden, completeness, guardrail), updated docs/PRD, and an ADR if the rationale changes. Attach a backtest comparison (fuzzy vs baselines) and a sensitivity result to the PR.

## Pull request checklist
- [ ] `make check` passes
- [ ] Tests include an edge case
- [ ] Docs / ADR updated
- [ ] No secrets or real personal data
- [ ] Synthetic results are labelled as synthetic

## Data
Never commit files under `data/` or `reports/` (git-ignored). Never commit tokens.
