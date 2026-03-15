# Requirements: Earthquake Astrology Prediction 2026

**Defined:** 2026-03-14
**Core Value:** Accurate prediction of high-risk earthquake dates and regions for 2026 using astrological planetary patterns — trained on 100 years of data, validated on 26 years of out-of-sample events.

## v1 Requirements

### Data Pipeline

- [x] **DATA-01**: System downloads M5.5+ earthquake records from USGS Earthquake Catalog API for 1900–2026, paginated by decade to stay under the 20,000-event API limit
- [x] **DATA-02**: System computes planetary positions (degrees, signs, retrograde status) for all dates 1900–2026 using pysweph (Swiss Ephemeris) locally — no Astro Seek scraping dependency
- [x] **DATA-03**: System computes planetary aspects (conjunction, opposition, trine, etc.) between all major planets for each date
- [x] **DATA-04**: System computes Vedic nakshatra (star) positions for key planets using sidereal calculation
- [x] **DATA-05**: Ephemeris output is validated against a known reference (JPL Horizons) for at least 10 spot-check dates to confirm accuracy

### Feature Engineering

- [ ] **FEAT-01**: Feature matrix is constructed with planetary degrees, retrograde flags, zodiac signs (one-hot encoded), house placements, aspects, and nakshatras — matching the ~265-column structure of the existing notebooks
- [ ] **FEAT-02**: All cyclical features (degrees 0–360, zodiac signs 1–12) are encoded using sin/cos transformation to prevent false distance between Aries (1) and Pisces (12)
- [ ] **FEAT-03**: Train/test split is enforced at 2000-01-01 — all scalers, encoders, and samplers are fit exclusively on pre-2000 data (no temporal leakage)
- [ ] **FEAT-04**: EQIndicator target variable is assigned as 1 for M5.5+ earthquake dates, 0 for non-earthquake dates
- [ ] **FEAT-05**: Features include regional geographic identifiers (country, lat/long grid cell) as prediction dimensions

### ML Model

- [ ] **MODEL-01**: Model trains on 1900–2000 earthquake + astrological feature data
- [ ] **MODEL-02**: Model is evaluated on 2000–2026 held-out test data using F1 score and Matthews Correlation Coefficient (MCC) as primary metrics (not accuracy)
- [ ] **MODEL-03**: Model predicts both date AND geographic region (country + lat/long grid cell) for high-risk earthquake events
- [ ] **MODEL-04**: At least two classifier types are compared (e.g., Lasso Logistic Regression, XGBoost) with class imbalance handling (class_weight='balanced' or SMOTE)
- [ ] **MODEL-05**: Trained model is saved to disk (joblib/pickle) for reproducible prediction runs

### Prediction Export

- [ ] **PRED-01**: System generates predictions for March–December 2026 and exports as `predictions.json` in the Next.js `public/data/` directory
- [ ] **PRED-02**: Predictions JSON schema includes: date, country, lat, lon, risk_score (0–1), top_planetary_aspects (array of strings)
- [ ] **PRED-03**: Only predictions above a defined risk threshold are included in the export (avoids 365 × N regions = excessive file size)

### Web UI

- [ ] **WEB-01**: Calendar view displays 2026 months (March–December) with dates color-coded by earthquake risk level
- [ ] **WEB-02**: Clicking a high-risk date shows a detail panel: risk score, predicted region(s), and top contributing planetary aspects
- [ ] **WEB-03**: A methodology page explains the astrological ML approach and displays model evaluation metrics (F1, MCC, confusion matrix) from the 2000–2026 test period
- [ ] **WEB-04**: A prominent scientific disclaimer is displayed stating this is an experimental astrological model and earthquakes cannot be reliably predicted
- [ ] **WEB-05**: Next.js app reads predictions.json at build time via Server Component (no client-side fetch)

### Deployment

- [ ] **DEPLOY-01**: Next.js app deploys to Vercel from the `web/` directory with predictions.json committed in `web/public/data/`
- [ ] **DEPLOY-02**: Vercel build succeeds with all static assets under size limits

## v2 Requirements

### Enhanced Visualization

- **VIZ-01**: Interactive world map (Leaflet.js) showing predicted high-risk regions for a selected date
- **VIZ-02**: Risk trend chart showing probability over time for the remainder of 2026
- **VIZ-03**: Filter by region/country to see only predictions for a geographic area

### Pipeline Automation

- **AUTO-01**: GitHub Actions workflow that re-runs the Python pipeline and rebuilds the Vercel app on a schedule (monthly)
- **AUTO-02**: CLI script to re-run predictions without retraining (just inference on new future dates)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time / live model inference | Python ML cannot run on Vercel serverless; architecture is static-only |
| Magnitude prediction | Binary risk classification only; magnitude adds complexity without clear astrological basis |
| User accounts / saved preferences | No backend; static Vercel deployment |
| Push/email alerts | No backend |
| Mobile native app | Web-first |
| Jupyter notebooks as deliverable | Migrating to clean Python scripts |
| Astro Seek scraping | Replaced by pysweph (Swiss Ephemeris) local computation — more reliable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| FEAT-05 | Phase 2 | Pending |
| MODEL-01 | Phase 3 | Pending |
| MODEL-02 | Phase 3 | Pending |
| MODEL-03 | Phase 3 | Pending |
| MODEL-04 | Phase 3 | Pending |
| MODEL-05 | Phase 3 | Pending |
| PRED-01 | Phase 3 | Pending |
| PRED-02 | Phase 3 | Pending |
| PRED-03 | Phase 3 | Pending |
| WEB-01 | Phase 4 | Pending |
| WEB-02 | Phase 4 | Pending |
| WEB-03 | Phase 4 | Pending |
| WEB-04 | Phase 4 | Pending |
| WEB-05 | Phase 4 | Pending |
| DEPLOY-01 | Phase 4 | Pending |
| DEPLOY-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 — traceability updated after roadmap creation (DEPLOY-01, DEPLOY-02 consolidated into Phase 4)*
