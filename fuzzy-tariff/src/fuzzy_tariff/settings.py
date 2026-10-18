"""Runtime settings read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    entsoe_token: str | None
    config_path: Path | None
    data_dir: Path
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        cfg = os.environ.get("FUZZY_TARIFF_CONFIG")
        return cls(
            entsoe_token=os.environ.get("ENTSOE_TOKEN") or None,
            config_path=Path(cfg) if cfg else None,
            data_dir=Path(os.environ.get("FUZZY_TARIFF_DATA_DIR", "data")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
