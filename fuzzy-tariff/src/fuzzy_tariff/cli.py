"""Command-line interface: demo, backtest, plot-mf, serve."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from fuzzy_tariff.settings import Settings

log = logging.getLogger("fuzzy_tariff")


def _cmd_demo(args: argparse.Namespace) -> int:
    from fuzzy_tariff.labels import label_text
    from fuzzy_tariff.services import get_services

    svc = get_services()
    res = svc.stage1.infer(P=args.P, A=args.A, G=args.G, T=args.T)
    print(f"score = {res.score:.1f}  ->  {label_text(res.top_set, args.lang)}")
    for f in res.fired:
        print(f"  {f.id}  strength={f.strength:.2f}  {f.description}")
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    from fuzzy_tariff.evaluation.backtest import run_backtest, to_markdown
    from fuzzy_tariff.fuzzy.config import load_config
    from fuzzy_tariff.synthetic import SCENARIOS, generate_year
    from fuzzy_tariff.tariff_sim import DYNAMIC_SCENARIOS, TariffSpec, generate_dynamic_year

    cfg = load_config(Settings.from_env().config_path)
    thresholds: tuple[float, float, float, float] | None = None
    if args.scenario in SCENARIOS:
        df = generate_year(args.year, args.scenario, args.seed)  # simple hourly toy scenarios
    else:
        name = args.scenario.removeprefix("dynamic_")
        if name not in DYNAMIC_SCENARIOS:
            raise SystemExit(f"unknown scenario {args.scenario!r}")
        spec = TariffSpec()
        base = {"grid": spec.std_grid_rp, "energy": spec.std_energy_rp}.get(
            args.component, spec.std_grid_rp + spec.std_energy_rp + spec.sdl_rp
        )
        df = generate_dynamic_year(args.year, args.seed, name, spec, args.component)
        thresholds = (base * 0.75 / 100, base * 0.95 / 100, base * 1.05 / 100, base * 1.25 / 100)
    result = run_backtest(df, cfg, fixed_thresholds=thresholds)
    text = f"# Backtest: {args.scenario} (seed {args.seed}, year {args.year})\n\n"
    text += to_markdown(result.summary) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        log.info("wrote %s", args.out)
    print(text)
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    from fuzzy_tariff.tariff_sim import generate_spot_and_load, simulate_dynamic_tariff

    spot, load = generate_spot_and_load(args.year, args.seed, args.scenario)
    tariff = simulate_dynamic_tariff(spot, load)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tariff.round(4).to_csv(args.out, index_label="timestamp_utc")
    print(f"wrote {args.out} ({len(tariff)} rows, 15-minute steps)")
    return 0


def _cmd_plot_tariff(args: argparse.Namespace) -> int:
    from fuzzy_tariff.tariff_sim import generate_spot_and_load, simulate_dynamic_tariff
    from fuzzy_tariff.viz import plot_tariff_days

    spot, load = generate_spot_and_load(2025, 0, "baseline")
    tariff = simulate_dynamic_tariff(spot, load)
    print(f"wrote {plot_tariff_days(tariff, ['2025-01-15', '2025-06-21'], args.out)}")
    return 0


def _cmd_plot(args: argparse.Namespace) -> int:
    from fuzzy_tariff.fuzzy.config import load_config
    from fuzzy_tariff.viz import plot_membership_functions

    cfg = load_config(Settings.from_env().config_path)
    path = plot_membership_functions(cfg.stage1, args.out)
    print(f"wrote {path}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("fuzzy_tariff.api.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    from fuzzy_tariff.api.main import _extract_step_timeseries_data
    from fuzzy_tariff.fuzzy.summarizer import discover_best_protoforms, generate_executive_narrative
    from fuzzy_tariff.services import get_services

    svc = get_services()
    date_str, ts_data = _extract_step_timeseries_data(args.scenario, svc)
    headline, bullets = generate_executive_narrative(ts_data, lang=args.lang)
    protoforms = discover_best_protoforms(ts_data, lang=args.lang)

    print(f"\n📢 {headline}\n")
    print(f"Date: {date_str} (Scenario: {args.scenario})\n")
    print("Executive Narrative:")
    for b in bullets:
        clean = b.replace("**", "")
        print(f"  • {clean}")
    print("\nVerified Fuzzy Protoforms (Yager / Kacprzyk):")
    for p in protoforms:
        print(f"  [{p.truth_degree:.2f} Truth, {p.coverage_degree:.2f} Cov] {p.statement}")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fuzzy-tariff", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="score one hour from crisp inputs")
    demo.add_argument("--P", type=float, default=12.0)
    demo.add_argument("--A", type=float, default=0.30)
    demo.add_argument("--G", type=float, default=0.20)
    demo.add_argument("--T", type=float, default=0.0)
    demo.add_argument("--lang", choices=["en", "de", "fr", "it"], default="en")
    demo.set_defaults(func=_cmd_demo)

    bt = sub.add_parser("backtest", help="compare fuzzy vs crisp baselines on a scenario")
    bt.add_argument(
        "--scenario",
        default="dynamic_baseline",
        help="toy: baseline|winter_evening_peak|solar_midday_dip|flat|spike; "
        "EKZ-style 15-min: dynamic_baseline|dynamic_cold_snap|dynamic_pv_surplus|dynamic_spike",
    )
    bt.add_argument("--component", choices=["grid", "energy", "total"], default="grid")
    bt.add_argument("--year", type=int, default=2025)
    bt.add_argument("--seed", type=int, default=0)
    bt.add_argument("--out", default=None)
    bt.set_defaults(func=_cmd_backtest)

    sim = sub.add_parser("simulate-tariff", help="write an EKZ-style 15-min dynamic tariff CSV")
    sim.add_argument("--year", type=int, default=2025)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--scenario", default="baseline")
    sim.add_argument("--out", default="data/synthetic/dynamic_tariff.csv")
    sim.set_defaults(func=_cmd_simulate)

    ptar = sub.add_parser("plot-tariff", help="figure of example days of the simulated tariff")
    ptar.add_argument("--out", default="reports/dynamic_tariff_examples.png")
    ptar.set_defaults(func=_cmd_plot_tariff)

    plot = sub.add_parser("plot-mf", help="plot membership functions (needs viz extra)")
    plot.add_argument("--out", default="reports/membership_functions.png")
    plot.set_defaults(func=_cmd_plot)

    serve = sub.add_parser("serve", help="run the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_cmd_serve)

    summ = sub.add_parser("summarize", help="linguistic summarization of a tariff day")
    summ.add_argument("--scenario", default="winter", help="winter|summer|autumn_dst|winter_cold_snap|january_spike|february_solar")
    summ.add_argument("--lang", choices=["en", "de", "fr", "it"], default="en")
    summ.set_defaults(func=_cmd_summarize)

    args = parser.parse_args(argv)
    logging.basicConfig(level=Settings.from_env().log_level, format="%(levelname)s %(message)s")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
