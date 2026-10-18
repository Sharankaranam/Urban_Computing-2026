"""Mamdani fuzzy inference system (min-AND, min-implication, max-aggregation, centroid).

Implemented on NumPy so every step is inspectable and vectorised for backtesting.
See docs/adr/0004-own-numpy-engine.md for why we do not depend on scikit-fuzzy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuzzy_tariff.fuzzy.rules import Rule
from fuzzy_tariff.fuzzy.variables import LinguisticVariable

_CHUNK = 4096


@dataclass(frozen=True)
class FiredRule:
    id: str
    strength: float
    description: str = ""


@dataclass(frozen=True)
class InferenceResult:
    score: float
    output_memberships: dict[str, float]
    fired: list[FiredRule] = field(default_factory=list)
    no_rule_fired: bool = False

    @property
    def top_set(self) -> str:
        return max(self.output_memberships, key=lambda k: self.output_memberships[k])


@dataclass(frozen=True)
class InferenceBatch:
    scores: NDArray[np.float64]
    strengths: NDArray[np.float64]  # (n, n_rules)
    no_rule_fired: NDArray[np.bool_]


class MamdaniFIS:
    def __init__(
        self,
        inputs: Mapping[str, LinguisticVariable],
        output: LinguisticVariable,
        rules: Sequence[Rule],
        defaults: Mapping[str, float] | None = None,
        resolution: int = 1001,
    ) -> None:
        self.inputs = dict(inputs)
        self.output = output
        self.rules = list(rules)
        self.defaults = dict(defaults or {})
        if resolution < 101:
            raise ValueError("resolution must be >= 101")
        self._validate()
        lo, hi = output.universe
        self._u = np.linspace(lo, hi, resolution)
        self._out_mu = {name: mf(self._u) for name, mf in output.sets.items()}
        self._required = sorted({v for r in self.rules for v in r.antecedents})

    def _validate(self) -> None:
        ids = [r.id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rule ids")
        for r in self.rules:
            for var, label in r.antecedents.items():
                if var not in self.inputs:
                    raise ValueError(f"{r.id}: unknown input variable {var!r}")
                if label not in self.inputs[var].sets:
                    raise ValueError(f"{r.id}: {var!r} has no set {label!r}")
            if r.consequent not in self.output.sets:
                raise ValueError(f"{r.id}: unknown output set {r.consequent!r}")

    # ---- inference -------------------------------------------------------------------
    def _prepare(self, crisp: Mapping[str, ArrayLike]) -> dict[str, NDArray[np.float64]]:
        unknown = set(crisp) - set(self.inputs)
        if unknown:
            raise ValueError(f"unknown inputs: {sorted(unknown)}")
        values: dict[str, NDArray[np.float64]] = {}
        for name in self._required:
            if name in crisp:
                values[name] = np.atleast_1d(np.asarray(crisp[name], dtype=float))
            elif name in self.defaults:
                values[name] = np.atleast_1d(np.asarray(self.defaults[name], dtype=float))
            else:
                raise KeyError(f"missing input {name!r}")
        n = max(v.shape[0] for v in values.values())
        out: dict[str, NDArray[np.float64]] = {}
        for name, v in values.items():
            if v.shape[0] not in (1, n):
                raise ValueError(f"input {name!r} has length {v.shape[0]}, expected {n}")
            out[name] = np.broadcast_to(v, (n,))
        return out

    def _rule_strengths(self, values: Mapping[str, NDArray[np.float64]]) -> NDArray[np.float64]:
        n = next(iter(values.values())).shape[0]
        fuzzified = {name: self.inputs[name].fuzzify(v) for name, v in values.items()}
        strengths = np.zeros((n, len(self.rules)))
        for j, rule in enumerate(self.rules):
            s = np.ones(n)
            for var, label in rule.antecedents.items():
                s = np.minimum(s, fuzzified[var][label])
            strengths[:, j] = s * rule.weight
        return strengths

    def infer_many(self, **crisp: ArrayLike) -> InferenceBatch:
        values = self._prepare(crisp)
        strengths = self._rule_strengths(values)
        n = strengths.shape[0]
        sets = list(self.output.sets)
        cons_idx = {s: [j for j, r in enumerate(self.rules) if r.consequent == s] for s in sets}
        clipped = np.zeros((n, len(sets)))
        for k, s in enumerate(sets):
            if cons_idx[s]:
                clipped[:, k] = strengths[:, cons_idx[s]].max(axis=1)
        mu = np.stack([self._out_mu[s] for s in sets])  # (K, U)
        scores = np.empty(n)
        empty = np.zeros(n, dtype=bool)
        mid = float(self._u.mean())
        for start in range(0, n, _CHUNK):
            sl = slice(start, start + _CHUNK)
            agg = np.minimum(clipped[sl, :, None], mu[None, :, :]).max(axis=1)  # (m, U)
            area = agg.sum(axis=1)
            ok = area > 1e-12
            centroid = np.full(agg.shape[0], mid)
            centroid[ok] = (agg[ok] @ self._u) / area[ok]
            scores[sl] = centroid
            empty[sl] = ~ok
        return InferenceBatch(scores=scores, strengths=strengths, no_rule_fired=empty)

    def infer(self, **crisp: float) -> InferenceResult:
        batch = self.infer_many(**crisp)
        score = float(batch.scores[0])
        fired = [
            FiredRule(r.id, float(batch.strengths[0, j]), r.description)
            for j, r in enumerate(self.rules)
            if batch.strengths[0, j] > 0
        ]
        fired.sort(key=lambda f: f.strength, reverse=True)
        return InferenceResult(
            score=score,
            output_memberships=self.output_memberships_at(score),
            fired=fired,
            no_rule_fired=bool(batch.no_rule_fired[0]),
        )

    def output_memberships_at(self, score: float) -> dict[str, float]:
        x = self.output.clip(score)
        return {name: float(mf(x)) for name, mf in self.output.sets.items()}
