# Frontend

React 19 + Vite + Tailwind 4 dashboard for the fuzzy-tariff API. `npm run build`
writes straight into `../src/fuzzy_tariff/api/static/`, which FastAPI serves at `/`,
so the backend needs no changes and no Node at runtime.

## Develop

```bash
# terminal 1: API on :8000
cd .. && uvicorn fuzzy_tariff.api.main:app --reload --app-dir src

# terminal 2: UI on :5173 with hot reload (proxies /v1 to :8000)
npm install
npm run dev
```

## Build

```bash
npm run build   # type-checks, then emits index.html + assets/ into the API static dir
```

Commit the built output so `pip install .` and the Docker image ship the UI.

## What is where

| Path | Purpose |
| --- | --- |
| `src/views/` | Scheduler, Engine, Summary, Report |
| `src/components/ui.tsx` | Panels, segmented control, toggle, number field, ECharts wrapper |
| `src/components/reactbits/CountUp.tsx` | reactbits.dev CountUp (hero savings number) |
| `src/components/watermelon/` | Watermelon UI Gauge, ScrubSlider, DiscreteTabs (adapted: controlled + keyboard) |
| `src/components/kokonutui/switch-button.tsx` | kokonutui theme switch |
| `src/lib/motion.ts` | anime.js rule pulse (Engine); Summary narrative stagger lives in its view |
| `src/lib/i18n.tsx` | EN/DE/FR/IT; shared strings in `src/lib/strings.json` |
| `src/index.css` | Design tokens (OKLCH, light + dark) |

Charts are Apache ECharts (tree-shaken in `ui.tsx`); they read colours from the CSS
tokens and redraw when the theme flips.
