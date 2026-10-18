"""IF-THEN rules. Antecedents are combined with AND (min); consequent is one output set."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rule:
    id: str
    antecedents: Mapping[str, str]
    consequent: str
    weight: float = 1.0
    description: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if not self.antecedents:
            raise ValueError(f"rule {self.id}: needs at least one antecedent")
        if not 0.0 < self.weight <= 1.0:
            raise ValueError(f"rule {self.id}: weight must be in (0, 1]")

    def __str__(self) -> str:
        cond = " AND ".join(f"{v} is {s}" for v, s in self.antecedents.items())
        return f"{self.id}: IF {cond} THEN {self.consequent}"
