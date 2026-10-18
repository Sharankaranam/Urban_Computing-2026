"""Device profiles, urgency computation, stage-2 advice and slot planning."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from fuzzy_tariff.fuzzy.config import FuzzyConfig, build_fis, load_config
from fuzzy_tariff.fuzzy.engine import MamdaniFIS
from fuzzy_tariff.labels import Action


class Device(StrEnum):
    EV = "ev"
    HEAT_PUMP = "heat_pump"
    WASHING_MACHINE = "washing_machine"


@dataclass(frozen=True)
class DeviceProfile:
    default_power_kw: float
    contiguous: bool  # must run in one block (appliance cycle) or may be split (EV, heat pump)


DEVICE_PROFILES: dict[Device, DeviceProfile] = {
    Device.EV: DeviceProfile(default_power_kw=7.4, contiguous=False),
    Device.HEAT_PUMP: DeviceProfile(default_power_kw=2.0, contiguous=False),
    Device.WASHING_MACHINE: DeviceProfile(default_power_kw=1.0, contiguous=True),
}


@dataclass(frozen=True)
class DeviceRequest:
    device: Device
    energy_kwh: float
    deadline_hours: float
    power_kw: float | None = None

    @property
    def effective_power_kw(self) -> float:
        return self.power_kw or DEVICE_PROFILES[self.device].default_power_kw

    @property
    def required_hours(self) -> float:
        return self.energy_kwh / self.effective_power_kw


def urgency(req: DeviceRequest) -> float:
    """Required run time divided by time available, clipped to [0, 1]."""
    if req.deadline_hours <= 0:
        return 1.0
    return float(np.clip(req.required_hours / req.deadline_hours, 0.0, 1.0))


@dataclass(frozen=True)
class Advice:
    action: Action
    urgency: float
    score: float


class DeviceAdvisor:
    def __init__(self, fis: MamdaniFIS) -> None:
        self.fis = fis

    @classmethod
    def from_config(cls, cfg: FuzzyConfig | None = None) -> DeviceAdvisor:
        return cls(build_fis((cfg or load_config()).stage2))

    def advise(self, suitability: float, req: DeviceRequest) -> Advice:
        u = urgency(req)
        res = self.fis.infer(S=suitability, U=u)
        return Advice(action=Action(res.top_set), urgency=u, score=res.score)


def plan_slots(
    scores: Sequence[float],
    required_hours: float,
    step_hours: float = 1.0,
    contiguous: bool = False,
) -> list[int]:
    """Choose the slots with the highest suitability that cover ``required_hours``.

    Non-contiguous: top-k slots (ties -> earliest). Contiguous: best-average block.
    Returns slot indices in chronological order. Raises if the horizon is too short.
    """
    k = math.ceil(required_hours / step_hours - 1e-9)
    n = len(scores)
    if k <= 0:
        return []
    if k > n:
        raise ValueError(f"need {k} slots but only {n} available before the deadline")
    arr = np.asarray(scores, dtype=float)
    if contiguous:
        sums = np.convolve(arr, np.ones(k), mode="valid")
        start = int(np.argmax(sums))  # argmax returns the earliest maximum
        return list(range(start, start + k))
    order = sorted(range(n), key=lambda i: (-arr[i], i))
    return sorted(order[:k])
