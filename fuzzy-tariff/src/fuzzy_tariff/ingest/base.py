"""Ports (interfaces) for external data. Core logic depends on these, never on a vendor API."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd


class PriceSource(Protocol):
    """Returns a tz-aware UTC-indexed Series of prices in CHF/kWh for [start, end)."""

    def fetch(self, start: datetime, end: datetime) -> pd.Series: ...


class LoadSource(Protocol):
    """Returns a tz-aware UTC-indexed Series of (residual) load for [start, end)."""

    def fetch(self, start: datetime, end: datetime) -> pd.Series: ...
