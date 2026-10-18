"""FastAPI application. Thin layer: validation in, service calls, serialisation out."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from fuzzy_tariff import __version__
from fuzzy_tariff.advisor.devices import DEVICE_PROFILES, DeviceRequest, plan_slots
from fuzzy_tariff.api.schemas import (
    AdviceRequest,
    AdviceResponse,
    DeviceScheduleItem,
    FiredRuleOut,
    PlanRequest,
    PlanResponse,
    ScheduledDeviceResult,
    ScoreRequest,
    ScoreResponse,
    SmartScheduleRequest,
    SmartScheduleResponse,
    TariffPreviewResponse,
    TariffStepOut,
)
from fuzzy_tariff.labels import Lang, action_text, label_text
from fuzzy_tariff.services import Services, get_services

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CSV_CACHE: pd.DataFrame | None = None


def _get_tariff_df() -> pd.DataFrame:
    global _CSV_CACHE
    if _CSV_CACHE is not None:
        return _CSV_CACHE

    candidates = [
        Path(__file__).resolve().parents[4] / "dynamic_tariff_2025_15min.csv",
        Path(__file__).resolve().parents[3] / "dynamic_tariff_2025_15min.csv",
        Path("dynamic_tariff_2025_15min.csv"),
        Path("../dynamic_tariff_2025_15min.csv"),
    ]
    p = next((c for c in candidates if c.exists()), None)
    if p is not None:
        _CSV_CACHE = pd.read_csv(p)
        return _CSV_CACHE
    raise FileNotFoundError("dynamic_tariff_2025_15min.csv not found")


def _format_time_step(step: int) -> str:
    h = (step * 15) // 60
    m = (step * 15) % 60
    return f"{h:02d}:{m:02d}"


def _group_slot_intervals(slots: list[int]) -> list[str]:
    if not slots:
        return []
    sorted_slots = sorted(slots)
    intervals: list[tuple[int, int]] = []
    start = prev = sorted_slots[0]
    for s in sorted_slots[1:]:
        if s == prev + 1:
            prev = s
        else:
            intervals.append((start, prev + 1))
            start = prev = s
    intervals.append((start, prev + 1))
    return [f"{_format_time_step(s)} – {_format_time_step(e)}" for s, e in intervals]


def _run_smart_schedule(
    req: SmartScheduleRequest, svc: Services
) -> SmartScheduleResponse:
    dates = {
        "winter": "2025-01-15",
        "spring": "2025-04-12",
        "summer": "2025-06-21",
        "autumn": "2025-10-15",
    }
    date_str = dates.get(req.season.lower(), "2025-01-15")
    df = _get_tariff_df()
    day_df = df[df["timestamp_utc"].str.startswith(date_str)].copy().reset_index(drop=True)
    if day_df.empty:
        day_df = df.iloc[:96].copy().reset_index(drop=True)

    prices = day_df["total_rp"].astype(float).tolist()
    step_hours = 0.25

    p_min = float(day_df["total_rp"].min())
    p_max = float(day_df["total_rp"].max())

    # 1. Compute Stage 1 Fuzzy Inference for all 96 slots
    fuzzy_scores: list[float] = []
    fuzzy_labels: list[str] = []
    slot_rules: list[list[str]] = []

    for s in range(96):
        total_rp = float(day_df.loc[s, "total_rp"])
        p = float(100.0 * (total_rp - p_min) / (p_max - p_min)) if p_max > p_min else 50.0
        a = float(total_rp / 100.0)
        net_load = float(day_df.loc[s, "net_load_mw"])
        g = float(max(0.0, min(1.0, (net_load - 100.0) / 100.0)))
        next_s = min(95, s + 8)
        diff = (float(day_df.loc[next_s, "total_rp"]) - total_rp) / 100.0
        t = float(max(-1.0, min(1.0, diff / 0.10)))

        res = svc.stage1.infer(P=p, A=a, G=g, T=t)
        fuzzy_scores.append(res.score)
        fuzzy_labels.append(res.top_set)
        slot_rules.append([f.id for f in res.fired])

    # 2. Multi-device constraint allocator
    slot_counts = [0] * 96
    slot_kw = [0.0] * 96
    slot_allocations: list[list[str]] = [[] for _ in range(96)]

    peak_steps = list(range(70, 82))
    peak_avg_rp = sum(prices[s] for s in peak_steps) / len(peak_steps) if peak_steps else 34.0

    scheduled_devices: list[ScheduledDeviceResult] = []
    total_cost_chf = 0.0
    total_peak_cost_chf = 0.0

    sorted_devs = sorted(
        req.devices,
        key=lambda d: (not d.contiguous, d.deadline_hours, -d.power_kw)
    )

    for dev in sorted_devs:
        req_steps = max(1, round(dev.energy_kwh / dev.power_kw / step_hours))
        deadline_step = min(96, max(req_steps, int(dev.deadline_hours / step_hours)))

        def can_use_slot(s: int) -> bool:
            if slot_counts[s] >= req.max_concurrent_devices:
                return False
            if req.max_total_kw and (slot_kw[s] + dev.power_kw > req.max_total_kw):
                return False
            return True

        chosen_slots: list[int] = []
        if dev.contiguous:
            best_block: list[int] | None = None
            best_score = -1.0
            for start in range(0, max(1, deadline_step - req_steps + 1)):
                block = list(range(start, start + req_steps))
                if all(can_use_slot(s) for s in block):
                    sc = sum(fuzzy_scores[s] for s in block) / len(block)
                    if sc > best_score:
                        best_score = sc
                        best_block = block
            if best_block:
                chosen_slots = best_block
            else:
                candidates = [s for s in range(0, deadline_step)]
                candidates.sort(key=lambda s: fuzzy_scores[s], reverse=True)
                chosen_slots = sorted(candidates[:req_steps])
        else:
            candidates = [s for s in range(0, deadline_step) if can_use_slot(s)]
            if len(candidates) < req_steps:
                candidates = list(range(0, deadline_step))
            candidates.sort(key=lambda s: fuzzy_scores[s], reverse=True)
            chosen_slots = sorted(candidates[:req_steps])

        for s in chosen_slots:
            slot_counts[s] += 1
            slot_kw[s] += dev.power_kw
            slot_allocations[s].append(dev.name)

        windows = _group_slot_intervals(chosen_slots)
        avg_rp = (
            sum(prices[s] for s in chosen_slots) / len(chosen_slots)
            if chosen_slots
            else 20.0
        )
        avg_score = (
            sum(fuzzy_scores[s] for s in chosen_slots) / len(chosen_slots)
            if chosen_slots
            else 50.0
        )
        cost_chf = (dev.energy_kwh * avg_rp) / 100.0
        peak_cost_chf = (dev.energy_kwh * peak_avg_rp) / 100.0
        saved_chf = max(0.0, peak_cost_chf - cost_chf)

        total_cost_chf += cost_chf
        total_peak_cost_chf += peak_cost_chf

        duration_hours = len(chosen_slots) * step_hours
        windows_str = ", ".join(windows) if windows else "Flexible overnight"

        urg = min(1.0, max(0.0, duration_hours / max(0.1, dev.deadline_hours)))

        active_rules_set: set[str] = set()
        for s in chosen_slots:
            active_rules_set.update(slot_rules[s])
        
        stage2_rule = "D01" if avg_score >= 75 else ("D06" if urg > 0.8 else "D02")
        active_rules_set.add(stage2_rule)

        stage2_action = "start_now" if avg_score >= 60 or urg > 0.8 else "wait"

        fuzzy_label = (
            "ideal" if avg_score >= 80
            else ("good" if avg_score >= 60
            else ("okay" if avg_score >= 40
            else ("wait" if avg_score >= 25 else "avoid")))
        )

        advice = (
            f"Fuzzy Suitability: {avg_score:.1f}/100 ({fuzzy_label.upper()}) • "
            f"Optimal time: {windows_str} (Avg tariff: {avg_rp:.1f} Rp./kWh)"
        )

        scheduled_devices.append(
            ScheduledDeviceResult(
                id=dev.id,
                name=dev.name,
                power_kw=dev.power_kw,
                energy_kwh=dev.energy_kwh,
                duration_hours=round(duration_hours, 2),
                slots=chosen_slots,
                time_windows=windows,
                avg_price_rp=round(avg_rp, 2),
                avg_fuzzy_score=round(avg_score, 1),
                fuzzy_label=fuzzy_label,
                stage2_action=stage2_action,
                fired_rules=sorted(list(active_rules_set))[:5],
                cost_chf=round(cost_chf, 2),
                peak_cost_chf=round(peak_cost_chf, 2),
                saved_chf=round(saved_chf, 2),
                advice_text=advice,
            )
        )

    hourly_allocations: list[list[str]] = []
    hourly_fuzzy_scores: list[float] = []
    hourly_fuzzy_labels: list[str] = []

    for h in range(24):
        devs_in_hour: set[str] = set()
        h_score_sum = 0.0
        for q in range(4):
            idx = h * 4 + q
            devs_in_hour.update(slot_allocations[idx])
            h_score_sum += fuzzy_scores[idx]
        hourly_allocations.append(sorted(list(devs_in_hour)))
        avg_h_score = h_score_sum / 4.0
        hourly_fuzzy_scores.append(round(avg_h_score, 1))
        h_label = (
            "ideal" if avg_h_score >= 80
            else ("good" if avg_h_score >= 60
            else ("okay" if avg_h_score >= 40
            else ("wait" if avg_h_score >= 25 else "avoid")))
        )
        hourly_fuzzy_labels.append(h_label)

    total_saved = max(0.0, total_peak_cost_chf - total_cost_chf)
    pct = (
        (total_saved / total_peak_cost_chf * 100.0)
        if total_peak_cost_chf > 0
        else 0.0
    )

    return SmartScheduleResponse(
        season=req.season,
        date=date_str,
        max_concurrent_devices=req.max_concurrent_devices,
        total_cost_chf=round(total_cost_chf, 2),
        total_peak_cost_chf=round(total_peak_cost_chf, 2),
        total_savings_chf=round(total_saved, 2),
        savings_percent=round(pct, 1),
        cheapest_window_overall="01:00 – 05:00",
        peak_window_to_avoid="17:30 – 20:30",
        devices=scheduled_devices,
        hourly_allocations=hourly_allocations,
        hourly_fuzzy_scores=hourly_fuzzy_scores,
        hourly_fuzzy_labels=hourly_fuzzy_labels,
    )



def _load_preview_steps(
    season: str, lang: Lang, svc: Services
) -> tuple[str, list[TariffStepOut]]:
    dates = {
        "winter": "2025-01-15",
        "spring": "2025-04-12",
        "summer": "2025-06-21",
        "autumn": "2025-10-15",
    }
    date_str = dates.get(season.lower(), "2025-01-15")
    df = _get_tariff_df()
    day_df = df[df["timestamp_utc"].str.startswith(date_str)].copy()
    if day_df.empty:
        day_df = df.iloc[:96].copy()

    p_min = float(day_df["total_rp"].min())
    p_max = float(day_df["total_rp"].max())

    steps: list[TariffStepOut] = []
    for _, row in day_df.iterrows():
        total_rp = float(row["total_rp"])
        p = float(100.0 * (total_rp - p_min) / (p_max - p_min)) if p_max > p_min else 50.0
        a = float(total_rp / 100.0)
        net_load = float(row["net_load_mw"])
        g = float(max(0.0, min(1.0, (net_load - 100.0) / 100.0)))
        res = svc.stage1.infer(P=p, A=a, G=g, T=0.0)
        time_str = str(row["timestamp_utc"])[11:16]
        steps.append(
            TariffStepOut(
                time=time_str,
                spot_eur_mwh=round(float(row["spot_eur_mwh"]), 2),
                net_load_mw=round(net_load, 2),
                energy_rp=round(float(row["energy_rp"]), 2),
                grid_rp=round(float(row["grid_rp"]), 2),
                sdl_rp=round(float(row["sdl_rp"]), 2),
                total_rp=round(total_rp, 2),
                score=round(float(res.score), 1),
                label=res.top_set,
                text=label_text(res.top_set, lang),
            )
        )
    return date_str, steps


def create_app() -> FastAPI:
    app = FastAPI(title="fuzzy-tariff", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        index_file = _STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>fuzzy-tariff API is running. Visit <a href='/docs'>/docs</a></h1>")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/v1/tariff/preview", response_model=TariffPreviewResponse)
    def tariff_preview(
        season: str = "winter",
        lang: Lang = "en",
        svc: Services = Depends(get_services),
    ) -> TariffPreviewResponse:
        date_str, steps = _load_preview_steps(season, lang, svc)
        return TariffPreviewResponse(season=season, date=date_str, steps=steps)

    @app.post("/v1/smart-schedule", response_model=SmartScheduleResponse)
    def smart_schedule(
        req: SmartScheduleRequest, svc: Services = Depends(get_services)
    ) -> SmartScheduleResponse:
        return _run_smart_schedule(req, svc)


    @app.post("/v1/score", response_model=ScoreResponse)
    def score(req: ScoreRequest, svc: Services = Depends(get_services)) -> ScoreResponse:
        res = svc.stage1.infer(P=req.P, A=req.A, G=req.G, T=req.T)
        if res.no_rule_fired:
            raise HTTPException(status_code=500, detail="no rule fired: rule base has a gap")
        return ScoreResponse(
            score=res.score,
            label=res.top_set,
            text=label_text(res.top_set, req.lang),
            memberships=res.output_memberships,
            fired_rules=[FiredRuleOut(**f.__dict__) for f in res.fired],
        )

    @app.post("/v1/advice", response_model=AdviceResponse)
    def advice(req: AdviceRequest, svc: Services = Depends(get_services)) -> AdviceResponse:
        request = DeviceRequest(req.device, req.energy_kwh, req.deadline_hours, req.power_kw)
        result = svc.advisor.advise(req.suitability, request)
        return AdviceResponse(
            action=result.action.value,
            text=action_text(result.action, req.lang),
            urgency=result.urgency,
        )

    @app.post("/v1/plan", response_model=PlanResponse)
    def plan(req: PlanRequest) -> PlanResponse:
        profile = DEVICE_PROFILES[req.device]
        power = req.power_kw or profile.default_power_kw
        required = req.energy_kwh / power
        try:
            slots = plan_slots(req.scores, required, req.step_hours, profile.contiguous)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return PlanResponse(slots=slots, required_hours=required)

    @app.get("/v1/config")
    def config(svc: Services = Depends(get_services)) -> dict[str, Any]:
        return svc.config.model_dump(by_alias=True)

    return app


app = create_app()


