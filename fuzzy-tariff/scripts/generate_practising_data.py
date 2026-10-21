"""Generate 4 months of 15-minute practicing dynamic tariff data with PGAT features and edge cases.

Timeframe: 2026-10-21 through 2027-02-28 (~131 days, ~12,580 intervals).
Methodology:
* 15-minute resolution (96 steps/day; 100 steps on 2026-10-25 DST transition).
* EKZ-style 2-component tariff:
    - Energy tariff proportional to day-ahead spot price curve within [std - 5, std + 5] Rp./kWh.
    - Grid tariff proportional to squared net load (MW^2) within [std - 5, std + 15] Rp./kWh.
    - Daily price parity against standard load profile.
    - Bounded clipping <= 2 hours per side per day.
* Pre-computed Stage 1 Mamdani FIS inputs (P, A, G, T) and defuzzified scores (S).
* 6 Embedded Real-World Edge Cases:
    1. Autumn DST Transition (2026-10-25): 100 steps, repeated 02:00 hour.
    2. November Storm / Wind Surplus (2026-11-12 to 2026-11-14): Negative prices, surplus soak.
    3. December Winter Cold Snap (2026-12-08 to 2026-12-18): Sub-zero heating peak, high load^2.
    4. Holiday Flat Tariff / Low Spread (2026-12-24 to 2026-12-26): Low IQR, neutral label.
    5. January Deep Freeze Spike (2027-01-18): 250 EUR/MWh generator tripping evening peak.
    6. February Late-Winter Solar Surge (2027-02-18 to 2027-02-22): Solar dip, low grid congestion.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fuzzy_tariff.features.reference import LOCAL_TZ, build_features
from fuzzy_tariff.fuzzy import build_fis, load_config
from fuzzy_tariff.tariff_sim import TariffSpec, _bump, simulate_dynamic_tariff


def generate_practising_spot_and_load(
    start_date: str = "2026-10-21",
    end_date: str = "2027-02-28 23:45",
    seed: int = 42,
) -> tuple[pd.Series, pd.Series]:
    """Generate realistic Swiss 15-min spot prices and net load with embedded edge cases."""
    rng = np.random.default_rng(seed)

    # 15-min DatetimeIndex in Europe/Zurich to properly handle DST transition on 2026-10-25
    local_idx = pd.date_range(start_date, end_date, freq="15min", tz=LOCAL_TZ)
    utc_idx = local_idx.tz_convert("UTC")

    hour = np.asarray(local_idx.hour) + np.asarray(local_idx.minute) / 60.0
    doy = np.asarray(local_idx.dayofyear)
    weekend = np.asarray(local_idx.dayofweek >= 5)

    # Seasonal winter factor: 1 in mid-January, ~0.65 in late October, ~0.80 in late February
    winter = 0.5 * (1 + np.cos(2 * np.pi * (doy - 15) / 365))
    summer = 1.0 - winter

    # --- BASELINE LOAD PROFILE ---
    # Heating base load increases as temperature drops in December and January
    base_load = 145.0 + 35.0 * winter
    morning_peak = 28.0 * _bump(hour, 8.0, 1.3)
    evening_peak = 62.0 * (0.6 + 0.8 * winter) * _bump(hour, 19.0, 1.8)
    night_trough = -28.0 * _bump(hour, 3.0, 2.5)
    weekend_drop = -12.0 * weekend

    load = base_load + morning_peak + evening_peak + night_trough + weekend_drop
    noise = pd.Series(rng.normal(0, 2.5, len(local_idx))).ewm(alpha=0.15).mean().to_numpy() * 2.0
    load = load + noise

    # Solar generation (minimal in Dec, reviving in Feb)
    solar_pot = 45.0 * summer + 20.0 * (doy > 40)
    solar = solar_pot * _bump(hour, 12.5, 2.5) * rng.uniform(0.3, 1.0, len(local_idx))
    net_load = np.maximum(20.0, load - solar)

    # --- BASELINE SPOT PRICE ---
    # Correlated with load and European gas/winter premium
    spot = 65.0 + 38.0 * winter + 0.25 * (net_load - 150.0) + rng.normal(0, 4.0, len(local_idx))

    # =========================================================================
    # INJECT REAL-WORLD EDGE CASES
    # =========================================================================

    # Edge Case 1: Autumn DST Transition (2026-10-25) - Naturally captured with 100 intervals!

    # Edge Case 2: November Storm / Wind Surplus (2026-11-12 to 2026-11-14)
    # Strong North Sea gale causes wind power export into Swiss grid; negative night spot prices
    is_nov_storm = (local_idx >= "2026-11-12") & (local_idx <= "2026-11-14")
    night_mask = (hour >= 0) & (hour <= 5)
    spot = np.where(is_nov_storm & night_mask, -15.0 - rng.exponential(8.0, len(local_idx)), spot)

    # Edge Case 3: December Winter Cold Snap (2026-12-08 to 2026-12-18)
    # Severe cold wave (-8 C): heat pumps at max, net load surges +25%, spot +45 EUR/MWh
    is_cold_snap = (local_idx >= "2026-12-08") & (local_idx <= "2026-12-18")
    net_load = np.where(is_cold_snap, net_load * 1.22, net_load)
    spot = np.where(is_cold_snap, spot + 45.0 + 15.0 * _bump(hour, 19.0, 1.5), spot)

    # Edge Case 4: Christmas Holiday Flat Period (2026-12-24 to 2026-12-26)
    # Factory shutdowns create flat consumption and low price spread
    is_holiday = (local_idx >= "2026-12-24") & (local_idx <= "2026-12-26")
    spot = np.where(is_holiday, 82.0 + rng.normal(0, 0.8, len(local_idx)), spot)
    net_load = np.where(is_holiday, 130.0 + rng.normal(0, 2.0, len(local_idx)), net_load)

    # Edge Case 5: January Deep Freeze & Generator Tripping Peak (2027-01-18)
    # Evening reserve scarcity: spot price spikes to 250 EUR/MWh between 17:30 and 20:30
    is_jan_spike = (local_idx.strftime("%Y-%m-%d") == "2027-01-18") & (hour >= 17.5) & (hour <= 20.5)
    spot = np.where(is_jan_spike, spot + 185.0, spot)

    # Edge Case 6: February Late-Winter Solar Surge (2027-02-18 to 2027-02-22)
    # High-pressure sunny days: massive solar surge between 11:00 and 15:00, net load drops to 40 MW
    is_feb_solar = (local_idx >= "2027-02-18") & (local_idx <= "2027-02-22")
    midday_sun = _bump(hour, 13.0, 2.0)
    net_load = np.where(is_feb_solar, np.maximum(25.0, net_load - 85.0 * midday_sun), net_load)
    spot = np.where(is_feb_solar & (hour >= 11.5) & (hour <= 14.5), -8.0 + rng.normal(0, 3.0, len(local_idx)), spot)

    # Clip extreme limits
    spot = np.clip(spot, -40.0, 450.0)

    # Reindex series with UTC index for simulation compatibility
    s_spot = pd.Series(spot, index=utc_idx, name="spot_eur_mwh")
    s_load = pd.Series(net_load, index=utc_idx, name="net_load_mw")
    return s_spot, s_load


def build_practising_dataset(
    start_date: str = "2026-10-21",
    end_date: str = "2027-02-28 23:45",
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate 4 months of EKZ-style dynamic tariffs and compute PGAT features + FIS scores."""
    print(f"Generating 4-month practicing inputs ({start_date} to {end_date})...")
    spot, load = generate_practising_spot_and_load(start_date, end_date, seed)

    print("Simulating EKZ-style dynamic tariff (energy, grid load^2, SDL, parity)...")
    spec = TariffSpec(
        std_energy_rp=12.5,
        std_grid_rp=10.5,
        energy_band_rp=(-5.0, 5.0),
        grid_band_rp=(-5.0, 15.0),
        max_clip_hours=2.0,
        sdl_rp=0.27,
    )
    tariff = simulate_dynamic_tariff(spot, load, spec=spec)

    print("Computing Stage 1 Fuzzy features (P, A, G, T)...")
    pipeline_df = tariff.copy()
    pipeline_df["price"] = pipeline_df["total_rp"] / 100.0
    pipeline_df["residual_load"] = pipeline_df["net_load_mw"]

    features = build_features(
        pipeline_df,
        window_days=30,
        price_col="price",
        load_col="residual_load",
    )

    tariff["P"] = features["P"].round(2)
    tariff["A"] = features["A"].round(4)
    tariff["G"] = features["G"].round(4)
    tariff["T"] = features["T"].round(4)

    # Evaluate Stage 1 Mamdani FIS Engine using FuzzyLabeler
    print("Evaluating Stage 1 Mamdani Fuzzy Inference Engine & Stability Layer...")
    from fuzzy_tariff.labeler import FuzzyLabeler
    labeler = FuzzyLabeler.from_config()
    labeled = labeler.label(tariff[["P", "A", "G", "T"]])

    tariff["suitability_score"] = labeled["score"].round(1)
    tariff["suitability_label"] = labeled["label"]

    tariff = tariff.reset_index().rename(columns={"index": "timestamp_utc"})
    return tariff


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4-month practicing dataset")
    parser.add_argument("--start", default="2026-10-21", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2027-02-28 23:45", help="End date (YYYY-MM-DD HH:MM)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", default=None, help="Output CSV path")
    args = parser.parse_args()

    df = build_practising_dataset(args.start, args.end, args.seed)

    primary_out = Path(__file__).resolve().parents[2] / "practising_tariff_4months_15min.csv"
    synthetic_out = (
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / "practising_tariff_4months_15min.csv"
    )

    dest_paths = [primary_out, synthetic_out]
    if args.out:
        dest_paths.append(Path(args.out))

    for p in dest_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False)
        print(f"Saved dataset ({len(df):,} rows) to: {p}")

    print("\nDataset Summary:")
    print(f"Date range: {df['timestamp_utc'].iloc[0]} to {df['timestamp_utc'].iloc[-1]}")
    print(f"Total 15-minute intervals: {len(df):,}")
    print(f"Total dynamic tariff range: {df['total_rp'].min():.2f} to {df['total_rp'].max():.2f} Rp./kWh")
    print(f"Average total tariff: {df['total_rp'].mean():.2f} Rp./kWh")
    print(f"Suitability Score mean: {df['suitability_score'].mean():.1f}/100")
    print("Label distribution:")
    print(df["suitability_label"].value_counts(normalize=True).round(3) * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
