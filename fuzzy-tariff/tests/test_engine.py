import numpy as np
import pytest

from fuzzy_tariff.fuzzy.engine import MamdaniFIS


def test_worked_example_from_docs(stage1):
    """flow.md section 5: P=12, A=0.30, G=0.20 -> rules R01/R02/R05 fire, score about 87."""
    res = stage1.infer(P=12, A=0.30, G=0.20, T=0.0)
    fired = {f.id: round(f.strength, 2) for f in res.fired}
    assert fired == {"R01": 0.80, "R02": 0.20, "R05": 0.13}
    assert res.score == pytest.approx(86.7, abs=0.2)
    assert res.top_set == "ideal"


def test_rule_base_has_no_gaps(stage1):
    grid = np.linspace(0, 1, 11)
    p, a, g, t = np.meshgrid(np.linspace(0, 100, 21), grid, grid, np.linspace(-1, 1, 5))
    batch = stage1.infer_many(P=p.ravel(), A=a.ravel(), G=g.ravel(), T=t.ravel())
    assert not batch.no_rule_fired.any()


def test_scores_stay_in_output_universe(stage1):
    rng = np.random.default_rng(1)
    batch = stage1.infer_many(
        P=rng.uniform(0, 100, 500),
        A=rng.uniform(0, 1, 500),
        G=rng.uniform(0, 1, 500),
        T=rng.uniform(-1, 1, 500),
    )
    assert batch.scores.min() >= 0 and batch.scores.max() <= 100


def test_cheaper_relative_price_scores_higher(stage1):
    s = [stage1.infer(P=p, A=0.5, G=0.5, T=0.0).score for p in (5, 50, 95)]
    assert s[0] > s[1] > s[2]


def test_absolute_guardrail_lowers_score(stage1):
    cheap_abs = stage1.infer(P=5, A=0.0, G=0.2, T=0.0).score
    pricey_abs = stage1.infer(P=5, A=1.0, G=0.2, T=0.0).score
    assert cheap_abs - pricey_abs > 15


def test_batch_matches_single(stage1):
    pts = [(12, 0.3, 0.2, 0.0), (80, 0.9, 0.8, -0.5), (50, 0.5, 0.5, 0.2)]
    batch = stage1.infer_many(
        P=[p[0] for p in pts], A=[p[1] for p in pts], G=[p[2] for p in pts], T=[p[3] for p in pts]
    )
    for i, (p, a, g, t) in enumerate(pts):
        assert batch.scores[i] == pytest.approx(stage1.infer(P=p, A=a, G=g, T=t).score)


def test_defaults_fill_missing_optional_inputs(stage1):
    with_defaults = stage1.infer(P=30, A=0.4)
    explicit = stage1.infer(P=30, A=0.4, G=0.5, T=0.0)
    assert with_defaults.score == pytest.approx(explicit.score)


def test_missing_required_input_raises(stage1):
    with pytest.raises(KeyError):
        stage1.infer(P=30)


def test_unknown_input_raises(stage1):
    with pytest.raises(ValueError, match="unknown inputs"):
        stage1.infer(P=30, A=0.4, X=1.0)


def test_engine_rejects_invalid_rule_base(stage1):
    bad = [stage1.rules[0].__class__("RX", {"P": "nope"}, "ideal")]
    with pytest.raises(ValueError, match="no set"):
        MamdaniFIS(stage1.inputs, stage1.output, bad)


def test_stage2_deadline_overrides_price(stage2):
    low_urgency = stage2.infer(S=15, U=0.05)
    high_urgency = stage2.infer(S=15, U=0.95)
    assert low_urgency.top_set == "wait"
    assert high_urgency.top_set == "must_start"
