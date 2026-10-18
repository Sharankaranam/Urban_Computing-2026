# Fuzzy Guidance for Dynamic Electricity Tariffs

**Course context:** Fuzzy Systems project
**Country / setting:** Switzerland, time-variable grid tariffs allowed since 1 January 2026
**Planning assumption:** ~12 weeks, small team (3-5 people)

---

## 1. Background

Since January 1, 2026, Swiss utilities may offer time-variable (dynamic) tariffs, initially for grid usage only. Heat pumps, electric vehicles and solar production are increasing and changing load, so shifting consumption to cheap, low-stress hours has real value for the grid and for households.

## 2. Problem

Households think in words ("cheap", "a bit expensive", "a good time to charge the car"), not in CHF/kWh. Fixed thresholds fail because context matters: a price that is cheap in winter may be expensive in summer. Without understandable guidance, dynamic tariffs risk being ignored or misunderstood.

**Core gap:** price signal (CHF/kWh) → human decision ("should I charge now?").

## 3. Why fuzzy systems?

The problem is a natural fit for fuzzy logic:

| Property of the problem | How fuzzy logic helps |
|---|---|
| Human categories are vague ("cheap", "expensive") with no sharp boundary | Linguistic variables and membership functions model gradual transitions |
| Context shifts meaning (season, day type, grid state) | Several inputs combine through IF-THEN rules written in plain language |
| Hard thresholds make labels flicker when a price crosses a cutoff by 0.1 Rp | Smooth membership degrees give stable, gradual outputs |
| Utilities and regulators must be able to explain the guidance | A rule base is human-readable and auditable, unlike a black-box model |
| Little labelled data exists for dynamic tariffs | Expert knowledge can be encoded directly in rules, then tuned with data |

## 4. Objectives

1. Design a **fuzzy inference system (FIS)** that converts hourly prices and context into a plain-language suitability label for consuming electricity.
2. Add a **second-stage device advisor** (EV, heat pump, washing machine) that adds the user's urgency and deadline.
3. **Validate** against crisp baselines (fixed CHF thresholds, percentile cut-offs) on stability, interpretability, savings and peak shifting.
4. Deliver a **working prototype** and evidence from user testing or a small pilot.

## 5. Research questions

- **RQ1:** Does a fuzzy labeller produce more stable (fewer flips per day) and more seasonally consistent labels than crisp thresholds?
- **RQ2:** How sensitive is the output to membership-function shape and parameters?
- **RQ3:** Which inputs (relative price, absolute price, grid stress, price trend) contribute most to useful guidance? (rule and input ablation)
- **RQ4:** Do users understand and trust fuzzy labels, and do they shift consumption accordingly?
- **RQ5 (stretch):** Do automatically tuned membership functions (genetic algorithm / PSO / ANFIS) beat hand-designed ones without losing interpretability?

## 6. Scope

**In scope**
- Fuzzy labelling engine (Mamdani FIS, optional Sugeno comparison)
- Device advisor FIS (second stage)
- Hourly day-ahead price handling, synthetic tariff scenarios
- Python reference implementation, evaluation, simple web UI
- DE/FR/IT/EN label set

**Out of scope**
- Real-time control of devices without user confirmation
- Billing, metering and settlement
- Energy-market bidding or forecasting beyond a simple trend input

---

## 7. System design (summary)

Details and diagrams are in `flow.md`.

### 7.1 Inputs (linguistic variables)

| Input | Meaning | Range | Fuzzy sets |
|---|---|---|---|
| **P** Relative price | Percentile of the hour's price within a reference window (same season, same day type, last 14-30 days) | 0-100 | Very Low, Low, Medium, High, Very High |
| **A** Absolute price | Price normalised to the tariff's annual min-max range | 0-1 | Low, Medium, High |
| **G** Grid stress | Normalised residual load (load minus solar), or tariff peak flag as proxy | 0-1 | Low, Medium, High |
| **T** Price trend | Expected price change over next 2 hours | -1 to +1 | Falling, Stable, Rising |

### 7.2 Output

**S** Suitability score, 0-100, with five fuzzy sets mapped to user-facing labels:

| Fuzzy set | User label | Meaning |
|---|---|---|
| Avoid | Very expensive: avoid | Postpone anything flexible |
| Wait | Expensive: better later | A cheaper window is likely soon |
| Okay | Normal | No strong reason to shift |
| Good | Cheap | Good time for flexible loads |
| Ideal | Very cheap: best time | Charge, pre-heat, run the dishwasher |

### 7.3 Inference method

- **Type:** Mamdani, min for AND, max for aggregation
- **Defuzzification:** centroid (compare with mean-of-maxima)
- **Comparison model:** Sugeno with constant consequents (faster, easier to tune)
- **Stretch:** interval type-2 sets to model uncertainty in price forecasts

### 7.4 Starting rule base (to be refined)

| # | IF | THEN S is |
|---|---|---|
| 1 | P is Very Low AND A is Low | Ideal |
| 2 | P is Very Low AND A is Medium | Good |
| 3 | P is Very Low AND A is High | Okay *(absolute guardrail)* |
| 4 | P is Very Low AND T is Rising | Ideal *(use it before it ends)* |
| 5 | P is Low AND G is Low | Good |
| 6 | P is Low AND G is Medium | Good |
| 7 | P is Low AND G is High | Okay |
| 8 | P is Medium | Okay |
| 9 | P is Medium AND T is Falling | Wait |
| 10 | P is Medium AND A is High | Wait |
| 11 | P is High AND T is Falling | Wait |
| 12 | P is High AND G is Low | Wait |
| 13 | P is High AND G is High | Avoid |
| 14 | P is Very High | Avoid |
| 15 | P is High AND G is Medium | Wait |

### 7.5 Second stage: device advisor

Inputs: **S** (suitability), **U** urgency (energy still needed ÷ hours until deadline), device type.
Output: **Action** with sets *Wait*, *Start now*, *Must start*.

| IF | THEN |
|---|---|
| S is Ideal or Good | Start now |
| S is Okay AND U is Low | Wait |
| S is Wait or Avoid AND U is Low | Wait |
| U is High | Must start *(the deadline overrides price)* |

Message examples: "Charge the car now, it will be full by 7:00 at the cheapest rate of the night." / "Wait until 22:00, a cheaper window is coming."

### 7.6 Stability measures

- Hysteresis on the final label and a minimum block length (no isolated one-hour "ideal" windows)
- Smooth membership functions (overlapping at about 50%)

---

## 8. Data

| Source | Use | Notes |
|---|---|---|
| Utility hourly grid tariff schedules | Main price signal | Ideally from one partner utility |
| ElCom tariff data | Baselines, annual ranges | Check licence and format |
| ENTSO-E Transparency / EPEX SPOT day-ahead | Realistic price dynamics, spikes, negative prices | Used when real dynamic tariffs are sparse |
| Swissgrid load and generation | Grid stress input G | Check resolution |
| MeteoSwiss | Temperature, solar radiation context | Heat pump scenarios |
| Synthetic scenarios | Winter evening peak, solar midday dip, flat day, spike day | Document all assumptions |

All sources must be verified for availability and licence before use.

## 9. Work plan

| Phase | Weeks | Key activities | Deliverables |
|---|---|---|---|
| 1. Definition | 1 | Charter, scope, success criteria, stakeholders | Project charter |
| 2. Research | 1-3 | Regulation, tariff landscape, fuzzy literature (energy, smart grid, demand response), 8-12 user interviews, competitor review | Literature review, personas, vocabulary list |
| 3. Data | 2-4 | Ingest, clean, DST handling, tag season / day type / hour, build synthetic scenarios | Clean dataset, data notes |
| 4. Fuzzy design | 4-6 | Define variables, membership functions, rule base, implement Mamdani FIS and Sugeno variant, device advisor | Documented FIS, Python code |
| 5. Validation | 6-7 | Backtest one year, baselines, sensitivity and ablation, savings and peak simulation, edge cases | Evaluation report |
| 6. UX design | 5-8 | Wording from interviews, wireframes, accessibility, multilingual copy, usability tests | Tested prototype, copy deck |
| 7. Build | 7-10 | Data pipeline, FIS service (API), web app, notifications | MVP |
| 8. Pilot | 10-12 | 10-30 households or simulated users, comprehension and action metrics, optional control group | Pilot results |
| 9. Handover | 12 | Report, demo, slides, open documentation | Final package |

## 10. Evaluation plan

**Compared methods:** (a) fixed CHF thresholds, (b) crisp percentile bands (20/40/60/80), (c) fuzzy Mamdani, (d) fuzzy Sugeno, (e) optional tuned fuzzy.

| Metric | Definition |
|---|---|
| Label stability | Label changes per day; fraction of isolated one-hour windows |
| Seasonal consistency | Label distribution per season; no "always expensive" winters |
| Savings | CHF/year for a household following advice vs flat tariff and naive shifting |
| Peak shifting | kWh moved out of peak hours; aggregate effect at X% adoption |
| Sensitivity | Output change under +/-10% membership parameter shifts |
| Ablation | Performance when removing G, T or A, and when removing single rules |
| Interpretability | Number of rules, readability rated by domain advisor |
| Comprehension and trust | Share of users who explain a label correctly; trust rating (Likert) |
| Action rate | Share of flexible loads moved into good windows in the pilot |

## 11. Tools and tech stack

- **Fuzzy logic:** Python (`scikit-fuzzy`, or own NumPy implementation for transparency); optional MATLAB Fuzzy Logic Toolbox for cross-checking
- **Data:** pandas, NumPy
- **Tuning (stretch):** DEAP or PyGAD for GA; PSO library
- **Visualisation:** matplotlib / Plotly for membership functions and rule surfaces
- **App:** FastAPI backend, simple PWA or Streamlit front end
- **Version control:** Git, with notebooks for experiments

## 12. Repository structure (suggested)

```
fuzzy-tariff/
  README.md
  project.md
  flow.md
  data/
    raw/
    processed/
    synthetic/
  fuzzy/
    variables.py        # membership functions
    rules.py            # rule base
    mamdani.py          # inference
    sugeno.py
    device_advisor.py
  evaluation/
    baselines.py
    metrics.py
    sensitivity.py
  app/
    api.py
    frontend/
  notebooks/
  reports/
  tests/
```

## 13. Team and roles

| Role | Responsibility |
|---|---|
| Project lead | Scope, timeline, stakeholder contact |
| Fuzzy / data analyst | Variables, rules, inference, validation |
| UX researcher / designer | Interviews, wording, usability tests |
| Developer | Pipeline, API, app |
| Domain advisor (utility / regulatory) | Tariff realism, rule review, data access |

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Little real dynamic-tariff data | Synthetic scenarios and day-ahead market data; involve a utility early |
| Rule base grows too large to explain | Limit to about 15-25 rules, use hierarchical (two-stage) FIS instead of one big rule table |
| Misleading labels in edge cases | Absolute-price guardrail, hysteresis, tests for negative prices, spikes, flat days |
| Hand-tuned membership functions seen as arbitrary | Sensitivity analysis plus data-driven tuning for comparison |
| Users ignore the guidance | Early usability tests, device-specific messages, not just colours |
| Privacy | No personal data in the MVP, consent for any meter data, Swiss FADP compliance |

## 15. Success criteria

- Fuzzy labeller shows measurably fewer label flips than crisp baselines at similar or better savings
- At least 80% of test users explain a label correctly
- Documented sensitivity and ablation results
- Documented savings and peak-reduction estimates
- At least one utility or stakeholder interested in continuing

## 16. Open decisions

- Primary user group (EV / heat pump / solar owners vs all households)
- Grid tariff only, or combined grid + energy price
- Which channel to prototype (PWA, smart home, in-home display)
- Whether the tuning stretch goal (GA / ANFIS / type-2) is included
- Which partner utility and dataset are available

## 17. Reading list (to be verified and extended)

- Zadeh, L. A. (1965). Fuzzy sets.
- Mamdani, E. H. and Assilian, S. (1975). An experiment in linguistic synthesis with a fuzzy logic controller.
- Takagi, T. and Sugeno, M. (1985). Fuzzy identification of systems.
- Literature on fuzzy logic for demand response, home energy management and smart-grid pricing (search required)
- ElCom and Swiss federal publications on time-variable grid tariffs (check current rules)
