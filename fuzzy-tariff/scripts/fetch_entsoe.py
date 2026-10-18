"""Download ENTSO-E day-ahead prices for CH to data/raw/entsoe_ch_<start>_<end>.csv.

Usage: ENTSOE_TOKEN=... python scripts/fetch_entsoe.py 2025-01-01 2025-12-31
"""

from __future__ import annotations

import sys
from datetime import datetime

from fuzzy_tariff.ingest.entsoe import EntsoeClient
from fuzzy_tariff.settings import Settings


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    start, end = (datetime.fromisoformat(a) for a in argv[1:])
    token = Settings.from_env().entsoe_token
    if not token:
        print("Set ENTSOE_TOKEN (see docs/data-sources.md)", file=sys.stderr)
        return 2
    client = EntsoeClient(token)
    out = Settings.from_env().data_dir / "raw" / f"entsoe_ch_{argv[1]}_{argv[2]}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    # ENTSO-E limits request spans; fetch month by month.
    parts = []
    cursor = start
    while cursor < end:
        nxt = min(datetime(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1), end)
        parts.append(client.fetch_day_ahead(cursor, nxt))
        cursor = nxt
    import pandas as pd

    pd.concat(parts).sort_index().to_csv(out, header=True)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
