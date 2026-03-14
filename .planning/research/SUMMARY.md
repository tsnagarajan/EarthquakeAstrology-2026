# Project Research Summary

**Project:** Earthquake Astrology 2026
**Domain:** Offline ML prediction pipeline + static-JSON-fed Next.js/Vercel web app
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a binary classification ML system that engineers astrological features (planetary positions, aspects, retrograde flags, nakshatras) from Swiss Ephemeris data and USGS earthquake catalog records spanning 1900–2026, trains on the 1900–2000 period, validates on 2000–2026, and exports risk predictions for the remaining 2026 dates as a pre-computed JSON file. The web front-end is a static Next.js/Vercel calendar app that reads that single JSON artifact at build time — Python ML never runs on Vercel. The two subsystems are completely independent and communicate only through `predictions.json`. This is the only viable approach given Vercel's 50 MB serverless function limit, which rules out any runtime ML inference.

The recommended technical path is: Python 3.12 + scikit-learn 1.8.0 + pysweph 2.10.3.6 (not pyswisseph, which is unmaintained) + XGBoost for the ML pipeline, and Next.js 15 + Tailwind CSS 3.4 + TypeScript for the web app. The pipeline must be migrated from Jupyter notebooks to modular `.py` scripts (the project already bans notebooks). The migration must treat notebook code as a reference, not a copy-paste source, because notebooks accumulate hidden execution state that breaks linear script runs. Feature engineering is the most complex phase, with ~265–309 columns that must be correctly cyclically encoded and computed on training data only before any scaler is fitted.

The dominant risks are all in the Python ML pipeline: temporal data leakage from preprocessing before splitting, incorrect use of K-Fold cross-validation on time-series data, relying on accuracy alone on an imbalanced dataset (earthquake days are rare — a naive "no earthquake" classifier exceeds 95% accuracy), and Swiss Ephemeris timezone/Julian Day errors that silently corrupt all planetary position features. On the web side, the main risk is accidentally bundling the predictions JSON into the Vercel function instead of serving it from `public/`. Every critical pitfall has a concrete prevention strategy; none require architectural pivots to fix if caught during the relevant phase.

---

## Key Findings

### Recommended Stack

The Python ML environment runs entirely locally or in CI — never on Vercel. It is built with Python 3.12 and `uv` for package management, with scikit-learn 1.8.0 as the primary ML framework and XGBoost 2.x as the secondary model for handling class imbalance. The critical library choice is `pysweph` (not `pyswisseph`): the original `pyswisseph` package is effectively unmaintained since mid-2025 with no confirmed Python 3.12 wheels, while `pysweph` 2.10.3.6 (released February 2026) is the active community fork with the same `import swisseph as swe` API surface. The web app is Next.js 15 with App Router, TypeScript, and Tailwind CSS 3.4, deployed on Vercel with Server Components reading the JSON artifact at build time.

**Core technologies:**
- Python 3.12: ML pipeline runtime — latest stable with confirmed scikit-learn 1.8.0 wheel support
- scikit-learn 1.8.0: Pipeline API for leakage-free preprocessing; LogisticRegression and KNN match existing model choices
- pysweph 2.10.3.6: Swiss Ephemeris Python bindings — active fork, same API as pyswisseph, do not use the original
- XGBoost 2.x: Handles class imbalance via `scale_pos_weight`; complement to LogReg for tabular binary classification
- imbalanced-learn 0.14.1: SMOTE resampling — only via `imblearn.pipeline.Pipeline`, never before train/test split
- pandas 2.2+ / numpy 2.x: Feature matrix construction and CSV I/O for 265+ column dataset
- requests 2.32+: USGS FDSNWS API with year-chunked pagination (20,000 event limit enforced per request)
- Next.js 15 + React 19: App Router SSG; Server Components read JSON at build time, zero runtime dependencies
- Tailwind CSS 3.4: Responsive calendar layout; stay on 3.4, not v4 alpha (breaking config changes)
- TypeScript 5.x: Type-safe contract between Python JSON output and Next.js components
- date-fns 3.x: Lightweight date utilities for calendar display; replaces moment.js

### Expected Features

The core user promise is a calendar heatmap of 2026 dates color-coded by seismic risk tier, with per-date detail panels and geographic region indicators. The predictions are pre-computed and static. A model accuracy summary card and methodology page with a prominent scientific disclaimer are non-negotiable for credibility — USGS explicitly states earthquakes cannot be reliably predicted, and omitting this is a trust failure.

**Must have (table stakes):**
- Calendar heatmap view (12-month 2026 grid, color by risk tier) — the core product promise
- Per-date detail panel (risk score, region, top planetary aspects) — makes the calendar actionable
- Geographic region text label per prediction — "where" is half the value
- Model accuracy summary card (F1, precision, recall on holdout) — ML credibility requirement
- Methodology and About page with prominent scientific disclaimer — legal and trust necessity
- Mobile-responsive layout — over 50% of web traffic is mobile
- Prediction data freshness indicator — single `generated_at` timestamp from JSON

**Should have (competitive):**
- Interactive world map with risk overlay — transforms calendar into geospatial tool (requires Leaflet)
- Confidence tier labels (Low/Moderate/High) with defined probability thresholds
- CSV/JSON prediction export link — trivial since data is already static JSON
- Predicted vs. actual comparison section — enable as 2026 events accumulate
- Planetary position annotations on calendar — unique to the astrological angle; requires planetary aspects in the JSON output

**Defer (v2+):**
- Full model evaluation dashboard (ROC curve, confusion matrix, per-year breakdown)
- Historical pattern explorer for 1900–2000 training data
- Astrological feature importance chart
- iCal export of high-risk dates

**Anti-features to avoid entirely:** real-time earthquake alerts, magnitude prediction display, user location tracking, push notifications, chat/LLM interpretation, user accounts. All violate the static architecture or overstate model capability.

### Architecture Approach

The system has two completely independent subsystems: a Python ML pipeline that runs offline and a Next.js web app deployed on Vercel. They communicate through a single file: `web/public/data/predictions.json`. Python writes it; Next.js reads it at build time via a Server Component. No Python runs on Vercel at any point. The project structure follows Cookiecutter Data Science v2 conventions for the pipeline (`data/raw/`, `data/interim/`, `data/processed/`, `data/models/`) and standard Next.js App Router conventions for the web app. The JSON schema is the API contract between the two subsystems and must be agreed on and locked before implementing either side.

**Major components:**
1. `pipeline/data/usgs.py` — fetches M5.5+ USGS earthquake records with year-chunked pagination; writes raw CSV
2. `pipeline/data/ephemeris.py` — computes planetary positions for 1900–2026 via pysweph (offline, deterministic)
3. `pipeline/features/engineering.py` — merges earthquake + planetary data; computes aspects, nakshatras, retrograde flags, cyclically-encoded zodiac positions; produces feature matrix CSV
4. `pipeline/models/train.py` — trains on 1900–2000 with temporal split; serializes model via joblib; logs F1/MCC metrics
5. `pipeline/models/predict.py` — loads model; runs inference on 2026 dates; writes `predictions.json` with schema
6. `pipeline/pipeline.py` — orchestrates all steps in sequence with intermediate CSV caching
7. `web/app/page.tsx` — Server Component; imports predictions JSON at build time; renders CalendarView
8. `web/components/CalendarView.tsx` + `DayCard.tsx` — calendar grid and per-day risk cell components

### Critical Pitfalls

1. **Temporal data leakage via preprocessing before the train/test split** — fit all scalers and transformers only on pre-2000 rows; use `sklearn.pipeline.Pipeline` to enforce this; assert `max(X_train.index) < min(X_test.index)` with actual dates
2. **Accuracy as the primary evaluation metric on an imbalanced dataset** — earthquake days are rare, making a naive "never earthquake" classifier score 95%+ accuracy; always report F1, MCC, and a confusion matrix; the ZeroR failure pattern is documented in 2024 scientific literature on earthquake ML
3. **K-Fold cross-validation on time-series data** — standard `KFold`/`StratifiedKFold` shuffles temporally correlated data, inflating scores by 5–20%; use only `sklearn.model_selection.TimeSeriesSplit` with chronological walk-forward folds
4. **SMOTE/resampling applied before the train/test split** — synthetic minority samples derived from test-set events contaminate training data; use `imblearn.pipeline.Pipeline` so resampling applies only inside training folds; the test set must preserve the natural class imbalance
5. **Swiss Ephemeris timezone and Julian Day errors** — all dates must be converted to UTC before calling `swe.julday()`; use `swe.calc_ut()` uniformly (not `swe.calc()`); always call `swe.set_ephe_path()` first; cross-validate 10 planetary positions against JPL Horizons before training
6. **USGS API 20,000-event silent truncation** — a single 1900–2026 query will be truncated; paginate by year or decade; assert no single response returns exactly 20,000 records
7. **Vercel JSON bundle bloat** — predictions JSON placed in `public/` is served via CDN without bundling; if imported as a module in a Server Component it enters the function bundle (250 MB limit); keep JSON in `public/`, never in `src/data/`

---

## Implications for Roadmap

Based on the combined research, the project has hard sequential dependencies that dictate phase order. The web app cannot be finalized without predictions data, and model training cannot begin without a complete feature matrix. However, the web app can be developed in parallel using mock predictions JSON once the schema is agreed on.

### Phase 1: Foundation and Data Pipeline

**Rationale:** Everything downstream depends on having correct USGS earthquake data and accurate planetary positions. This phase has the most external dependencies (USGS API, Swiss Ephemeris data files) and the highest-risk integration — the timezone/Julian Day error in Swiss Ephemeris would corrupt the entire feature matrix if not caught here. Address it first so it cannot propagate.

**Delivers:** `data/raw/usgs_1900_2026.csv` (paginated, complete), `data/raw/ephemeris_1900_2026.csv` (validated against JPL Horizons), project structure with `pyproject.toml`, `uv` environment, and `config.py`

**Addresses:** USGS API pagination (Pitfall 9), Swiss Ephemeris setup and timezone errors (Pitfall 5), Astro Seek scraping elimination (Pitfall 6)

**Avoids:** Do not write a monolithic script; separate `usgs.py` and `ephemeris.py` so each can be re-run independently

**Research flag:** Standard patterns — USGS FDSNWS API is well-documented; pysweph API is documented on Astrodienst

### Phase 2: Feature Engineering Pipeline

**Rationale:** Feature engineering is the most complex phase, with ~265–309 columns including cyclical planetary degree encodings, aspect calculations, retrograde flags, nakshatras, and zodiac sign encodings. The correctness of this phase determines model quality. Cyclical encoding errors (Pitfall 7) and notebook-to-script migration bugs (Pitfall 8) both live here. This phase must produce a verifiable, deterministic feature matrix CSV — not a notebook artifact.

**Delivers:** `data/processed/feature_matrix.csv` (1900–2026 dates, ~265+ columns, cyclically encoded, no leakage); unit-tested feature engineering functions in `pipeline/features/engineering.py`

**Addresses:** Zodiac sign cyclical encoding (Pitfall 7), notebook hidden state migration (Pitfall 8), agreed feature column schema

**Avoids:** Do not apply rolling means or interaction-term statistics across the full dataset before the 2000 split boundary

**Research flag:** Needs deeper research during planning — the existing notebooks contain the feature definitions; a column audit against the notebooks is required to map all 265+ features to their correct encoding strategy

### Phase 3: Model Training and Prediction Export

**Rationale:** With a clean feature matrix and correct train/test temporal split, this phase trains the classifier, evaluates using the correct metrics, and exports predictions JSON. The temporal split (Pitfall 1), CV strategy (Pitfall 2), imbalance handling (Pitfalls 3 and 4), and metric selection all converge here. The output is the JSON schema contract that gates Phase 4.

**Delivers:** `data/models/eq_classifier.pkl` (joblib-serialized, temporal split verified); model evaluation report with F1, MCC, and confusion matrix on 2000–2026 holdout; `web/public/data/predictions.json` with agreed schema including `date`, `risk_score`, `risk_level`, `regions`, `generated_at`, and `model_version`

**Addresses:** Temporal data leakage (Pitfall 1), K-Fold on time series (Pitfall 2), accuracy-only evaluation (Pitfall 3), SMOTE before split (Pitfall 4)

**Uses:** scikit-learn Pipeline API, `TimeSeriesSplit`, `imblearn.pipeline.Pipeline`, XGBoost `scale_pos_weight`, joblib serialization

**Research flag:** Standard patterns — scikit-learn Pipeline and imbalanced-learn documentation is comprehensive; XGBoost class imbalance handling is well-documented

### Phase 4: Next.js Calendar Web App

**Rationale:** Can start in parallel with Phase 3 using a mock `predictions.json` stub that matches the agreed schema. The web app is a pure consumer of the JSON contract. Once real predictions arrive from Phase 3, the mock is swapped out. This phase should not start before the JSON schema is locked.

**Delivers:** Responsive Next.js 15 calendar app with monthly heatmap, per-date detail panel, region indicators, model accuracy summary card, methodology/disclaimer page; deployed to Vercel

**Addresses:** All P1 table-stakes features from FEATURES.md; mobile-responsive layout; Vercel bundle size pitfall (Pitfall 10)

**Avoids:** Do not fetch predictions at runtime in the browser (Anti-Pattern 1); do not import JSON as a module into server components (keep in `public/`); do not run model inference in Vercel serverless functions (Anti-Pattern 2)

**Research flag:** Standard patterns — Next.js App Router SSG and Vercel deployment are well-documented; calendar heatmap libraries (cal-heatmap, shadcn-calendar-heatmap) are available

### Phase 5: Integration, Validation, and Deployment

**Rationale:** Final phase connects the real predictions output from Phase 3 to the web app from Phase 4, verifies the full build pipeline end-to-end, and deploys to Vercel. The predictions JSON completeness check (all March–December 2026 dates present) and Vercel bundle size verification both live here.

**Delivers:** Live Vercel deployment with real 2026 predictions; verified bundle sizes; prediction JSON completeness assertion; documentation of pipeline re-run instructions for future updates

**Addresses:** "Looks Done But Isn't" checklist from PITFALLS.md; Vercel bundle validation (Pitfall 10); prediction freshness indicator

**Research flag:** Standard patterns — Vercel deployment via git push is well-documented; no novel integration work required

### Phase Ordering Rationale

- Phases 1 and 2 are strictly sequential — feature engineering depends on raw data
- Phase 3 depends on Phase 2 but JSON schema definition can happen earlier
- Phase 4 can begin in parallel with Phase 3 once the JSON schema is agreed on; this is the primary opportunity to save calendar time
- Phase 5 requires both Phase 3 (real predictions) and Phase 4 (built web app)
- The web app (Phase 4) is blocked on mock JSON until Phase 3 completes, so agree on the JSON schema as the first cross-phase deliverable

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Feature Engineering):** The 265–309 column feature space is defined in existing notebooks that contain both production logic and exploratory code mixed together. A column-by-column audit is required before planning can produce accurate task estimates. Research should enumerate all feature types (aspects, nakshatras, retrograde, signs, houses) and their correct encoding strategy.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Pipeline):** USGS FDSNWS API is thoroughly documented; pysweph setup is documented on Astrodienst; pagination strategy is clear
- **Phase 3 (Model Training):** scikit-learn Pipeline, TimeSeriesSplit, and imbalanced-learn patterns are authoritative and well-covered
- **Phase 4 (Next.js UI):** App Router SSG, Vercel deployment, and Tailwind CSS are well-documented; no novel integration work
- **Phase 5 (Deployment):** Git-push-to-Vercel is standard; no research needed

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core choices (Python 3.12, scikit-learn 1.8.0, Next.js 15, Vercel) verified against official release notes and documentation; pysweph vs. pyswisseph finding is HIGH confidence (multiple sources confirm pyswisseph abandonment); Tailwind 3.4 vs. v4 distinction verified |
| Features | MEDIUM | Feature landscape derived from USGS reference apps, open-source earthquake forecasting repos, and ML dashboard standards; feature prioritization reflects research consensus but has not been validated against target audience; confidence on "what users expect" is MEDIUM |
| Architecture | HIGH | Two-subsystem pattern (offline pipeline + static JSON + SSG web app) is the only technically viable approach given Vercel Python constraints; patterns are well-documented in official Next.js and Vercel docs; no speculative architecture choices |
| Pitfalls | HIGH | Critical ML pitfalls (leakage, CV strategy, imbalance metrics) are sourced from official scikit-learn and imbalanced-learn documentation and peer-reviewed literature; USGS API limit is official documentation; Swiss Ephemeris timezone issues sourced from official Astrodienst programming guide |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Existing notebook column inventory:** The exact set of 265–309 feature columns, their current encoding (raw integer vs. one-hot vs. cyclical), and which ones correspond to scraped vs. computed values is not enumerated in any research file. This must be audited from the Archive notebooks before Phase 2 planning produces accurate estimates. Risk: feature engineering complexity is underestimated.
- **pysweph migration from pyswisseph:** Research confirms `pysweph` 2.10.3.6 has breaking changes from `pyswisseph` 2.10.3.2. The migration guide has not been reviewed in detail. This needs to be consulted before Phase 1 implementation begins. Risk: existing ephemeris code may require non-trivial rewrites.
- **Model performance expectations:** No prior model performance benchmarks exist in the research files. The 2000–2026 holdout F1/MCC baseline is unknown. If model performance on the holdout is poor, the web app's model accuracy summary card becomes a liability rather than a credibility asset. Research flags this as a known risk but cannot resolve it without running the pipeline.
- **Planetary aspect data in predictions JSON:** The FEATURES.md dependency diagram notes that planetary annotations on the calendar require planetary aspect data to be included in `predictions.json` — but the predictions schema defined in ARCHITECTURE.md does not yet include an `aspects` field. This must be added to the schema before Phase 3 or the P2 planetary annotations feature cannot be implemented in Phase 4.

---

## Sources

### Primary (HIGH confidence)
- [pysweph PyPI](https://pypi.org/project/pysweph/) — active fork status, v2.10.3.6 Feb 2026 release
- [pyswisseph PyPI](https://pypi.org/project/pyswisseph/) — maintenance discontinuation confirmed
- [USGS FDSNWS Event API](https://earthquake.usgs.gov/fdsnws/event/1/) — 20,000-event limit, query parameters, CSV format
- [scikit-learn Common Pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) — leakage and CV pitfalls
- [imbalanced-learn Common Pitfalls](https://imbalanced-learn.org/stable/common_pitfalls.html) — SMOTE before split warning
- [Swiss Ephemeris Programming Interface (Astrodienst)](https://www.astro.com/swisseph/swephprg.htm) — `calc_ut` vs `calc`, `set_ephe_path`, time scales
- [Next.js Static Exports](https://nextjs.org/docs/app/guides/static-exports) — App Router SSG pattern
- [Vercel Next.js framework](https://vercel.com/docs/frameworks/full-stack/nextjs) — deployment integration and limits
- [Vercel Limits](https://vercel.com/docs/limits) — 250 MB function bundle limit
- [Frontiers in Earth Science — Earthquake ML imbalanced datasets](https://www.frontiersin.org/articles/10.3389/feart.2022.847808/full) — MCC recommended for seismic classification
- [Scientific Reports 2024 — Earthquake prediction LA](https://www.nature.com/articles/s41598-024-76483-x) — ZeroR baseline failure documented

### Secondary (MEDIUM confidence)
- [Cal-Heatmap library](https://cal-heatmap.com/v2/) — calendar heatmap component patterns
- [Cookiecutter Data Science v2](https://cookiecutter-data-science.drivendata.org/) — pipeline directory structure conventions
- [Cyclical Encoding for Time Series — Towards Data Science](https://towardsdatascience.com/cyclical-encoding-an-alternative-to-one-hot-encoding-for-time-series-features-4db46248ebba/) — sin/cos encoding rationale
- [Temporal Leakage in LSTM Forecasting — arXiv 2512.06932](https://arxiv.org/html/2512.06932v1) — empirical 20%+ bias from pre-split preprocessing
- WebSearch: pyswisseph maintenance discontinuation mid-2025 (multiple sources agree)

### Tertiary (LOW confidence)
- [Made With ML — Moving from Notebooks to Scripts](https://madewithml.com/courses/mlops/scripting/) — migration patterns (single source)
- [Aalto Scientific Computing — Jupyter Pitfalls](https://scicomp.aalto.fi/scicomp/jupyter-pitfalls/) — notebook state issues (MEDIUM-LOW)

---

*Research completed: 2026-03-14*
*Ready for roadmap: yes*
