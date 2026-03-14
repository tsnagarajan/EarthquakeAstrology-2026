# Pitfalls Research

**Domain:** ML time-series prediction system (earthquake + astrology) with scikit-learn, Swiss Ephemeris, and Next.js/Vercel deployment
**Researched:** 2026-03-14
**Confidence:** HIGH (critical pitfalls verified via official docs and multiple sources); MEDIUM (Swiss Ephemeris edge cases, Vercel limits); LOW noted where single source

---

## Critical Pitfalls

### Pitfall 1: Temporal Data Leakage via Preprocessing Before Splitting

**What goes wrong:**
Any preprocessing step (normalization, imputation, scaler fit, SMOTE/resampling) applied to the full dataset before the train/test split leaks test-set statistics into the training pipeline. The model learns the distribution of future data before it's supposed to know it. Reported performance (accuracy, F1) is inflated — model appears better than it will be on true future data.

**Why it happens:**
Notebook-style code encourages processing data as a single DataFrame. A call to `scaler.fit_transform(df)` before splitting is the canonical mistake. It looks harmless but encodes test-set mean/std into the scaler used in training.

**How to avoid:**
- Always `fit` preprocessing transformers on training data only; `transform` test data.
- Use `sklearn.pipeline.Pipeline` + `ColumnTransformer` so transformations are scoped to the training fold automatically.
- Enforce the split before any feature engineering beyond raw calculations (planetary degrees can be computed freely from ephemeris, but derived statistics — rolling means, interaction terms — must be computed on train data only and applied to test).
- The train/test boundary is 2000-01-01. Never pass a DataFrame that spans both sides into `fit`.

**Warning signs:**
- Validation accuracy is suspiciously high (e.g., >85% on a binary earthquake prediction task where the majority class alone gives ~95%).
- Removing features improves out-of-sample but not in-sample performance.
- Scaler object is initialized outside a pipeline before `train_test_split`.

**Phase to address:** Data pipeline + feature engineering phase (before model training). Validate with an explicit assertion: `assert scaler.data_max_.shape == (n_train_features,)` fitted only on pre-2000 rows.

---

### Pitfall 2: Using Standard K-Fold Cross-Validation on Time-Series Data

**What goes wrong:**
Standard `KFold` or `StratifiedKFold` shuffles data randomly, creating folds where future samples appear in training and past samples appear in validation. This directly violates the temporal ordering of the earthquake/planetary dataset. Cross-validation scores become optimistic by 5–20% compared to true future performance.

**Why it happens:**
`StratifiedKFold` is the default recommendation for imbalanced classification, but it was designed for i.i.d. (independent, identically distributed) data, not time series.

**How to avoid:**
- Use `sklearn.model_selection.TimeSeriesSplit` for any cross-validation during hyperparameter tuning.
- Set up folds that walk forward chronologically (e.g., train on 1900–1950, validate on 1950–1960; then train on 1900–1960, validate on 1960–1970; etc.).
- Never use `cross_val_score` with default `cv` parameter on this dataset.

**Warning signs:**
- Cross-validation scores are higher than scores on the explicit held-out 2000–2026 test set.
- Fold indices are not monotonically increasing when sorted by date.

**Phase to address:** Model training phase. Add a `TimeSeriesSplit` wrapper as the only approved CV strategy in project configuration.

---

### Pitfall 3: Accuracy as the Primary Evaluation Metric on an Imbalanced Dataset

**What goes wrong:**
Earthquake days (M5.5+) are rare. On a per-day basis the dataset may have 95%+ negative days globally, and far higher if predicting specific regions. A model that predicts "no earthquake" for every day achieves 95%+ accuracy — this is the ZeroR baseline. A 2024 study on earthquake ML in Los Angeles found that one model "failed to surpass the ZeroR baseline," meaning it had no actual predictive skill. Using accuracy as the primary metric hides this failure completely.

**Why it happens:**
Accuracy is the default metric in sklearn `score()`. It feels natural and prints well in notebooks.

**How to avoid:**
- Primary metrics must be: Precision, Recall, F1 (minority class), AUC-ROC, and Matthews Correlation Coefficient (MCC).
- Set `class_weight='balanced'` in all sklearn classifiers as a baseline.
- Report a confusion matrix explicitly, not just a summary score.
- Define an explicit baseline: "predict earthquake on top X% of risk-score days" and verify the model beats this.
- Never report accuracy alone in any evaluation output.

**Warning signs:**
- Notebook reports "73% accuracy" without also reporting recall on the earthquake class.
- Confusion matrix shows all or near-all predictions are in the negative class.
- F1 score is materially lower than accuracy.

**Phase to address:** Model training and evaluation phase. Embed MCC and F1 into the evaluation script as the primary reported metrics.

---

### Pitfall 4: Resampling (SMOTE/Oversampling) Applied Before the Train/Test Split

**What goes wrong:**
This is a double-leakage pitfall combining Pitfalls 1 and 2. Applying SMOTE to the full dataset before splitting means synthetic minority samples generated from test-set earthquake events contaminate training data. The model learns from synthetic samples derived from future events it is supposed to predict. Performance is severely inflated.

**Why it happens:**
The imbalanced-learn documentation explicitly warns about this but it remains one of the most common mistakes. The natural code order in a notebook is: load data, balance classes, split, train.

**How to avoid:**
- Apply SMOTE or any oversampling only inside the training fold, never before splitting.
- Use `imblearn.pipeline.Pipeline` (not sklearn's Pipeline) which correctly integrates resampling steps before fitting.
- Test set must always represent the natural class imbalance — never balance the test set.

**Warning signs:**
- SMOTE is called on the full DataFrame before `train_test_split`.
- Test set has a suspiciously even class distribution for what is a rare-event task.

**Phase to address:** Model training phase. Use `imblearn.pipeline.Pipeline` as the standard pattern.

---

### Pitfall 5: Swiss Ephemeris Timezone and Julian Day Errors

**What goes wrong:**
Swiss Ephemeris (`pyswisseph`) operates in Julian Day Number (JDN) referenced to Universal Time (UT1) by default. Errors arise in three ways:
1. Feeding local times or naive datetimes without timezone conversion to UTC first — planetary positions shift by hours, causing degree-level errors.
2. Mixing `swe_calc()` (expects Ephemeris Time / TT) with `swe_calc_ut()` (expects UT). The delta between TT and UT grows over time — up to ~70 seconds in 2026, but was different in 1900.
3. Not calling `swe_set_ephe_path()` before calculations — the library may silently fall back to a lower-precision Moshier ephemeris without warning.

**Why it happens:**
The distinction between UT, UT1, UTC, and TT is easy to overlook. The library documentation is dense. Existing notebook code may have been written for a single timezone and silently hardcodes assumptions.

**How to avoid:**
- Always call `swe.set_ephe_path('/path/to/ephe')` before any calculation.
- Convert all input dates to UTC explicitly before computing JDN via `swe.julday()`.
- Use `swe_calc_ut()` uniformly with UT input — never mix with `swe_calc()` unless you explicitly handle TT conversion.
- Cross-validate a sample of computed planetary positions against a known reference (e.g., NASA JPL Horizons online ephemeris) for at least 5 dates spanning 1900–2026.
- Verify the `.se1` ephemeris data files cover the full 1800–2100 range and are present on the path.

**Warning signs:**
- Planetary longitudes differ from reference values by more than 0.1 degrees.
- Calculations succeed without ephemeris files present on disk (silent Moshier fallback).
- Retrograde flags disagree with published station dates.

**Phase to address:** Astrological data pipeline phase. Build a validation script that cross-checks 10 known planetary positions from JPL Horizons.

---

### Pitfall 6: Astro Seek Scraping Brittleness and Legal/Robots Risk

**What goes wrong:**
Astro Seek is a third-party web service with no public API. Scraping it for ~126 years of daily planetary data (~46,000+ requests) will:
1. Trigger rate limiting or IP blocks.
2. Break silently when the site updates its HTML structure — class names, table layouts, or JavaScript rendering changes.
3. Potentially violate terms of service, risking blocks or legal exposure.

Scraped data is also opaque — errors (wrong planet, wrong date, timezone mix-up on the server) are hard to detect without cross-validation against an independent source.

**Why it happens:**
The existing notebook codebase already uses scraping, so it seems like the natural extension. The alternative (Swiss Ephemeris computation) requires more setup.

**How to avoid:**
- Swiss Ephemeris is the correct path for this project. It is deterministic, offline, free, and covers 1800–2100 with sub-arcsecond accuracy.
- Use Astro Seek scraping only as a last resort for specific features that pyswisseph cannot compute (e.g., certain Vedic nakshatra sub-divisions), and even then cache results aggressively.
- If scraping is used for any features, write a validation test comparing 100 scraped values against Swiss Ephemeris computations. Discrepancies > 1 degree indicate a parsing or timezone error.
- Include exponential backoff and request throttling (minimum 2-second delay between requests) if scraping is unavoidable.

**Warning signs:**
- Scraper returns 429 or HTML error pages silently parsed as data.
- Scraped degree values cluster oddly (all near 0, all the same, etc.).
- CI pipeline fails unpredictably due to network calls.

**Phase to address:** Astrological data pipeline phase. Decision: default to Swiss Ephemeris computation; document scraping as fallback only.

---

### Pitfall 7: Zodiac Sign and Cyclical Feature Encoding Errors

**What goes wrong:**
Zodiac signs (Aries=1 through Pisces=12) and planetary degrees (0–360) are cyclical. Encoding them as raw integers or one-hot categories creates two problems:
1. Raw integers tell the model "Pisces (12) is far from Aries (1)" when in fact they are adjacent — a 30-degree difference not a 330-degree difference.
2. One-hot encoding a 12-category zodiac feature adds 12 sparse binary columns. With 13 planets × 12 signs = 156 sparse columns, tree-based models handle this fine, but linear models (Logistic Regression, which the existing code uses as best performer) suffer from a high-dimensional sparse space.

Cyclical encoding (sin/cos) is the mathematically correct approach for degrees and sign positions, but requires both sin AND cos — using only sin introduces an ambiguity (sin(30°) == sin(150°)).

**Why it happens:**
One-hot encoding is the default advice for categorical data. The cyclic nature of zodiac positions is not obvious to ML practitioners who are not domain experts.

**How to avoid:**
- Encode planetary degrees as `sin(deg * 2π / 360)` and `cos(deg * 2π / 360)` — always both.
- Encode zodiac sign (1–12) as `sin(sign * 2π / 12)` and `cos(sign * 2π / 12)`.
- For tree-based models (Random Forest, XGBoost), one-hot encoding is also acceptable and sometimes performs better — use both and evaluate.
- Existing code uses ~265–309 columns. Audit which are raw integer zodiac encodings and convert to cyclical before model training.

**Warning signs:**
- Model performs poorly when a planet is near degree 0 or 360 (the discontinuity point).
- Removing zodiac sign features does not significantly change model performance (indicates they are not being learned correctly).

**Phase to address:** Feature engineering phase. Add a column audit step that flags any integer-encoded cyclical column.

---

### Pitfall 8: Notebook-to-Script Migration Hidden State Bugs

**What goes wrong:**
Jupyter notebooks accumulate hidden execution state. Cells run out of order, variables overwritten mid-session, or deleted cells leave stale values in memory. When migrating to `.py` scripts, code that "worked" in the notebook may:
1. Fail outright (NameError on variable that was set in a now-deleted cell).
2. Silently produce wrong results because the "correct" notebook output relied on a specific execution order that the script does not replicate.
3. Rely on global mutable state (DataFrames modified in-place across cells) that becomes fragile when linearized.

A survey found over a third of Jupyter notebooks on GitHub fail to reproduce from top-to-bottom execution.

**Why it happens:**
Non-linear experimentation is the feature of notebooks. The code evolved organically; the "final" version was never meant to be run top-to-bottom.

**How to avoid:**
- Before migrating, run `Kernel → Restart & Run All` on every notebook and verify outputs match expected values.
- Convert each notebook to a script with a single entry point (`if __name__ == '__main__'`).
- Replace all in-place DataFrame mutations (`df['col'] = ...` without assignment) with explicit reassignment or copies.
- Parameterize all hardcoded date ranges, file paths, and thresholds via config files or CLI arguments.
- Add assertions at each pipeline stage: row counts, date ranges, column names, value ranges.

**Warning signs:**
- Script raises NameError on first run but "worked" in the notebook.
- Output CSV has different row count from notebook equivalent.
- Script requires running twice to get correct output (state dependency).

**Phase to address:** Pipeline migration phase (notebook → scripts). Treat the migration as a rewrite with tests, not a copy-paste.

---

### Pitfall 9: USGS API 20,000-Event Request Limit Causing Silent Data Truncation

**What goes wrong:**
The USGS FDSN Event API enforces a hard 20,000-event limit per query. A single query for M5.5+ earthquakes from 1900–2026 (~126 years) will return only 20,000 events and silently truncate the rest, with an HTTP 400 error if the limit is exceeded. The researcher either receives an error (and no data) or — worse — receives exactly 20,000 records without realizing the full catalog is larger.

**Why it happens:**
Documentation mentions the limit but it's easy to miss. Initial queries to the API for recent data (e.g., last 5 years) return far fewer than 20,000 events, so the limit is not encountered in testing.

**How to avoid:**
- Paginate by year or decade: issue one query per 5-year window and concatenate results.
- Use the `offset` parameter for further pagination within dense periods.
- After downloading, verify total event counts against USGS published statistics or cross-check a sample year's count against the USGS web search UI.
- Build a download script with explicit pagination logic that asserts no single query returns exactly 20,000 events (which would indicate truncation).

**Warning signs:**
- Total downloaded events is exactly 20,000 for a multi-decade query.
- Event counts are suspiciously low for known high-seismicity years (e.g., 2011 Japan, 2004 Sumatra).

**Phase to address:** Data pipeline phase. Implement decade-by-decade pagination as the default download strategy.

---

### Pitfall 10: Vercel Deployment of Large JSON Prediction Files

**What goes wrong:**
Large pre-computed prediction JSON files bundled into a Next.js server component or imported directly via `import` statements get included in the serverless function bundle, which has a 250 MB unzipped limit. Even before hitting the hard limit, large imports increase cold start time. A 126-year dataset with 265+ features exported as JSON could be hundreds of MB.

**Why it happens:**
The project correctly plans to pre-compute predictions offline and serve static JSON. However, if predictions are `import`-ed in a server component or API route, Next.js includes the file in the function bundle.

**How to avoid:**
- Place all prediction JSON files in `public/` — they are served directly over Vercel's CDN without being bundled.
- Fetch prediction data on the client or in `getStaticProps` via `fetch('/predictions.json')` rather than `import predictions from '../data/predictions.json'`.
- Split predictions into smaller files by month or region if a single file exceeds ~5 MB.
- The prediction JSON for 2026 (March–December, ~300 days) should be small; the risk is if full historical data is accidentally exported alongside it.

**Warning signs:**
- Build output shows function size near or over 50 MB.
- Cold start latency is high (>3 seconds) on the deployed app.
- `import` of JSON file appears in any `pages/api/` or `app/` server component.

**Phase to address:** Web deployment phase. Establish a rule: prediction JSON lives in `public/`, never imported as a module.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding date range 1900–2026 as strings | Fast initial setup | Must update manually for future runs; no extensibility | MVP only, with a TODO comment |
| Single monolithic data pipeline script | Simple to reason about | Impossible to re-run a single stage; full pipeline runs take hours | Never for production; split into stages early |
| Skipping feature importance analysis | Saves time in Phase 1 | Model includes noise features; harder to debug poor performance | Never acceptable — takes 30 min, saves days |
| Using accuracy as the only reported metric | Easy to report | Hides complete model failure on earthquake class | Never — always report F1/MCC alongside accuracy |
| Committing ephemeris `.se1` files to git | Avoids setup instructions | Repository becomes hundreds of MB; breaks GitHub limits | Never — use a download script or `.gitignore` |
| Downloading USGS data without pagination | Simpler code | Silent truncation at 20,000 events | Never — pagination is required for the full catalog |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Swiss Ephemeris | Not calling `swe.set_ephe_path()` before calculations | Always call `set_ephe_path()` as the first setup step; assert `.se1` files exist on disk |
| Swiss Ephemeris | Using `swe_calc()` (TT) when `swe_calc_ut()` (UT) is needed | Use `calc_ut()` uniformly and input UTC-converted dates; document time scale explicitly |
| USGS API | Single large request for 1900–2026 | Paginate by decade; assert no single response hits exactly 20,000 records |
| USGS API | Not filtering for `minmagnitude=5.5` | Query returns millions of small events; specify `minmagnitude` and verify post-download |
| Vercel | Importing large JSON via `import` in server component | Place JSON in `public/` and fetch via HTTP; never bundle prediction data |
| scikit-learn Pipeline | Using sklearn Pipeline with SMOTE | Use `imblearn.pipeline.Pipeline` which supports resampling steps correctly |
| pandas DatetimeTZLocalization | Naive datetime comparison with timezone-aware | Standardize all timestamps to UTC at ingestion; assert `df['date'].dt.tz == UTC` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing planetary positions in Python loop per row | Data generation takes hours for 126-year daily dataset (~46,000 rows) | Vectorize date generation; batch ephemeris calls; cache intermediate results | At ~1,000+ rows without batching |
| Loading full historical planetary CSV into Vercel API route | Slow page loads; function timeout | Pre-compute predictions offline; serve only 2026 prediction subset | Any file >10 MB in serverless context |
| Recomputing features on every model run | Development loop takes 30+ minutes | Cache intermediate CSV files (raw USGS, raw ephemeris, merged features) separately | Immediately without a staged pipeline |
| No pipeline caching for 126-year ephemeris computation | Re-downloading or recomputing from scratch on each run | Persist ephemeris data as CSV artifact; only recompute if source data changes | Every run in a CI-like environment |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing Swiss Ephemeris binary `.se1` files to git | Repository bloat (100-400 MB), GitHub size warnings | Add `*.se1` to `.gitignore`; provide download script |
| Storing Astro Seek session cookies or scraped data in git | Potential ToS violation; exposes scraping infrastructure | Keep scraped cache files in `.gitignore`; use ephemeris instead |
| Exposing USGS query parameters that reveal prediction methodology | Low risk but unnecessary | Keep pipeline scripts out of the Next.js public folder |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing raw probability scores (0.73, 0.68) without context | Users don't understand what the threshold means | Translate to human labels: "High Risk / Moderate Risk / Low Risk" with a defined threshold |
| Displaying all 365 days of 2026 with equal visual weight | Calendar feels cluttered; high-risk dates not scannable | Only highlight days above the risk threshold; grey out or minimize low-risk days |
| No explanation of what "earthquake risk" means in this model | Users interpret as a definitive earthquake prediction | Add clear disclaimer: "Astrological risk indicator, not seismic forecast" with confidence context |
| Calendar loads all prediction data on initial page load | Slow Time-to-Interactive; poor mobile performance | Lazy-load by month; pre-render the current/next month only |

---

## "Looks Done But Isn't" Checklist

- [ ] **Temporal split:** Model says "trained on 1900–2000, tested on 2000–2026" — verify by asserting `max(X_train.index) < min(X_test.index)` with dates
- [ ] **Scaler leakage:** Pipeline reports good test scores — verify scaler was `fit` only on training rows, not the full DataFrame
- [ ] **Class imbalance handling:** Training code runs without errors — verify confusion matrix shows meaningful recall on the earthquake class (not all-negative predictions)
- [ ] **USGS completeness:** Download script reports success — verify total event count for 1900–2026 against expected range (should be 50,000–150,000+ M5.5+ events globally)
- [ ] **Ephemeris accuracy:** pyswisseph computations run — spot-check 5 dates across 1900, 1950, 2000, 2020, 2026 against JPL Horizons
- [ ] **Vercel bundle size:** App deploys successfully — check Vercel build output for function bundle sizes; prediction data should NOT appear in function bundle
- [ ] **Prediction JSON completeness:** Predictions export runs — verify all dates March–December 2026 are present with no gaps
- [ ] **Feature encoding correctness:** Feature pipeline runs — verify zodiac sign columns are cyclically encoded (two columns per sign: sin + cos), not raw integers

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Temporal data leakage discovered post-model-training | MEDIUM | Re-run feature engineering with split-first approach; retrain model; expect lower reported accuracy (this is correct) |
| Accuracy-only evaluation hid class imbalance failure | LOW | Add F1/MCC metrics to existing evaluation script; rerun without retraining |
| USGS data truncated at 20,000 events | LOW | Implement paginated download; re-download affected years; merge with existing data |
| Swiss Ephemeris timezone error discovered | HIGH | Re-compute all planetary positions with corrected UTC conversion; rebuild merged feature DataFrame; retrain model |
| Astro Seek scraper broke mid-download | MEDIUM | Switch to Swiss Ephemeris for affected features; or re-run scraper with retry logic |
| Vercel bundle size exceeded | LOW | Move JSON from `src/data/` to `public/`; replace `import` with `fetch` |
| Notebook migration produced wrong outputs | HIGH | Restart from notebook, run top-to-bottom with `Restart & Run All`; compare outputs cell-by-cell against script stage outputs |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Temporal data leakage (scaler/preprocessing) | Feature engineering + model training | Assert `scaler.fit()` called only on pre-2000 rows |
| K-Fold CV on time series | Model training | Verify `TimeSeriesSplit` is the only CV strategy used |
| Accuracy as primary metric | Model evaluation | F1 and MCC must appear in every evaluation report |
| SMOTE before split | Model training | Confirm `imblearn.Pipeline` used; test set class distribution matches natural base rate |
| Swiss Ephemeris timezone/JDN errors | Astrological data pipeline | Cross-validate 10 planetary positions against JPL Horizons |
| Astro Seek scraping brittleness | Astrological data pipeline | Decision gate: default to Swiss Ephemeris; scraping requires written justification |
| Zodiac sign integer encoding | Feature engineering | Audit column dtypes; flag any integer column in range 1–12 representing a sign |
| Notebook hidden state bugs | Pipeline migration | Run `Restart & Run All` on all notebooks before migration; write output comparison tests |
| USGS API 20,000-event truncation | Data download pipeline | Assert no single API response has exactly 20,000 records |
| Vercel large JSON bundle | Web deployment | Check Vercel build output; prediction JSON must not appear in function trace |

---

## Sources

- [scikit-learn Common Pitfalls — Official Documentation](https://scikit-learn.org/stable/common_pitfalls.html) — HIGH confidence
- [imbalanced-learn Common Pitfalls](https://imbalanced-learn.org/stable/common_pitfalls.html) — HIGH confidence; explicitly warns about resampling before split
- [Temporal Leakage in LSTM Forecasting — arXiv 2512.06932](https://arxiv.org/html/2512.06932v1) — HIGH confidence; empirical study showing 20%+ evaluation bias from pre-split sequence generation
- [Swiss Ephemeris Programming Interface — Astrodienst](https://www.astro.com/swisseph/swephprg.htm) — HIGH confidence; official documentation on `set_ephe_path`, `calc_ut` vs `calc`
- [pyswisseph — PyPI](https://pypi.org/project/pyswisseph/) — HIGH confidence
- [USGS FDSN Event API Documentation](https://earthquake.usgs.gov/fdsnws/event/1/) — HIGH confidence; 20,000-event limit documented
- [Earthquake Forecast as ML Problem for Imbalanced Datasets — Frontiers in Earth Science](https://www.frontiersin.org/articles/10.3389/feart.2022.847808/full) — HIGH confidence; MCC recommended for imbalanced seismic data
- [Improving Earthquake Prediction Accuracy in LA — Scientific Reports 2024](https://www.nature.com/articles/s41598-024-76483-x) — HIGH confidence; ZeroR baseline failure documented
- [Cyclical Encoding for Time Series — Towards Data Science](https://towardsdatascience.com/cyclical-encoding-an-alternative-to-one-hot-encoding-for-time-series-features-4db46248ebba/) — MEDIUM confidence
- [Vercel Limits Documentation](https://vercel.com/docs/limits) — HIGH confidence; 250 MB function limit
- [Jupyter Pitfalls — Aalto Scientific Computing](https://scicomp.aalto.fi/scicomp/jupyter-pitfalls/) — MEDIUM confidence
- [Moving from Notebooks to Scripts — Made With ML](https://madewithml.com/courses/mlops/scripting/) — MEDIUM confidence

---
*Pitfalls research for: Earthquake Astrology ML Prediction System — scikit-learn, Swiss Ephemeris, Next.js/Vercel*
*Researched: 2026-03-14*
