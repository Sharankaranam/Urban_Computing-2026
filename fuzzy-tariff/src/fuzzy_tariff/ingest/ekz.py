"""EKZ dynamic tariff adapter (SKELETON).

EKZ publishes the next day's dynamic tariff from 18:00 the day before at
https://api.tariffs.ekz.ch/ (15-minute intervals). The response schema and authentication
requirements are defined in EKZ's API documentation, which must be read before implementing.

TODO(data-engineer): implement `fetch` after reading the API docs, add a recorded fixture
under tests/fixtures/, and a daily logging job (scripts/log_ekz_tariff.py) so that we build
our own real dynamic-tariff history. Do not guess the schema.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


class EkzTariffSource:
    def __init__(self, base_url: str = "https://api.tariffs.ekz.ch/") -> None:
        self.base_url = base_url

    def fetch(self, start: datetime, end: datetime) -> pd.Series:
        raise NotImplementedError("Implement after reading the EKZ API documentation.")
