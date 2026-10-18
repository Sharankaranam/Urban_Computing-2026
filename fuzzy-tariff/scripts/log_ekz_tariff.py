"""Daily job: archive tomorrow's EKZ dynamic tariff to data/raw/ekz/YYYY-MM-DD.json.

PURPOSE: Swiss dynamic grid tariffs have no public multi-year history yet. Run this daily
(cron / GitHub Actions) from today on, so we accumulate a real dataset for evaluation.

STATUS: skeleton. Implement after reading the EKZ API docs (https://api.tariffs.ekz.ch/).
Store the RAW response unmodified; parse in fuzzy_tariff.ingest.ekz.
"""

from __future__ import annotations

import sys


def main() -> int:
    print("TODO: implement after reading the EKZ API documentation", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
