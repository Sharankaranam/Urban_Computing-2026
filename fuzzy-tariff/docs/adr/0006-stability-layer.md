# ADR-0006: Stability layer: hysteresis on memberships plus minimum block length

- Status: accepted
- Date: 2026-10-18

## Context
Even smooth memberships can make the argmax label flip when a score hovers near a boundary, and a single "ideal" hour is not actionable for an EV or appliance.

## Decision
Label by the strongest output set, but switch only if the new set beats the current one by at least 0.1 membership (hysteresis). For day-ahead sequences, replace runs shorter than 2 steps by the neighbouring label (minimum block).

## Alternatives considered
- Moving average on scores: delays real changes and blurs windows.
- Debounce in the UI only: leaves the API inconsistent.

## Consequences
- Fewer flips and zero isolated cheap windows in backtests (synthetic so far).
- The minimum block uses future information within the known day-ahead horizon; do not apply it to a live causal stream without redesign.
