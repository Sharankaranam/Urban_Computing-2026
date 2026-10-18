# ADR-0004: Own NumPy engine instead of scikit-fuzzy

- Status: accepted
- Date: 2026-10-18

## Context
We need vectorised inference over thousands of hours, per-rule firing strengths for explanations, and a tiny dependency surface. scikit-fuzzy is convenient but less transparent about rule strengths and adds a dependency with uneven maintenance.

## Decision
Implement Mamdani inference directly on NumPy (about 100 lines in `fuzzy/engine.py`).

## Alternatives considered
- scikit-fuzzy: fine for prototypes; weaker for batch + explanation use.
- MATLAB Fuzzy Logic Toolbox: excellent, not available to everyone; can be used to cross-check results.

## Consequences
- Full control and easy testing (golden example, batch equals single).
- We own correctness: keep property tests, and cross-check a few points against MATLAB or scikit-fuzzy in a notebook.
