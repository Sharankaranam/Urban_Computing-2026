import pandas as pd

from fuzzy_tariff.ingest.io import read_timeseries_csv


def test_reads_sorts_deduplicates_and_converts_to_utc(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text(
        "ts;val\n"
        "2025-06-01 02:00;3\n"
        "2025-06-01 00:00;1\n"
        "2025-06-01 01:00;2\n"
        "2025-06-01 01:00;2.5\n",
    )
    s = read_timeseries_csv(csv, "ts", "val", sep=";", source_tz="Europe/Zurich")
    assert str(s.index.tz) == "UTC"
    assert s.index.is_monotonic_increasing
    assert len(s) == 3 and s.loc[pd.Timestamp("2025-05-31 22:00", tz="UTC")] == 1.0
    assert s.loc[pd.Timestamp("2025-05-31 23:00", tz="UTC")] == 2.5  # last duplicate wins
