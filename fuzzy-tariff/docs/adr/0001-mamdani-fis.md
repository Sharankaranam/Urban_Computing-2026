# ADR-0001: Mamdani FIS as the primary inference engine

- Status: accepted
- Date: 2026-10-18

## Context
Output labels must be explainable to utilities and users. The project is a Fuzzy Systems course project, so linguistic output sets matter.

## Decision
Use a Mamdani FIS: min for AND, min implication, max aggregation, centroid defuzzification. Output is a linguistic variable (avoid, wait, okay, good, ideal).

## Alternatives considered
- **Sugeno (TSK):** faster and easier to tune, but consequents are numbers, so rules read less naturally. Planned as a comparison engine, not the primary one.
- **Crisp thresholds / percentile bands:** the baselines we compare against.
- **Black-box ML:** needs labelled data we do not have and is hard to audit.

## Consequences
- Rules read as plain language and every answer lists fired rules.
- Centroid on a 1001-point grid is more expensive than Sugeno; vectorised and chunked, acceptable (a year of hourly data runs in seconds).
- Centroid can pull results towards the middle when many sets fire; hysteresis and min block compensate at label level.
