"""Application service container: loads config once and wires stage 1 + stage 2."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fuzzy_tariff.advisor.devices import DeviceAdvisor
from fuzzy_tariff.fuzzy.config import FuzzyConfig, build_fis, load_config
from fuzzy_tariff.fuzzy.engine import MamdaniFIS
from fuzzy_tariff.settings import Settings


@dataclass(frozen=True)
class Services:
    config: FuzzyConfig
    stage1: MamdaniFIS
    advisor: DeviceAdvisor


@lru_cache(maxsize=1)
def get_services() -> Services:
    settings = Settings.from_env()
    cfg = load_config(settings.config_path)
    return Services(
        config=cfg, stage1=build_fis(cfg.stage1), advisor=DeviceAdvisor.from_config(cfg)
    )
