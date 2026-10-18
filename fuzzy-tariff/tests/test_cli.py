from fuzzy_tariff.cli import main


def test_demo_prints_label(capsys):
    assert main(["demo", "--P", "12", "--A", "0.3", "--G", "0.2"]) == 0
    assert "Very cheap" in capsys.readouterr().out


def test_plot_membership_functions(tmp_path):
    out = tmp_path / "mf.png"
    assert main(["plot-mf", "--out", str(out)]) == 0
    assert out.exists() and out.stat().st_size > 1000


def test_simulate_tariff_writes_a_year_of_15_minute_rows(tmp_path):
    import pandas as pd

    out = tmp_path / "t.csv"
    assert main(["simulate-tariff", "--out", str(out)]) == 0
    df = pd.read_csv(out)
    assert len(df) == 35040 and {"energy_rp", "grid_rp", "total_rp"} <= set(df.columns)


def test_plot_tariff_writes_a_figure(tmp_path):
    out = tmp_path / "tariff.png"
    assert main(["plot-tariff", "--out", str(out)]) == 0
    assert out.stat().st_size > 1000
