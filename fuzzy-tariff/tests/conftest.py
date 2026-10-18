from __future__ import annotations

import pytest

from fuzzy_tariff.fuzzy import build_fis, load_config
from fuzzy_tariff.fuzzy.engine import MamdaniFIS
from fuzzy_tariff.synthetic import generate_year


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session")
def stage1(cfg) -> MamdaniFIS:
    return build_fis(cfg.stage1)


@pytest.fixture(scope="session")
def stage2(cfg) -> MamdaniFIS:
    return build_fis(cfg.stage2)


@pytest.fixture(scope="session")
def year_df():
    return generate_year(2025, "baseline", seed=0)
