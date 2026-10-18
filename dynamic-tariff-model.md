# Dynamic tariff model (EKZ-style simulator)

The project is about **dynamic tariffs**. Real Swiss dynamic tariffs only exist since 2026 and there is no public multi-year history, so we generate data that has the same structure as the real thing and keep the code ready to accept real inputs.

Implementation: `src/fuzzy_tariff/tariff_sim.py`. Decision record: `docs/adr/0007-ekz-style-tariff-simulator.md`.

## What the real tariff looks like (EKZ, 2026)

From EKZ's "Dynamischer Tarif 2026 - Technischer Beschrieb" (28.08.2025) and the 2026 tariff sheets:

| Aspect | EKZ design |
|---|---|
| Resolution | 15 minutes, 96 steps per day |
| Publication | day before, from about 18:00, via web API (https://api.tariffs.ekz.ch/) |
| Components | dynamic **energy** tariff and dynamic **grid-use** tariff, built with the same pattern |
| Energy curve | proportional to the day-ahead spot price (Switzerland) |
| Grid curve | proportional to the **squared** net-load forecast of the grid (level 7), sign preserved |
| Bands | energy: standard tariff ±5 Rp./kWh; grid: standard −5 / +15 Rp./kWh |
| Price parity | for the standard load profile the dynamic tariff has the same average as the standard tariff |
| Clipping | at the band limits for at most 2 hours per day |
| Target spread | energy: spot spread (factor 1); grid: 1 Rp./kWh per (25 MW)² |
| Other | EKZ solves a mixed-integer program (SCIP); SDL (Swissgrid) 0.27 Rp./kWh excl. VAT in 2026; fallback to standard tariff if the API is unavailable by midnight |

## What our simulator does

1. **Inputs** (same index, tz-aware): day-ahead spot price (EUR/MWh) and net load (MW).
2. **Curves:** energy curve = spot in Rp./kWh; grid curve = sign(load) · load².
3. **Per local day:** find a scale `k` and offset `b` so that `tariff = clip(k · curve + b, lo, hi)` satisfies price parity with the standard tariff (weighted by a standard load profile) and has at most 2 h at each limit; the largest feasible `k` up to the target spread wins.
4. **Outputs:** `energy_rp`, `grid_rp`, `sdl_rp`, `total_rp` (Rp./kWh) per step; `to_pipeline_frame` turns the chosen component into `price` (CHF/kWh) and `residual_load` for the fuzzy pipeline.

Default component for the fuzzy system is **grid** (the 2026 regulation allows dynamic grid tariffs first); `energy` and `total` are available (`--component`).

## Synthetic inputs (until real series are plugged in)

`generate_spot_and_load(year, seed, scenario)` creates a Swiss-like year:
- net load (MW): winter premium, morning and evening peaks, weekend dip, solar subtraction with random cloudiness per day
- spot (EUR/MWh): winter premium, driven by net load, noise, negative prices on sunny weekends
- scenarios: `baseline`, `cold_snap`, `pv_surplus`, `spike`

## Replace synthetic with real data

The same function works with real series:

```python
from fuzzy_tariff.ingest.entsoe import EntsoeClient  # spot, EUR/MWh
from fuzzy_tariff.ingest.io import read_timeseries_csv  # e.g. ewz city load
from fuzzy_tariff.tariff_sim import scale_load_to_mean_mw, simulate_dynamic_tariff

spot = ...  # tz-aware UTC Series, resample to 15 min with ffill if hourly
load = scale_load_to_mean_mw(read_timeseries_csv(path, ts_col, value_col), mean_mw=150)
tariff = simulate_dynamic_tariff(spot, load.reindex(spot.index).interpolate())
```

Candidate real inputs: ENTSO-E day-ahead prices; ewz gross load curve of the City of Zurich (15 min, since 2019) or Swissgrid load. See `docs/data-sources.md`.

## Validation done (tests)

`tests/test_tariff_sim.py`: bands respected, daily parity with the standard tariff to 1e-3 Rp., at most 8 clipped steps (2 h) per side, grid tariff correlates with net load, DST days (92/100 steps), determinism, 35040 steps for a year.

## Honest limitations

- Standard tariff levels (12 and 10 Rp./kWh) and the standard load profile are **illustrative**: the numbers on the EKZ sheet were not machine-readable here. Replace them with the real sheet values (`TariffSpec`).
- Heuristic instead of EKZ's mixed-integer optimisation; results are similar in structure, not identical.
- Synthetic spot and load are plausible shapes, not forecasts of the real market.
- Parity is on a standard profile, not on any real household.
- Findings from simulated tariffs are method checks, not evidence about real households.
