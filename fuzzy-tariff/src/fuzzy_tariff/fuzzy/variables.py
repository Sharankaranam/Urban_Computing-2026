"""Linguistic variables: a named universe with labelled fuzzy sets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuzzy_tariff.fuzzy.membership import MembershipFunction


@dataclass(frozen=True)
class LinguisticVariable:
    name: str
    universe: tuple[float, float]
    sets: Mapping[str, MembershipFunction]

    def __post_init__(self) -> None:
        lo, hi = self.universe
        if not lo < hi:
            raise ValueError(f"{self.name}: universe must satisfy lo < hi")
        if not self.sets:
            raise ValueError(f"{self.name}: needs at least one fuzzy set")

    def clip(self, x: ArrayLike) -> NDArray[np.float64]:
        lo, hi = self.universe
        return np.clip(np.asarray(x, dtype=float), lo, hi)

    def fuzzify(self, x: ArrayLike) -> dict[str, NDArray[np.float64]]:
        """Membership degree of x in every set (inputs are clipped to the universe)."""
        xs = self.clip(x)
        return {label: mf(xs) for label, mf in self.sets.items()}
