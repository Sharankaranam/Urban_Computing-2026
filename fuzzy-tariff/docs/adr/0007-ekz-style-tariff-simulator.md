# ADR-0007: EKZ-style dynamic tariff simulator instead of toy price curves

- Status: accepted
- Date: 2026-10-18

## Context
The project targets dynamic tariffs. Real ones exist only since 2026 and have no public history. Our first synthetic prices were hourly toy curves that did not behave like a real tariff (no bands, no price parity, no 15-minute steps, no component structure).

## Decision
Generate tariffs with the structure EKZ publishes: energy component from the spot price, grid component from the squared net load, bands around a standard tariff, daily price parity, at most 2 h clipping per side, 15-minute resolution. Keep the generator input-agnostic so real spot prices and real grid load can replace the synthetic ones.

## Alternatives considered
- Keep toy curves: unrealistic structure would make results meaningless for tariff design questions.
- Wait for real data: blocks the project; logging real EKZ data starts now in parallel.
- Reproduce EKZ's MIP exactly: needs a solver dependency (SCIP) and EKZ's inputs; a heuristic reproduces the constraints.

## Consequences
- The fuzzy pipeline is developed on 15-minute data with realistic constraints (bounded spread, parity).
- Parameters in time units are expressed in hours (min block, trend horizon) and converted by index spacing.
- Standard levels and the standard load profile are placeholders until taken from the tariff sheet.
- Results remain simulated evidence; real EKZ logs and the ETH/EKZ pilot dataset are needed for claims.
