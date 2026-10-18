"""ENTSO-E Transparency Platform day-ahead prices (document type A44).

ENTSO-E prices are ENERGY MARKET prices in EUR/MWh, not Swiss grid tariffs. Use them as a
realistic shape/volatility source or as an energy-price signal, not as the tariff itself.

Status: parser unit-tested on a hand-built fixture; live API not exercised in CI.
Verify bidding zone availability for CH at https://transparency.entsoe.eu before relying on it.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
import pandas as pd

BASE_URL = "https://web-api.tp.entsoe.eu/api"
DOMAIN_CH = "10YCH-SWISSGRIDZ"
_RES_MINUTES = {"PT15M": 15, "PT30M": 30, "PT60M": 60}


class EntsoeError(RuntimeError):
    pass


def _tag(el: ET.Element) -> str:
    return el.tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in el if _tag(c) == name), None)


def _text(el: ET.Element, name: str) -> str:
    child = _child(el, name)
    if child is None or child.text is None:
        raise EntsoeError(f"missing element {name!r}")
    return child.text.strip()


def parse_day_ahead_xml(xml_text: str) -> pd.Series:
    """Parse a Publication_MarketDocument into a UTC-indexed Series (EUR/MWh).

    Handles PT15M/PT30M/PT60M and omitted points (curve type A03: value repeats until changed).
    """
    root = ET.fromstring(xml_text)
    if _tag(root) == "Acknowledgement_MarketDocument":
        reason = _child(root, "Reason")
        msg = _text(reason, "text") if reason is not None else "unknown reason"
        raise EntsoeError(f"ENTSO-E returned no data: {msg}")

    pieces: list[pd.Series] = []
    for ts in (e for e in root if _tag(e) == "TimeSeries"):
        for period in (e for e in ts if _tag(e) == "Period"):
            interval = _child(period, "timeInterval")
            if interval is None:
                raise EntsoeError("Period without timeInterval")
            start = pd.Timestamp(_text(interval, "start"))
            end = pd.Timestamp(_text(interval, "end"))
            resolution = _text(period, "resolution")
            if resolution not in _RES_MINUTES:
                raise EntsoeError(f"unsupported resolution {resolution}")
            step = pd.Timedelta(minutes=_RES_MINUTES[resolution])
            n = int((end - start) / step)
            values: dict[int, float] = {}
            for point in (e for e in period if _tag(e) == "Point"):
                values[int(_text(point, "position"))] = float(_text(point, "price.amount"))
            idx = pd.date_range(start, periods=n, freq=step)
            series = pd.Series([values.get(i + 1) for i in range(n)], index=idx, dtype=float)
            pieces.append(series.ffill())
    if not pieces:
        raise EntsoeError("no TimeSeries found")
    out = pd.concat(pieces).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index = out.index.tz_convert("UTC") if out.index.tz else out.index.tz_localize("UTC")
    out.name = "price_eur_mwh"
    return out


class EntsoeClient:
    def __init__(
        self,
        token: str,
        domain: str = DOMAIN_CH,
        client: httpx.Client | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        if not token:
            raise ValueError("ENTSOE_TOKEN is required (free account, see docs/data-sources.md)")
        self._token = token
        self._domain = domain
        self._client = client or httpx.Client(timeout=30.0)
        self._base_url = base_url

    def fetch_day_ahead(self, start: datetime, end: datetime) -> pd.Series:
        params = {
            "securityToken": self._token,
            "documentType": "A44",
            "in_Domain": self._domain,
            "out_Domain": self._domain,
            "periodStart": pd.Timestamp(start).strftime("%Y%m%d%H%M"),
            "periodEnd": pd.Timestamp(end).strftime("%Y%m%d%H%M"),
        }
        resp = self._client.get(self._base_url, params=params)
        resp.raise_for_status()
        return parse_day_ahead_xml(resp.text)
