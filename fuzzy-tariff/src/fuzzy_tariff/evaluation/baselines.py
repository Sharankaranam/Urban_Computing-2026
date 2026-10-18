"""Crisp baselines the fuzzy labeller is compared against (same label vocabulary)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from fuzzy_tariff.labels import Label

# Ordered from cheapest to most expensive.
_CHEAP_TO_EXPENSIVE = [Label.IDEAL, Label.GOOD, Label.OKAY, Label.WAIT, Label.AVOID]


def _bucket(values: pd.Series, cuts: Sequence[float]) -> pd.Series:
    if len(cuts) != 4 or list(cuts) != sorted(cuts):
        raise ValueError("need 4 ascending cut points")
    idx = np.digitize(values.to_numpy(dtype=float), cuts)  # 0..4
    labels = pd.Series([_CHEAP_TO_EXPENSIVE[i].value for i in idx], index=values.index)
    return labels.where(values.notna())


def fixed_threshold_labels(
    price: pd.Series, thresholds_chf: Sequence[float] = (0.07, 0.09, 0.11, 0.13)
) -> pd.Series:
    """Baseline A: fixed CHF/kWh thresholds (ignores season and context)."""
    return _bucket(price, thresholds_chf)


def percentile_band_labels(p: pd.Series, cuts: Sequence[float] = (20, 40, 60, 80)) -> pd.Series:
    """Baseline B: crisp percentile bands over the same reference window as the fuzzy P."""
    return _bucket(p, cuts)
