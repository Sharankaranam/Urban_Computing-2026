# ADR-0002: Membership functions and rules live in validated YAML

- Status: accepted
- Date: 2026-10-18

## Context
Domain experts (utility advisors) must be able to review and adjust rules without reading Python. Parameters are uncalibrated starting values and will change.

## Decision
Keep sets and rules in `src/fuzzy_tariff/fuzzy/default.yaml`, loaded through pydantic models that reject unordered parameters, unknown set references, duplicate rule IDs and defaults for unknown inputs.

## Alternatives considered
- Python constants: fast to write, but hides behaviour in code and invites silent edits.
- Database or UI-editable config: over-engineered for the current scope.

## Consequences
- A typo fails at load time, not at 2 am in production.
- Tuning tools can output a YAML file instead of patching code.
- Every YAML edit is a behaviour change and must update tests and docs (see AGENTS.md).
