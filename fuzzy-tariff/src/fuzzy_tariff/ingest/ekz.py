"""EKZ dynamic tariff adapter.

Connects to EKZ's public tariff API (https://api.tariffs.ekz.ch/v1/tariffs) to retrieve
published 15-minute dynamic tariffs.

Products supported:
* integrated_400D: dynamic energy + dynamic grid + levies (CHF/kWh)
* electricity_dynamic: dynamic energy component only (CHF/kWh)
* grid_400D: dynamic grid component (with SDL) (CHF/kWh)
* grid_400D_woSDL: dynamic grid component without SDL (CHF/kWh)
* standard tariffs (electricity_standard, grid_400ST, etc.)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

BASE_URL = "https://api.tariffs.ekz.ch/v1/tariffs"
LOCAL_TZ = "Europe/Zurich"


class EkzError(RuntimeError):
    """Raised when the EKZ API returns an error or invalid payload."""


def _parse_timestamp(ts_str: str) -> pd.Timestamp:
    """Parse ISO8601 timestamp string into tz-aware Timestamp in UTC."""
    ts = pd.Timestamp(ts_str)
    if ts.tzinfo is None:
        ts = ts.tz_localize(LOCAL_TZ)
    return ts.tz_convert("UTC")


def parse_ekz_tariffs_json(data: dict[str, Any], default_sdl_rp: float = 0.27) -> pd.DataFrame:
    """Parse EKZ API JSON response into a normalized DataFrame.

    Output columns:
    * energy_rp: Energy tariff in Rp./kWh
    * grid_rp: Grid tariff in Rp./kWh
    * sdl_rp: SDL / Swissgrid ancillary in Rp./kWh
    * total_rp: Total combined dynamic tariff in Rp./kWh
    * price: Total tariff in CHF/kWh (pipeline-ready)
    """
    prices = data.get("prices", [])
    if not prices:
        return pd.DataFrame(
            columns=["energy_rp", "grid_rp", "sdl_rp", "total_rp", "price"],
            index=pd.DatetimeIndex([], tz="UTC"),
        )

    records: list[dict[str, Any]] = []
    indices: list[pd.Timestamp] = []

    for entry in prices:
        start_ts = _parse_timestamp(entry["start_timestamp"])
        indices.append(start_ts)

        # Helper to extract CHF/kWh value from component array
        def get_val(key: str) -> float | None:
            items = entry.get(key, [])
            for item in items:
                if item.get("unit") == "CHF_kWh":
                    return float(item.get("value", 0.0))
            return None

        integrated_chf = get_val("integrated")
        electricity_chf = get_val("electricity")
        grid_chf = get_val("grid")
        regional_chf = get_val("regional_fees") or 0.0

        # Convert CHF/kWh to Rp./kWh (1 CHF = 100 Rp.)
        if electricity_chf is not None:
            energy_rp = electricity_chf * 100.0
        else:
            energy_rp = 0.0

        if grid_chf is not None:
            grid_rp = grid_chf * 100.0
        else:
            grid_rp = 0.0

        sdl_rp = default_sdl_rp

        if integrated_chf is not None:
            total_rp = integrated_chf * 100.0
            if electricity_chf is None and grid_chf is None:
                # Estimate components if only integrated is requested
                # Regulated standard approx: 55% energy, 45% grid
                energy_rp = max(0.0, total_rp - 10.0 - sdl_rp)
                grid_rp = max(0.0, total_rp - energy_rp - sdl_rp)
        else:
            total_rp = energy_rp + grid_rp + (regional_chf * 100.0)

        records.append(
            {
                "energy_rp": round(energy_rp, 4),
                "grid_rp": round(grid_rp, 4),
                "sdl_rp": round(sdl_rp, 4),
                "total_rp": round(total_rp, 4),
                "price": round(total_rp / 100.0, 6),
            }
        )

    df = pd.DataFrame(records, index=pd.DatetimeIndex(indices, name="timestamp_utc"))
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


class EkzTariffSource:
    """Client for fetching and parsing dynamic tariffs from api.tariffs.ekz.ch."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url
        self._client = client or httpx.Client(timeout=timeout)

    def fetch(
        self,
        start: datetime | str,
        end: datetime | str,
        tariff_name: str = "integrated_400D",
        tariff_type: str | None = None,
        max_chunk_days: int = 14,
    ) -> pd.DataFrame:
        """Fetch tariffs for the given time range, automatically chunking large spans."""
        start_dt = pd.Timestamp(start)
        if start_dt.tzinfo is None:
            start_dt = start_dt.tz_localize(LOCAL_TZ)

        end_dt = pd.Timestamp(end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.tz_localize(LOCAL_TZ)

        if end_dt < start_dt:
            raise ValueError(f"end ({end_dt}) must be >= start ({start_dt})")

        frames: list[pd.DataFrame] = []
        curr_start = start_dt

        while curr_start <= end_dt:
            curr_end = min(curr_start + timedelta(days=max_chunk_days), end_dt)
            params: dict[str, str] = {
                "start_timestamp": curr_start.isoformat(),
                "end_timestamp": curr_end.isoformat(),
            }
            if tariff_name:
                params["tariff_name"] = tariff_name
            if tariff_type:
                params["tariff_type"] = tariff_type

            try:
                resp = self._client.get(self.base_url, params=params)
            except httpx.RequestError as exc:
                raise EkzError(f"HTTP request to EKZ API failed: {exc}") from exc

            if resp.status_code != 200:
                raise EkzError(
                    f"EKZ API returned status {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            chunk_df = parse_ekz_tariffs_json(data)
            if not chunk_df.empty:
                frames.append(chunk_df)

            curr_start = curr_end + timedelta(minutes=15)

        if not frames:
            return pd.DataFrame(
                columns=["energy_rp", "grid_rp", "sdl_rp", "total_rp", "price"],
                index=pd.DatetimeIndex([], tz="UTC"),
            )

        combined = pd.concat(frames)
        combined = combined[~combined.index.duplicated(keep="first")].sort_index()
        return combined

    def fetch_latest_day(self, tariff_name: str = "integrated_400D") -> pd.DataFrame:
        """Fetch today and tomorrow's tariff."""
        now = pd.Timestamp.now(tz=LOCAL_TZ)
        start = now.normalize()
        end = start + timedelta(days=2)
        return self.fetch(start, end, tariff_name=tariff_name)
