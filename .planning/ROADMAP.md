# Roadmap: Earthquake Astrology Prediction 2026

## Overview

The project builds in four sequential phases. Phase 1 establishes the two raw data sources — USGS earthquake records and Swiss Ephemeris planetary positions — with validation so corruption cannot propagate. Phase 2 transforms raw data into the full ~265-column feature matrix with correct cyclical encoding and a strict 2000-01-01 temporal boundary. Phase 3 trains the classifier, evaluates it on the 26-year holdout with the right metrics, and exports predictions.json — the artifact that gates the web app. Phase 4 builds the Next.js calendar UI against real predictions and deploys to Vercel.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Pipeline** - Fetch and validate USGS earthquake records and Swiss Ephemeris planetary positions for 1900–2026
- [ ] **Phase 2: Feature Engineering** - Build the full ~265-column feature matrix with cyclical encoding, aspects, nakshatras, and strict no-leakage temporal split
- [ ] **Phase 3: Model Training and Prediction Export** - Train classifier on 1900–2000 data, evaluate on 2000–2026 holdout, export predictions.json for March–December 2026
- [ ] **Phase 4: Web App and Deployment** - Build Next.js calendar app consuming predictions.json and deploy to Vercel

## Phase Details

### Phase 1: Data Pipeline
**Goal**: Raw earthquake and planetary position data for 1900–2026 exists on disk, is complete, and is validated as accurate
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. Running `python pipeline/data/usgs.py` produces a CSV covering all M5.5+ events from 1900–2026 with no decade having exactly 20,000 records (proving no silent API truncation)
  2. Running `python pipeline/data/ephemeris.py` produces a CSV of daily planetary positions for 1900–2026 using pysweph with all dates converted to UTC before Julian Day calculation
  3. Planetary aspects (conjunction, opposition, trine, etc.) and Vedic nakshatra positions are computed and written to the ephemeris output
  4. A spot-check validation script confirms ephemeris output matches JPL Horizons for at least 10 dates, with results logged to a file for audit
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Initialize Python project and download USGS M5.5+ earthquake catalog (1900-2026) with decade pagination
- [ ] 01-02-PLAN.md — Compute daily planetary positions, aspects, and Vedic nakshatras using pysweph for 1900-2026
- [ ] 01-03-PLAN.md — Validate ephemeris output against JPL Horizons for 10 spot-check dates

### Phase 2: Feature Engineering
**Goal**: A single deterministic feature matrix CSV exists covering 1900–2026 with ~265 columns, correctly encoded, and with all scalers/encoders fit exclusively on pre-2000 data
**Depends on**: Phase 1
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05
**Success Criteria** (what must be TRUE):
  1. `data/processed/feature_matrix.csv` is produced by running `pipeline/features/engineering.py` and contains planetary degrees, retrograde flags, one-hot zodiac signs, house placements, aspects, nakshatras, and an EQIndicator target column
  2. All cyclical features (planetary degrees 0–360, zodiac sign numerals 1–12) are encoded as sin/cos pairs — no raw integer degree or sign columns remain in the final matrix
  3. An assertion in the script confirms `max(X_train.index) < datetime(2000, 1, 1)` and `min(X_test.index) >= datetime(2000, 1, 1)` — no pre-2000 test rows and no post-2000 training rows
  4. Regional geographic identifiers (country name, lat/long grid cell) appear as prediction dimensions in the feature matrix alongside the EQIndicator target
**Plans**: TBD

### Phase 3: Model Training and Prediction Export
**Goal**: A trained, serialized classifier exists with a documented evaluation report, and predictions.json covering March–December 2026 is exported and ready for the web app
**Depends on**: Phase 2
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, PRED-01, PRED-02, PRED-03
**Success Criteria** (what must be TRUE):
  1. `data/models/eq_classifier.pkl` exists and was trained exclusively on pre-2000 data using scikit-learn Pipeline API so no scaler or encoder was fit on post-2000 rows
  2. An evaluation report file exists showing F1 score and Matthews Correlation Coefficient (MCC) on the 2000–2026 holdout — accuracy is not used as a primary metric
  3. At least two classifier types (e.g., Lasso Logistic Regression and XGBoost) were compared with class imbalance handling, and the chosen model is documented with rationale
  4. `web/public/data/predictions.json` exists, covers all dates March–December 2026, and each entry has the schema: `date`, `country`, `lat`, `lon`, `risk_score`, `top_planetary_aspects`, plus only entries above the risk threshold are included
**Plans**: TBD

### Phase 4: Web App and Deployment
**Goal**: A live Vercel-deployed Next.js app displays 2026 earthquake risk predictions as an interactive calendar, with model transparency and a scientific disclaimer visible to all users
**Depends on**: Phase 3
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. Visiting the deployed Vercel URL shows a calendar grid for March–December 2026 with dates color-coded by earthquake risk tier — no JavaScript fetch occurs at page load (predictions are embedded at build time via Server Component)
  2. Clicking a high-risk date opens a detail panel showing the risk score, predicted region(s), and the top contributing planetary aspects for that date
  3. A methodology page is reachable from the calendar and displays model evaluation metrics (F1, MCC, confusion matrix) from the 2000–2026 test period
  4. A prominent scientific disclaimer stating this is an experimental model and earthquakes cannot be reliably predicted is visible on the main page without requiring any user interaction
  5. The Vercel build completes without errors and all static assets are within Vercel size limits, with predictions.json served from `public/data/` (not bundled into the serverless function)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Pipeline | 0/3 | Not started | - |
| 2. Feature Engineering | 0/TBD | Not started | - |
| 3. Model Training and Prediction Export | 0/TBD | Not started | - |
| 4. Web App and Deployment | 0/TBD | Not started | - |
