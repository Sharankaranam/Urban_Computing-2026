# 🇨🇭 Swiss Dynamic Tariff • Two-Stage Fuzzy Inference System & Smart Scheduler

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Fuzzy Logic](https://img.shields.io/badge/Fuzzy%20Logic-Two--Stage%20Mamdani%20FIS-purple.svg)](fuzzy-tariff/src/fuzzy_tariff/fuzzy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Swiss%20StromVG%202026-red.svg)](https://www.uvek.admin.ch/)

An autonomous, explainable **Two-Stage Mamdani Fuzzy Inference System (FIS)** and **Multi-Device Household Concurrency Scheduler** built for the Swiss Federal Electricity Act (**StromVG revision, Jan 2026**).

The system continuously evaluates wholesale electricity spot prices and local grid transformer congestion, sequences heavy residential loads (EV, heat pump, laundry) into the cheapest, safest hours, and **saves homeowners over 55% on energy costs while strictly preventing household circuit breaker trips**.

---

## 📑 Table of Contents
1. [The Real-World Problem (StromVG 2026)](#-the-real-world-problem-stromvg-2026)
2. [Why Classical (If-Else) Logic Fails](#-why-classical-if-else-logic-fails)
3. [The Fuzzy Solution: Two-Stage Mamdani Architecture](#-the-fuzzy-solution-two-stage-mamdani-architecture)
4. [The 4 Real-Life Situations Where Fuzzy Logic Decides](#-the-4-real-life-situations-where-fuzzy-logic-decides)
5. [User Inputs vs. Automated Background Ingestion](#-user-inputs-vs-automated-background-ingestion)
6. [Quickstart: How to Run Locally](#-quickstart-how-to-run-locally)
7. [Live Interactive Web Dashboard](#-live-interactive-web-dashboard)
8. [Benchmark Results](#-benchmark-results)
9. [Project & Codebase Directory Map](#-project--codebase-directory-map)
10. [Documentation & Presentation Materials](#-documentation--presentation-materials)

---

## ⚡ The Real-World Problem (StromVG 2026)

Starting in January 2026, Swiss utilities are mandated to deploy dynamic retail electricity tariffs:
1. **Volatile 15-Minute Wholesale Pricing:** Energy prices fluctuate every 15 minutes based on European spot markets (ENTSO-E), swinging from negative prices up to 35+ Rp./kWh.
2. **Quadratic Grid Fees:** Grid-use fees scale non-linearly with substation transformer load ($load^2$). Peak demand hours (17:30–20:30) carry massive surcharges.
3. **The Household Fuse Bottleneck:** If an EV charger (7.4 kW), heat pump (2.5 kW), and tumble dryer (2.5 kW) start simultaneously, they pull **12.4 kW (>50 Amps)**, immediately blowing standard 16A or 25A household circuit breakers!

---

## ❌ Why Classical (If-Else) Logic Fails

Writing hardcoded rules like `IF price < 18 Rp. THEN turn on, ELSE turn off` causes serious real-world failures:
* **The "Chattering / Rapid Switching" Trap:** Passing clouds at midday cause prices to hover around the boundary (`17.9` $\to$ `18.1` $\to$ `17.9 Rp.`). Appliances turn ON and OFF **14 times a day**, rapidly burning out heat pump compressors and damaging EV battery systems.
* **Context Blindness:** In summer, `20 Rp./kWh` is an expensive peak. In winter, `20 Rp./kWh` is a massive discount. A hardcoded number cannot adapt to seasonal market shifts.
* **The Cheap Energy Trap:** At 18:00 on a winter evening, foreign wind power might dump cheap power onto the market, but the local street transformer is already glowing red from dinner cooking and heating. Simple price-sorters turn on all heavy loads and **trigger a neighborhood blackout**.

---

## 🧠 The Fuzzy Solution: Two-Stage Mamdani Architecture

```
[ Wholesale Spot & Grid Data ]                      [ User Household Needs ]
  (Price, Grid Stress, Trend)                       (Energy Needed, Deadline)
               │                                                │
               ▼                                                ▼
┌──────────────────────────────┐                ┌──────────────────────────────┐
│  STAGE 1: MAMDANI ENGINE     │                │   USER URGENCY CALCULATION   │
│  Inputs: P, A, G, T          │                │   U = Duration / Deadline    │
│  Fuzzification: Tri & Trap   │                └──────────────┬───────────────┘
│  Rules: 19 Linguistic Rules  │                               │
│  Defuzzification: Centroid   │                               │
└──────────────┬───────────────┘                               │
               │                                               │
               ▼                                               ▼
         Suitability S(t)                                  Urgency U
        (Score 0 to 100)                                (0.0 to 1.0)
               │                                               │
               └───────────────────────┬───────────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   STAGE 2: APPLIANCE ADVISOR  │
                       │   Rules D01 – D06             │
                       │   Decision: Start Now vs. Wait│
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │ MULTI-DEVICE BREAKER SCHEDULER│
                       │ Assigns to best S(t) slots    │
                       │ Enforces: Concurrent Load ≤ 1 │
                       └───────────────┬───────────────┘
                                       ▼
                       [ Smart Wallbox (OCPP) • SG-Ready Heat Pump ]
```

1. **Stage 1 FIS (The Grid Brain):**
   * Computes continuous Suitability Scores $S(t) \in [0, 100]$ using **19 Mamdani Rules** and **Centroid Defuzzification** (covering all standard regimes plus 4 critical power-engineering edge cases).
   * Completely eliminates abrupt on/off flickers (**65% reduction in switching chatter**).
2. **Stage 2 FIS (The Household Brain):**
   * Fuzzifies **User Urgency** $U = \frac{\text{Required Run Hours}}{\text{Deadline Hours}}$.
   * Evaluates rules $D01-D06$ to make practical decisions (`START_NOW`, `WAIT`, `MUST_START`).
3. **Breaker Constraint Scheduler:**
   * Automatically sequences heavy appliances into the highest suitability slots without exceeding the home breaker capacity (defaults safely to **1 heavy device at a time**).

---

## 🎯 The 4 Real-Life Situations Where Fuzzy Logic Decides

| Situation | What Dumb If-Else Does | What Our Fuzzy Engine Does |
| :--- | :--- | :--- |
| **1. The Cheap Energy Trap**<br>*(Winter 18:00: cheap spot price, but neighborhood transformer maxed out)* | Turns on EV + Heat pump immediately $\to$ **Substation blackout**. | **Rule R15 fires:** High grid stress forces score to **9.3 (AVOID)**. Postpones charging until grid clears. |
| **2. Passing Solar Clouds**<br>*(Midday: tariff hovers around 18.0 Rp. cutoff)* | Switches heat pump on/off 4 times in 1 hour $\to$ **Motor damage**. | Fuzzified membership blends smoothly $\to$ Score stays steady at **68 (GOOD)**. Appliance runs without interruption. |
| **3. Falling Price Trend**<br>*(23:00: price is 16 Rp., but will drop to 12 Rp. at 02:00)* | Starts charging immediately at 16 Rp. $\to$ **Misses 25% extra savings**. | **Rule R12 fires:** Price is Medium + Trend is Falling $\implies$ **WAIT**. Recommends waiting for 02:00 valley. |
| **4. Urgent Deadline Conflict**<br>*(5:30 PM: hospital shift at 8:30 PM, price is peak 34 Rp.)* | Postpones charging to 2:00 AM $\to$ **Car is dead; user cannot drive!** | **Stage 2 Rule D06 fires:** Urgency is Critical $\implies$ **MUST START NOW**. Overrides price to guarantee user safety. |

---

## 👤 User Inputs vs. Automated Background Ingestion

A homeowner does **NOT** enter market prices or solve formulas daily:

### What the User Sets (Only 3 Practical Inputs):
1. **Energy Needed (kWh):** e.g., `22.2 kWh` for EV / `3.0 kWh` for Washer.
2. **Deadline (Hours):** e.g., "Ready within 10 hours" (by 7:00 AM).
3. **Breaker Limit (1-Time Setting):** e.g., Max 1 heavy appliance at a time (protects 16A/25A fuses).

### What the System Automates (100% Zero-Touch):
* **ENTSO-E Spot Prices:** Ingested daily at 13:00 CET via API.
* **Grid Net Load:** Monitored every 15 minutes from the digital smart meter.
* **Normalization ($P, A, G, T$):** Calculated for all 96 daily intervals.
* **Fuzzy Rule Evaluation & Centroid Defuzzification:** Computed autonomously.
* **Appliance Execution:** Dispatched automatically via OCPP (EV wallbox), SG-Ready relays (heat pump), and Matter/Zigbee (smart plugs).

---

## 🚀 Quickstart: How to Run Locally

### Prerequisites
* **Python 3.11 or 3.12**
* **Git**

### Step 1: Clone the Repository
```bash
git clone https://github.com/Sharankaranam/Urban_Computing-2026.git
cd Urban_Computing-2026
```

### Step 2: Create Virtual Environment & Install
```bash
# Create a Python 3.12 virtual environment
python3.12 -m venv .venv

# Activate environment
source .venv/bin/activate       # On macOS/Linux
# .venv\Scripts\activate        # On Windows

# Install package in editable mode with dependencies
cd fuzzy-tariff
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 3: Start the Server
```bash
fuzzy-tariff serve --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Open in Your Browser
Open your browser and navigate to:
👉 **[http://localhost:8000/](http://localhost:8000/)**

To inspect the interactive Swagger API documentation:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Step 5: Run Automated Tests
```bash
pytest
```
*(All 13 test suites validate the Mamdani engine, rule coverage, defuzzification, stability layer, and API contracts).*

---

## 💻 Live Interactive Web Dashboard

The web app at `http://localhost:8000/` is a React + Vite dashboard (source in [`fuzzy-tariff/frontend`](fuzzy-tariff/frontend)), built into the API's static folder so the Python server serves it with no Node at runtime. It works in English, German, French and Italian, in light and dark themes, and has four views:

### 1. Scheduler
* A one-line answer up top: what today's loads cost and how much less that is than running them in the evening peak.
* A 96-slot ribbon of the day coloured by fuzzy suitability, with ticks where each appliance runs and the 17:30–20:30 peak bracketed.
* Tariff day picker (2025 benchmark days, 2026–27 practice scenarios, live EKZ), breaker limit (1 / 2 / 3 / unlimited devices), and per-appliance energy and deadline.
* Hourly suitability vs. price chart, a 15-minute appliance timeline, and a plan table with score, average tariff, fired rules and savings per appliance.

### 2. Engine
* Scrub sliders for price percentile $P$, absolute price $A$, grid congestion $G$ and trend $T$, plus Night / Solar / Peak presets.
* Live membership-function plots read from `/v1/config`, the clipped output sets with the centroid marked, and a gauge for the defuzzified score.
* The full Stage 1 rule base with each rule's firing strength.

### 3. Summary
* The linguistic summariser's headline and narrative for the selected day, the strongest protoforms with truth and coverage, and a builder to evaluate any Q / B / S combination.

### 4. Report
* The 7-section technical report with formulas and the benchmark comparison.

To work on the UI: `cd fuzzy-tariff/frontend && npm install && npm run dev` (hot reload, proxies the API), then `npm run build` to update the served files. See [`fuzzy-tariff/frontend/README.md`](fuzzy-tariff/frontend/README.md).

---

## 📊 Benchmark Results

Evaluated on **35,040 intervals** (full year 2025 Swiss dynamic tariff data) and **12,580 intervals** (4-month 2026–2027 practicing dataset):

| Evaluation Metric | Fixed-Threshold Baseline | 2-Stage Mamdani FIS | Improvement |
| :--- | :--- | :--- | :--- |
| **Label Flips per Day (Chatter)** | 14.0 flips/day | **4.9 flips/day** | **65% Reduction (Stable)** |
| **EV Cost (22.2 kWh cycle)** | CHF 7.04 (Peak) | **CHF 3.17 (Scheduled)** | **55.0% – 58.97% Savings** |
| **Oracle Efficiency Ratio** | 89.2% | **99.5% of Oracle** | **Near-Theoretical Optimum** |
| **Peak Avoidance (17:30–20:30)** | 31% of loads in peak | **0% of loads in peak** | **100% Peak Elimination** |
| **Breaker Trip Incidents** | Frequent overlapping spikes | **Zero Overlaps** | **100% Electrical Safety** |

---

## 📂 Project & Codebase Directory Map

```
Urban_Computing-2026/
├── README.md                                   # Master Project Documentation
├── dynamic-tariff-model.md                     # Swiss Dynamic Tariff Model Specification
├── dynamic_tariff_2025_15min.csv               # Full 2025 15-Minute Swiss Market Dataset (35,040 rows)
├── practising_tariff_4months_15min.csv         # 4-Month Practicing Dataset (Oct 2026 - Feb 2027, 12,580 rows)
├── sample_tariff_24h_96intervals.csv           # Clean 24-Hour Sample Dataset (96 intervals)
├── sample_dataset_presentation_slide.md        # Sample Data Table Presentation Slide
├── team_presentation_slides.md                # 12-Slide Deck with Speaker Notes
├── team_master_handbook.md                     # Comprehensive Team Reference Guide
├── fuzzy_tariff_project_report.md              # 7-Section Formal Academic Report
└── fuzzy-tariff/                               # Core Python Package
    ├── pyproject.toml                          # Package dependencies & build configuration
    ├── prd.md                                  # Product Requirements Document
    ├── scripts/
    │   ├── generate_practising_data.py         # 4-month practicing dataset generator with 6 edge cases
    │   ├── fetch_ekz_data.py                   # On-demand live EKZ API fetcher & Stage 1 processor
    │   └── log_ekz_tariff.py                   # Daily cron archiver for tomorrow's EKZ dynamic tariff
    ├── frontend/                               # React + Vite dashboard (builds into api/static)
    │   └── src/                                # views/, components/, lib/ (API client, i18n, tokens)
    ├── src/fuzzy_tariff/
    │   ├── ingest/                             # Ports + adapters: EKZ API, ENTSO-E, CSV loader
    │   ├── features/                           # Normalised inputs P, A, G, T
    │   ├── fuzzy/                              # STAGE 1 FIS + linguistic summariser
    │   │   ├── default.yaml                    # Rule base (19 Stage 1 rules + 6 Stage 2 rules)
    │   │   ├── engine.py                       # Mamdani engine (NumPy min-AND, max-aggregation, centroid)
    │   │   ├── membership.py                   # Triangular & trapezoidal membership functions
    │   │   ├── rules.py · variables.py · config.py
    │   │   └── summarizer.py                   # Yager / Kacprzyk protoforms
    │   ├── advisor/devices.py                  # STAGE 2 advisor: urgency, start-now vs. wait, slot planning
    │   ├── evaluation/                         # Baselines, metrics, sensitivity, backtest
    │   ├── labeler.py · stability.py · labels.py
    │   ├── cli.py                              # `fuzzy-tariff` command
    │   └── api/
    │       ├── main.py                         # FastAPI server (2025 benchmark, practice data, live EKZ)
    │       ├── schemas.py                      # Pydantic v2 models (public /v1 contract)
    │       └── static/                         # Built dashboard (generated by `npm run build`)
    └── tests/                                  # Pytest test suite (90 tests across 14 suites, 100% passing)
```

---

## 📚 Documentation & Presentation Materials

* 🎤 **Presentation Slides (12 Slides + Speaker Notes):** [`team_presentation_slides.md`](team_presentation_slides.md)
* 📖 **Team Master Handbook:** [`team_master_handbook.md`](team_master_handbook.md)
* 📑 **Formal 7-Section Academic Report:** [`fuzzy_tariff_project_report.md`](fuzzy_tariff_project_report.md)
* 📊 **Sample 24-Hour Dataset Slide:** [`sample_dataset_presentation_slide.md`](sample_dataset_presentation_slide.md)

---

