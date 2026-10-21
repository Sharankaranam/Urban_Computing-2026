"""FastAPI application. Thin layer: validation in, service calls, serialisation out."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
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
    EvaluateProtoformRequest,
    EvaluateProtoformResponse,
    FiredRuleOut,
    LinguisticOptionItem,
    LinguisticSummaryItem,
    LinguisticSummaryResponse,
    PlanRequest,
    PlanResponse,
    ScheduledDeviceResult,
    ScoreRequest,
    ScoreResponse,
    SmartScheduleRequest,
    SmartScheduleResponse,
    TariffPreviewResponse,
    TariffStepOut,
    TranslateRequest,
    TranslateResponse,
)
from fuzzy_tariff.fuzzy.summarizer import (
    QUALIFIER_LABELS,
    QUANTIFIER_LABELS,
    SUMMARIZER_LABELS,
    StepTimeSeriesData,
    discover_best_protoforms,
    evaluate_protoform,
    generate_executive_narrative,
)
from fuzzy_tariff.ingest.ekz import EkzTariffSource
from fuzzy_tariff.labels import Lang, action_text, label_text
from fuzzy_tariff.services import Services, get_services

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_BENCHMARK_CACHE: pd.DataFrame | None = None
_PRACTISING_CACHE: pd.DataFrame | None = None
_TRANSLATION_CACHE: dict[str, str] = {}

PRACTISING_SCENARIOS: dict[str, str] = {
    "autumn_dst": "2026-10-25",
    "november_wind": "2026-11-13",
    "winter_cold_snap": "2026-12-15",
    "holiday_flat": "2026-12-25",
    "january_spike": "2027-01-18",
    "february_solar": "2027-02-18",
}

BENCHMARK_SCENARIOS: dict[str, str] = {
    "winter": "2025-01-15",
    "spring": "2025-04-12",
    "summer": "2025-06-21",
    "autumn": "2025-10-15",
}


def _find_csv(filename: str) -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[4] / filename,
        Path(__file__).resolve().parents[3] / filename,
        Path(filename),
        Path("..") / filename,
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / filename,
    ]
    return next((c for c in candidates if c.exists()), None)


def _get_tariff_df(use_practising: bool = False) -> pd.DataFrame:
    global _BENCHMARK_CACHE, _PRACTISING_CACHE
    if use_practising:
        if _PRACTISING_CACHE is not None:
            return _PRACTISING_CACHE
        p = _find_csv("practising_tariff_4months_15min.csv")
        if p is not None:
            _PRACTISING_CACHE = pd.read_csv(p)
            return _PRACTISING_CACHE

    if _BENCHMARK_CACHE is not None:
        return _BENCHMARK_CACHE
    p = _find_csv("dynamic_tariff_2025_15min.csv")
    if p is not None:
        _BENCHMARK_CACHE = pd.read_csv(p)
        return _BENCHMARK_CACHE

    # Fallback to practicing file if benchmark is missing
    p_prac = _find_csv("practising_tariff_4months_15min.csv")
    if p_prac is not None:
        _BENCHMARK_CACHE = pd.read_csv(p_prac)
        return _BENCHMARK_CACHE

    raise FileNotFoundError("Dynamic tariff dataset CSV not found")


def _load_day_df(season_or_date: str) -> tuple[str, pd.DataFrame]:
    """Retrieve day slice from live EKZ API, 4-month practicing dataset, or 2025 benchmark."""
    key = season_or_date.lower().strip()

    # 1. Live EKZ API on-demand option
    if key in ("live_ekz", "live", "today"):
        try:
            source = EkzTariffSource()
            live_df = source.fetch_latest_day()
            if not live_df.empty:
                today_str = pd.Timestamp.now(tz="Europe/Zurich").strftime("%Y-%m-%d")
                live_reset = live_df.reset_index()
                live_reset["timestamp_utc"] = live_reset["timestamp_utc"].astype(str)
                day_slice = live_reset[live_reset["timestamp_utc"].str.startswith(today_str)].copy()
                if day_slice.empty:
                    day_slice = live_reset.iloc[:96].copy()
                if "net_load_mw" not in day_slice.columns:
                    day_slice["net_load_mw"] = 150.0
                if "spot_eur_mwh" not in day_slice.columns:
                    day_slice["spot_eur_mwh"] = 80.0
                return f"{today_str} (Live EKZ API)", day_slice.reset_index(drop=True)
        except Exception as exc:
            print(f"Warning: live EKZ API query fell back to practicing dataset ({exc})")

    # 2. Check practicing scenarios
    if key in PRACTISING_SCENARIOS:
        date_str = PRACTISING_SCENARIOS[key]
        prac_df = _get_tariff_df(use_practising=True)
        day_df = prac_df[prac_df["timestamp_utc"].str.startswith(date_str)].copy()
        if not day_df.empty:
            return date_str, day_df.reset_index(drop=True)

    # 3. Check direct date string in practicing range (2026 or 2027)
    if key.startswith("2026") or key.startswith("2027"):
        date_str = key[:10]
        prac_df = _get_tariff_df(use_practising=True)
        day_df = prac_df[prac_df["timestamp_utc"].str.startswith(date_str)].copy()
        if not day_df.empty:
            return date_str, day_df.reset_index(drop=True)

    # 4. Check benchmark scenarios
    date_str = BENCHMARK_SCENARIOS.get(key, key[:10] if len(key) >= 10 else "2025-01-15")
    bench_df = _get_tariff_df(use_practising=False)
    day_df = bench_df[bench_df["timestamp_utc"].str.startswith(date_str)].copy()
    if day_df.empty:
        # Try finding in practicing dataset as fallback
        prac_df = _get_tariff_df(use_practising=True)
        day_df = prac_df[prac_df["timestamp_utc"].str.startswith(date_str)].copy()
    if day_df.empty:
        day_df = bench_df.iloc[:96].copy()

    return date_str, day_df.reset_index(drop=True)


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


def _extract_step_timeseries_data(season: str, svc: Services) -> tuple[str, StepTimeSeriesData]:
    import numpy as np

    date_str, day_df = _load_day_df(season)
    n_slots = len(day_df)
    p_min = float(day_df["total_rp"].min())
    p_max = float(day_df["total_rp"].max())
    has_pgat = {"P", "A", "G", "T"}.issubset(day_df.columns)

    hours = np.zeros(n_slots, dtype=float)
    scores = np.zeros(n_slots, dtype=float)
    g_stress = np.zeros(n_slots, dtype=float)
    t_trend = np.zeros(n_slots, dtype=float)
    total_rp = np.zeros(n_slots, dtype=float)

    memberships: dict[str, list[float]] = {
        "avoid": [],
        "wait": [],
        "okay": [],
        "good": [],
        "ideal": [],
    }

    for s in range(n_slots):
        hours[s] = s * 0.25
        t_rp = float(day_df.loc[s, "total_rp"])
        total_rp[s] = t_rp

        if has_pgat and pd.notna(day_df.loc[s, "P"]):
            p = float(day_df.loc[s, "P"])
            a = float(day_df.loc[s, "A"])
            g = float(day_df.loc[s, "G"])
            t = float(day_df.loc[s, "T"])
        else:
            p = float(100.0 * (t_rp - p_min) / (p_max - p_min)) if p_max > p_min else 50.0
            a = float(t_rp / 100.0)
            net_load = float(day_df.loc[s, "net_load_mw"]) if "net_load_mw" in day_df.columns else 150.0
            g = float(max(0.0, min(1.0, (net_load - 100.0) / 100.0)))
            next_s = min(n_slots - 1, s + 8)
            diff = (float(day_df.loc[next_s, "total_rp"]) - t_rp) / 100.0
            t = float(max(-1.0, min(1.0, diff / 0.10)))

        g_stress[s] = g
        t_trend[s] = t

        res = svc.stage1.infer(P=p, A=a, G=g, T=t)
        scores[s] = res.score
        for k in ("avoid", "wait", "okay", "good", "ideal"):
            memberships[k].append(float(res.output_memberships.get(k, 0.0)))

    ts_data = StepTimeSeriesData(
        hours=hours,
        scores=scores,
        memberships={k: np.array(v, dtype=float) for k, v in memberships.items()},
        g_stress=g_stress,
        t_trend=t_trend,
        total_rp=total_rp,
    )
    return date_str, ts_data


def _run_smart_schedule(
    req: SmartScheduleRequest, svc: Services
) -> SmartScheduleResponse:
    date_str, day_df = _load_day_df(req.season)
    prices = day_df["total_rp"].astype(float).tolist()
    step_hours = 0.25
    n_slots = len(day_df)

    p_min = float(day_df["total_rp"].min())
    p_max = float(day_df["total_rp"].max())

    # 1. Compute Stage 1 Fuzzy Inference for all slots
    fuzzy_scores: list[float] = []
    fuzzy_labels: list[str] = []
    slot_rules: list[list[str]] = []

    has_pgat = {"P", "A", "G", "T"}.issubset(day_df.columns)

    for s in range(n_slots):
        total_rp = float(day_df.loc[s, "total_rp"])
        if has_pgat and pd.notna(day_df.loc[s, "P"]):
            p = float(day_df.loc[s, "P"])
            a = float(day_df.loc[s, "A"])
            g = float(day_df.loc[s, "G"])
            t = float(day_df.loc[s, "T"])
        else:
            p = float(100.0 * (total_rp - p_min) / (p_max - p_min)) if p_max > p_min else 50.0
            a = float(total_rp / 100.0)
            net_load = float(day_df.loc[s, "net_load_mw"]) if "net_load_mw" in day_df.columns else 150.0
            g = float(max(0.0, min(1.0, (net_load - 100.0) / 100.0)))
            next_s = min(n_slots - 1, s + 8)
            diff = (float(day_df.loc[next_s, "total_rp"]) - total_rp) / 100.0
            t = float(max(-1.0, min(1.0, diff / 0.10)))

        res = svc.stage1.infer(P=p, A=a, G=g, T=t)
        fuzzy_scores.append(res.score)
        fuzzy_labels.append(res.top_set)
        slot_rules.append([f.id for f in res.fired])

    # 2. Multi-device constraint allocator
    slot_counts = [0] * n_slots
    slot_kw = [0.0] * n_slots
    slot_allocations: list[list[str]] = [[] for _ in range(n_slots)]

    peak_start = int(17.5 / step_hours)
    peak_end = min(n_slots, int(20.5 / step_hours))
    peak_steps = list(range(peak_start, peak_end))
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
        deadline_step = min(n_slots, max(req_steps, int(dev.deadline_hours / step_hours)))

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

        loc_label = label_text(fuzzy_label, req.lang)
        loc_action = action_text(stage2_action, req.lang)
        advice = f"{loc_label} • {loc_action} ({windows_str})"

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

    n_hours = max(24, (n_slots + 3) // 4)
    for h in range(n_hours):
        devs_in_hour: set[str] = set()
        h_score_sum = 0.0
        count_in_hour = 0
        for q in range(4):
            idx = h * 4 + q
            if idx < n_slots:
                devs_in_hour.update(slot_allocations[idx])
                h_score_sum += fuzzy_scores[idx]
                count_in_hour += 1
        hourly_allocations.append(sorted(list(devs_in_hour)))
        avg_h_score = (h_score_sum / count_in_hour) if count_in_hour > 0 else 50.0
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
    date_str, day_df = _load_day_df(season)
    p_min = float(day_df["total_rp"].min())
    p_max = float(day_df["total_rp"].max())
    n_slots = len(day_df)

    has_pgat = {"P", "A", "G", "T"}.issubset(day_df.columns)

    steps: list[TariffStepOut] = []
    for s in range(n_slots):
        row = day_df.iloc[s]
        total_rp = float(row["total_rp"])
        if has_pgat and pd.notna(row.get("P")):
            p = float(row["P"])
            a = float(row["A"])
            g = float(row["G"])
            t = float(row["T"])
        else:
            p = float(100.0 * (total_rp - p_min) / (p_max - p_min)) if p_max > p_min else 50.0
            a = float(total_rp / 100.0)
            net_load = float(row["net_load_mw"]) if "net_load_mw" in day_df.columns else 150.0
            g = float(max(0.0, min(1.0, (net_load - 100.0) / 100.0)))
            next_s = min(n_slots - 1, s + 8)
            diff = (float(day_df.iloc[next_s]["total_rp"]) - total_rp) / 100.0
            t = float(max(-1.0, min(1.0, diff / 0.10)))

        res = svc.stage1.infer(P=p, A=a, G=g, T=t)
        time_str = str(row["timestamp_utc"])[11:16]
        spot_val = float(row["spot_eur_mwh"]) if "spot_eur_mwh" in day_df.columns else 75.0
        load_val = float(row["net_load_mw"]) if "net_load_mw" in day_df.columns else 150.0

        steps.append(
            TariffStepOut(
                time=time_str,
                spot_eur_mwh=round(spot_val, 2),
                net_load_mw=round(load_val, 2),
                energy_rp=round(float(row.get("energy_rp", total_rp * 0.5)), 2),
                grid_rp=round(float(row.get("grid_rp", total_rp * 0.5)), 2),
                sdl_rp=round(float(row.get("sdl_rp", 0.27)), 2),
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

    @app.post("/v1/translate", response_model=TranslateResponse)
    async def translate(req: TranslateRequest) -> TranslateResponse:
        s_lang = req.source_lang.lower().strip()
        t_lang = req.target_lang.lower().strip()
        text = req.text.strip()

        if s_lang == t_lang or not text:
            return TranslateResponse(
                original_text=req.text,
                translated_text=req.text,
                source_lang=s_lang,
                target_lang=t_lang,
                provider="identity",
            )

        cache_key = f"{s_lang}:{t_lang}:{text.lower()}"
        if cache_key in _TRANSLATION_CACHE:
            return TranslateResponse(
                original_text=req.text,
                translated_text=_TRANSLATION_CACHE[cache_key],
                source_lang=s_lang,
                target_lang=t_lang,
                provider="cache",
            )

        # Call free MyMemory API
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={s_lang}|{t_lang}"
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    translated = data.get("responseData", {}).get("translatedText")
                    if translated and "MYMEMORY WARNING" not in translated.upper():
                        _TRANSLATION_CACHE[cache_key] = translated
                        return TranslateResponse(
                            original_text=req.text,
                            translated_text=translated,
                            source_lang=s_lang,
                            target_lang=t_lang,
                            provider="mymemory_free_api",
                        )
        except Exception:
            pass

        return TranslateResponse(
            original_text=req.text,
            translated_text=req.text,
            source_lang=s_lang,
            target_lang=t_lang,
            provider="fallback",
        )

    @app.get("/v1/summarize/daily", response_model=LinguisticSummaryResponse)
    def summarize_daily(
        season: str = "winter",
        lang: Lang = "en",
        svc: Services = Depends(get_services),
    ) -> LinguisticSummaryResponse:
        date_str, ts_data = _extract_step_timeseries_data(season, svc)
        headline, bullets = generate_executive_narrative(ts_data, lang=lang)
        protoforms = discover_best_protoforms(ts_data, lang=lang)

        q_labels = QUANTIFIER_LABELS.get(lang, QUANTIFIER_LABELS["en"])
        b_labels = QUALIFIER_LABELS.get(lang, QUALIFIER_LABELS["en"])
        s_labels = SUMMARIZER_LABELS.get(lang, SUMMARIZER_LABELS["en"])

        items = [
            LinguisticSummaryItem(
                protoform_type=p.protoform_type,
                quantifier=p.quantifier,
                quantifier_label=p.quantifier_label,
                qualifier=p.qualifier,
                qualifier_label=p.qualifier_label,
                summarizer=p.summarizer,
                summarizer_label=p.summarizer_label,
                cardinality_ratio=p.cardinality_ratio,
                truth_degree=p.truth_degree,
                coverage_degree=p.coverage_degree,
                validity_score=p.validity_score,
                statement=p.statement,
            )
            for p in protoforms
        ]

        return LinguisticSummaryResponse(
            season=season,
            date=date_str,
            lang=lang,
            headline=headline,
            narrative=bullets,
            top_protoforms=items,
            quantifiers=[LinguisticOptionItem(id=k, label=v) for k, v in q_labels.items()],
            qualifiers=[LinguisticOptionItem(id=k, label=v) for k, v in b_labels.items()],
            summarizers=[LinguisticOptionItem(id=k, label=v) for k, v in s_labels.items()],
        )

    @app.post("/v1/summarize/evaluate", response_model=EvaluateProtoformResponse)
    def evaluate_summary(
        req: EvaluateProtoformRequest,
        svc: Services = Depends(get_services),
    ) -> EvaluateProtoformResponse:
        _, ts_data = _extract_step_timeseries_data(req.season, svc)
        try:
            ev = evaluate_protoform(
                quantifier=req.quantifier,
                qualifier=req.qualifier,
                summarizer=req.summarizer,
                data=ts_data,
                lang=req.lang,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        status = "valid" if ev.truth_degree >= 0.70 else ("moderate" if ev.truth_degree >= 0.40 else "false")

        return EvaluateProtoformResponse(
            protoform_type=ev.protoform_type,
            quantifier=ev.quantifier,
            quantifier_label=ev.quantifier_label,
            qualifier=ev.qualifier,
            qualifier_label=ev.qualifier_label,
            summarizer=ev.summarizer,
            summarizer_label=ev.summarizer_label,
            cardinality_ratio=ev.cardinality_ratio,
            truth_degree=ev.truth_degree,
            coverage_degree=ev.coverage_degree,
            validity_score=ev.validity_score,
            statement=ev.statement,
            status=status,
        )

    return app


app = create_app()


