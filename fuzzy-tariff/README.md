# fuzzy-tariff

Two-stage Mamdani fuzzy inference system, multi-device breaker-aware scheduler, linguistic summariser, and React dashboard for Swiss dynamic electricity tariffs (**StromVG 2026**).

It turns 15-minute wholesale prices and local grid stress into continuous suitability scores (`0–100`), plain-language labels, appliance schedules (`start_now` / `wait` / `must_start`), and Yager/Kacprzyk protoform summaries.

## Why
Switzerland allows dynamic grid tariffs since 1 January 2026. People think in words, not in CHF/kWh, and "cheap" depends on season, trend, and local transformer load. Fuzzy logic models that vagueness without threshold chattering and stays explainable rule-by-rule. See [`prd.md`](prd.md) and the top-level [`README.md`](../README.md).

## Quickstart
```bash
python3.12 -m venv .venv && source .venv/bin/activate
make install            # or: pip install -e ".[dev]"
fuzzy-tariff serve --reload
```
Open `http://localhost:8000/` for the web dashboard, or `http://localhost:8000/docs` for the OpenAPI docs.

```bash
fuzzy-tariff demo --P 12 --A 0.30 --G 0.20
```
Output:
```
score = 86.7  ->  Very cheap: best time
  R01  strength=0.80  Very cheap relative to context and cheap in absolute terms
  R02  strength=0.20  ...
```

### CLI
| Command | Purpose |
|---|---|
| `fuzzy-tariff demo` | Score one interval from crisp inputs (`--P`, `--A`, `--G`, `--T`) |
| `fuzzy-tariff simulate-tariff --out data/synthetic/dynamic_tariff.csv` | Generate an EKZ-style 15-minute dynamic tariff for a year |
| `fuzzy-tariff plot-tariff` | Plot example days of the simulated tariff |
| `fuzzy-tariff backtest --scenario dynamic_baseline --component grid` | Compare fuzzy vs. crisp baselines (`dynamic_baseline`, `dynamic_cold_snap`, `dynamic_pv_surplus`, `dynamic_spike`, plus hourly scenarios) |
| `fuzzy-tariff plot-mf` | Plot membership functions (requires `viz` extra) |
| `fuzzy-tariff summarize` | Linguistic summarization of a tariff day |
| `fuzzy-tariff serve` | Run the FastAPI server + built React dashboard |

### API endpoints
| Endpoint | Purpose |
|---|---|
| `GET /` | Built React + Vite dashboard (`api/static/`) |
| `GET /healthz` | Health check |
| `GET /v1/config` | Membership functions, rule base, and labels |
| `GET /v1/tariff/preview` | 2025 benchmark, 2026–27 practice scenarios, or live EKZ day |
| `POST /v1/score` | Stage 1 fuzzy suitability score and fired rules |
| `POST /v1/advice` | Stage 2 appliance action (`start_now`, `wait`, `must_start`) |
| `POST /v1/plan` | Single-day slot planning |
| `POST /v1/smart-schedule` | Multi-device concurrency schedule under household breaker limits |
| `GET /v1/summarize/daily` | Daily linguistic summary and top protoforms |
| `POST /v1/summarize/evaluate` | Evaluate any `Q / B / S` protoform combination |
| `POST /v1/translate` | Multilingual translation (`en`, `de`, `fr`, `it`) |

Example:
```bash
curl -s localhost:8000/v1/score -H 'content-type: application/json' \
  -d '{"P": 12, "A": 0.30, "G": 0.20, "lang": "de"}'
```

### Library example
```python
from fuzzy_tariff.features import build_features
from fuzzy_tariff.labeler import FuzzyLabeler
from fuzzy_tariff.synthetic import generate_year

df = generate_year(2025, "baseline", seed=0)  # price (CHF/kWh), residual_load
labels = FuzzyLabeler.from_config().label(build_features(df))
print(labels["label"].value_counts())
```

## How it works
```
prices + load -> P, A, G, T -> Stage 1 FIS (19 rules) -> score 0–100 -> hysteresis + min block -> label
                                                       -> Stage 2 FIS (6 rules) + urgency -> wait / start_now / must_start
                                                       -> Multi-device breaker scheduler -> 15-min slots
```
Rules and membership functions: [`src/fuzzy_tariff/fuzzy/default.yaml`](src/fuzzy_tariff/fuzzy/default.yaml). Diagrams: [`docs/flow.md`](docs/flow.md). Design: [`architecture.md`](architecture.md).

## Frontend
The dashboard at `/` is a React 19 + Vite + Tailwind 4 app in [`frontend/`](frontend/) with four views (**Scheduler**, **Engine**, **Summary**, **Report**), light/dark themes, and EN/DE/FR/IT i18n. Its production build is committed under `src/fuzzy_tariff/api/static/` so the Python server runs with no Node dependency at runtime. See [`frontend/README.md`](frontend/README.md) for dev server and build commands.

## Repository layout
```
prd.md  architecture.md  CONTRIBUTING.md  Makefile  Dockerfile  pyproject.toml
src/fuzzy_tariff/
  fuzzy/          Stage 1 Mamdani engine, membership functions, default.yaml (19+6 rules), summarizer
  features/       Normalised inputs P, A, G, T
  advisor/        Stage 2 appliance advisor & multi-device breaker scheduler
  ingest/         Adapters for EKZ API (ekz.py), ENTSO-E (entsoe.py), and CSVs
  evaluation/     Crisp baselines, stability metrics, sensitivity, backtesting
  api/            FastAPI app (/v1/*), Pydantic schemas, and built static/ dashboard
  cli.py          `fuzzy-tariff` CLI
  labeler.py · stability.py · labels.py · synthetic.py · tariff_sim.py
frontend/         React + Vite dashboard source
scripts/          fetch_ekz_data.py, log_ekz_tariff.py, generate_practising_data.py
tests/            Pytest suite covering engine, advisor, summarizer, ingest, API, and CLI
docs/             adr/, data-sources.md, flow.md, glossary.md, project.md
```

## Dynamic tariff data
Real Swiss dynamic tariffs only started in 2026:
* **Live EKZ ingestion:** [`src/fuzzy_tariff/ingest/ekz.py`](src/fuzzy_tariff/ingest/ekz.py) fetches live EKZ tariffs (`api.tariffs.ekz.ch`), paired with `scripts/fetch_ekz_data.py` and `scripts/log_ekz_tariff.py`.
* **Simulated 2025 & 2026–27 datasets:** `tariff_sim.py` generates EKZ-style 15-minute tariffs (spot energy + quadratic grid load + daily parity + clipping). Details: [`../dynamic-tariff-model.md`](../dynamic-tariff-model.md).

## Docs
[Root README](../README.md) | [Frontend README](frontend/README.md) | [PRD](prd.md) | [Architecture](architecture.md) | [ADRs](docs/adr) | [Dynamic tariff model](../dynamic-tariff-model.md) | [Data sources](docs/data-sources.md) | [Glossary](docs/glossary.md) | [Project plan](docs/project.md) | [Flow diagrams](docs/flow.md)
