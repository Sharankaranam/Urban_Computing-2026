# Data sources

Compiled 2026-10-18 from web research. **Verify licence, format and availability before use.** Where the schema is not documented here, read the official documentation first and record what you find (see `src/fuzzy_tariff/ingest/AGENTS.md`).

## Prices

| Source | What | Access | Notes |
|---|---|---|---|
| EKZ dynamic tariff API | Real Swiss dynamic tariff, 15-minute intervals, next day published from about 18:00 | https://api.tariffs.ekz.ch/ ; tariff sheet: https://www.ekz.ch/dam/ekz/privatkunden/strom/tarife-und-agb/Tarifdokumente/tarife-2026/ekz-dynamischer-tarif-2026-tarifblatt.pdf | Grid component driven by a squared load forecast; energy component within ±5 Rp./kWh of standard. Check API docs for auth. No history: **log it daily** (`scripts/log_ekz_tariff.py`). |
| ENTSO-E Transparency Platform | Day-ahead market prices (EUR/MWh) | https://transparency.entsoe.eu ; free account, request an API token via web API access | Energy price, not a grid tariff. Verify CH domain availability. Parser: `ingest/entsoe.py`. |
| ElCom tariff data | Annual tariffs per provider/municipality, 2009-2026 | https://www.strompreis.elcom.admin.ch/ ; https://opendata.swiss/en/dataset/strompreis-per-stromnetzbetreiber (SPARQL endpoint) | Not hourly. Use for annual min-max range for input A. |
| Other utilities | BKW announced a voluntary dynamic grid tariff from 2027; Groupe E offered one early | utility sites | No public API found. |

## Grid and weather

| Source | What | Access |
|---|---|---|
| Swissgrid energy statistics | Load/generation, 15-minute aggregates, yearly files from 2009 | https://www.swissgrid.ch/en/home/customers/topics/energy-data-ch |
| BFE Energy Dashboard | Hourly national consumption, daily updates | https://www.energiedashboard.admin.ch/dashboard |
| MeteoSwiss Open Data | Hourly measurements and forecasts (temperature `tre200s0`, global radiation `gre000z0`, forecast radiation `gre000h0`) | docs: https://opendatadocs.meteoswiss.ch ; STAC API: https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn ; cite the source |

## Household load data (for savings simulation)

| Dataset | What | Access |
|---|---|---|
| HEAPO | 15-minute smart-meter data of 1,408 heat-pump households (Zurich area), 2018-2024, CC BY 4.0, about 458 MB | https://zenodo.org/records/15056919 |
| Kaiser et al., ETH/EKZ | 15-minute data of 2,447 Swiss residential installations, 2023-2024, including price profiles of a pilot with novel tariffs | https://arxiv.org/pdf/2607.19294 (find the data link in the paper; not verified here) |

## How the simulator uses these sources

| Simulator input | Real source to plug in |
|---|---|
| Spot price (EUR/MWh) | ENTSO-E / EPEX day-ahead (Switzerland) |
| Net load (MW) of the tariff area | ewz gross load curve of the City of Zurich (15 min, since 2019, https://data.stadt-zuerich.ch/dataset/ewz_bruttolastgang_stadt_zuerich), Swissgrid, or BFE dashboard, scaled with `scale_load_to_mean_mw` |
| Tariff structure and bands | EKZ "Dynamischer Tarif 2026 - Technischer Beschrieb" (https://www.ekz.ch/dam/ekz/privatkunden/strom/tarife-und-agb/Tarifdokumente/tarife-2026/EKZ_Dynamischer-Tarif-2026_technischer-Beschrieb.pdf) |
| Standard tariff levels | EKZ tariff sheets (the numbers were not machine-readable when read; enter them in `TariffSpec`) |

Other Swiss data on opendata.swiss: ewz quarter-hour consumption on grid levels 5 and 7 (Zurich since 2015, Mittelbünden since 2018). Innostrom (Swisspower) API test environment returns constant dummy prices, so it is useful only for checking formats.

Correction: the ElCom opendata.swiss page lists temporal coverage 2009-2021; use https://www.strompreis.elcom.admin.ch/ for current years.

## Mapping to fuzzy inputs

| Input | Source |
|---|---|
| P relative price | EKZ / ENTSO-E / synthetic prices, reference window computed by `features/` |
| A absolute price | same prices; annual range from the tariff sheet or ElCom |
| G grid stress | Swissgrid or BFE dashboard load minus solar (residual load); EKZ's own load-based design is a useful reference |
| T trend | next hours of the same price series |
| Heat-pump context | MeteoSwiss temperature |
| Savings simulation | HEAPO and the ETH/EKZ dataset |

## Open items
- Read the EKZ API documentation and implement `ingest/ekz.py`.
- Confirm ENTSO-E CH day-ahead coverage with a real token.
- Locate the download link for the ETH/EKZ dataset.
- Confirm licences for Swissgrid and BFE data reuse.
