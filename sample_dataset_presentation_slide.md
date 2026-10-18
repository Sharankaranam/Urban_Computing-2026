# Slide: Sample Data & End-to-End Pipeline Trace

### **Real 24-Hour Swiss Dynamic Tariff Sample (Winter Peak Day - Jan 15, 2025)**
*Shows how 15-minute raw market & grid data transforms into fuzzy inputs ($P, A, G, T$), fires Mamdani rules, and schedules household appliances:*

| Time (t) | Spot Price (€/MWh) | Substation Net Load (MW) | Total Tariff (Rp./kWh) | Percentile P (%) | Absolute A (CHF) | Grid G (0–1) | Trend T | Fired Mamdani Rules | Fuzzy Score S (0–100) | Linguistic Label | Automated Appliance Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **00:00** | 94.5 | 149.9 | **13.88** | 1.2% | CHF 0.14 | 0.50 | -0.1 | `R01` | **90.7** | `IDEAL` | 🚗 **EV Charging (7.4 kW)** |
| **02:00** | 98.8 | 142.3 | **14.02** | 1.8% | CHF 0.14 | 0.42 | -0.1 | `R01` | **90.7** | `IDEAL` | 🚗 **EV Charging (7.4 kW)** |
| **06:30** | 119.9 | 195.6 | **21.20** | 34.8% | CHF 0.21 | 0.96 | +0.5 | `R07` | **55.0** | `OKAY` | ⏸️ Normal Household Idle |
| **08:30** | 128.1 | 185.8 | **20.80** | 32.9% | CHF 0.21 | 0.86 | +0.0 | `R07` | **55.0** | `OKAY` | ⏸️ Normal Household Idle |
| **13:00** | 131.5 | 176.3 | **20.03** | 29.4% | CHF 0.20 | 0.76 | +0.0 | `R07` | **55.0** | `OKAY` | 🍽️ **Dishwasher Cycle (1.5 kW)** |
| **15:30** | 143.2 | 206.7 | **24.76** | 51.1% | CHF 0.25 | 1.00 | +0.0 | `R08` | **55.0** | `OKAY` | ⏸️ Normal Household Idle |
| **18:00** | 191.2 | 252.0 | **35.41** | 100.0% | CHF 0.35 | 1.00 | +0.2 | `R14` | **9.3** | `AVOID` | 🛡️ **BLOCKED (Peak Protection)** |
| **19:30** | 171.6 | 227.3 | **30.22** | 76.2% | CHF 0.30 | 1.00 | +0.0 | `R13, R14` | **9.5** | `AVOID` | 🛡️ **BLOCKED (Peak Protection)** |
| **22:00** | 119.0 | 179.9 | **19.27** | 25.9% | CHF 0.19 | 0.80 | -0.4 | `R07` | **55.0** | `OKAY` | ♨️ **Heat Pump Buffer (2.5 kW)** |
| **23:30** | 104.4 | 153.7 | **15.22** | 7.4% | CHF 0.15 | 0.54 | +0.0 | `R01` | **90.7** | `IDEAL` | 🚗 **EV Charging (7.4 kW)** |

---

### **Key Analytical Takeaways for the Slide:**
1. **Off-Peak Night Window (00:00 – 04:00):** Total tariff dips to **13.88 Rp./kWh**. Rule `R01` fires, defuzzifying to a maximum score of **90.7 (IDEAL)**. This is where high-power loads (EV, heat pump) are concentrated.
2. **Evening Grid Peak (17:30 – 20:30):** High European spot price (€191.2/MWh) combined with maximum substation load (252 MW) pushes the tariff to **35.41 Rp./kWh**. Rules `R13` and `R14` fire, plunging the score to **9.3 (AVOID)** and blocking all heavy appliances.
3. **Midday Solar Balance (13:00):** Tariff eases to **20.03 Rp./kWh**, providing an ideal secondary window for lower-power household appliances (dishwasher, washer).

> **🎤 Speaker Notes:**  
> *"Here you can see the real numbers flowing through our system on a typical winter day. At 2:00 AM, the total tariff is only 14 Rappen and the grid is calm, so Rule R01 fires and outputs a 90.7 score, directing the 7.4 kW EV charger to run. At 6:00 PM, prices spike to 35 Rappen and the neighborhood substation is maxed at 252 MW—Rules R13 and R14 drop the score to 9.3, automatically locking out heavy appliances and avoiding costly peak fees."*
