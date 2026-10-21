"""Tests for the pure fuzzy linguistic summarizer (protoforms, quantifiers, narratives)."""

import numpy as np
import pytest

from fuzzy_tariff.fuzzy.summarizer import (
    QUANTIFIERS,
    QUALIFIER_LABELS,
    SUMMARIZER_LABELS,
    StepTimeSeriesData,
    discover_best_protoforms,
    evaluate_protoform,
    generate_executive_narrative,
)


@pytest.fixture
def sample_timeseries_data() -> StepTimeSeriesData:
    """96 steps of synthetic 15-min tariff data with cheap night, solar midday, and evening peak."""
    n = 96
    hours = np.linspace(0.0, 23.75, n)
    scores = np.zeros(n)
    g_stress = np.zeros(n)
    t_trend = np.zeros(n)
    total_rp = np.zeros(n)

    memberships = {
        "avoid": np.zeros(n),
        "wait": np.zeros(n),
        "okay": np.zeros(n),
        "good": np.zeros(n),
        "ideal": np.zeros(n),
    }

    for i, h in enumerate(hours):
        if 0.0 <= h < 6.0:
            # Cheap night
            scores[i] = 88.0
            g_stress[i] = 0.15
            total_rp[i] = 14.0
            memberships["ideal"][i] = 0.90
            memberships["good"][i] = 0.10
        elif 11.0 <= h < 15.0:
            # Solar midday
            scores[i] = 72.0
            g_stress[i] = 0.25
            total_rp[i] = 18.0
            memberships["good"][i] = 0.85
            memberships["okay"][i] = 0.15
        elif 17.5 <= h <= 20.5:
            # Evening peak
            scores[i] = 12.0
            g_stress[i] = 0.85
            total_rp[i] = 36.0
            memberships["avoid"][i] = 0.95
            memberships["wait"][i] = 0.05
        else:
            # Standard hours
            scores[i] = 52.0
            g_stress[i] = 0.40
            total_rp[i] = 22.0
            memberships["okay"][i] = 0.80

    return StepTimeSeriesData(
        hours=hours,
        scores=scores,
        memberships=memberships,
        g_stress=g_stress,
        t_trend=t_trend,
        total_rp=total_rp,
    )


def test_quantifiers_monotonicity():
    for name, q in QUANTIFIERS.items():
        assert q.params[0] <= q.params[-1]
        assert 0.0 <= q(0.0) <= 1.0
        assert 0.0 <= q(1.0) <= 1.0


def test_evaluate_protoform_type_1_all_day(sample_timeseries_data):
    ev = evaluate_protoform("most", "all_day", "cheap", sample_timeseries_data, lang="en")
    assert ev.protoform_type == "type_1"
    assert 0.0 <= ev.truth_degree <= 1.0
    assert 0.0 <= ev.cardinality_ratio <= 1.0
    assert "intervals of the day" in ev.statement


def test_evaluate_protoform_type_2_night_ideal(sample_timeseries_data):
    # Almost all night hours should be ideal
    ev = evaluate_protoform("almost_all", "night_hours", "ideal", sample_timeseries_data, lang="en")
    assert ev.protoform_type == "type_2"
    assert ev.cardinality_ratio >= 0.85
    assert ev.truth_degree >= 0.80
    assert "Almost all night hours" in ev.statement


def test_evaluate_protoform_type_2_evening_avoid(sample_timeseries_data):
    # Almost all evening peak hours should be avoid
    ev = evaluate_protoform("almost_all", "evening_peak", "avoid", sample_timeseries_data, lang="de")
    assert ev.truth_degree >= 0.80
    assert "Fast alle Abend-Spitzenstunden" in ev.statement


def test_discover_best_protoforms(sample_timeseries_data):
    results = discover_best_protoforms(sample_timeseries_data, lang="en", min_truth=0.50)
    assert len(results) > 0
    # Every discovered protoform should have T >= 0.50
    for r in results:
        assert r.truth_degree >= 0.50


def test_generate_executive_narrative_multilingual(sample_timeseries_data):
    for lang in ("en", "de", "fr", "it"):
        headline, bullets = generate_executive_narrative(sample_timeseries_data, lang=lang)
        assert len(headline) > 10
        assert len(bullets) == 4
