"""Feature engineering: turn raw price/load series into fuzzy-system inputs P, A, G, T."""

from fuzzy_tariff.features.reference import (
    build_features,
    normalize_price,
    price_trend,
    rolling_percentile,
)

__all__ = ["build_features", "normalize_price", "price_trend", "rolling_percentile"]
