"""Typed, validated loading of the fuzzy configuration (YAML -> pydantic -> engine)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from fuzzy_tariff.fuzzy.engine import MamdaniFIS
from fuzzy_tariff.fuzzy.membership import MembershipFunction
from fuzzy_tariff.fuzzy.rules import Rule
from fuzzy_tariff.fuzzy.variables import LinguisticVariable

DEFAULT_CONFIG_PATH = Path(__file__).with_name("default.yaml")


class MFSpec(BaseModel):
    shape: Literal["tri", "trap"]
    params: list[float]

    @model_validator(mode="after")
    def _check(self) -> MFSpec:
        MembershipFunction(self.shape, tuple(self.params))  # raises ValueError if invalid
        return self


class VarSpec(BaseModel):
    universe: tuple[float, float]
    sets: dict[str, MFSpec]


class OutputSpec(VarSpec):
    name: str


class RuleSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    if_: dict[str, str] = Field(alias="if")
    then: str
    weight: float = 1.0
    description: str = ""


class FISSpec(BaseModel):
    name: str
    defaults: dict[str, float] = Field(default_factory=dict)
    inputs: dict[str, VarSpec]
    output: OutputSpec
    rules: list[RuleSpec]

    @model_validator(mode="after")
    def _check_references(self) -> FISSpec:
        ids = [r.id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.name}: duplicate rule ids")
        for r in self.rules:
            for var, label in r.if_.items():
                if var not in self.inputs:
                    raise ValueError(f"{r.id}: unknown input {var!r}")
                if label not in self.inputs[var].sets:
                    raise ValueError(f"{r.id}: input {var!r} has no set {label!r}")
            if r.then not in self.output.sets:
                raise ValueError(f"{r.id}: unknown output set {r.then!r}")
        unknown_defaults = set(self.defaults) - set(self.inputs)
        if unknown_defaults:
            raise ValueError(f"{self.name}: defaults for unknown inputs {sorted(unknown_defaults)}")
        return self


class FuzzyConfig(BaseModel):
    version: int
    stage1: FISSpec
    stage2: FISSpec


def load_config(path: str | Path | None = None) -> FuzzyConfig:
    """Load and validate a fuzzy configuration (defaults to the packaged default.yaml)."""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    raw: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    return FuzzyConfig.model_validate(raw)


def _variable(name: str, spec: VarSpec) -> LinguisticVariable:
    sets = {k: MembershipFunction(v.shape, tuple(v.params)) for k, v in spec.sets.items()}
    return LinguisticVariable(name=name, universe=spec.universe, sets=sets)


def build_fis(spec: FISSpec, resolution: int = 1001) -> MamdaniFIS:
    inputs: Mapping[str, LinguisticVariable] = {n: _variable(n, v) for n, v in spec.inputs.items()}
    output = _variable(spec.output.name, spec.output)
    rules = [
        Rule(r.id, dict(r.if_), r.then, weight=r.weight, description=r.description)
        for r in spec.rules
    ]
    return MamdaniFIS(inputs, output, rules, defaults=spec.defaults, resolution=resolution)
