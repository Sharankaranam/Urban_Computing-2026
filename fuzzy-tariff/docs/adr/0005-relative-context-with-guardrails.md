# ADR-0005: Relative percentile context plus absolute guardrail and flat-data guards

- Status: accepted
- Date: 2026-10-18

## Context
A price that is cheap in winter may be expensive in summer, so fixed CHF thresholds mislead. But purely relative labels can call an objectively high price "cheap", and noise on a flat tariff becomes fake structure.

## Decision
- P: percentile of the price within a reference window (previous 30 local days, same day type, plus the labelled day).
- A: absolute price normalised to an annual range, used by rules such as R03 to prevent "cheap" on objectively high prices.
- Flat guards: IQR below 0.005 CHF/kWh sets P to 50; annual range below 0.02 CHF/kWh sets A to 0.5; trend scale is floored.

## Alternatives considered
- Fixed thresholds: ignore season.
- Z-scores: sensitive to outliers and spikes.
- Percentile only: no absolute guardrail.

## Consequences
- Labels adapt to season and day type.
- Window length and day-type split are tunable parameters and must be reported in sensitivity analysis.
- 15-minute tariffs (EKZ) need the window and minimum block to be re-examined.
