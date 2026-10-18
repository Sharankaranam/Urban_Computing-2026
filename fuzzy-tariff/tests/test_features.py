import numpy as np
import pandas as pd
import pytest

from fuzzy_tariff.features import build_features, rolling_percentile


def _series(values, start="2025-03-03", freq="h"):
    idx = pd.date_range(start, periods=len(values), freq=freq, tz="UTC")
    return pd.Series(values, index=idx, name="price", dtype=float)


def test_percentile_of_lowest_and_highest_value():
    rng = np.random.default_rng(0)
    s = _series(rng.uniform(0.05, 0.15, 24 * 20))
    p = rolling_percentile(s, window_days=30, same_day_type=False)
    assert p[s.idxmin()] < 5 and p[s.idxmax()] > 95


def test_flat_tariff_is_neutral_not_noise():
    rng = np.random.default_rng(0)
    s = _series(0.11 + rng.normal(0, 0.0002, 24 * 20))
    p = rolling_percentile(s, same_day_type=False, min_spread=0.005)
    assert (p.dropna() == 50.0).all()


def test_requires_timezone_aware_index():
    s = pd.Series([1.0] * 48, index=pd.date_range("2025-01-01", periods=48, freq="h"))
    with pytest.raises(ValueError, match="timezone"):
        rolling_percentile(s)


def test_year_features_are_complete_and_in_range(year_df):
    feats = build_features(year_df)
    assert len(feats) == 8760  # no duplicate or lost hours across DST changes
    valid = feats.dropna()
    assert len(valid) > 8000
    assert valid["P"].between(0, 100).all()
    assert valid["A"].between(0, 1).all()
    assert valid["G"].between(0, 1).all()
    assert valid["T"].between(-1, 1).all()


def test_trend_is_positive_before_a_price_rise():
    s = _series([0.10] * 10 + [0.20] * 10)
    from fuzzy_tariff.features import price_trend

    t = price_trend(s, horizon_steps=2)
    assert t.iloc[8] > 0.3
