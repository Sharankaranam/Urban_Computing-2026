"""Synthetic hourly tariff scenarios for tests, demos and edge-case evaluation.

These are NOT real tariffs. They mimic qualitative features (evening peaks, solar midday dip,
winter premium, price tied to squared residual load as in EKZ's 2026 design) so the
pipeline can be exercised before real dynamic-tariff history exists.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

Scenario = Literal["baseline", "winter_evening_peak", "solar_midday_dip", "flat", "spike"]
SCENARIOS: tuple[Scenario, ...] = (
    "baseline",
    "winter_evening_peak",
    "solar_midday_dip",
    "flat",
    "spike",
)


def _bump(hour: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((hour - centre) / width) ** 2)


def generate_year(year: int = 2025, scenario: Scenario = "baseline", seed: int = 0) -> pd.DataFrame:
    """Hourly UTC-indexed frame with ``price`` (CHF/kWh) and ``residual_load`` (GW, arbitrary)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}")
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", inclusive="left", tz="UTC")
    local = idx.tz_convert("Europe/Zurich")
    hour = np.asarray(local.hour) + np.asarray(local.minute) / 60.0
    doy = np.asarray(local.dayofyear)
    weekend = np.asarray(local.dayofweek >= 5)
    winter = 0.5 * (1 + np.cos(2 * np.pi * (doy - 15) / 365))  # 1 in January, 0 in July
    summer = 1.0 - winter

    evening_amp = 1.8 * (2.0 if scenario == "winter_evening_peak" else 1.0)
    evening = evening_amp * (0.6 + 0.8 * winter) * _bump(hour, 19, 1.8)
    morning = 1.0 * _bump(hour, 8, 1.2)
    night = -0.9 * _bump(hour, 3, 2.5)
    load = 6.5 + 1.2 * winter + morning + evening + night - 0.4 * weekend
    load = load + rng.normal(0, 0.08, len(idx))

    solar_cap = 3.0 * (2.0 if scenario == "solar_midday_dip" else 1.0)
    solar = solar_cap * summer * _bump(hour, 13, 2.8)
    residual = load - solar

    price = 0.06 + 0.05 * (residual / 6.5) ** 2 + rng.normal(0, 0.003, len(idx))
    if scenario == "flat":
        price = 0.11 + rng.normal(0, 0.0005, len(idx))
    if scenario == "spike":
        days = rng.choice(np.unique(doy), size=6, replace=False)
        spike = np.isin(doy, days) & (hour >= 18) & (hour < 21)
        price = price + spike * 0.25
    price = np.clip(price, 0.0, None)
    return pd.DataFrame({"price": price, "residual_load": residual}, index=idx)
