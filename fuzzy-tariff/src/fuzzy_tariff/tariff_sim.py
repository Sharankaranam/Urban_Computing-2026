"""Realistic dynamic-tariff simulator modelled on EKZ's published 2026 method.

Why: Swiss dynamic tariffs only exist since 2026 and there is no public multi-year history.
This module generates 15-minute tariffs with the same STRUCTURE as the real one, so the fuzzy
pipeline can be developed and evaluated now, and later fed with real spot prices and real
grid load (same function, real inputs).

Source of the method: EKZ "Dynamischer Tarif 2026 - Technischer Beschrieb" (28.08.2025) and the
EKZ tariff sheets 2026. Reproduced features:

* 96 steps of 15 min per day, tariff published the evening before (~18:00).
* Two components built with the SAME pattern:
    energy tariff  ~ proportional to the day-ahead spot price curve
    grid tariff    ~ proportional to the SQUARED net-load forecast of the grid, sign preserved
* Each component stays inside a band around its standard tariff
  (energy: standard +/- 5 Rp./kWh; grid: standard -5 / +15 Rp./kWh).
* Price parity: over a day, weighted by a standard load profile, the dynamic tariff has the
  same average as the standard tariff.
* Clipping at the band limits is allowed for at most 2 hours per day on each side.
* Target spread: energy factor 1 (spread follows the spot spread); grid 1 Rp./kWh per (25 MW)^2.

Differences from EKZ (be honest in reports): EKZ solves a mixed-integer program (SCIP); we use
an equivalent heuristic (scale the curve down until the clipping limits hold, solve the offset
for parity). The standard tariff levels, the standard load profile, the spot prices and the
grid load are illustrative stand-ins unless you supply real series.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from fuzzy_tariff.features.reference import LOCAL_TZ, infer_step_hours

Component = Literal["grid", "energy", "total"]
DynamicScenario = Literal["baseline", "cold_snap", "pv_surplus", "spike"]
DYNAMIC_SCENARIOS: tuple[DynamicScenario, ...] = ("baseline", "cold_snap", "pv_surplus", "spike")


@dataclass(frozen=True)
class TariffSpec:
    """Tariff parameters. Levels are ILLUSTRATIVE: take real values from the tariff sheet."""

    std_energy_rp: float = 12.0
    std_grid_rp: float = 10.0
    energy_band_rp: tuple[float, float] = (-5.0, 5.0)  # relative to the standard tariff
    grid_band_rp: tuple[float, float] = (-5.0, 15.0)
    max_clip_hours: float = 2.0
    energy_spread_factor: float = 1.0
    grid_spread_rp_per_mw2: float = 1.0 / 25.0**2
    sdl_rp: float = 0.27  # Swissgrid system services, excl. VAT (EKZ sheet 2026)
    eur_chf: float = 0.93  # approximate; used only to express spot prices in Rp./kWh


def _bump(x: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - centre) / width) ** 2)


def standard_load_weights(local_index: pd.DatetimeIndex) -> np.ndarray:
    """Illustrative standard load profile (stand-in for EKZ's 2024 customer-group profile)."""
    tod = np.asarray(local_index.hour) + np.asarray(local_index.minute) / 60.0
    weekend = np.asarray(local_index.dayofweek >= 5)
    weekday_w = (
        0.55 + 0.30 * _bump(tod, 8, 1.5) + 0.55 * _bump(tod, 19, 2.0) + 0.2 * _bump(tod, 12.5, 2.5)
    )
    weekend_w = 0.60 + 0.20 * _bump(tod, 11, 3.0) + 0.45 * _bump(tod, 19, 2.2)
    return np.where(weekend, weekend_w, weekday_w)


@dataclass(frozen=True)
class FitInfo:
    scale: float
    steps_at_upper: int
    steps_at_lower: int
    spread_rp: float


def _parity_offset(
    curve: np.ndarray, k: float, w: np.ndarray, lo: float, hi: float, std: float
) -> float:
    """Offset b with sum(w * clip(k*curve + b, lo, hi)) == std (w sums to 1)."""
    b_lo = lo - k * float(curve.max()) - 1e-6
    b_hi = hi - k * float(curve.min()) + 1e-6
    for _ in range(50):
        mid = 0.5 * (b_lo + b_hi)
        if float((w * np.clip(k * curve + mid, lo, hi)).sum()) < std:
            b_lo = mid
        else:
            b_hi = mid
    return 0.5 * (b_lo + b_hi)


def fit_day_tariff(
    curve: np.ndarray,
    weights: np.ndarray,
    std: float,
    lo: float,
    hi: float,
    target_spread: float,
    max_clip_steps: int,
) -> tuple[np.ndarray, FitInfo]:
    """Tariff proportional to ``curve``, inside [lo, hi], with price parity and bounded clipping."""
    c = np.asarray(curve, dtype=float)
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    if not lo < std < hi:
        raise ValueError("standard tariff must lie strictly inside the band")
    if float(np.ptp(c)) < 1e-12:
        t = np.full_like(c, std)
        return t, FitInfo(0.0, 0, 0, 0.0)

    def build(k: float) -> np.ndarray:
        b = _parity_offset(c, k, w, lo, hi, std)
        return np.clip(k * c + b, lo, hi)

    def feasible(t: np.ndarray) -> bool:
        return (
            int((t >= hi - 1e-9).sum()) <= max_clip_steps
            and int((t <= lo + 1e-9).sum()) <= max_clip_steps
        )

    k0 = max(target_spread, 0.0) / float(np.ptp(c))
    t = build(k0)
    k = k0
    if not feasible(t):
        k_ok, k_bad = 0.0, k0
        for _ in range(30):
            mid = 0.5 * (k_ok + k_bad)
            if feasible(build(mid)):
                k_ok = mid
            else:
                k_bad = mid
        k = k_ok
        t = build(k)
    info = FitInfo(
        scale=k,
        steps_at_upper=int((t >= hi - 1e-9).sum()),
        steps_at_lower=int((t <= lo + 1e-9).sum()),
        spread_rp=float(np.ptp(t)),
    )
    return t, info


def simulate_dynamic_tariff(
    spot_eur_mwh: pd.Series, net_load_mw: pd.Series, spec: TariffSpec | None = None
) -> pd.DataFrame:
    """Build energy, grid and total dynamic tariffs (Rp./kWh) from spot prices and net load.

    Inputs share one tz-aware index (15-minute is the EKZ resolution). Use REAL series
    (ENTSO-E/EPEX spot, ewz/Swissgrid load scaled to the tariff area's MW) when available.
    """
    spec = spec or TariffSpec()
    if not spot_eur_mwh.index.equals(net_load_mw.index):
        raise ValueError("spot and load must share the same index")
    if spot_eur_mwh.isna().any() or net_load_mw.isna().any():
        raise ValueError("inputs must not contain NaN")
    idx = pd.DatetimeIndex(spot_eur_mwh.index)
    step_hours = infer_step_hours(idx)
    max_clip = max(1, round(spec.max_clip_hours / step_hours))
    local = idx.tz_convert(LOCAL_TZ)
    days = local.normalize()
    weights = standard_load_weights(local)

    spot_rp = spot_eur_mwh.to_numpy(dtype=float) * 0.1 * spec.eur_chf  # EUR/MWh -> Rp./kWh
    load = net_load_mw.to_numpy(dtype=float)
    grid_curve = np.sign(load) * load**2  # squared, sign preserved (EKZ)

    e_lo, e_hi = (spec.std_energy_rp + b for b in spec.energy_band_rp)
    g_lo, g_hi = (spec.std_grid_rp + b for b in spec.grid_band_rp)
    energy = np.empty(len(idx))
    grid = np.empty(len(idx))
    for day in days.unique():
        m = np.asarray(days == day)
        energy[m], _ = fit_day_tariff(
            spot_rp[m],
            weights[m],
            spec.std_energy_rp,
            e_lo,
            e_hi,
            spec.energy_spread_factor * float(np.ptp(spot_rp[m])),
            max_clip,
        )
        grid[m], _ = fit_day_tariff(
            grid_curve[m],
            weights[m],
            spec.std_grid_rp,
            g_lo,
            g_hi,
            spec.grid_spread_rp_per_mw2 * float(np.ptp(grid_curve[m])),
            max_clip,
        )
    out = pd.DataFrame(
        {
            "spot_eur_mwh": spot_eur_mwh.to_numpy(dtype=float),
            "net_load_mw": load,
            "energy_rp": energy,
            "grid_rp": grid,
            "sdl_rp": spec.sdl_rp,
        },
        index=idx,
    )
    out["total_rp"] = out["energy_rp"] + out["grid_rp"] + out["sdl_rp"]
    return out


def to_pipeline_frame(tariff: pd.DataFrame, component: Component = "grid") -> pd.DataFrame:
    """Add the columns the fuzzy pipeline expects: ``price`` (CHF/kWh) and ``residual_load``."""
    col = {"grid": "grid_rp", "energy": "energy_rp", "total": "total_rp"}[component]
    out = tariff.copy()
    out["price"] = out[col] / 100.0
    out["residual_load"] = out["net_load_mw"]
    return out


def scale_load_to_mean_mw(load: pd.Series, mean_mw: float = 150.0) -> pd.Series:
    """Rescale a real load series (e.g. ewz city load) to the MW range of a tariff area."""
    return load * (mean_mw / float(load.mean()))


def generate_spot_and_load(
    year: int = 2025, seed: int = 0, scenario: DynamicScenario = "baseline"
) -> tuple[pd.Series, pd.Series]:
    """Synthetic Swiss-like day-ahead spot (EUR/MWh, hourly steps) and net load (MW, 15 min)."""
    if scenario not in DYNAMIC_SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}")
    rng = np.random.default_rng(seed)
    idx = pd.date_range(
        f"{year}-01-01", f"{year + 1}-01-01", freq="15min", inclusive="left", tz="UTC"
    )
    local = idx.tz_convert(LOCAL_TZ)
    hour = np.asarray(local.hour) + np.asarray(local.minute) / 60.0
    doy = np.asarray(local.dayofyear)
    weekend = np.asarray(local.dayofweek >= 5)
    winter = 0.5 * (1 + np.cos(2 * np.pi * (doy - 15) / 365))
    summer = 1.0 - winter

    day_codes, day_pos = np.unique(np.asarray(local.normalize().asi8), return_inverse=True)
    cloud = rng.uniform(0.25, 1.0, len(day_codes))[day_pos]

    load_boost = 1.25 if scenario == "cold_snap" else 1.0
    load = (
        150
        + 25 * winter
        + 30 * _bump(hour, 8, 1.2)
        + 55 * (0.6 + 0.8 * winter) * _bump(hour, 19, 1.8)
    )
    load = load - 30 * _bump(hour, 3, 2.5) - 10 * weekend
    load = load * np.where(winter > 0.7, load_boost, 1.0)
    noise = pd.Series(rng.normal(0, 3.0, len(idx))).ewm(alpha=0.1).mean().to_numpy() * 2.5
    solar_cap = 110.0 * (1.6 if scenario == "pv_surplus" else 1.0)
    solar = solar_cap * summer * cloud * _bump(hour, 13, 2.8)
    net = load + noise - solar

    hourly = pd.Series(net, index=idx).resample("1h").mean()
    z = (hourly - hourly.mean()) / hourly.std()
    h_local = hourly.index.tz_convert(LOCAL_TZ)
    h_winter = 0.5 * (1 + np.cos(2 * np.pi * (np.asarray(h_local.dayofyear) - 15) / 365))
    spot = 70 + 35 * h_winter + 28 * z.to_numpy() + rng.normal(0, 6.0, len(hourly))
    if scenario == "cold_snap":
        spot = spot + np.where(h_winter > 0.7, 40.0, 0.0)
    if scenario == "spike":
        h_doy = np.asarray(h_local.dayofyear)
        h_hour = np.asarray(h_local.hour)
        days = rng.choice(np.unique(h_doy), size=6, replace=False)
        spot = spot + np.isin(h_doy, days) * ((h_hour >= 18) & (h_hour < 21)) * 180.0
    surplus = (hourly.to_numpy() < 25) & np.asarray(h_local.dayofweek >= 5)
    spot = np.where(surplus, -5 - rng.exponential(15, len(hourly)), spot)
    spot = np.clip(spot, -60, 500)

    spot_15 = pd.Series(spot, index=hourly.index).reindex(idx, method="ffill")
    return spot_15.rename("spot_eur_mwh"), pd.Series(net, index=idx, name="net_load_mw")


def generate_dynamic_year(
    year: int = 2025,
    seed: int = 0,
    scenario: DynamicScenario = "baseline",
    spec: TariffSpec | None = None,
    component: Component = "grid",
) -> pd.DataFrame:
    """One year of EKZ-style 15-minute dynamic tariffs, ready for the fuzzy pipeline."""
    spot, load = generate_spot_and_load(year, seed, scenario)
    tariff = simulate_dynamic_tariff(spot, load, spec)
    return to_pipeline_frame(tariff, component)
