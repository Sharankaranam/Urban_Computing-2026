# fuzzy-tariff

Fuzzy-logic guidance for Swiss dynamic electricity tariffs. It turns hourly prices into plain-language, context-aware labels ("very cheap: best time") and device advice ("start the car now") with a fully explainable Mamdani fuzzy inference system.

> Status: v0.1 scaffold. Engine, API, evaluation and tests work. Parameters are uncalibrated starting values; results so far use **synthetic** data only.

## Why
Switzerland allows dynamic grid tariffs since 1 January 2026. People think in words, not in CHF/kWh, and "cheap" depends on season and context. Fuzzy logic models that vagueness and stays explainable. See [`prd.md`](prd.md).

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
make install            # or: pip install -e ".[dev]"
make check              # ruff + mypy + pytest
fuzzy-tariff demo --P 12 --A 0.30 --G 0.20
```
Output:
```
score = 86.7  ->  Very cheap: best time
  R01  strength=0.80  Very cheap relative to context and cheap in absolute terms
  R02  strength=0.20  ...
  R05  strength=0.13  ...
```

### CLI
| Command | Purpose |
|---|---|
| `fuzzy-tariff demo` | score one hour from crisp inputs |
| `fuzzy-tariff simulate-tariff --out data/synthetic/dynamic_tariff.csv` | EKZ-style 15-minute dynamic tariff for a year (energy, grid, total) |
| `fuzzy-tariff plot-tariff` | figure of example days of the simulated tariff |
| `fuzzy-tariff backtest --scenario dynamic_baseline --component grid` | fuzzy vs crisp baselines on the 15-min dynamic tariff (`dynamic_baseline`, `dynamic_cold_snap`, `dynamic_pv_surplus`, `dynamic_spike`; toy hourly scenarios `baseline`, `flat`, ... also exist) |
| `fuzzy-tariff plot-mf` | membership-function figure |
| `fuzzy-tariff serve` | HTTP API, docs at `/docs` |

### API example
```bash
curl -s localhost:8000/v1/score -H 'content-type: application/json' \
  -d '{"P": 12, "A": 0.30, "G": 0.20, "lang": "de"}'
```

### Library example
```python
import pandas as pd
from fuzzy_tariff.features import build_features
from fuzzy_tariff.labeler import FuzzyLabeler
from fuzzy_tariff.synthetic import generate_year

df = generate_year(2025, "baseline", seed=0)  # price (CHF/kWh), residual_load
labels = FuzzyLabeler.from_config().label(build_features(df))
print(labels["label"].value_counts())
```

## How it works
```
prices + load -> P, A, G, T -> Stage 1 FIS (15 rules) -> score 0-100 -> hysteresis + min block -> label
                                                       -> Stage 2 FIS (6 rules) with urgency -> wait / start_now / must_start
```
Rules and membership functions: [`src/fuzzy_tariff/fuzzy/default.yaml`](src/fuzzy_tariff/fuzzy/default.yaml). Diagrams: [`docs/flow.md`](docs/flow.md). Design: [`architecture.md`](architecture.md).

## Repository layout
```
prd.md  architecture.md  AGENTS.md  CLAUDE.md  CONTRIBUTING.md
src/fuzzy_tariff/   fuzzy/ features/ advisor/ evaluation/ ingest/ api/ + labeler, stability, labels, synthetic, tariff_sim, cli
tests/              ~85 tests, ~90% coverage
docs/               adr/ data-sources.md glossary.md project.md flow.md
.claude/agents/     fuzzy-engineer, data-engineer, test-engineer, reviewer
.github/workflows/  CI (lint, types, tests on 3.11/3.12, backtest smoke, docker build)
scripts/ data/ reports/ notebooks/
```

## Dynamic tariff data
Real Swiss dynamic tariffs only exist since 2026 and have no public history, so `tariff_sim.py` generates **EKZ-style** tariffs: 15-minute steps, energy part from the spot price, grid part from the squared net load, bands around the standard tariff, daily price parity, at most 2 h clipping per side. It accepts real spot prices and real grid load as drop-in inputs. Details and limitations: [`docs/dynamic-tariff-model.md`](docs/dynamic-tariff-model.md).

## Current evidence (simulated tariff only)
`dynamic_baseline`, grid component, 2025, seed 0 (`make backtest`):

| method | flips/day | isolated cheap windows | EV saving vs naive |
|---|---|---|---|
| fixed CHF thresholds | 14.00 | 0.00 | 59.2% |
| percentile bands | 13.18 | 0.03 | 59.2% |
| fuzzy | 4.90 | 0.00 | 59.0% |

Read this as a plumbing check: the fuzzy labeller flips about 2.7x less often and picks hours about as well as the baselines. "Naive" charges on arrival at 18:00, which is the evening peak, so the saving figure is large and says little about method quality; the metric cannot separate methods that rank by price. Real data and a user study are required for any claim.

## Next steps
1. Implement the EKZ adapter after reading its API docs and run the daily logger; replace the illustrative standard tariff levels with the sheet values.
2. Pull ENTSO-E history; calibrate sets; expert rule review.
3. PWA with timeline; usability tests; pilot.

## Docs
[PRD](prd.md) | [Architecture](architecture.md) | [Agents guide](AGENTS.md) | [ADRs](docs/adr) | [Dynamic tariff model](docs/dynamic-tariff-model.md) | [Data sources](docs/data-sources.md) | [Glossary](docs/glossary.md) | [Project plan](docs/project.md) | [Flow diagrams](docs/flow.md)

License: to be chosen by the project owner.
