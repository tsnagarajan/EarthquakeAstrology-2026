# Architecture Research

**Domain:** Offline ML prediction pipeline + static-JSON-fed Next.js web app
**Researched:** 2026-03-14
**Confidence:** HIGH

## Standard Architecture

### System Overview

This system has two completely independent subsystems connected by a single artifact: a pre-computed JSON predictions file. The Python ML pipeline runs locally (never on Vercel). The Next.js web app reads that JSON at build time and renders a static site. Nothing runs at request time.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PYTHON ML PIPELINE (local)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │ data/        │    │ features/    │    │ models/                  │   │
│  │ usgs.py      │───▶│ engineering  │───▶│ train.py → predict.py    │   │
│  │ ephemeris.py │    │ .py          │    │                          │   │
│  └──────────────┘    └──────────────┘    └────────────┬─────────────┘   │
│        ▲                                              │                 │
│  USGS Catalog API                                     │                 │
│  Swiss Ephemeris                                      ▼                 │
│  (offline, no network at predict time)          predictions.json        │
│                                                       │                 │
└───────────────────────────────────────────────────────┼─────────────────┘
                                                        │ manual copy
                                                        │ OR git commit
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       NEXT.JS WEB APP (Vercel)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  /public/data/predictions.json   ← static asset, committed to repo      │
│          │                                                               │
│          ▼ (read at build time via import or fs.readFileSync)            │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │  app/page.tsx  →  CalendarView component  →  DayCard component │      │
│  └────────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  npm run build → Vercel CDN → static HTML/JS bundle                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `pipeline/data/usgs.py` | Fetch M5.5+ earthquake records via USGS Catalog API, write raw CSV | Nothing (entry point) |
| `pipeline/data/ephemeris.py` | Compute planetary positions for 1900–2026 using pyswisseph, write CSV | Nothing (entry point) |
| `pipeline/features/engineering.py` | Merge earthquake + planetary data, compute aspects, nakshatras, retrograde flags, produce feature matrix CSV | Reads outputs of data scripts |
| `pipeline/models/train.py` | Train classifier on 1900–2000 data, serialize model artifact | Reads feature matrix |
| `pipeline/models/predict.py` | Load model, run inference on 2026 dates, write `predictions.json` | Reads model artifact + 2026 feature matrix |
| `pipeline/pipeline.py` | Orchestrate the above scripts in sequence via subprocess or direct function calls | Calls all components |
| `web/public/data/predictions.json` | Static artifact consumed by the web app. The only file crossing the boundary | Written by Python, read by Next.js |
| `web/app/page.tsx` | Root page: reads JSON at build time, passes data to calendar | Reads predictions.json |
| `web/components/CalendarView.tsx` | Renders a month-grid calendar, highlights high-risk dates | Receives prediction data as props |
| `web/components/DayCard.tsx` | Renders a single day cell with risk level and region info | Receives single-day prediction as prop |

## Recommended Project Structure

```
Earthquake 2026/
├── pipeline/                       # Python ML subsystem
│   ├── data/
│   │   ├── usgs.py                 # USGS Catalog API download (M5.5+, 1900-2026)
│   │   └── ephemeris.py            # Planetary positions via pyswisseph
│   ├── features/
│   │   └── engineering.py          # Feature matrix construction (aspects, nakshatras, etc.)
│   ├── models/
│   │   ├── train.py                # Train on 1900-2000, serialize with joblib
│   │   └── predict.py              # Load model, predict 2026, export JSON
│   ├── pipeline.py                 # Top-level orchestrator: run all steps in order
│   ├── config.py                   # Paths, date ranges, magnitude threshold
│   └── requirements.txt            # pinned: pandas, scikit-learn, pyswisseph, etc.
│
├── data/                           # Data artifacts (gitignored except final predictions)
│   ├── raw/
│   │   ├── usgs_1900_2026.csv      # Downloaded from USGS
│   │   └── ephemeris_1900_2026.csv # Computed from Swiss Ephemeris
│   ├── interim/
│   │   └── merged_features.csv     # Merged earthquake + astro features
│   ├── processed/
│   │   └── feature_matrix.csv      # Final ML-ready features
│   └── models/
│       └── eq_classifier.pkl       # Serialized trained model (joblib)
│
├── web/                            # Next.js subsystem
│   ├── public/
│   │   └── data/
│   │       └── predictions.json    # THE BRIDGE — committed to repo after each pipeline run
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Root: imports predictions.json, renders CalendarView
│   │   └── globals.css
│   ├── components/
│   │   ├── CalendarView.tsx        # 12-month grid for 2026
│   │   ├── DayCard.tsx             # Single date cell with risk indicator
│   │   └── RegionBadge.tsx         # Country/region chip display
│   ├── lib/
│   │   └── predictions.ts          # Type definitions + loader utility
│   ├── package.json
│   └── next.config.ts
│
├── .planning/                      # Project planning artifacts
└── Archive/                        # Historical notebooks (read-only reference)
```

### Structure Rationale

- **pipeline/ vs web/:** Hard separation. Python code never imports JS; Next.js never calls Python. The only connection is the JSON file.
- **data/raw/, data/interim/, data/processed/:** Follows Cookiecutter Data Science v2 convention. Raw data is immutable; transformations produce new files, never overwrite originals. Enables re-running from any stage without re-fetching.
- **data/models/:** Model artifacts stay with the pipeline, not the web app. The web app never loads a `.pkl` file.
- **web/public/data/:** Placing `predictions.json` in `public/data/` makes it accessible as a static asset at `/data/predictions.json` and also importable at build time via `import` or `fs.readFileSync` in Server Components.
- **pipeline/config.py:** Centralizes all tunable parameters (date ranges, magnitude threshold, model hyperparameters) in one place so scripts don't have magic strings scattered through them.

## Architectural Patterns

### Pattern 1: Offline Batch Prediction → Static JSON Export

**What:** The Python pipeline runs on a developer's machine (or CI), produces a fully pre-computed `predictions.json`, and that file is committed to the repo. The web app reads this file at build time. No ML code runs at request time.

**When to use:** When the model's inputs (planetary positions) are deterministic and known in advance — perfect for astrological forecasting. Vercel cannot run Python, so this is the only viable approach.

**Trade-offs:** Predictions are frozen at build time. Updating predictions requires re-running the pipeline and re-deploying. For a 2026-scoped project this is acceptable — run once, deploy once.

**Example:**
```python
# pipeline/models/predict.py
import json, joblib, pandas as pd
from pipeline.config import PREDICTION_OUTPUT_PATH

model = joblib.load("data/models/eq_classifier.pkl")
features_2026 = pd.read_csv("data/processed/features_2026.csv")
probs = model.predict_proba(features_2026)[:, 1]

predictions = [
    {
        "date": row["date"],
        "risk_score": round(float(prob), 4),
        "region": row["region"],
        "lat": row["lat"],
        "lon": row["lon"],
    }
    for row, prob in zip(features_2026.to_dict("records"), probs)
]

with open(PREDICTION_OUTPUT_PATH, "w") as f:
    json.dump(predictions, f, indent=2)
```

### Pattern 2: Next.js Server Component JSON Import at Build Time

**What:** In the App Router, `page.tsx` is a Server Component by default. Import the JSON file directly (Node.js `fs` or `import`) — this runs only at build time on the server, never in the browser.

**When to use:** When JSON is small enough to inline (predictions for ~300 days with metadata is under 500KB — fine). Avoids a client-side fetch, which would cause a loading flash and require error handling.

**Trade-offs:** JSON is baked into the page bundle at build time. This is a feature, not a bug — it means zero runtime dependencies on external services.

**Example:**
```typescript
// web/app/page.tsx  (Server Component — runs at build time)
import predictionsData from "../public/data/predictions.json";
import { CalendarView } from "../components/CalendarView";

export default function Home() {
  return <CalendarView predictions={predictionsData} />;
}
```

### Pattern 3: Temporal Train/Validate/Predict Split

**What:** The dataset is partitioned strictly by time: train on 1900–2000, validate on 2000–2026, generate predictions for March–December 2026. No shuffling across these boundaries.

**When to use:** Always, for time-series data. Shuffling earthquake data would cause data leakage because nearby dates have correlated planetary positions.

**Trade-offs:** Reduces effective training set size compared to cross-validation, but avoids the fundamental error of predicting the past using the future.

**Example:**
```python
# pipeline/models/train.py
train = df[df["year"] <= 2000]
validate = df[(df["year"] > 2000) & (df["year"] <= 2026)]
predict_set = df[df["year"] == 2026]

X_train, y_train = train[FEATURE_COLS], train["eq_happened"]
X_val, y_val = validate[FEATURE_COLS], validate["eq_happened"]
```

## Data Flow

### Pipeline Execution Flow

```
Developer runs: python pipeline/pipeline.py
    │
    ├── Step 1: data/usgs.py
    │       USGS Catalog API (HTTP) → data/raw/usgs_1900_2026.csv
    │
    ├── Step 2: data/ephemeris.py
    │       pyswisseph (local, offline) → data/raw/ephemeris_1900_2026.csv
    │
    ├── Step 3: features/engineering.py
    │       usgs CSV + ephemeris CSV → merge on date
    │       compute: degrees, aspects, retrograde, nakshatras, signs, houses
    │       → data/interim/merged_features.csv
    │       → data/processed/feature_matrix.csv
    │
    ├── Step 4: models/train.py
    │       feature_matrix.csv [1900-2000] → LogisticRegression fit
    │       evaluate on [2000-2026] holdout → print metrics
    │       → data/models/eq_classifier.pkl
    │
    └── Step 5: models/predict.py
            feature_matrix.csv [2026 dates only] + model → predict_proba
            → web/public/data/predictions.json   ← BRIDGE
```

### Web App Request Flow

```
Vercel Build (npm run build)
    │
    ├── Next.js reads web/public/data/predictions.json (at build time)
    │
    ├── page.tsx (Server Component) passes predictions to CalendarView
    │
    └── Renders 12-month calendar HTML with risk scores baked in
            ↓
    CDN distributes static bundle
            ↓
    User visits URL → HTML delivered instantly, no API calls
```

### Predictions JSON Schema

The JSON file is the only cross-boundary artifact. Its schema must be agreed before implementing either side.

```json
{
  "generated_at": "2026-03-14T10:00:00Z",
  "model_version": "1.0.0",
  "validation_accuracy": 0.73,
  "predictions": [
    {
      "date": "2026-03-15",
      "risk_score": 0.812,
      "risk_level": "high",
      "regions": [
        {
          "country": "Japan",
          "lat": 35.6,
          "lon": 139.7,
          "confidence": 0.78
        }
      ]
    }
  ]
}
```

`risk_level` is a derived string (`"high"` if `risk_score > 0.7`, `"medium"` if `> 0.5`, `"low"` otherwise). Both sides should agree on these thresholds and not recalculate them independently.

## Build Order

The two subsystems must be built in this order — each phase is a hard dependency for the next:

```
Phase 1: Python data layer
  - USGS data download works
  - pyswisseph ephemeris computation works
  - Merged dataset with correct date alignment verified

Phase 2: Python feature engineering
  - All ~265-309 feature columns from existing notebooks recreated as Python functions
  - Feature matrix matches known shape from historical CSVs
  - Requires Phase 1

Phase 3: Python ML training + prediction export
  - Train/validate split confirmed (no leakage)
  - Model exported, validation metrics logged
  - predictions.json written with correct schema
  - Requires Phase 2

Phase 4: Next.js calendar UI
  - Can start in parallel with Phase 3 using a mock predictions.json
  - Calendar renders with dummy data before real predictions exist
  - Final integration: swap mock JSON for real predictions.json from Phase 3

Phase 5: Vercel deployment
  - Copy real predictions.json to web/public/data/
  - npm run build passes
  - Deploy to Vercel
  - Requires Phases 3 + 4
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 users | Current architecture is exactly right. Static site, no backend. |
| 100-10K users | No changes needed. Vercel CDN handles this trivially with static files. |
| 10K-1M users | Still no changes needed. Static HTML has near-zero server cost. Bottleneck is CDN egress, not compute. |
| Live predictions (future) | Would require adding an API route (Next.js Route Handler) and a Python inference server. This is an architectural change, not a scaling change. Out of scope for current project. |

### Scaling Priorities

1. **First bottleneck:** The pipeline runtime on the developer's machine. USGS data download for 1900–2026 may take minutes; ephemeris computation for 45,000+ days (126 years * 365) takes seconds with pyswisseph. Optimize data scripts first if iteration is slow.
2. **Second bottleneck:** predictions.json file size. If predictions include per-region data for every date in 2026, the file could reach 1-5MB. Acceptable for static delivery but should be verified before implementing.

## Anti-Patterns

### Anti-Pattern 1: Fetching Predictions at Runtime in the Browser

**What people do:** Place `predictions.json` in an API route or external URL and `fetch()` it in a React `useEffect` hook.

**Why it's wrong:** Introduces loading states, error handling, and hydration complexity. The data is static — it never changes during the user's session. Fetching at runtime provides zero benefit and adds failure modes (network down, CORS, rate limits).

**Do this instead:** Import the JSON in a Server Component at build time. The HTML rendered by Vercel already contains the predictions. No client-side fetch needed.

### Anti-Pattern 2: Running Model Inference in a Vercel Serverless Function

**What people do:** Deploy the sklearn model as a Vercel Python serverless function and call it from the Next.js app.

**Why it's wrong:** Vercel serverless functions have a 50MB size limit. The sklearn + numpy + pandas dependency tree alone exceeds this. Additionally, planetary position computation requires Swiss Ephemeris data files. This approach is technically blocked, not just inadvisable.

**Do this instead:** Pre-compute all predictions offline. The model only needs to run once. Commit `predictions.json` to the repo and let Vercel serve it as a static asset.

### Anti-Pattern 3: Storing Data Files in the Python Pipeline's Output Without a Schema Contract

**What people do:** Have the Python pipeline write whatever columns are convenient and have the Next.js app figure it out.

**Why it's wrong:** The JSON schema is the API contract between two independent systems. If the Python side changes the output shape, the web app silently breaks (or TypeScript shows type errors only at build time, not at pipeline runtime).

**Do this instead:** Define the TypeScript type for predictions in `web/lib/predictions.ts` and mirror it as a Python dataclass or TypedDict in `pipeline/models/predict.py`. Keep both in sync consciously.

### Anti-Pattern 4: Mixing Notebook Code Directly into the New Pipeline

**What people do:** Convert the Jupyter notebook cells directly to a script by stripping markdown and stitching code cells together.

**Why it's wrong:** The existing notebook has global state, cells that run exploratory analysis mixed with production logic, and no separation between the scraping phase (which needs the internet) and the feature engineering phase (which doesn't). A direct conversion produces an untestable monolith.

**Do this instead:** Port logic function by function, separating concerns into the module structure above (data/, features/, models/). Each module should be independently runnable and testable.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| USGS Earthquake Catalog API | HTTP GET from `data/usgs.py`, write CSV once | URL: `https://earthquake.usgs.gov/fdsnws/event/1/query`. Paginate for 1900-2026. One-time download; cache locally. |
| Swiss Ephemeris (pyswisseph) | Local Python library, no network | Ephemeris data files bundled with pyswisseph. Covers 1900-2026 without internet. Existing code used Astro Seek scraping — replace this with pyswisseph for reliability. |
| Vercel | Git push triggers deploy | predictions.json must be committed to repo before deploying. Vercel reads it during `npm run build`. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Python pipeline → Next.js web app | `web/public/data/predictions.json` (file on disk) | Single file. Agreed schema. Python writes it; Next.js reads it. No other channel. |
| pipeline/data → pipeline/features | CSV files in `data/raw/` and `data/interim/` | Data scripts write CSVs; feature engineering reads them. No in-memory passing between modules. |
| pipeline/models/train.py → predict.py | `data/models/eq_classifier.pkl` (joblib) | Train writes the model artifact; predict loads it. Decoupled — retrain without re-running predictions, predict without retraining. |
| Next.js page → CalendarView component | TypeScript props (Prediction[]) | Server Component passes the full predictions array; CalendarView handles grouping by month/date internally. |

## Sources

- Next.js App Router static data fetching: [nextjs.org/docs/app/guides/static-exports](https://nextjs.org/docs/app/guides/static-exports)
- Next.js public folder conventions: [nextjs.org/docs/app/api-reference/file-conventions/public-folder](https://nextjs.org/docs/app/api-reference/file-conventions/public-folder)
- Cookiecutter Data Science v2 project layout: [cookiecutter-data-science.drivendata.org](https://cookiecutter-data-science.drivendata.org/)
- pyswisseph (Swiss Ephemeris Python bindings): [github.com/astrorigin/pyswisseph](https://github.com/astrorigin/pyswisseph)
- PySwisseph on PyPI: [pypi.org/project/pyswisseph](https://pypi.org/project/pyswisseph/)
- Next.js getStaticProps + JSON pattern (Pages Router reference): [nextjs.org/docs/pages/building-your-application/data-fetching/get-static-props](https://nextjs.org/docs/pages/building-your-application/data-fetching/get-static-props)

---
*Architecture research for: Earthquake Astrology Prediction 2026 — offline ML pipeline + static Next.js calendar*
*Researched: 2026-03-14*
