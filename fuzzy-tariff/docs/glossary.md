# Glossary

| Term | Meaning |
|---|---|
| Fuzzy set | A set where membership is a degree in [0, 1], not yes/no |
| Membership function (MF) | Function giving the degree to which a value belongs to a fuzzy set (here triangular or trapezoidal) |
| Linguistic variable | A variable whose values are words ("low", "high") defined by fuzzy sets over a numeric universe |
| Universe of discourse | The numeric range of a variable (P: 0-100) |
| Fuzzification | Turning a crisp input into membership degrees |
| Rule base | Set of IF-THEN rules |
| Antecedent / consequent | The IF part / the THEN part of a rule |
| Firing strength | Degree to which a rule's antecedent holds (min of its memberships) |
| Implication | Clipping the consequent set at the firing strength (min) |
| Aggregation | Combining all clipped consequents (max) |
| Defuzzification | Turning the aggregated fuzzy output into one number (centroid) |
| Mamdani FIS | Fuzzy system with fuzzy sets in the consequents |
| Sugeno (TSK) FIS | Fuzzy system with crisp or linear consequents |
| Type-2 fuzzy set | Fuzzy set whose membership degrees are themselves fuzzy (models uncertainty) |
| Hysteresis | Requiring a margin before switching state, to avoid flicker |
| Residual load | Load minus solar generation; proxy for grid stress |
| P, A, G, T, S, U | Relative price percentile, absolute price, grid stress, trend, suitability score, urgency |
| Day-ahead tariff | Tariff for the next day, published before it starts |
| Dynamic (time-variable) tariff | Tariff whose price changes by time of day |
