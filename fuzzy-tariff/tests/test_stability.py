import itertools

import numpy as np

from fuzzy_tariff.stability import enforce_min_block, hysteresis_labels


def test_hysteresis_reduces_flicker_near_a_boundary(stage1):
    # scores oscillate around the good/ideal crossover
    scores = np.array([80, 83, 79, 84, 80, 83, 79, 84], dtype=float)
    raw = hysteresis_labels(stage1, scores, margin=0.0)
    stable = hysteresis_labels(stage1, scores, margin=0.3)
    flips = lambda xs: sum(a != b for a, b in itertools.pairwise(xs))  # noqa: E731
    assert flips(stable) < flips(raw)


def test_min_block_removes_isolated_windows():
    labels = ["okay", "okay", "ideal", "okay", "okay", "good", "good", "good"]
    assert enforce_min_block(labels, 2) == ["okay"] * 5 + ["good"] * 3


def test_min_block_first_run_uses_next_label():
    assert enforce_min_block(["ideal", "okay", "okay"], 2) == ["okay", "okay", "okay"]


def test_min_block_keeps_nan_runs():
    out = enforce_min_block([np.nan, np.nan, "okay", "okay"], 2)
    assert np.isnan(out[0]) and out[2] == "okay"


def test_nan_scores_give_nan_labels(stage1):
    out = hysteresis_labels(stage1, np.array([np.nan, 50.0]), margin=0.1)
    assert np.isnan(out[0]) and out[1] == "okay"
