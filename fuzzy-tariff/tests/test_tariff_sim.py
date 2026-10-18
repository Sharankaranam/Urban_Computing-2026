import numpy as np
import pandas as pd
import pytest

from fuzzy_tariff.evaluation.backtest import run_backtest
from fuzzy_tariff.features.reference import LOCAL_TZ, infer_step_hours
from fuzzy_tariff.tariff_sim import (
    TariffSpec,
    fit_day_tariff,
    generate_dynamic_year,
    generate_spot_and_load,
    scale_load_to_mean_mw,
    simulate_dynamic_tariff,
    standard_load_weights,
    to_pipeline_frame,
)

SPEC = TariffSpec()


@pytest.fixture(scope="module")
def month():
    """January 2025 only: fast, but contains weekdays and weekends."""
    spot, load = generate_spot_and_load(2025, 0)
    sl = slice("2025-01-01", "2025-01-31 23:45")
    return simulate_dynamic_tariff(spot.loc[sl], load.loc[sl], SPEC)


def test_full_year_has_15_minute_steps_and_is_deterministic():
    spot, load = generate_spot_and_load(2025, seed=4)
    assert len(spot) == 365 * 96
    assert infer_step_hours(pd.DatetimeIndex(spot.index)) == 0.25
    spot2, load2 = generate_spot_and_load(2025, seed=4)
    assert spot.equals(spot2) and load.equals(load2)


def test_tariffs_stay_inside_their_bands(month):
    e_lo, e_hi = (SPEC.std_energy_rp + b for b in SPEC.energy_band_rp)
    g_lo, g_hi = (SPEC.std_grid_rp + b for b in SPEC.grid_band_rp)
    assert month["energy_rp"].between(e_lo - 1e-9, e_hi + 1e-9).all()
    assert month["grid_rp"].between(g_lo - 1e-9, g_hi + 1e-9).all()


def test_daily_price_parity_with_standard_tariff(month):
    local = month.index.tz_convert(LOCAL_TZ)
    for _, g in month.groupby(local.normalize()):
        w = standard_load_weights(g.index.tz_convert(LOCAL_TZ))
        w = w / w.sum()
        assert (w * g["energy_rp"]).sum() == pytest.approx(SPEC.std_energy_rp, abs=1e-3)
        assert (w * g["grid_rp"]).sum() == pytest.approx(SPEC.std_grid_rp, abs=1e-3)


def test_clipping_is_limited_to_two_hours_per_side(month):
    local = month.index.tz_convert(LOCAL_TZ)
    for _, g in month.groupby(local.normalize()):
        for col, band in (("energy_rp", SPEC.energy_band_rp), ("grid_rp", SPEC.grid_band_rp)):
            std = SPEC.std_energy_rp if col == "energy_rp" else SPEC.std_grid_rp
            hi, lo = std + band[1], std + band[0]
            assert (g[col] >= hi - 1e-9).sum() <= 8  # 2 h at 15 min
            assert (g[col] <= lo + 1e-9).sum() <= 8


def test_grid_tariff_rises_with_net_load_within_a_day(month):
    local = month.index.tz_convert(LOCAL_TZ)
    day = month[local.normalize() == local.normalize()[0]]
    corr = np.corrcoef(day["net_load_mw"], day["grid_rp"])[0, 1]
    assert corr > 0.9


def test_total_is_sum_of_components(month):
    total = month["energy_rp"] + month["grid_rp"] + month["sdl_rp"]
    assert np.allclose(month["total_rp"], total)


def test_flat_curve_gives_the_standard_tariff():
    t, info = fit_day_tariff(np.full(96, 5.0), np.ones(96), 10.0, 5.0, 25.0, 12.0, 8)
    assert np.allclose(t, 10.0) and info.spread_rp == 0.0


def test_standard_tariff_must_be_inside_band():
    with pytest.raises(ValueError):
        fit_day_tariff(np.arange(96.0), np.ones(96), 10.0, 10.0, 25.0, 12.0, 8)


def test_dst_days_are_handled():
    spot, load = generate_spot_and_load(2025, 0)
    for day in ("2025-03-30", "2025-10-26"):  # 23 h and 25 h local days
        sl = slice(f"{day} 00:00", f"{day} 23:59")
        local = spot.index.tz_convert(LOCAL_TZ)
        mask = (local >= pd.Timestamp(day, tz=LOCAL_TZ)) & (
            local < pd.Timestamp(day, tz=LOCAL_TZ) + pd.DateOffset(days=1)
        )
        t = simulate_dynamic_tariff(spot[mask], load[mask], SPEC)
        assert len(t) in (92, 100) and t["grid_rp"].notna().all()
        del sl


def test_mismatched_inputs_are_rejected():
    spot, load = generate_spot_and_load(2025, 0)
    with pytest.raises(ValueError, match="same index"):
        simulate_dynamic_tariff(spot.iloc[:96], load.iloc[1:97])


def test_real_data_can_be_scaled_into_the_tariff_area():
    load = pd.Series([10.0, 20.0, 30.0])
    assert scale_load_to_mean_mw(load, 150).mean() == pytest.approx(150.0)


def test_pipeline_frame_uses_chf_per_kwh(month):
    frame = to_pipeline_frame(month, "grid")
    assert frame["price"].between(0.04, 0.21).all()
    assert (frame["residual_load"] == month["net_load_mw"]).all()


def test_synthetic_year_has_plausible_structure():
    spot, _ = generate_spot_and_load(2025, 0)
    assert (spot < 0).any() and spot.max() < 500  # negative-price hours exist, no absurd values


def test_fuzzy_pipeline_runs_on_15_minute_dynamic_tariff():
    df = generate_dynamic_year(2025, 0)
    res = run_backtest(df.loc["2025-01-01":"2025-03-31"])
    s = res.summary.set_index("method")
    assert s.loc["fuzzy", "flips_per_day"] < s.loc["percentile_bands", "flips_per_day"]
    assert s.loc["fuzzy", "isolated_cheap_window_rate"] == 0.0
