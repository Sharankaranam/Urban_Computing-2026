import pytest

from fuzzy_tariff.synthetic import SCENARIOS, generate_year


def test_deterministic_for_same_seed():
    a = generate_year(2025, "baseline", seed=3)
    b = generate_year(2025, "baseline", seed=3)
    assert a.equals(b)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_all_scenarios_are_valid(scenario):
    df = generate_year(2025, scenario, seed=1)
    assert len(df) == 8760
    assert (df["price"] >= 0).all() and df["price"].max() < 1.0
    assert df.index.tz is not None


def test_winter_costs_more_than_summer(year_df):
    months = year_df.index.tz_convert("Europe/Zurich").month
    assert year_df.loc[months == 1, "price"].mean() > year_df.loc[months == 7, "price"].mean()


def test_unknown_scenario_rejected():
    with pytest.raises(ValueError):
        generate_year(2025, "nope")  # type: ignore[arg-type]
