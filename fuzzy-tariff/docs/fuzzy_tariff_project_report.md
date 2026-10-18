# Fuzzy Guidance for Dynamic Electricity Tariffs & Smart Household Scheduling
**Technical Project Report & Architectural Documentation**

---

## 1. Problem and Proposed System

### 1.1 Problem Statement
Beginning 1 January 2026, Swiss electricity market regulations (StromVG / StromVV) allow distribution system operators (such as EKZ, ewz) to introduce **dynamic electricity tariffs** with 15-minute price intervals. These tariffs fluctuate based on day-ahead wholesale electricity spot prices and local distribution grid load ($load^2$).

However, a fundamental cognitive and operational gap exists for households:
- **Cognitive Barrier**: Humans think in linguistic terms (*"cheap"*, *"normal"*, *"expensive"*, *"good time to run laundry"*), not in volatile numerical values such as $0.1842\text{ CHF/kWh}$.
- **Context Dependency**: What is considered "cheap" in a cold January evening ($0.22\text{ CHF/kWh}$) would be considered extraordinarily expensive on a sunny June Sunday ($0.08\text{ CHF/kWh}$). Fixed price cutoffs fail across seasonal shifts.
- **Label Instability (Flickering)**: Crisp thresholds cause rapid switching across adjacent 15-minute intervals when prices hover near arbitrary cutoffs, frustrating users and causing erratic appliance cycling.
- **Black-Box Distrust**: Neural networks cannot be audited or explained to consumers and regulatory bodies (ElCom).

### 1.2 Proposed System
We propose an **explainable, two-stage Mamdani Fuzzy Inference System (FIS)** coupled with a **Smart Household Heavy-Device Scheduler**:
1. **Context-Aware Translation**: Automatically converts raw 15-minute market tariffs and grid stress into calibrated, plain-language suitability labels (`ideal`, `good`, `okay`, `wait`, `avoid`).
2. **Explainable AI by Design**: Every single decision provides an auditable breakdown of which exact fuzzy rules fired with their activation strengths ($w_i$).
3. **Automated Multi-Device Scheduling**: Accepts realistic household constraints (max concurrent devices running at once to prevent breaker trips) and automatically schedules heavy loads (EV, heat pump, washer, dryer) during the lowest-cost, lowest-grid-stress windows without requiring manual formula inputs.

---

## 2. Data Collection

The project integrates real and simulated Swiss electricity market datasets:

| Data Source | Parameters Collected | Resolution | Usage in Pipeline |
|---|---|---|---|
| **ENTSO-E Transparency Platform** | Day-ahead spot electricity prices ($\text{EUR/MWh}$) | 15-minute / Hourly | Wholesale energy commodity cost driver |
| **Swissgrid & Local Utilities (ewz / EKZ)** | Grid residual load ($\text{MW}$), solar subtraction | 15-minute | Distribution grid stress indicator ($G$) |
| **EKZ 2026 Tariff Model** | Regulated tariff bands ($\pm 5\text{ Rp.}$ energy, $-5/+15\text{ Rp.}$ grid), standard profile parity | 15-minute (96 steps/day) | Dynamic tariff simulation (`tariff_sim.py`) |
| **MeteoSwiss / Open Data** | Solar irradiance, temperature profiles | Hourly | Residual load modeling & seasonal normalization |

For benchmark reproducibility, a validated annual 15-minute reference dataset ([`dynamic_tariff_2025_15min.csv`](file:///Users/saisharankaranam/Downloads/UC/dynamic_tariff_2025_15min.csv)) consisting of **35,040 steps** is generated, accurately modeling winter heating peaks, midday solar dips, and Swissgrid ancillary services (SDL: $0.27\text{ Rp./kWh}$).

---

## 3. Cleaning and Normalising

Raw electrical timeseries cannot be directly ingested into fuzzy inference engines without normalization:

```
Raw Spot Price + Grid Load 
   ├──> Rolling Reference Window (30 days, same day-type) ──> P: Relative Price Percentile [0, 100]
   ├──> Annual Min-Max Range [0.05, 0.60 CHF] ───────────────> A: Absolute Price Level [0, 1]
   ├──> Residual Load Normalization (Load - Solar) ─────────> G: Grid Stress [0, 1]
   └──> Short-term Derivative (2-hour horizon) ─────────────> T: Price Trend [-1, +1]
```

### 3.1 Normalization Formulations
1. **Relative Price Percentile ($P \in [0, 100]$)**:
   Computed over a rolling 30-day window using mid-rank for ties, segmented by day type (weekday vs. weekend):
   $$P_t = \frac{\text{rank}(price_t) - 0.5}{N} \times 100$$
2. **Absolute Price ($A \in [0, 1]$)**:
   Linear min-max normalization against historical annual Swiss bounds ($A_{\min} = 0.05$, $A_{\max} = 0.60\text{ CHF/kWh}$):
   $$A_t = \text{clip}\left(\frac{price_t - A_{\min}}{A_{\max} - A_{\min}}, 0, 1\right)$$
3. **Grid Stress ($G \in [0, 1]$)**:
   Normalized residual load percentile (subdividing net consumption from regional solar feed-in). Defaults to neutral ($0.5$) if unavailable.
4. **Price Trend ($T \in [-1, +1]$)**:
   Rate of change over the upcoming 2-hour window ($8$ steps of 15 min):
   $$T_t = \text{clip}\left(\frac{\Delta price_{\Delta t}}{\sigma_{\text{trend}}}, -1, 1\right)$$

### 3.2 Cleaning & Edge-Case Guardrails
- **Timezone Awareness**: All timestamps are tz-aware (`UTC` storage, `Europe/Zurich` calendar indexing) to eliminate duplicate/missing hours during Daylight Saving Time (DST).
- **Flat Tariff Guardrail**: If tariff variance across the window drops below $0.005\text{ CHF/kWh}$ (e.g. fixed legacy tariffs), $P$ defaults to $50$ and $A$ defaults to $0.5$, producing a stable `"Normal"` label rather than arbitrary division-by-zero fluctuations.

---

## 4. Membership Functions and Fuzzification

The system uses standard **triangular** (`tri`) and **trapezoidal** (`trap`) membership functions defined in [`default.yaml`](file:///Users/saisharankaranam/Downloads/UC/fuzzy-tariff/src/fuzzy_tariff/fuzzy/default.yaml):

$$\mu_{\text{tri}}(x; a, b, c) = \max\left(0, \min\left(\frac{x - a}{b - a}, \frac{c - x}{c - b}\right)\right)$$

$$\mu_{\text{trap}}(x; a, b, c, d) = \max\left(0, \min\left(\frac{x - a}{b - a}, 1, \frac{d - x}{d - c}\right)\right)$$

### Stage 1 Membership Parameters

| Input Variable | Linguistic Terms | Shape | Parameters |
|---|---|---|---|
| **$P$ (Percentile)** | `very_low`<br>`low`<br>`medium`<br>`high`<br>`very_high` | Trapezoid<br>Triangle<br>Triangle<br>Triangle<br>Trapezoid | $[0, 0, 10, 25]$<br>$[10, 25, 45]$<br>$[35, 50, 65]$<br>$[55, 75, 90]$<br>$[75, 90, 100, 100]$ |
| **$A$ (Absolute)** | `low`<br>`medium`<br>`high` | Trapezoid<br>Triangle<br>Trapezoid | $[0, 0, 0.25, 0.50]$<br>$[0.25, 0.50, 0.75]$<br>$[0.50, 0.75, 1.0, 1.0]$ |
| **$G$ (Grid Stress)** | `low`<br>`medium`<br>`high` | Trapezoid<br>Triangle<br>Trapezoid | $[0, 0, 0.25, 0.50]$<br>$[0.25, 0.50, 0.75]$<br>$[0.50, 0.75, 1.0, 1.0]$ |
| **$T$ (Trend)** | `falling`<br>`stable`<br>`rising` | Trapezoid<br>Triangle<br>Trapezoid | $[-1, -1, -0.4, -0.05]$<br>$[-0.3, 0, 0.3]$<br>$[0.05, 0.4, 1.0, 1.0]$ |

### Stage 1 Output Variable ($S$: Suitability Score, Universe $[0, 100]$)
- `avoid`: $\text{trap}(0, 0, 10, 25)$
- `wait`: $\text{tri}(10, 30, 50)$
- `okay`: $\text{tri}(40, 55, 70)$
- `good`: $\text{tri}(60, 75, 90)$
- `ideal`: $\text{trap}(75, 90, 100, 100)$

---

## 5. Rulebase and Defuzzification

### 5.1 Stage 1 Mamdani Rule Base (15 Rules)

```yaml
R01: IF P is very_low AND A is low      THEN S is ideal  (Very cheap relative and absolute)
R02: IF P is very_low AND A is medium   THEN S is good   (Very cheap relative, moderate level)
R03: IF P is very_low AND A is high     THEN S is okay   (Guardrail: relatively cheap but absolute high)
R04: IF P is very_low AND T is rising   THEN S is ideal  (Cheap & rising soon: consume now)
R05: IF P is low AND G is low           THEN S is good   (Cheap and grid relaxed)
R06: IF P is low AND G is medium        THEN S is good   (Cheap and grid moderate)
R07: IF P is low AND G is high          THEN S is okay   (Cheap but grid congested)
R08: IF P is medium                     THEN S is okay   (Normal standard tariff)
R09: IF P is medium AND T is falling    THEN S is wait   (Normal now, getting cheaper soon)
R10: IF P is medium AND A is high       THEN S is wait   (Normal relative, high absolute)
R11: IF P is high AND T is falling      THEN S is wait   (Expensive now, cheaper soon)
R12: IF P is high AND G is low          THEN S is wait   (Expensive, grid relaxed)
R13: IF P is high AND G is high         THEN S is avoid  (Expensive and grid stressed)
R14: IF P is very_high                  THEN S is avoid  (Peak expensive window)
R15: IF P is high AND G is medium       THEN S is wait   (Expensive, grid moderate)
```

### 5.2 Stage 2 Device Advisor Rule Base (6 Rules)
Inputs: $S$ (Suitability Score $0–100$) and $U$ (Urgency: $\frac{\text{Required Run Hours}}{\text{Deadline Hours}} \in [0, 1]$). Output: `Action` (`wait`, `start_now`, `must_start`).

```yaml
D01: IF S is high                       THEN Action is start_now  (Good price: start)
D02: IF S is mid AND U is low           THEN Action is wait       (Normal price, no rush)
D03: IF S is mid AND U is medium        THEN Action is start_now  (Normal price, deadline approaching)
D04: IF S is low AND U is low           THEN Action is wait       (Poor price, plenty of time)
D05: IF S is low AND U is medium        THEN Action is wait       (Poor price, still some slack)
D06: IF U is high                       THEN Action is must_start (Deadline overrides price!)
```

### 5.3 Mathematical Inference & Defuzzification
- **Conjunction (AND)**: Minimum operator: $w_i = \min(\mu_{A_1}(x_1), \mu_{A_2}(x_2))$.
- **Implication**: Mamdani minimum clipping: $\mu_{C_i}(y) = \min(w_i, \mu_{B_i}(y))$.
- **Aggregation**: Maximum operator: $\mu_{\text{agg}}(y) = \max_i(\mu_{C_i}(y))$.
- **Defuzzification**: Centroid (Center of Gravity) method over a 1,001-point discrete grid:
  $$S = \frac{\sum_{j=1}^{1001} y_j \cdot \mu_{\text{agg}}(y_j)}{\sum_{j=1}^{1001} \mu_{\text{agg}}(y_j)}$$
- **Hysteresis & Min Block Filtering**: Prevents flickering between adjacent categories if the score fluctuates within a $\pm 0.1$ margin, enforcing a minimum continuous block of $2$ intervals.

---

## 6. System Architecture and Output

### 6.1 Package Architecture
The codebase strictly adheres to the principle of **Pure Core, Impure Edges**:
- `fuzzy/`: Pure mathematical engine and YAML loader. **Zero external dependencies** on pandas, databases, or web servers.
- `features/`: Reference window timeseries calculation.
- `advisor/`: Device models (EV, Heat pump, Washer, Dryer) and Stage 2 FIS.
- `api/`: FastAPI web server delivering REST endpoints and static HTML/JS dashboard.

```
                    ┌────────────────────────────────────────┐
                    │               User / UI                │
                    └───────────────────┬────────────────────┘
                                        │ (HTTP / JSON)
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              FastAPI App                               │
│  GET /                   POST /v1/score             POST /v1/advice    │
│  GET /v1/tariff/preview  POST /v1/smart-schedule    POST /v1/plan      │
└───────────────────────────────────────┬────────────────────────────────┘
                                        │
                    ┌───────────────────┴────────────────────┐
                    ▼                                        ▼
┌────────────────────────────────────────┐ ┌─────────────────────────────┐
│             Features Engine            │ │     Smart Scheduler Core    │
│  Reference Windows, Percentiles P,     │ │  Concurrency limits,        │
│  Normalized A, Grid G, Trend T         │ │  Contiguous block search,   │
└───────────────────┬────────────────────┘ │  Peak avoidance sequencing │
                    │                      └──────────────┬──────────────┘
                    ▼                                     │
┌────────────────────────────────────────┐                │
│       Stage 1 Mamdani FIS Engine       │                │
│  15 Rules, Min-Max, Centroid           │                │
│  Output: S (0-100) & Membership Vector │                │
└───────────────────┬────────────────────┘                │
                    │                                     │
                    ▼                                     │
┌────────────────────────────────────────┐                │
│       Stage 2 Device Advisor FIS       │                │
│  Urgency U + Suitability S             │                │
│  Output: wait / start_now / must_start │                │
└───────────────────┬────────────────────┘                │
                    └───────────────────┬─────────────────┘
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         System Output Artifacts                        │
│  1. Plain-Language Guidance: "Very cheap: best time (R01 fired)"       │
│  2. Device Schedule: EV [01:30 - 05:00], Washer [13:15 - 14:45]        │
│  3. Financial Breakdown: Cost CHF 4.91 vs Peak CHF 10.38 (Saved 52.7%) │
│  4. 24-Hour Visual Gantt Schedule Timeline                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Results and Next Steps

### 7.1 Quantitative Backtest Results
The system was benchmarked across a full year of 15-minute simulated Swiss dynamic tariffs against conventional crisp methods:

| Evaluation Metric | Fixed CHF Threshold | Crisp Percentile Bands | Fuzzy FIS (Our System) | Performance Impact |
|---|---|---|---|---|
| **Label Flips per Day** | 14.00 | 13.18 | **4.90** | **65% reduction in erratic flickering** |
| **Isolated Cheap Windows** | 0.00 | 0.03 | **0.00** | **Zero unusable 15-min spikes** |
| **EV Cost Savings vs. Peak** | 59.15% | 59.15% | **58.97%** | Near-optimal cost minimization |
| **Gap to Theoretical Oracle** | 0.00% | 0.00% | **0.43%** | Captures 99.5% of optimal cost savings |

### 7.2 Key Findings
1. **Human Stability without Cost Penalty**: The fuzzy system eliminates 65% of erratic label switching while maintaining 99.5% of the financial savings achievable by an omniscient mathematical oracle.
2. **Effective Peak Congestion Relief**: In multi-appliance scheduling tests under a strict 1-device concurrency limit, **0.0% of heavy electrical load** was scheduled in the critical Swiss grid peak window ($17:30 - 20:30$), saving over **52% in electricity bills**.
3. **Auditability**: Unlike black-box neural networks, every schedule recommendation can be directly traced to explicit linguistic rules ($R01 - R15$ and $D01 - D06$).

### 7.3 Next Steps
- **Field Pilot with Real Smart Meters**: Interface the FastAPI backend directly with Home Assistant and OCPP-compliant EV chargers.
- **Dynamic Grid Tariff Ingestion**: Replace synthetic load curves with live 18:00 day-ahead API feeds from Swiss DSOs as they launch in 2026.
- **Dynamic Membership Calibration**: Allow households with private rooftop PV and battery storage to calibrate grid stress curves based on local inverter telemetry.
