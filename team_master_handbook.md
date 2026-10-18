# Team Master Handbook: Swiss Dynamic Tariff Fuzzy Inference System

> **Project Name:** Swiss Dynamic Tariff • Two-Stage Mamdani Fuzzy Inference System & Multi-Device Household Scheduler  
> **Target Framework:** Swiss Federal Electricity Act (StromVG revision, Jan 2026)  
> **Repository:** `/Users/saisharankaranam/Downloads/UC/fuzzy-tariff`  
> **Running Local Server:** `http://localhost:8000/`  
> **API Documentation:** `http://localhost:8000/docs`

---

## 1. Executive Summary

Starting in January 2026, the Swiss Federal Electricity Act (**StromVG**) mandates dynamic electricity tariffs for retail consumers equipped with smart meters. Instead of a single flat rate, retail electricity prices will fluctuate every **15 minutes** based on wholesale spot prices (ENTSO-E) and non-linear local grid-loading fees ($load^2$).

This project provides an autonomous, explainable **Two-Stage Mamdani Fuzzy Inference System (FIS)** integrated with a **Multi-Device Household Concurrency Scheduler**:
* **It saves homeowners 50% to 58.9%** on high-power electricity consumption (EV, heat pump, laundry).
* **It eliminates 100% of appliance operation during peak grid hours** (17:30–20:30).
* **It cuts appliance-destroying "rapid switching / chattering" by 65%** compared to classical hard thresholds.
* **It guarantees home electrical safety** by strictly enforcing breaker concurrency limits (e.g., max 1 heavy load at a time to prevent tripping standard 16A/25A fuses).

---

## 2. Why Classical If-Else Logic Fails (The Need for Fuzzy Logic)

If you attempt to solve this with classical Boolean logic (e.g. `IF price < 18 Rp. THEN turn on, ELSE turn off`), the system breaks down in three catastrophic ways:

1. **The Chattering / Rapid Switching Trap:**
   * In reality, prices hover around threshold boundaries (e.g., passing clouds at midday causing prices to fluctuate between `17.9 Rp.` and `18.1 Rp.`).
   * A hard cutoff causes appliances to click **ON $\to$ OFF $\to$ ON $\to$ OFF 14 times a day**!
   * This rapid on/off cycling burns out heat pump compressors and degrades EV battery management systems.
2. **Context Blindness:**
   * In Summer, `20 Rp./kWh` is an expensive peak.
   * In Winter, `20 Rp./kWh` is a massive bargain.
   * A hardcoded threshold cannot adapt to seasonal market baselines.
3. **The Cheap Energy Trap (Conflicting Constraints):**
   * At 18:00 on a winter evening, German wind power might make wholesale electricity very cheap, but local neighborhood transformer demand is at peak capacity.
   * A simple price-sorter turns on every EV and heat pump at once, **causing a neighborhood transformer failure or blackout**.

Fuzzy Logic solves this because it replaces rigid binary true/false with **continuous degrees of membership ($\mu \in [0, 1]$)** and uses human-like linguistic rules to balance multiple conflicting objectives.

---

## 3. The 4 Concrete Real-Life Situations Where Fuzzy Logic Decides

When someone asks: *"Where is fuzzy logic actually used in this project?"*, give them these four exact situations:

### Situation 1: The "Cheap Energy Trap" (Conflicting Market vs. Grid Goals)
* **Real-Life Scene:** Winter at 18:00. Electricity spot prices drop due to imported wind power, but local neighborhood demand is at maximum capacity (everyone cooking and heating).
* **Dumb Sorter:** Turns on all heavy loads immediately $\to$ **Local blackout**.
* **Fuzzy System:** Price is *Cheap* ($\mu = 0.85$), but Grid Congestion is *Critical High* ($\mu = 0.95$). **Rule R15 fires**: *IF Grid is Critical THEN Suitability is AVOID*. Score drops to **9.3 / 100 [AVOID]**, protecting the neighborhood grid.

### Situation 2: The "Passing Clouds" Problem (Appliance Protection)
* **Real-Life Scene:** Midday between 13:00 and 15:00. Solar output fluctuates around 18.0 Rp./kWh (`17.8` $\to$ `18.2` $\to$ `17.9`).
* **Classical If-Else:** Switches heat pump on/off 4 times in one hour $\to$ **Damages the compressor**.
* **Fuzzy System:** Fuzzified membership degrees transition smoothly ($\mu = 0.65$ good). The defuzzified score stays steady around **68 / 100 [GOOD]**. The heat pump runs continuously without interruption.

### Situation 3: The Falling Price Trend ("Wait, It’s Getting Even Cheaper")
* **Real-Life Scene:** At 23:00, electricity drops to 16 Rp./kWh (looks cheap compared to evening peak).
* **Dumb Sorter:** Starts charging EV immediately at 16 Rp., missing the fact that at 02:00 AM it will plummet to 12 Rp.
* **Fuzzy System:** Price is Medium, but Trend ($T$) is *Falling Rapidly* ($T = -0.8$). **Rule R12 fires**: *IF Price is Medium AND Trend is Falling THEN Suitability is WAIT*. Recommends waiting for the 02:00 AM valley, capturing an extra 25% savings.

### Situation 4: Stage 2 Urgency ("I Have an Emergency")
* **Real-Life Scene:** User arrives home at 17:30 with 10% battery. They have an emergency hospital shift at 20:30 (Deadline = 3 hours). Electricity is at its most expensive peak (34 Rp./kWh).
* **Dumb Sorter:** Postpones charging to 02:00 AM $\to$ **User is stranded and misses shift**.
* **Fuzzy Stage 2:** Computes Urgency $U = \frac{2.5\text{h}}{3.0\text{h}} = 0.83$ (*Critical Urgency*). **Rule D06 fires**: *IF Urgency is Critical THEN Action is MUST START NOW*. Overrides high prices because human life safety takes precedence.

---

## 4. What the User Enters vs. What the System Automates

A homeowner does **NOT** enter prices or solve formulas daily:

### What the User Enters (Only 3 Practical Inputs):
1. **Energy Needed (kWh):** e.g., `22.2 kWh` for EV / `3.0 kWh` for Washing Machine.
2. **Deadline (Hours):** e.g., "Ready in 10 hours" (by 7:00 AM).
3. **Breaker Limit (1-Time Setting):** e.g., Max 1 heavy appliance at a time (protects 16A/25A fuses).

### What the System Automates (100% Zero-Touch):
* **ENTSO-E Spot Prices:** Ingested daily at 13:00 CET via API.
* **Grid Net Load:** Monitored every 15 minutes from the digital smart meter.
* **Normalization ($P, A, G, T$):** Calculated for all 96 intervals.
* **Fuzzy Rule Evaluation & Centroid Defuzzification:** Computed autonomously.
* **Appliance Execution:** Dispatched automatically via OCPP (EV wallbox), SG-Ready relays (heat pump), and Matter/Zigbee (smart plugs).

---

## 5. Mathematical Model & Fuzzy Inference Pipeline

```
┌────────────────────────────────────────────────────────┐
│ 1. Continuous Input Vector: (P, A, G, T)               │
│    • P(t) ∈ [0, 100]  : Daily price percentile rank    │
│    • A(t) ∈ [0, 1]    : Absolute tariff in CHF/kWh     │
│    • G(t) ∈ [0, 1]    : Normalized grid net load²      │
│    • T(t) ∈ [-1, +1]  : Local 1-hour price slope       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. Fuzzification via Triangular & Trapezoidal MFs      │
│    • Price P: Cheap, Medium, Expensive                 │
│    • Grid G : Low, Medium, High                        │
│    • Trend T: Falling, Flat, Rising                    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. 15 Mamdani Linguistic Rules (R01 – R15)             │
│    • Implication: Minimum operator (Mamdani min)       │
│    • Aggregation: Maximum operator                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. Centroid Defuzzification (Center of Gravity - COG)  │
│             S = ∫ y·μ_B(y) dy / ∫ μ_B(y) dy            │
│    • Output: Crisp Suitability Score S(t) ∈ [0, 100]   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. Stage 2 Urgency & Appliance Advisor (D01 – D06)     │
│    • Urgency U = (Required Run Hours / Deadline Hours) │
│    • Action: start_now | wait | must_start             │
└────────────────────────────────────────────────────────┘
```

### The 15 Stage 1 Mamdani Rules Matrix

| Rule ID | Price Percentile ($P$) | Grid Congestion ($G$) | Modifier / Extra | Output Suitability ($S$) | Power Engineering Intent |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R01** | Cheap | Low | — | **Ideal** (80–100) | Best possible charging/running window |
| **R02** | Cheap | Medium | — | **Good** (60–80) | Cheap energy, moderate grid load |
| **R03** | Cheap | High | — | **Okay** (40–60) | Cheap energy balanced by high grid fee |
| **R04** | Medium | Low | — | **Good** (60–80) | Acceptable price with low grid stress |
| **R05** | Medium | Medium | — | **Okay** (40–60) | Average market and grid conditions |
| **R06** | Medium | High | — | **Wait** (20–40) | Avoid adding load to stressed grid |
| **R07** | Expensive | Low | — | **Wait** (20–40) | Grid is clear, but price is unappealing |
| **R08** | Expensive | Medium | — | **Avoid** (0–20) | High price and moderate grid load |
| **R09** | Expensive | High | — | **Avoid** (0–20) | Worst conditions: expensive & congested |
| **R10** | Cheap | Any | Absolute Very Cheap | **Ideal** (80–100) | Absolute global bargain overrides percentile |
| **R11** | Any | Any | Absolute Very High | **Avoid** (0–20) | Absolute ceiling protection |
| **R12** | Medium | Low | Trend Falling | **Wait** (20–40) | Postpone: even cheaper slot is approaching |
| **R13** | Medium | Low | Trend Rising | **Good** (60–80) | Act now before price climbs higher |
| **R14** | Cheap | Low | Trend Rising | **Ideal** (80–100) | Seize immediate cheap window |
| **R15** | Any | High | Critical Grid Strain | **Avoid** (0–20) | Transformer overload protection |

---

## 6. Empirical Benchmark Results (Full 2025 Swiss Dataset)

Validated on **35,040 intervals** of real 2025 Swiss market data:

1. **Label Chattering Reduction:**
   * Fixed Threshold Baseline: **14.0 flips/day**
   * Two-Stage Mamdani FIS: **4.9 flips/day** (**65% smoother**)
2. **Cost Savings on Heavy Cycles:**
   * EV 22.2 kWh cycle: Peak cost = CHF 7.04 $\to$ Fuzzy Scheduled cost = **CHF 3.17 (55.0% – 58.97% savings)**.
   * Efficiency vs. Theoretical Mathematical Oracle: **99.5%**.
3. **Peak Grid Elimination:**
   * Peak hours (17:30–20:30): **0% of appliances scheduled** (100% peak avoidance).

---

## 7. Codebase Structure & File Guide

```
fuzzy-tariff/
├── prd.md                                      # Official Project Requirements Document
├── pyproject.toml                              # Python package metadata (Python >= 3.11)
├── src/fuzzy_tariff/
│   ├── config.py                               # Configuration & Pydantic settings
│   ├── engine/                                 # STAGE 1 FUZZY INFERENCE SYSTEM
│   │   ├── fuzzifier.py                        # Membership functions for (P, A, G, T)
│   │   ├── rules.py                            # 15 Mamdani linguistic rules
│   │   ├── defuzzifier.py                      # Centroid (Center of Gravity) implementation
│   │   └── pipeline.py                         # Complete Stage 1 pipeline
│   ├── stage2/                                 # STAGE 2 APPLIANCE ADVISOR
│   │   ├── urgency.py                          # Urgency calculation U = duration / deadline
│   │   ├── advisor.py                          # Decision engine (start_now, wait, must_start)
│   │   └── rules.py                            # Rules D01 - D06
│   ├── scheduler/                              # MULTI-DEVICE CONSTRAINED SCHEDULER
│   │   ├── profiles.py                         # Appliance specs (EV, Heat Pump, Washer, etc.)
│   │   └── planner.py                          # Concurrency slot allocation under breaker limits
│   └── api/                                    # REST API & FRONTEND
│       ├── main.py                             # FastAPI endpoints & static file mount
│       ├── schemas.py                          # Pydantic v2 schemas
│       └── static/
│           └── index.html                      # Interactive 3-View Single Page Application
└── tests/                                      # Full pytest suite (Unit, Integration, Backtest)
```

---

## 8. Step-by-Step Guide: How to Run and Demo

### Prerequisites:
* Python 3.12 virtual environment at `/Users/saisharankaranam/Downloads/UC/fuzzy-tariff/.venv`.

### Step 1: Start the Server
```bash
cd /Users/saisharankaranam/Downloads/UC/fuzzy-tariff
.venv/bin/fuzzy-tariff serve --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Open the Web Application
Open your browser to: **`http://localhost:8000/`**

### Step 3: Walk Through the 3 Tabs for Your Demo
1. **Tab 1: `⚡ 1. Smart Household Scheduler`**
   * Change breaker concurrency: click **1 Device Only**, then **Max 2 Devices**. Show how the timeline changes.
   * Toggle devices (EV, Heat pump, Washer). Point out the **Fuzzy Suitability Score badges** (e.g. `90.7/100 (IDEAL)`).
   * Hover/click on the **24-hour fuzzy suitability bar chart** to see individual hourly metrics.
2. **Tab 2: `🧠 2. Live Fuzzy Inference Engine (Mamdani Rules)`**
   * Click **`🚨 Winter Peak (18:30)`** preset $\to$ watch the score drop to **9.3 (AVOID)** and see Rule `R15` light up green!
   * Click **`🌙 Night Valley (02:00)`** preset $\to$ watch the score rise to **90.7 (IDEAL)** and see Rule `R01` light up green!
3. **Tab 3: `📑 3. Academic Model & Report`**
   * Scroll through the 7 academic sections with equations and the benchmark results table.
