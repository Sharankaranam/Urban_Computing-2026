# AGENTS.md: ingestion

Scope: everything that talks to the outside world.

- **Only** this package may import `httpx` or know a vendor file layout.
- Adapters implement the ports in `base.py` and return **UTC-indexed pandas Series** with documented units.
- Never guess a schema. Before implementing an adapter, read the official documentation and record the URL, date read and any assumptions in `docs/data-sources.md`.
- Store raw responses unmodified in `data/raw/`. Parse separately so parsing can be re-run.
- Tests use recorded fixtures or `httpx.MockTransport`. No live network in tests.
- Token handling: read from `Settings`, never log tokens, never commit them.
- Handle: gaps, duplicated timestamps, DST changes, 15-minute vs hourly resolution, negative prices.
- Known TODO: `ekz.py` and `scripts/log_ekz_tariff.py` are skeletons. Implement only after reading the EKZ API documentation.
