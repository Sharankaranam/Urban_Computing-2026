"""Request/response models. These are the public contract: change with care (see AGENTS.md)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fuzzy_tariff.advisor.devices import Device
from fuzzy_tariff.labels import Lang


class ScoreRequest(BaseModel):
    P: float = Field(ge=0, le=100, description="Price percentile in reference window")
    A: float = Field(ge=0, le=1, description="Absolute price, normalised 0-1")
    G: float = Field(0.5, ge=0, le=1, description="Grid stress 0-1 (default neutral)")
    T: float = Field(0.0, ge=-1, le=1, description="Price trend -1..1 (default stable)")
    lang: Lang = "en"


class FiredRuleOut(BaseModel):
    id: str
    strength: float
    description: str


class ScoreResponse(BaseModel):
    score: float
    label: str
    text: str
    memberships: dict[str, float]
    fired_rules: list[FiredRuleOut]


class AdviceRequest(BaseModel):
    suitability: float = Field(ge=0, le=100)
    device: Device
    energy_kwh: float = Field(gt=0)
    deadline_hours: float = Field(gt=0)
    power_kw: float | None = Field(None, gt=0)
    lang: Lang = "en"


class AdviceResponse(BaseModel):
    action: str
    text: str
    urgency: float


class PlanRequest(BaseModel):
    scores: list[float] = Field(min_length=1, max_length=192, description="Suitability per slot")
    device: Device
    energy_kwh: float = Field(gt=0)
    power_kw: float | None = Field(None, gt=0)
    step_hours: float = Field(1.0, gt=0, le=1.0)


class PlanResponse(BaseModel):
    slots: list[int]
    required_hours: float


class TariffStepOut(BaseModel):
    time: str
    spot_eur_mwh: float
    net_load_mw: float
    energy_rp: float
    grid_rp: float
    sdl_rp: float
    total_rp: float
    score: float
    label: str
    text: str


class TariffPreviewResponse(BaseModel):
    season: str
    date: str
    steps: list[TariffStepOut]


class DeviceScheduleItem(BaseModel):
    id: str
    name: str
    power_kw: float = Field(gt=0)
    energy_kwh: float = Field(gt=0)
    deadline_hours: float = Field(default=24.0, ge=1.0, le=24.0)
    contiguous: bool = False
    priority: int = 1


class SmartScheduleRequest(BaseModel):
    season: str = "winter"
    max_concurrent_devices: int = Field(default=1, ge=1, le=10)
    max_total_kw: float | None = Field(default=None, gt=0)
    devices: list[DeviceScheduleItem]
    lang: Lang = "en"


class ScheduledDeviceResult(BaseModel):
    id: str
    name: str
    power_kw: float
    energy_kwh: float
    duration_hours: float
    slots: list[int]
    time_windows: list[str]
    avg_price_rp: float
    avg_fuzzy_score: float
    fuzzy_label: str
    stage2_action: str
    fired_rules: list[str]
    cost_chf: float
    peak_cost_chf: float
    saved_chf: float
    advice_text: str


class SmartScheduleResponse(BaseModel):
    season: str
    date: str
    max_concurrent_devices: int
    total_cost_chf: float
    total_peak_cost_chf: float
    total_savings_chf: float
    savings_percent: float
    cheapest_window_overall: str
    peak_window_to_avoid: str
    devices: list[ScheduledDeviceResult]
    hourly_allocations: list[list[str]]
    hourly_fuzzy_scores: list[float]
    hourly_fuzzy_labels: list[str]



