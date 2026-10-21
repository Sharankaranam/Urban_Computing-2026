"""Fetch real historical / current dynamic tariffs from EKZ API and build PGAT Stage 1 dataset.

Usage:
    python scripts/fetch_ekz_data.py --start 2026-07-01 --end 2026-10-21 --out data/ekz_real_stage1.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fuzzy_tariff.features.reference import build_features
from fuzzy_tariff.fuzzy import build_fis, load_config
from fuzzy_tariff.ingest.ekz import EkzTariffSource
from fuzzy_tariff.labeler import FuzzyLabeler


def fetch_and_process_ekz_data(
    start: str = "2026-07-01",
    end: str = "2026-10-21",
    tariff_name: str = "integrated_400D",
) -> pd.DataFrame:
    print(f"Connecting to EKZ API: fetching {tariff_name} from {start} to {end}...")
    source = EkzTariffSource()
    tariff = source.fetch(start=start, end=end, tariff_name=tariff_name)

    if tariff.empty:
        raise ValueError(f"No data returned by EKZ API for range {start} to {end}")

    print(f"Received {len(tariff):,} 15-minute intervals from EKZ API.")

    # Compute P, A, G, T
    pipeline_df = tariff.copy()
    pipeline_df["price"] = pipeline_df["total_rp"] / 100.0

    print("Computing Stage 1 Fuzzy inputs (P, A, G, T)...")
    feats = build_features(pipeline_df, window_days=30, price_col="price")
    tariff["P"] = feats["P"].round(2)
    tariff["A"] = feats["A"].round(4)
    tariff["G"] = feats["G"].round(4)
    tariff["T"] = feats["T"].round(4)

    # Evaluate Stage 1 Mamdani FIS
    print("Evaluating Stage 1 Mamdani FIS & Stability Layer...")
    labeler = FuzzyLabeler.from_config()
    labeled = labeler.label(tariff[["P", "A", "G", "T"]])

    tariff["suitability_score"] = labeled["score"].round(1)
    tariff["suitability_label"] = labeled["label"]

    tariff = tariff.reset_index().rename(columns={"index": "timestamp_utc"})
    return tariff


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch real dynamic tariffs from EKZ API")
    parser.add_argument("--start", default="2026-07-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-10-21", help="End date (YYYY-MM-DD)")
    parser.add_argument("--tariff", default="integrated_400D", help="EKZ product name")
    parser.add_argument("--out", default="data/ekz_real_stage1.csv", help="Output CSV path")
    args = parser.parse_args()

    df = fetch_and_process_ekz_data(args.start, args.end, args.tariff)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved real EKZ dataset ({len(df):,} rows) to: {out_path.resolve()}")
    print("Label summary:")
    print(df["suitability_label"].value_counts(normalize=True).round(3) * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
