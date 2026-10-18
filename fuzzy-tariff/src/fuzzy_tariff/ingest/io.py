"""Generic time-series CSV loader used by file-based adapters (Swissgrid, MeteoSwiss, utilities).

We deliberately avoid hard-coding vendor file layouts here: column names and formats are
parameters, and vendor specifics are verified against current documentation in docs/data-sources.md.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_timeseries_csv(
    path: str | Path,
    timestamp_col: str,
    value_col: str,
    sep: str = ",",
    timestamp_format: str | None = None,
    source_tz: str = "UTC",
) -> pd.Series:
    """Read one value column into a UTC-indexed, sorted, de-duplicated Series."""
    raw = pd.read_csv(path, sep=sep, usecols=[timestamp_col, value_col])
    ts = pd.to_datetime(raw[timestamp_col], format=timestamp_format)
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(source_tz, ambiguous="infer", nonexistent="shift_forward")
    series = pd.Series(raw[value_col].to_numpy(dtype=float), index=pd.DatetimeIndex(ts))
    series.index = series.index.tz_convert("UTC")
    series = series[~series.index.duplicated(keep="last")].sort_index()
    series.name = value_col
    return series
