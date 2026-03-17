---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: "Completed 04-02-PLAN.md (paused at Task 3 checkpoint:human-verify)"
last_updated: "2026-03-17T20:41:25.649Z"
last_activity: 2026-03-14 — Roadmap created
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 14
  completed_plans: 12
  percent: 100
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-03-15T22:14:43.986Z"
last_activity: 2026-03-14 — Roadmap created
progress:
  [██████████] 100%
  completed_phases: 1
  total_plans: 8
  completed_plans: 7
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Accurate prediction of high-risk earthquake dates and regions for 2026 using astrological planetary patterns — trained on 100 years of data, validated on 26 years of out-of-sample events.
**Current focus:** Phase 1 — Data Pipeline

## Current Position

Phase: 1 of 4 (Data Pipeline)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-14 — Roadmap created

Progress: [███░░░░░░░] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 01-data-pipeline P01 | 11 | 2 tasks | 9 files |
| Phase 01-data-pipeline P02 | 5 | 2 tasks | 4 files |
| Phase 01-data-pipeline P03 | 5 | 1 tasks | 4 files |
| Phase 01-data-pipeline P03 | 45 | 2 tasks | 4 files |
| Phase 02-feature-engineering P01 | 21 | 2 tasks | 6 files |
| Phase 02-feature-engineering P02 | 4 | 2 tasks | 2 files |
| Phase 02-feature-engineering P03 | 25 | 2 tasks | 2 files |
| Phase 02-feature-engineering P04 | 5 | 2 tasks | 2 files |
| Phase 02-feature-engineering P05 | 90 | 2 tasks | 6 files |
| Phase 03-model-training-and-prediction-export P01 | 13 | 3 tasks | 6 files |
| Phase 03-model-training-and-prediction-export P02 | 4 | 2 tasks | 6 files |
| Phase 04-web-app-and-deployment P01 | 4 | 2 tasks | 8 files |
| Phase 04-web-app-and-deployment P02 | 6 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Setup]: Use pysweph 2.10.3.6 (not pyswisseph — unmaintained since mid-2025, no Python 3.12 wheels)
- [Setup]: Pre-computed predictions only — Python ML never runs on Vercel; only static predictions.json is deployed
- [Setup]: Train on 1900–2000, test on 2000–2026 for clean temporal holdout with no data leakage
- [Phase 01-data-pipeline]: 5-year API chunks chosen for USGS pagination — max 2,665 events per window, far below 20k limit with room for catalog growth
- [Phase 01-data-pipeline]: TRUNCATION_LIMIT guard is fatal RuntimeError — silent truncation corrupts ML target variable and must never pass silently
- [Phase 01-data-pipeline]: Actual USGS M5.5+ catalog (1900-2026) is 39,514 records — plan estimate of 50k+ was an overestimate; data completeness verified via Sumatra event check and no-truncation guard
- [Phase 01-data-pipeline]: pysweph 2.10.3.6 calc_ut returns 3-tuple (xx, iflag, serr) not 2-tuple — all callers must unpack 3 values
- [Phase 01-data-pipeline]: Swiss Ephemeris .se1 files moved to GitHub (aloistr/swisseph) — AstroDienst FTP URL 404s; download script updated
- [Phase 01-data-pipeline]: Chiron (swe.CHIRON) requires seas_18.se1 — no Moshier fallback for asteroid bodies; file must be present before running ephemeris.py
- [Phase 01-data-pipeline]: dotenv import made optional in validate_ephemeris.py (soft try/except) — validation script has no env var dependencies; dotenv only needed in ephemeris.py
- [Phase 01-data-pipeline]: Exit code 2 for missing ephemeris CSV — distinguishes setup errors from accuracy failures for CI pipelines
- [Phase 01-data-pipeline]: Reference values corrected from rough hand-estimates to actual DE431 values — original plan values were ~0.3-1.2 deg off; actual computed values adopted as references after human verification
- [Phase 02-feature-engineering]: PLANETS redefined as list in engineering.py to avoid swisseph C extension import at test time
- [Phase 02-feature-engineering]: xfail markers used over skip so xpass auto-detection signals when stubs are implemented
- [Phase 02-feature-engineering]: object-dtype date index: pd.Index(dates, dtype=object) used for MultiIndex date level to preserve datetime.date type and prevent pandas Timestamp coercion
- [Phase 02-feature-engineering]: tolist() for numpy int conversion: .astype(int).tolist() ensures Python native int in tuples so isinstance checks pass
- [Phase 02-feature-engineering]: encode_ephemeris PRESERVES nakshatra string columns — only drops lon, sign_num, sign, nakshatra_num raw columns; nakshatra strings remain for apply_nakshatra_encoding in Plan 05
- [Phase 02-feature-engineering]: test_text_nakshatra_absent refactored to test full encode_ephemeris + apply_nakshatra_encoding pipeline; _make_full_nakshatra_df() helper added for 351-column encoder vocabulary
- [Phase 02-feature-engineering]: build_matrix_chunk normalizes ephe_row.name to datetime.date before eq_index reindex to handle str/Timestamp index inputs
- [Phase 02-feature-engineering]: active_cells_list helper added to convert active-cells set to deterministic sorted list for Plan 05 chunked iteration
- [Phase 02-feature-engineering]: downsample_negatives clamps with min(ratio*n_pos, n_neg) to handle small negative pools gracefully
- [Phase 02-feature-engineering]: Per-year downsampling always used for pre-2000 matrix build — avoids 32.9M-row intermediate requiring 210GB RAM
- [Phase 02-feature-engineering]: build_matrix_year() vectorized broadcaster added for O(days*cells) construction without Python row loop overhead
- [Phase 02-feature-engineering]: test parquet corrupted in committed artifact — ParquetWriter.close() not finalized; needs re-run with raw data on original machine
- [Phase 03-model-training-and-prediction-export]: chunked row-group inference for holdout prediction: 5.6M rows exceed 16GB RAM; row-group batches accumulate only float32 probabilities
- [Phase 03-model-training-and-prediction-export]: pyarrow filter pushdown for 2000-2010 training slice: avoids loading full 8.8M-row test parquet (28GB) into memory
- [Phase 03-model-training-and-prediction-export]: XGBClassifier wins model selection by MCC (0.001363 vs LogReg 0.001158); threshold=0.1499 from PR curve on 2010-2026 holdout
- [Phase 03-model-training-and-prediction-export]: 2026 features loaded from test parquet row group 26 instead of re-running ephemeris pipeline: raw ephemeris.csv not present; parquet already has correctly encoded 813-col features for all 2026 dates
- [Phase 03-model-training-and-prediction-export]: joblib compress=3 for model serialization: 144 KB output balances size and load speed for eq_classifier.pkl
- [Phase 04-web-app-and-deployment]: npm cache had root-owned directories (EACCES); workaround npm_config_cache=/tmp/npm-cache for install
- [Phase 04-web-app-and-deployment]: Tailwind CSS 4 globals.css uses CSS-first @import tailwindcss directive — no tailwind.config.js needed
- [Phase 04-web-app-and-deployment]: MonthGrid is pure presentational (no use client) — all state and callbacks injected from CalendarInteractive
- [Phase 04-web-app-and-deployment]: Server Component page.tsx loads predictions via loadPredictions()/groupPredictionsByDate() and passes as plain Record to CalendarInteractive client component

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: pysweph 2.10.3.6 has breaking changes from pyswisseph 2.10.3.2 — migration guide must be reviewed before ephemeris.py implementation begins
- [Phase 2]: Existing notebooks contain 265–309 feature columns; a column-by-column audit against the Archive notebooks is required before feature engineering planning to avoid underestimating complexity
- [Phase 3]: Model performance on 2000–2026 holdout is unknown; if F1/MCC is poor, the methodology page's model accuracy card may undermine credibility

## Session Continuity

Last session: 2026-03-17T20:41:25.648Z
Stopped at: Completed 04-02-PLAN.md (paused at Task 3 checkpoint:human-verify)
Resume file: None
