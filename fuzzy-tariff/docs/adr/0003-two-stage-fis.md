# ADR-0003: Two-stage (hierarchical) FIS

- Status: accepted
- Date: 2026-10-18

## Context
Inputs are P, A, G, T (price context and grid) plus user urgency and device. One rule table over all of them would explode combinatorially and lose readability.

## Decision
Stage 1 scores the hour from price and grid inputs (15 rules). Stage 2 combines that score with urgency to produce an action (6 rules).

## Alternatives considered
- Single FIS with 6 inputs: about 5x3x3x3x5x3 potential combinations; unmaintainable.
- Device logic in plain code: loses the fuzzy treatment of "tight deadline".

## Consequences
- Each rule base is small enough to review in one sitting.
- Stage-1 output is reusable for the timeline view, independent of any device.
- Errors can be localised: stage 1 bad means labels wrong; stage 2 bad means advice wrong.
