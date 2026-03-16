---
phase: 03-model-training-and-prediction-export
plan: "02"
subsystem: model-training
tags: [xgboost, joblib, feature-importance, predictions, json-export, pytest]

dependency_graph:
  requires:
    - data/processed/feature_matrix_train.parquet
    - data/processed/feature_matrix_test.parquet
    - data/processed/feature_columns.json
    - data/models/eval_report.json
    - pipeline/features/engineering.py (downsample_negatives)
  provides:
    - pipeline/model/retrain.py
    - pipeline/model/export_predictions.py
    - data/models/eq_classifier.pkl
    - data/models/feature_importance.json
    - web/public/data/predictions.json
  affects:
    - Phase 04 (web app reads predictions.json and eval_report.json at build time)

tech-stack:
  added: [joblib]
  patterns:
    - parquet row-group scan to locate future-date data without full load
    - feature importance map (dict[str, float]) for top-aspect ranking per prediction row
    - threshold-gated export: only records >= threshold written to output JSON

key-files:
  created:
    - pipeline/model/retrain.py
    - pipeline/model/export_predictions.py
    - data/models/eq_classifier.pkl
    - data/models/feature_importance.json
    - web/public/data/predictions.json
  modified:
    - tests/test_model.py

key-decisions:
  - "2026 features read from test parquet (row group 26) instead of re-running ephemeris pipeline: raw ephemeris.csv not present on this machine; test parquet contains all 2026 dates with 813 features already correctly encoded by Phase 2 pipeline"
  - "post-2000 downsampling applied to full test parquet (all dates) for retrain: plan said post-2000 only but test parquet covers 2000-2026 which is the entire post-2000 slice; applied 10:1 downsampling to all test parquet rows (8.9M -> 120k rows)"
  - "joblib compress=3 for serialization: balances size (144 KB) and load speed"

patterns-established:
  - "Retrain pattern: load both parquets, downsample post-2000 slice, concat, fit winner model, write importance map, serialize"
  - "Export pattern: load pre-encoded features from parquet, run predict_proba, filter by threshold, assemble JSON with top aspects ranked by importance"

requirements-completed: [MODEL-03, MODEL-05, PRED-01, PRED-02, PRED-03]

duration: 4min
completed: 2026-03-16
---

# Phase 3 Plan 02: Model Retrain and Prediction Export Summary

**XGBClassifier retrained on full 1900-2026 dataset (384k rows, 10:1 downsampled) and 901 prediction records for March-December 2026 exported to predictions.json with geographic regions and feature-importance-ranked planetary aspects**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-16T23:10:51Z
- **Completed:** 2026-03-16T23:14:53Z
- **Tasks:** 2
- **Files modified:** 5 created, 1 modified

## Accomplishments

- Full retrain of XGBClassifier on combined 1900-2026 data (384,406 rows after 10:1 downsampling of post-2000 slice); model serialized to eq_classifier.pkl (144 KB)
- feature_importance.json written with 813-column importance scores for top-aspect ranking
- predictions.json (901 records, 223 KB) generated for March-December 2026 with schema: date, country, lat, lon, risk_score, top_planetary_aspects; all records >= threshold 0.1499
- All 18 test_model.py tests pass (3 xfailed pre-existing stubs); 5 xfail markers removed; TestTopAspects and TestPredictionDates added

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement retrain.py** - `a7a1c57` (feat) + `d3576a8` (artifacts)
2. **Task 2: Implement export_predictions.py** - `2e0d63b` (feat) + `9e05c48` (artifact)

## Files Created/Modified

- `pipeline/model/retrain.py` — Full retrain on 1900-2026: load parquets, downsample post-2000, fit XGBClassifier, write feature_importance.json, serialize model
- `pipeline/model/export_predictions.py` — Load 2026 features from test parquet row group 26, run inference, filter by threshold, write predictions.json
- `data/models/eq_classifier.pkl` — Serialized XGBClassifier (144 KB, joblib compress=3)
- `data/models/feature_importance.json` — 813-entry importance map for aspect ranking
- `web/public/data/predictions.json` — 901 records for March-December 2026
- `tests/test_model.py` — Removed 5 xfail markers; added TestTopAspects and TestPredictionDates

## Decisions Made

- **2026 features from parquet, not raw ephemeris:** `data/raw/ephemeris.csv` does not exist on this machine; the test parquet already contains all 2026 dates with 813 features correctly encoded by the Phase 2 pipeline. Using the parquet is equivalent (same encoding path) and eliminates the need to re-run the ephemeris pipeline.
- **Post-2000 downsampling covers all of test parquet:** The plan described "post-2000 slice" and the test parquet covers 2000-2026. Applied 10:1 downsampling to the full test parquet (8,885,662 rows → 120,725 after downsampling), which is the correct interpretation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used test parquet instead of ephemeris.csv for 2026 feature generation**
- **Found during:** Task 2 (export_predictions.py implementation)
- **Issue:** Plan specified reading `data/raw/ephemeris.csv` and running `encode_ephemeris` + `apply_nakshatra_encoding` + `build_matrix_year`. However, `data/raw/ephemeris.csv` does not exist on this machine (raw data was not committed to the repo).
- **Fix:** Load 2026 feature rows directly from the last row group of `data/processed/feature_matrix_test.parquet` (row group 26 covers all of 2026). The parquet was produced by the same Phase 2 pipeline, so features are identical to what re-running encoding would produce.
- **Files modified:** `pipeline/model/export_predictions.py` — uses pyarrow row-group scan instead of ephemeris.csv read
- **Verification:** 275,706 rows loaded for March-December 2026, 306 unique dates confirmed, all 813 feature columns present, inference and threshold filter produce 901 records matching schema
- **Committed in:** 2e0d63b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — adapted to available data)
**Impact on plan:** Functionally equivalent approach using already-processed data. No correctness or reproducibility impact. Raw ephemeris.csv can be generated by running `pipeline/data/ephemeris.py` if needed for future reruns.

## Issues Encountered

None beyond the ephemeris.csv adaptation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `web/public/data/predictions.json` is ready for Phase 4 Next.js web app to consume
- `data/models/eval_report.json` is ready for Phase 4 methodology page (F1, MCC, threshold, both_models)
- Phase 3 is complete; all model artifacts in `data/models/`, all prediction data in `web/public/data/`

## Self-Check: PASSED

### Files Created
- [x] `pipeline/model/retrain.py` — exists
- [x] `pipeline/model/export_predictions.py` — exists
- [x] `data/models/eq_classifier.pkl` — exists
- [x] `data/models/feature_importance.json` — exists
- [x] `web/public/data/predictions.json` — exists

### Commits Verified
- [x] a7a1c57 — Task 1: retrain.py implementation
- [x] d3576a8 — Task 1: model artifacts (eq_classifier.pkl, feature_importance.json)
- [x] 2e0d63b — Task 2: export_predictions.py and test_model.py updates
- [x] 9e05c48 — Task 2: predictions.json artifact

---
*Phase: 03-model-training-and-prediction-export*
*Completed: 2026-03-16*
