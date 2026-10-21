# PRD: Fuzzy Guidance for Dynamic Electricity Tariffs

| | |
|---|---|
| **Status** | Draft v0.1 (scaffold implemented, pilot not started) |
| **Date** | 2026-10-18 |
| **Owner** | _TBD (project lead)_ |
| **Course context** | Fuzzy Systems project |
| **Related** | `architecture.md`, `docs/project.md`, `docs/flow.md`, `docs/adr/` |

---

## 1. Problem

Since 1 January 2026 Swiss utilities may offer time-variable (dynamic) tariffs, initially for grid usage. The aim is to move flexible consumption (EV charging, heat pumps, appliances, batteries) to hours when electricity is cheap and the grid is less stressed.

Households, however, think in words ("cheap", "a bit expensive", "good time to charge the car"), not in CHF/kWh. A raw price such as 0.14 CHF/kWh carries no meaning without a reference point, and fixed thresholds mislead because context changes what "cheap" means (a cheap January price can be an expensive July price). Unexplained dynamic tariffs risk being ignored or misunderstood, and their benefit for the grid and for households is lost.

**Core gap:** price signal (CHF/kWh) to human decision ("should I charge now?").

## 2. Why fuzzy logic

| Need | Fuzzy-systems answer |
|---|---|
| Human categories without sharp borders ("cheap" / "normal") | Linguistic variables with overlapping membership functions |
| Meaning depends on context (season, day type, grid state) | Several inputs combined by readable IF-THEN rules |
| Labels must not flip when a price crosses a cut-off by 0.1 Rp | Gradual memberships plus hysteresis on memberships |
| Utilities and regulators must explain the guidance | Rule base is auditable; every answer lists the rules that fired |
| Little labelled data exists for new tariffs | Expert knowledge encoded directly, tuned with data later |

## 3. Goals and non-goals

### Goals
- **G1** Translate hourly (or 15-minute) tariff data into one of five plain-language labels, relative to context.
- **G2** Give device-specific advice (start now / wait / must start) that respects the user's deadline.
- **G3** Be explainable: every label comes with the rules that produced it.
- **G4** Be stable: no flickering labels, no isolated one-hour "best time" windows.
- **G5** Be evaluated honestly against crisp baselines (fixed CHF thresholds, percentile bands).
- **G6** Work in DE, FR, IT and EN.

### Non-goals
- Real-time automatic control of devices without user confirmation.
- Billing, metering, settlement, or energy-market trading.
- Price forecasting beyond a simple short-term trend input.
- Storing or processing personal smart-meter data in the MVP.

## 4. Users

| Persona | Situation | Needs |
|---|---|---|
| **Anna**, EV owner | Charges at home overnight, leaves 07:00 | "Is tonight cheap? When should the car charge?" Done by morning. |
| **Marc**, heat pump + PV owner | Has flexibility in heating and solar surplus | Know when to pre-heat; avoid grid-stress hours |
| **Lucia**, ordinary household | Dishwasher, washing machine, no smart home | One glance: good time or not; plain words, no jargon |
| **Utility product manager** | Offers a dynamic tariff | Customers understand it and act; guidance is explainable and auditable |
| **Researcher / regulator** | Evaluates tariff design | Reproducible method, documented parameters, sensitivity results |

## 5. User stories

Priority: **M**ust, **S**hould, **C**ould.

| ID | As a... | I want... | Priority | Status |
|---|---|---|---|---|
| US-1 | household | a current label for the present hour in my language | M | Implemented (engine + API) |
| US-2 | household | a 24-48 h colour timeline of labels | M | Planned (UI) |
| US-3 | EV owner | the best hours to charge N kWh before my departure | M | Implemented (`plan_slots`, `/v1/plan`) |
| US-4 | household | a message telling me whether to start a device now | M | Implemented (`/v1/advice`) |
| US-5 | utility PM | see why a label was given (rules fired) | M | Implemented (`fired_rules`) |
| US-6 | researcher | rerun a backtest with a seed and get identical numbers | M | Implemented (`make backtest`) |
| US-7 | utility PM | adjust sets/rules without a code change | S | Implemented (YAML + validation) |
| US-8 | researcher | sensitivity and ablation reports | S | Implemented (library); report page planned |
| US-9 | household | notifications when a cheap window starts | S | Planned |
| US-10 | smart-home user | Home Assistant / EV charger integration | C | Planned |
| US-11 | researcher | automatically tuned membership functions (GA/PSO/ANFIS) | C | Planned (stretch) |
| US-12 | colour-blind user | labels readable without colour | M | Planned (UI; labels already textual) |

## 6. Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| **FR-1** | Compute context features P (price percentile in reference window), A (normalised absolute price), G (grid stress), T (trend) | Given a year of hourly prices, features are in range, have no gaps, and the index has 8760 hours across DST changes (tests: `test_features.py`) |
| **FR-2** | Stage-1 Mamdani FIS maps (P, A, G, T) to suitability S in 0-100 and a label from {avoid, wait, okay, good, ideal} | Worked example P=12, A=0.30, G=0.20, T=0 gives R01/R02/R05 firing at 0.80/0.20/0.13 and S ≈ 86.7, label ideal (`test_engine.py`) |
| **FR-3** | Rule base is complete | No input combination on a dense grid leaves all rules at zero (`test_rule_base_has_no_gaps`) |
| **FR-4** | Absolute-price guardrail | P=5 with A=1.0 scores at least 15 points lower than P=5 with A=0.0 |
| **FR-5** | Flat-tariff safety | A flat tariff yields mostly "okay" and fewer than 0.5 label changes per day |
| **FR-6** | Stability layer | Hysteresis reduces flicker near set boundaries; minimum block removes isolated one-step cheap windows |
| **FR-7** | Stage-2 device advisor returns Action in {wait, start_now, must_start} | Poor price + slack gives wait; poor price + tight deadline gives must_start; good price gives start_now |
| **FR-8** | Slot planner chooses best slots before deadline; contiguous for appliances | Chronological slot list; error if the horizon is too short |
| **FR-9** | Messages in DE/FR/IT/EN | All labels and actions exist in 4 languages; translations validated by native speakers before pilot |
| **FR-10** | HTTP API: `/healthz`, `/v1/score`, `/v1/advice`, `/v1/plan`, `/v1/config` | Input validation (422 on out-of-range), OpenAPI docs at `/docs` |
| **FR-11** | Configuration as data | MF parameters and rules in YAML; invalid references or unordered parameters are rejected at load time |
| **FR-12** | Backtest vs baselines | `fuzzy-tariff backtest` prints flips/day, isolated-window rate, EV saving vs naive and gap to oracle for fixed, percentile and fuzzy methods |
| **FR-13** | Sensitivity and ablation | Library functions perturb input sets by ±x% and drop single inputs, reporting label agreement |
| **FR-15** | Realistic dynamic tariff data | `simulate_dynamic_tariff` reproduces EKZ's published structure: 15-min steps, energy from spot, grid from squared net load, bands (energy ±5, grid -5/+15 Rp.), daily price parity, at most 2 h clipping per side; accepts real spot and load series (`tests/test_tariff_sim.py`) |
| **FR-14** | Real data ingestion | ENTSO-E day-ahead parser (done); EKZ dynamic tariff adapter and daily logger (planned); generic CSV loader (done) |

## 7. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Latency | Single `/v1/score` under 50 ms p95 on a laptop-class CPU |
| NFR-2 | Throughput | Backtest of one year hourly (8760 rows) in under 10 s |
| NFR-3 | Determinism | Same config + seed gives identical outputs |
| NFR-4 | Explainability | Every score response lists fired rules with strengths |
| NFR-5 | Privacy | No personal data stored in the MVP; compliance with Swiss FADP (and GDPR if relevant) for any pilot data; consent required |
| NFR-6 | Accessibility | Information never conveyed by colour alone; WCAG AA contrast in UI |
| NFR-7 | Maintainability | Ruff + mypy clean, coverage gate 85% (currently ~94%) |
| NFR-8 | Portability | Python 3.11+, single Docker image, no GPU, no external services required to run the core |
| NFR-9 | Security | Secrets only via environment variables; no secrets in repo; dependency updates reviewed |

## 8. Success metrics

| Metric | Target | How measured |
|---|---|---|
| Label comprehension | at least 80% of test users explain a label correctly | Usability test, 8-12 users per language group |
| Trust | mean at least 4 of 5 on "I trust this guidance" | Post-test questionnaire |
| Action rate | measurable share of flexible load moved into good/ideal hours vs control | Pilot, 10-30 households, control sees raw prices |
| Stability | fewer label flips per day than percentile-band baseline; zero isolated cheap windows | Backtest on real data |
| Seasonal consistency | no "always expensive" season; label shares per season reported | Backtest |
| Robustness | graceful on negative prices, spikes, flat days, DST | Tests + backtest scenarios |
| Stakeholder interest | at least one utility willing to continue | Handover meeting |

Honest note on current evidence: results so far come from an **EKZ-style simulated** dynamic tariff and demonstrate that the machinery works (e.g. fuzzy labels flip about 2.7x less than percentile bands). They are not evidence about real households.

## 9. Scope and release plan

| Milestone | Weeks | Content | State |
|---|---|---|---|
| **M0 Scaffold** | 0 | Repo, engine, config, API, tests, CI, docs | Done |
| **M1 Data** | 2-4 | ENTSO-E history, EKZ API logger running, Swissgrid/MeteoSwiss loaders, scenario library | Partly (parser + generic loader) |
| **M2 Method** | 4-7 | Calibrate MFs on data, expert rule review with a utility advisor, sensitivity + ablation report | Library done, calibration pending |
| **M3 UX + app** | 5-10 | Wording from interviews, wireframes, PWA with timeline and device advice, DE/FR/IT/EN | Not started |
| **M4 Pilot** | 10-12 | 10-30 households or simulated users, comprehension and action-rate study | Not started |
| **M5 Handover** | 12 | Report, demo, open documentation | Not started |

### MVP definition
Stage-1 labels + stage-2 advice behind the API, a simple web UI with 24-48 h timeline, 4 languages, evaluated on real price data (ENTSO-E plus at least one real dynamic tariff stream) and a small user test.

## 10. Assumptions and dependencies

- A partner utility (e.g. EKZ, which publishes its dynamic tariff through an API) or equivalent data is reachable. Without it we rely on ENTSO-E prices and the EKZ-style simulated dynamic tariff (`../dynamic-tariff-model.md`).
- Standard tariff levels and the standard load profile used by the simulator are illustrative until replaced with the values on the real tariff sheet.
- ENTSO-E token is granted (free but manual approval).
- Membership parameters are starting values; the project must calibrate and justify them.
- The 2026 regulation (dynamic grid tariffs) is verified against current ElCom/BFE publications before final claims.

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| No public multi-year history of Swiss dynamic tariffs | Weak evaluation | Start logging the EKZ API now; use ENTSO-E plus synthetic scenarios; use ETH/EKZ pilot dataset for comparison |
| Rule base grows too large to explain | Loses the main fuzzy advantage | Cap at about 15-25 rules; hierarchical two-stage design; review rules with domain advisor |
| Hand-tuned parameters look arbitrary | Credibility | Sensitivity analysis; data-driven tuning as comparison; document rationale per set |
| Savings metric cannot discriminate methods that rank by price | Misleading conclusions | State the limitation; add scenarios where grid stress and trend matter; compare with real pilot data |
| Users ignore guidance | No benefit | Early usability tests; device-specific messages rather than generic colours |
| Translation quality | Confusion | Native-speaker review, comprehension test per language |
| Privacy concerns | Blocks pilot | No personal data in MVP; explicit consent; data minimisation |

## 12. Open questions

1. Primary audience for the MVP: EV/heat-pump/PV owners only, or all households?
2. Grid tariff only, or combined grid + energy signal?
3. Which channel first: PWA, smart-home integration, in-home display, bill portal?
4. Is automatic tuning (GA/PSO/ANFIS) in scope for the course deliverable?
5. Which partner utility and dataset are available, and under which licence?
6. How do 15-minute tariffs (EKZ) change the reference-window design (window length, min block)?

## Appendix A: label vocabulary

| Set | EN | DE | FR | IT |
|---|---|---|---|---|
| ideal | Very cheap: best time | Sehr günstig: beste Zeit | Très bon marché : meilleur moment | Molto conveniente: momento migliore |
| good | Cheap | Günstig | Bon marché | Conveniente |
| okay | Normal | Normal | Normal | Normale |
| wait | Expensive: better later | Teuer: später besser | Cher : mieux plus tard | Caro: meglio più tardi |
| avoid | Very expensive: avoid | Sehr teuer: meiden | Très cher : à éviter | Molto caro: da evitare |

Draft translations; validate before any user-facing use.

## Appendix B: where the rules live

The rule base and membership functions are in `src/fuzzy_tariff/fuzzy/default.yaml` (15 stage-1 rules, 6 stage-2 rules). Changing them changes product behaviour: update tests, `docs/` and this PRD in the same pull request.
