# Flow: Fuzzy Guidance for Dynamic Electricity Tariffs

This file shows how the project and the fuzzy system fit together. Diagrams use Mermaid and render on GitHub, VS Code (with a Mermaid extension) and most Markdown viewers.

Contents:
1. Project workflow end to end
2. Timeline
3. Fuzzy inference pipeline
4. Two-stage structure (price label, then device advisor)
5. Worked example
6. System architecture and runtime sequence
7. User decision flow

---

## 1. Project workflow end to end

```mermaid
flowchart TD
    A["1. Definition<br/>charter, scope, success criteria"] --> B["2. Research<br/>regulation, fuzzy literature, user interviews"]
    B --> C["3. Data<br/>prices, grid load, weather, synthetic scenarios"]
    B --> V["Vocabulary from users<br/>words for the output labels"]
    C --> D["4. Fuzzy design<br/>variables, membership functions, rules"]
    V --> D
    D --> E["5. Validation<br/>backtest, baselines, sensitivity, ablation"]
    E -->|"results poor or unstable"| D
    E --> F["6. UX design<br/>wording, wireframes, usability tests"]
    F --> G["7. Build<br/>pipeline, FIS API, web app"]
    G --> H["8. Pilot<br/>comprehension, trust, action rate"]
    H -->|"feedback"| D
    H --> I["9. Handover<br/>report, demo, open documentation"]
```

---

## 2. Timeline (12 weeks, example start 2 Nov 2026)

```mermaid
gantt
    title Project timeline
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section Setup
    Definition           :a1, 2026-11-02, 1w
    Research             :a2, 2026-11-02, 3w
    Data                 :a3, 2026-11-09, 3w
    section Fuzzy system
    Fuzzy design         :b1, 2026-11-23, 3w
    Validation           :b2, 2026-12-07, 2w
    section Product
    UX design            :c1, 2026-11-30, 4w
    Build                :c2, 2026-12-14, 4w
    section Delivery
    Pilot                :d1, 2027-01-04, 3w
    Handover             :d2, 2027-01-18, 1w
```

Adjust dates for holidays and your actual deadline.

---

## 3. Fuzzy inference pipeline (Mamdani)

```mermaid
flowchart LR
    subgraph IN["Crisp inputs per hour"]
        P["P: price percentile<br/>in reference window"]
        A["A: absolute price<br/>normalised 0-1"]
        G["G: grid stress<br/>0-1"]
        T["T: price trend<br/>next 2 h"]
    end

    subgraph F["1. Fuzzification"]
        FP["P: Very Low, Low, Medium,<br/>High, Very High"]
        FA["A: Low, Medium, High"]
        FG["G: Low, Medium, High"]
        FT["T: Falling, Stable, Rising"]
    end

    RB["2. Rule evaluation<br/>AND = min<br/>15 IF-THEN rules"]
    AG["3. Aggregation<br/>clip each output set,<br/>combine with max"]
    DF["4. Defuzzification<br/>centroid"]
    S["S: suitability 0-100"]
    LBL["Label + colour + icon<br/>Very cheap ... Very expensive"]
    ST["Stability layer<br/>hysteresis, minimum block length"]

    P --> FP
    A --> FA
    G --> FG
    T --> FT
    FP --> RB
    FA --> RB
    FG --> RB
    FT --> RB
    RB --> AG --> DF --> S --> ST --> LBL
```

### Membership functions (starting values, to be calibrated on data)

| Variable | Set | Shape | Parameters |
|---|---|---|---|
| P (0-100) | Very Low | trapezoid | 0, 0, 10, 25 |
| P | Low | triangle | 10, 25, 45 |
| P | Medium | triangle | 35, 50, 65 |
| P | High | triangle | 55, 75, 90 |
| P | Very High | trapezoid | 75, 90, 100, 100 |
| A (0-1) | Low | trapezoid | 0, 0, 0.25, 0.5 |
| A | Medium | triangle | 0.25, 0.5, 0.75 |
| A | High | trapezoid | 0.5, 0.75, 1, 1 |
| G (0-1) | Low, Medium, High | same shapes as A | |
| S (0-100) | Avoid | trapezoid | 0, 0, 10, 25 |
| S | Wait | triangle | 10, 30, 50 |
| S | Okay | triangle | 40, 55, 70 |
| S | Good | triangle | 60, 75, 90 |
| S | Ideal | trapezoid | 75, 90, 100, 100 |

---

## 4. Two-stage structure

Stage 1 judges the hour. Stage 2 adds the user's situation. Splitting the system keeps each rule base small and explainable.

```mermaid
flowchart TD
    subgraph STAGE1["Stage 1: Price suitability FIS"]
        I1["P, A, G, T"] --> F1["Mamdani FIS<br/>15 rules"]
        F1 --> S1["S: suitability 0-100<br/>and label"]
    end

    subgraph STAGE2["Stage 2: Device advisor FIS"]
        U["Urgency U<br/>energy still needed / hours to deadline"]
        D["Device type<br/>EV, heat pump, washing machine"]
        S1 --> F2["Mamdani FIS<br/>about 6 rules"]
        U --> F2
        D --> F2
        F2 --> ACT["Action<br/>Wait, Start now, Must start"]
    end

    ACT --> MSG["Plain-language message<br/>e.g. Charge now, car full by 07:00"]
```

---

## 5. Worked example

One hour on a winter night. The numbers below were calculated by hand and should be confirmed by the code.

**Crisp inputs:** P = 12, A = 0.30, G = 0.20, T = stable

**Step 1: Fuzzification**

| Variable | Membership degrees |
|---|---|
| P = 12 | Very Low 0.87, Low 0.13 |
| A = 0.30 | Low 0.80, Medium 0.20 |
| G = 0.20 | Low 1.0 |
| T = stable | Stable 1.0 |

**Step 2: Rules that fire** (AND = min)

| Rule | Calculation | Strength | Output set |
|---|---|---|---|
| R1: P Very Low AND A Low | min(0.87, 0.80) | 0.80 | Ideal |
| R2: P Very Low AND A Medium | min(0.87, 0.20) | 0.20 | Good |
| R5: P Low AND G Low | min(0.13, 1.0) | 0.13 | Good |

All other rules have strength 0.

**Step 3: Aggregation.** Ideal is clipped at 0.80. Good gets max(0.20, 0.13) = 0.20 and is clipped there. The two clipped shapes are combined with max.

**Step 4: Defuzzification.** The centroid of the combined shape is about **S = 87**.

**Result:** label **"Very cheap: best time"**, and the device advisor can say "Charge the car now" if the user needs the energy by the morning.

```mermaid
flowchart LR
    X["P=12, A=0.30, G=0.20"] --> Y["R1 = 0.80 -> Ideal<br/>R2 = 0.20 -> Good<br/>R5 = 0.13 -> Good"]
    Y --> Z["Aggregate + centroid<br/>S about 87"]
    Z --> W["Very cheap: best time"]
```

---

## 6. System architecture and runtime sequence

### Architecture

```mermaid
flowchart LR
    subgraph SRC["Data sources"]
        U1["Utility tariff schedule"]
        U2["ENTSO-E / EPEX day-ahead"]
        U3["Swissgrid load and generation"]
        U4["MeteoSwiss"]
    end

    subgraph BACK["Backend"]
        ING["Ingestion job<br/>hourly or daily"]
        DB[("Time-series store")]
        REF["Reference window<br/>percentiles, annual ranges"]
        FIS["Fuzzy engine<br/>stage 1 + stage 2"]
        API["REST API"]
    end

    subgraph FRONT["Front end"]
        APP["Web app / PWA<br/>status, next best window, 24-48 h timeline"]
        NOTE["Notifications"]
        HA["Optional: Home Assistant,<br/>EV charger, heat pump"]
    end

    U1 --> ING
    U2 --> ING
    U3 --> ING
    U4 --> ING
    ING --> DB --> REF --> FIS --> API
    API --> APP
    API --> NOTE
    API --> HA
```

### Runtime sequence

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant I as Ingestion
    participant R as Reference window
    participant F as Fuzzy engine
    participant A as API
    participant U as User app

    S->>I: Fetch next-day prices and context
    I->>R: Store and update percentiles
    R->>F: P, A, G, T for each hour
    F->>F: Stage 1 suitability S
    F->>F: Stability layer (hysteresis, block length)
    F->>A: Labels for next 24-48 h
    U->>A: Open app, set car needed by 07:00
    A->>F: Stage 2 with urgency U and device
    F-->>A: Action and best window
    A-->>U: Message and timeline
```

---

## 7. User decision flow

```mermaid
flowchart TD
    START(["User opens app or gets notification"]) --> L{"Current label"}
    L -->|"Very cheap or Cheap"| NOW["Message: good time, start flexible loads"]
    L -->|"Normal"| NEED{"Deadline close?"}
    L -->|"Expensive or Very expensive"| DL{"Deadline close?"}

    NEED -->|"No"| WAITN["Message: no rush, a cheaper window may come"]
    NEED -->|"Yes"| GO["Message: start now to be ready in time"]

    DL -->|"No"| WAITE["Message: wait, next good window at HH:MM"]
    DL -->|"Yes"| MUST["Message: must start now, partial charging in cheapest hours"]

    NOW --> FB["Optional: user confirms or ignores"]
    WAITN --> FB
    GO --> FB
    WAITE --> FB
    MUST --> FB
    FB --> LOG["Log action for pilot evaluation<br/>(consent required)"]
```

---

## Evaluation flow

```mermaid
flowchart TD
    D["Historical + synthetic price data"] --> M1["Fixed CHF thresholds"]
    D --> M2["Crisp percentile bands"]
    D --> M3["Fuzzy Mamdani"]
    D --> M4["Fuzzy Sugeno"]
    D --> M5["Tuned fuzzy (stretch)"]
    M1 --> E["Metrics"]
    M2 --> E
    M3 --> E
    M4 --> E
    M5 --> E
    E --> E1["Label flips per day"]
    E --> E2["Seasonal label distribution"]
    E --> E3["Savings CHF/year, peak shift kWh"]
    E --> E4["Sensitivity and ablation"]
    E --> E5["User comprehension and trust"]
    E1 --> R["Comparison and conclusions"]
    E2 --> R
    E3 --> R
    E4 --> R
    E5 --> R
```
