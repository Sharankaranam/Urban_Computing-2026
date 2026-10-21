"""Fuzzy inference core: membership functions, variables, rules, engine, config."""

from fuzzy_tariff.fuzzy.config import FuzzyConfig, build_fis, load_config
from fuzzy_tariff.fuzzy.engine import FiredRule, InferenceResult, MamdaniFIS
from fuzzy_tariff.fuzzy.membership import MembershipFunction
from fuzzy_tariff.fuzzy.rules import Rule
from fuzzy_tariff.fuzzy.summarizer import (
    QUANTIFIERS,
    ProtoformEvaluation,
    StepTimeSeriesData,
    discover_best_protoforms,
    evaluate_protoform,
    generate_executive_narrative,
)
from fuzzy_tariff.fuzzy.variables import LinguisticVariable

__all__ = [
    "FiredRule",
    "FuzzyConfig",
    "InferenceResult",
    "LinguisticVariable",
    "MamdaniFIS",
    "MembershipFunction",
    "ProtoformEvaluation",
    "QUANTIFIERS",
    "Rule",
    "StepTimeSeriesData",
    "build_fis",
    "discover_best_protoforms",
    "evaluate_protoform",
    "generate_executive_narrative",
    "load_config",
]
