import pytest
import yaml
from pydantic import ValidationError

from fuzzy_tariff.fuzzy import build_fis, load_config
from fuzzy_tariff.fuzzy.config import DEFAULT_CONFIG_PATH


def test_default_config_loads_and_builds(cfg):
    assert cfg.version == 1
    assert len(cfg.stage1.rules) == 19
    assert len(cfg.stage2.rules) == 6
    build_fis(cfg.stage1)
    build_fis(cfg.stage2)


def _write(tmp_path, mutate):
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    mutate(raw)
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


def test_rule_referencing_unknown_set_is_rejected(tmp_path):
    def mutate(raw):
        raw["stage1"]["rules"][0]["if"]["P"] = "very_cheap"

    with pytest.raises(ValidationError, match="no set"):
        load_config(_write(tmp_path, mutate))


def test_duplicate_rule_ids_are_rejected(tmp_path):
    def mutate(raw):
        raw["stage1"]["rules"][1]["id"] = raw["stage1"]["rules"][0]["id"]

    with pytest.raises(ValidationError, match="duplicate"):
        load_config(_write(tmp_path, mutate))


def test_unordered_membership_params_are_rejected(tmp_path):
    def mutate(raw):
        raw["stage1"]["inputs"]["P"]["sets"]["low"]["params"] = [45, 25, 10]

    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, mutate))
