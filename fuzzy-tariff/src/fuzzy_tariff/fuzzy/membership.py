"""Triangular and trapezoidal membership functions (vectorised, shoulder-safe)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

Shape = Literal["tri", "trap"]
_EXPECTED_PARAMS: dict[str, int] = {"tri": 3, "trap": 4}


def trimf(x: ArrayLike, a: float, b: float, c: float) -> NDArray[np.float64]:
    """Triangle with feet a, c and peak b. a == b or b == c gives a vertical edge."""
    xs = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        left = np.where(b > a, (xs - a) / (b - a), (xs >= b).astype(float))
        right = np.where(c > b, (c - xs) / (c - b), (xs <= b).astype(float))
    return np.clip(np.minimum(left, right), 0.0, 1.0)


def trapmf(x: ArrayLike, a: float, b: float, c: float, d: float) -> NDArray[np.float64]:
    """Trapezoid with feet a, d and plateau b..c. a == b or c == d gives a shoulder."""
    xs = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        left = np.where(b > a, (xs - a) / (b - a), (xs >= b).astype(float))
        right = np.where(d > c, (d - xs) / (d - c), (xs <= c).astype(float))
    return np.clip(np.minimum(left, right), 0.0, 1.0)


@dataclass(frozen=True)
class MembershipFunction:
    shape: Shape
    params: tuple[float, ...]

    def __post_init__(self) -> None:
        expected = _EXPECTED_PARAMS.get(self.shape)
        if expected is None:
            raise ValueError(f"unknown shape {self.shape!r}")
        if len(self.params) != expected:
            raise ValueError(f"{self.shape} needs {expected} params, got {len(self.params)}")
        if any(p2 < p1 for p1, p2 in zip(self.params, self.params[1:], strict=False)):
            raise ValueError(f"params must be non-decreasing: {self.params}")
        if self.params[0] == self.params[-1]:
            raise ValueError("membership function has zero width")

    def __call__(self, x: ArrayLike) -> NDArray[np.float64]:
        if self.shape == "tri":
            return trimf(x, *self.params)
        return trapmf(x, *self.params)

    def shifted(self, delta: float) -> MembershipFunction:
        return MembershipFunction(self.shape, tuple(p + delta for p in self.params))
