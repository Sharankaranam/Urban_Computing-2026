"""Backtest runner: fuzzy labeller vs crisp baselines on one price series."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fuzzy_tariff.evaluation.baselines import fixed_threshold_labels, percentile_band_labels
from fuzzy_tariff.evaluation.metrics import (
    flexible_load_cost,
    flips_per_day,
    isolated_window_rate,
    label_distribution_by_season,
)
from fuzzy_tariff.features.reference import build_features, infer_step_hours
from fuzzy_tariff.fuzzy.config import FuzzyConfig, load_config
from fuzzy_tariff.labeler import FuzzyLabeler


@dataclass
class BacktestResult:
    features: pd.DataFrame
    labels: pd.DataFrame  # one column per method
    scores: pd.Series  # fuzzy score
    summary: pd.DataFrame  # one row per method
    season_distribution: dict[str, pd.DataFrame]


def run_backtest(
    df: pd.DataFrame,
    cfg: FuzzyConfig | None = None,
    window_days: int = 30,
    fixed_thresholds: tuple[float, float, float, float] | None = None,
    min_block_hours: float = 2.0,
    trend_horizon_hours: float = 2.0,
) -> BacktestResult:
    """Compare methods. Works for hourly and 15-minute data: time-based parameters are given
    in hours and converted to steps using the spacing of the index."""
    cfg = cfg or load_config()
    step = infer_step_hours(pd.DatetimeIndex(df.index))
    feats = build_features(
        df, window_days=window_days, horizon_steps=max(1, round(trend_horizon_hours / step))
    )
    labeler = FuzzyLabeler.from_config(cfg, min_block=max(1, round(min_block_hours / step)))
    fuzzy = labeler.label(feats)
    fixed = (
        fixed_threshold_labels(df["price"], fixed_thresholds)
        if fixed_thresholds
        else (fixed_threshold_labels(df["price"]))
    )
    labels = pd.DataFrame(
        {
            "fixed_threshold": fixed,
            "percentile_bands": percentile_band_labels(feats["P"]),
            "fuzzy": fuzzy["label"],
        }
    )
    # Score used to rank hours for the charging simulation: higher = better time to charge.
    ranking = pd.DataFrame(
        {
            "fixed_threshold": -df["price"],
            "percentile_bands": -feats["P"],
            "fuzzy": fuzzy["score"],
        }
    )
    valid = feats["P"].notna()
    rows = []
    for method in labels.columns:
        lab = labels.loc[valid, method]
        sim_df = df.loc[valid].assign(_rank=ranking.loc[valid, method])
        cost = flexible_load_cost(sim_df, "_rank", step_hours=step)
        rows.append(
            {
                "method": method,
                "flips_per_day": flips_per_day(lab),
                "isolated_cheap_window_rate": isolated_window_rate(lab),
                "ev_saving_vs_naive_pct": cost["saving_vs_naive_pct"],
                "ev_gap_to_oracle_pct": cost["gap_to_oracle_pct"],
            }
        )
    season = {m: label_distribution_by_season(labels.loc[valid, m]) for m in labels.columns}
    return BacktestResult(feats, labels, fuzzy["score"], pd.DataFrame(rows), season)


def to_markdown(table: pd.DataFrame, floatfmt: str = ".2f") -> str:
    cols = list(table.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in table.iterrows():
        cells = [format(v, floatfmt) if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
