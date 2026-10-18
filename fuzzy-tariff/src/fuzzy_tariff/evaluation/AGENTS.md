# AGENTS.md: evaluation

Scope: baselines, metrics, sensitivity, backtest.

- Every comparison must include the crisp baselines (fixed thresholds, percentile bands) on the **same** data and window.
- Report metrics, not impressions: flips/day, isolated cheap-window rate, seasonal label shares, EV cost vs naive and oracle.
- Be honest about what a metric can and cannot show. The EV-cost metric cannot distinguish methods that rank by price alone; do not present it as proof of superiority.
- Synthetic results are plumbing checks, not findings. Label them "synthetic" in every report.
- Sensitivity and tuning use seeds and held-out periods. Never tune and evaluate on the same period.
- Output tables as Markdown into `reports/` (git-ignored).
