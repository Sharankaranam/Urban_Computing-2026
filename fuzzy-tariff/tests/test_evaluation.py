import numpy as np
import pandas as pd

from fuzzy_tariff.evaluation.backtest import run_backtest, to_markdown
from fuzzy_tariff.evaluation.baselines import fixed_threshold_labels, percentile_band_labels
from fuzzy_tariff.evaluation.metrics import (
    flexible_load_cost,
    flips_per_day,
    isolated_window_rate,
    label_distribution_by_season,
)
from fuzzy_tariff.evaluation.sensitivity import input_ablation, membership_sensitivity
from fuzzy_tariff.features import build_features


def _labels(values):
    idx = pd.date_range("2025-03-03", periods=len(values), freq="h", tz="UTC")
    return pd.Series(values, index=idx)


def test_flip_and_isolation_metrics():
    lab = _labels(["okay"] * 6 + ["ideal"] + ["okay"] * 5 + ["good", "good"] + ["okay"] * 10)
    assert flips_per_day(lab) > 0
    assert isolated_window_rate(lab) == 0.5  # one single-step window, one two-step window


def test_baseline_bucketing():
    p = pd.Series([5.0, 30.0, 50.0, 70.0, 95.0, np.nan])
    out = percentile_band_labels(p)
    assert list(out.iloc[:5]) == ["ideal", "good", "okay", "wait", "avoid"]
    assert pd.isna(out.iloc[5])
    price = pd.Series([0.05, 0.12, 0.20])
    assert list(fixed_threshold_labels(price)) == ["ideal", "wait", "avoid"]


def test_flexible_load_oracle_is_a_lower_bound(year_df):
    df = year_df.assign(rank=-year_df["price"])
    res = flexible_load_cost(df, "rank")
    assert res["nights"] > 300
    assert res["gap_to_oracle_pct"] < 1e-6
    assert res["saving_vs_naive_pct"] > 0


def test_season_distribution_rows_sum_to_one(year_df):
    feats = build_features(year_df)
    labels = percentile_band_labels(feats["P"]).dropna()
    dist = label_distribution_by_season(labels)
    assert np.allclose(dist.sum(axis=1), 1.0)
    assert set(dist.index) == {"winter", "spring", "summer", "autumn"}


def test_backtest_runs_and_fuzzy_has_no_isolated_cheap_windows(year_df, cfg):
    result = run_backtest(year_df, cfg)
    summary = result.summary.set_index("method")
    assert set(summary.index) == {"fixed_threshold", "percentile_bands", "fuzzy"}
    assert summary.loc["fuzzy", "isolated_cheap_window_rate"] == 0.0
    assert "| method |" in to_markdown(result.summary)


def test_sensitivity_and_ablation_report_sane_values(year_df, cfg):
    feats = build_features(year_df).iloc[: 24 * 90]
    sens = membership_sensitivity(feats, cfg.stage1, rel=0.05, n=3)
    assert sens["label_agreement"].between(0.5, 1.0).all()
    abl = input_ablation(feats, cfg.stage1)
    assert set(abl["ablated_input"]) == {"G", "T", "A"}


def test_flat_tariff_yields_a_calm_neutral_label():
    from fuzzy_tariff.synthetic import generate_year

    res = run_backtest(generate_year(2025, "flat", seed=0))
    fuzzy = res.labels["fuzzy"].dropna()
    assert (fuzzy == "okay").mean() > 0.99
    assert res.summary.set_index("method").loc["fuzzy", "flips_per_day"] < 0.5
