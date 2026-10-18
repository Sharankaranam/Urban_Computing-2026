"""Context-aware features.

P  relative price   percentile of the price within its reference window (0-100)
A  absolute price   price normalised to an annual min-max range (0-1)
G  grid stress      percentile of residual load within its reference window (0-1)
T  price trend      expected change over the next steps, scaled to [-1, 1]

Reference window (default): the previous ``window_days`` calendar days of the SAME day type
(weekday vs weekend) plus the whole day being labelled. Including the labelled day is not
leakage because day-ahead tariffs are published before the day starts (EKZ: from 18:00).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LOCAL_TZ = "Europe/Zurich"


def infer_step_hours(index: pd.DatetimeIndex) -> float:
    """Median spacing of a time index in hours (1.0 for hourly, 0.25 for 15-minute data)."""
    diffs = pd.Series(index).diff().dropna()
    if diffs.empty:
        raise ValueError("need at least two timestamps")
    return float(diffs.median().total_seconds() / 3600.0)


def _local_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if index.tz is None:
        raise ValueError("index must be timezone-aware (UTC or Europe/Zurich)")
    return index.tz_convert(LOCAL_TZ)


def rolling_percentile(
    values: pd.Series,
    window_days: int = 30,
    same_day_type: bool = True,
    min_samples: int = 24,
    min_spread: float = 0.0,
) -> pd.Series:
    """Percentile rank (0-100, mid-rank for ties) of each value in its reference window.

    ``min_spread``: if the interquartile range of the window is below this value the
    distribution carries no information (e.g. a flat tariff) and 50 is returned, so a
    flat price can never produce a spurious "cheap" or "expensive" label.
    """
    local = _local_index(pd.DatetimeIndex(values.index))
    days = local.normalize()
    weekend = np.asarray(local.dayofweek >= 5)
    v = values.to_numpy(dtype=float)
    finite = ~np.isnan(v)
    out = np.full(len(v), np.nan)

    for day in days.unique():
        day_mask = np.asarray(days == day)
        start = day - pd.DateOffset(days=window_days)
        win = np.asarray((days >= start) & (days <= day)) & finite
        if same_day_type:
            win &= weekend == weekend[day_mask][0]
        w = np.sort(v[win])
        if len(w) < min_samples:
            continue
        if min_spread > 0 and (np.quantile(w, 0.75) - np.quantile(w, 0.25)) < min_spread:
            out[day_mask] = 50.0
            continue
        x = v[day_mask]
        lo = np.searchsorted(w, x, side="left")
        hi = np.searchsorted(w, x, side="right")
        out[day_mask] = 100.0 * (lo + hi) / 2.0 / len(w)
    return pd.Series(out, index=values.index, name=f"{values.name}_pct")


def normalize_price(
    price: pd.Series, lo: float | None = None, hi: float | None = None, min_range: float = 0.02
) -> pd.Series:
    """Scale price to [0, 1]. Defaults to the 1st-99th percentile of the series.

    If the range is narrower than ``min_range`` (CHF/kWh) the tariff is effectively flat and
    returning a stretched 0..1 signal would amplify noise, so a neutral 0.5 is returned.
    """
    lo = float(price.quantile(0.01)) if lo is None else lo
    hi = float(price.quantile(0.99)) if hi is None else hi
    if hi - lo < min_range:
        return pd.Series(0.5, index=price.index, name="A")
    return ((price - lo) / (hi - lo)).clip(0.0, 1.0).rename("A")


def price_trend(price: pd.Series, horizon_steps: int = 2, min_scale: float = 0.005) -> pd.Series:
    """Mean of the next ``horizon_steps`` values minus now, scaled by price std, in [-1, 1].

    ``min_scale`` (CHF/kWh) floors the scale so noise on a flat tariff is not amplified.
    """
    future = pd.concat([price.shift(-k) for k in range(1, horizon_steps + 1)], axis=1).mean(axis=1)
    std = float(price.std())
    scale = max(std, min_scale) if np.isfinite(std) else min_scale
    return ((future - price) / scale).clip(-1.0, 1.0).fillna(0.0).rename("T")


def build_features(
    df: pd.DataFrame,
    window_days: int = 30,
    price_col: str = "price",
    load_col: str = "residual_load",
    price_range: tuple[float, float] | None = None,
    min_spread: float = 0.005,
    horizon_steps: int = 2,
) -> pd.DataFrame:
    """Compute P, A, G, T for a time-indexed frame with a price (CHF/kWh) column."""
    price = df[price_col].astype(float)
    lo, hi = price_range if price_range else (None, None)
    feats = pd.DataFrame(index=df.index)
    feats["P"] = rolling_percentile(price, window_days=window_days, min_spread=min_spread)
    feats["A"] = normalize_price(price, lo, hi)
    if load_col in df.columns:
        feats["G"] = rolling_percentile(df[load_col].astype(float), window_days=window_days) / 100.0
    else:
        feats["G"] = 0.5
    feats["T"] = price_trend(price, horizon_steps=horizon_steps)
    return feats
