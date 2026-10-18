"""Metrics for comparing labellers: stability, seasonal consistency, flexible-load cost."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fuzzy_tariff.features.reference import LOCAL_TZ
from fuzzy_tariff.labels import Label

_CHEAP = {Label.GOOD.value, Label.IDEAL.value}
_SEASONS = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}


def flips_per_day(labels: pd.Series) -> float:
    """Average number of label changes per local calendar day."""
    lab = labels.dropna()
    changes = (lab != lab.shift()).iloc[1:]
    days = lab.index.tz_convert(LOCAL_TZ).normalize().nunique()
    return float(changes.sum() / max(days, 1))


def isolated_window_rate(labels: pd.Series) -> float:
    """Share of 'cheap' windows (good/ideal runs) that last a single step."""
    cheap = labels.isin(_CHEAP).to_numpy()
    if not cheap.any():
        return 0.0
    starts = np.flatnonzero(cheap & ~np.r_[False, cheap[:-1]])
    ends = np.flatnonzero(cheap & ~np.r_[cheap[1:], False])
    lengths = ends - starts + 1
    return float((lengths == 1).mean())


def label_distribution_by_season(labels: pd.Series) -> pd.DataFrame:
    """Row-normalised label shares per meteorological season."""
    lab = labels.dropna()
    season = pd.Series(lab.index.tz_convert(LOCAL_TZ).month.map(_SEASONS), index=lab.index)
    table = pd.crosstab(season, lab, normalize="index")
    return table.reindex(columns=[x.value for x in Label], fill_value=0.0)


def _evening_windows(df: pd.DataFrame, start_hour: int = 18, span_hours: int = 13) -> pd.Series:
    local = df.index.tz_convert(LOCAL_TZ)
    offset = (local.hour - start_hour) % 24
    in_window = offset < span_hours
    key = (local - pd.Timedelta(hours=start_hour)).normalize()
    return pd.Series(np.where(in_window, key.astype("int64"), -1), index=df.index)


def flexible_load_cost(
    df: pd.DataFrame,
    score_col: str,
    hours_needed: float = 4.0,
    power_kw: float = 7.4,
    price_col: str = "price",
    step_hours: float = 1.0,
) -> dict[str, float]:
    """Overnight EV-charging simulation (arrive 18:00, leave 07:00, charge ``hours_needed``).

    guided : charge in the hours with the highest score (ties -> earliest)
    naive  : start charging on arrival
    oracle : the cheapest hours by actual price (lower bound)
    Returns mean cost per night in CHF and relative savings.
    """
    n_slots = max(1, round(hours_needed / step_hours))
    key = _evening_windows(df)
    guided, naive, oracle = [], [], []
    for k, g in df.groupby(key):
        if k == -1 or len(g) < n_slots + 1 or g[score_col].isna().any():
            continue
        price = g[price_col].to_numpy()
        score = g[score_col].to_numpy()
        order = sorted(range(len(g)), key=lambda i: (-score[i], i))[:n_slots]
        guided.append(price[order].sum() * power_kw * step_hours)
        naive.append(price[:n_slots].sum() * power_kw * step_hours)
        oracle.append(np.sort(price)[:n_slots].sum() * power_kw * step_hours)
    if not guided:
        return {
            "nights": 0,
            "guided_chf": np.nan,
            "naive_chf": np.nan,
            "oracle_chf": np.nan,
            "saving_vs_naive_pct": np.nan,
            "gap_to_oracle_pct": np.nan,
        }
    g_, n_, o_ = (float(np.mean(x)) for x in (guided, naive, oracle))
    return {
        "nights": float(len(guided)),
        "guided_chf": g_,
        "naive_chf": n_,
        "oracle_chf": o_,
        "saving_vs_naive_pct": 100 * (n_ - g_) / n_ if n_ else np.nan,
        "gap_to_oracle_pct": 100 * (g_ - o_) / o_ if o_ else np.nan,
    }
