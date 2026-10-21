"""Daily job: archive tomorrow's EKZ dynamic tariff to data/raw/ekz/YYYY-MM-DD.json.

PURPOSE: Swiss dynamic grid tariffs have no public multi-year history yet. Run this daily
(cron / GitHub Actions) from 18:00 onward, so we accumulate a real dataset for evaluation.

STATUS: Production. Fetches raw response from https://api.tariffs.ekz.ch/v1/tariffs.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

import httpx

API_URL = "https://api.tariffs.ekz.ch/v1/tariffs"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "ekz"


def fetch_and_archive(target_date: str | None = None) -> Path:
    """Fetch tomorrow's EKZ dynamic tariff and save raw JSON."""
    now = datetime.now()
    if target_date is None:
        tomorrow = now + timedelta(days=1)
        target_date = tomorrow.strftime("%Y-%m-%d")

    start_str = f"{target_date}T00:00:00+02:00"
    end_str = f"{target_date}T23:59:59+02:00"

    print(f"Fetching EKZ dynamic tariffs for {target_date}...")
    params = {
        "tariff_name": "integrated_400D",
        "start_timestamp": start_str,
        "end_timestamp": end_str,
    }

    resp = httpx.get(API_URL, params=params, timeout=15.0)
    if resp.status_code != 200:
        raise RuntimeError(f"EKZ API error: {resp.status_code} - {resp.text}")

    data = resp.json()
    prices = data.get("prices", [])
    print(f"Successfully received {len(prices)} price intervals for {target_date}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{target_date}.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Archived to {out_file}")
    return out_file


def main() -> int:
    try:
        date_arg = sys.argv[1] if len(sys.argv) > 1 else None
        fetch_and_archive(date_arg)
        return 0
    except Exception as exc:
        print(f"Error archiving EKZ tariff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
