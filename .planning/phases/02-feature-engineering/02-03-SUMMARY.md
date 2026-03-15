---
phase: 02-feature-engineering
plan: 03
subsystem: feature-engineering
tags: [tdd, ephemeris-encoding, cyclic-features, nakshatra, one-hot-encoder, sklearn]
dependency_graph:
  requires: [02-01-scaffold, 01-03-ephemeris-validation]
  provides: [encode_cyclic, compute_tithi, encode_ephemeris, fit_nakshatra_encoder, apply_nakshatra_encoding, NAKSHATRA_COLS, TITHIS]
  affects: [02-04-matrix-builder, 02-05-train-test-split]
tech_stack:
  added: [scikit-learn>=1.8.0 (OneHotEncoder with sparse_output, handle_unknown=ignore)]
  patterns: [cyclic sin/cos encoding, TDD green phase, vectorised pandas transforms]
key_files:
  created: []
  modified:
    - pipeline/features/engineering.py
    - tests/test_engineering.py
decisions:
  - "encode_ephemeris PRESERVES {p}_nakshatra string columns — only {p}_lon, {p}_sign_num, {p}_sign, {p}_nakshatra_num are dropped; nakshatra strings remain for apply_nakshatra_encoding in Plan 05"
  - "TITHIS list uses SP1-SP14, FM (idx 14), KP1-KP14, NM (idx 29) — full moon at position 14, new moon at position 29"
  - "test_text_nakshatra_absent refactored to test_text_nakshatra_absent_after_full_pipeline — uses both encode_ephemeris + apply_nakshatra_encoding to correctly verify the two-step pipeline"
  - "tithi encoded as cyclic with period=30 (0-29 integer index mapped to 30-step circle)"
  - "_make_full_nakshatra_df() helper added — 27 rows covering all 27 nakshatras so encoder vocabulary is complete"
metrics:
  duration_minutes: 25
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 0
  files_modified: 2
---

# Phase 2 Plan 03: Ephemeris Encoding Functions Summary

**One-liner:** Cyclic sin/cos encoding pipeline for 469-column raw ephemeris — encode_cyclic, compute_tithi, encode_ephemeris (preserving nakshatra strings), fit_nakshatra_encoder, apply_nakshatra_encoding; all 15 target tests pass.

## What Was Built

### Task 1: encode_cyclic, compute_tithi, encode_ephemeris

**`encode_cyclic(series, period)`** — vectorised sin/cos transform using `series * (2π / period)`. Handles period=360 (longitudes), period=12 (sign numbers), period=27 (nakshatra numbers), period=30 (tithi index).

**`compute_tithi(sun_lon, moon_lon)`** — computes Vedic lunar day from `(moon_lon - sun_lon) % 360 / 12`. Returns `(int 0-29, name str)`. TITHIS list: SP1-SP14, FM (index 14), KP1-KP14, NM (index 29).

**`encode_ephemeris(ephe_df)`** — master orchestration function:
1. Computes tithi_sin/tithi_cos from sun_lon/moon_lon (before dropping columns)
2. For each of 13 planets: adds {p}_lon_sin/cos (period=360), {p}_sign_num_sin/cos (period=12), {p}_nakshatra_num_sin/cos (period=27)
3. Converts all {p}_retro bool columns to int (0/1)
4. Converts all aspect bool columns to int (0/1) via `_ASPECT_TYPES` suffix matching
5. Drops {p}_lon, {p}_sign_num, {p}_sign, {p}_nakshatra_num raw columns
6. **PRESERVES** {p}_nakshatra string columns — these stay for apply_nakshatra_encoding

Output column count after encode_ephemeris (before nakshatra one-hot):
- 26 lon sin/cos + 26 sign_num sin/cos + 26 nakshatra_num sin/cos = 78 cyclic
- 13 retro + 390 aspect + 2 tithi = 405 binary/cyclic
- 13 nakshatra strings (preserved) = 13
- Total: 496 feature columns + date

Commit: `296a6fa`

### Task 2: fit_nakshatra_encoder, apply_nakshatra_encoding, save_encoder, load_encoder

**`NAKSHATRA_COLS`** — module-level constant `[f"{p}_nakshatra" for p in PLANETS]` (13 strings).

**`fit_nakshatra_encoder(pre2000_df)`** — fits sklearn `OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.uint8)` on the 13 nakshatra name columns. Input must be pre-2000 training data with all 27 nakshatra vocabulary present.

**`apply_nakshatra_encoding(df, encoder)`** — transforms 13 nakshatra string columns into 351 uint8 one-hot columns (names like `sun_nakshatra_Ashwini`), drops original string columns, concatenates results.

**`save_encoder(encoder, path)` / `load_encoder(path)`** — joblib persistence for Plan 05 to write `data/processed/nakshatra_encoder.pkl`.

Final column count after full pipeline (encode_ephemeris + apply_nakshatra_encoding):
- 496 (from above) - 13 nakshatra strings + 351 one-hot columns = **834 feature columns + date**

Commit: `296a6fa` (included with Task 1 in atomic implementation)

## Test Classes Updated

| Class | Status | Tests |
|---|---|---|
| TestCyclicalEncoding | PASSING (xfail removed) | 3 tests |
| TestColumnInventory | PASSING (xfail removed) | 2 tests |
| TestNoRawColumns | PASSING (xfail removed, refactored) | 5 tests |
| TestEncoderFitScope | PASSING (xfail removed, expanded) | 5 tests |

## Verification Results

| Check | Result |
|---|---|
| `pytest TestCyclicalEncoding -q` | 3 passed |
| `pytest TestColumnInventory -q` | 2 passed |
| `pytest TestNoRawColumns -q` | 5 passed (includes two-step pipeline test) |
| `pytest TestEncoderFitScope -q` | 5 passed (351 columns, handle_unknown=ignore verified) |
| Smoke: encode_cyclic([0,90,180,270], 360) | [(0,1),(1,0),(0,-1),(-1,0)] PASS |
| Smoke: nakshatra strings preserved after encode_ephemeris | 13/13 preserved PASS |
| Smoke: tithi_sin/tithi_cos columns present | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestNoRawColumns::test_text_nakshatra_absent refactored**
- Found during: Task 1 implementation
- Issue: Original test called only `encode_ephemeris(ephe_df)` and asserted `{p}_nakshatra` absent — but the plan explicitly states encode_ephemeris MUST preserve nakshatra strings. The test contradicted the plan's must_haves and was incorrect.
- Fix: Renamed to `test_text_nakshatra_absent_after_full_pipeline`; now calls both `encode_ephemeris()` then `apply_nakshatra_encoding()`. Added new `test_nakshatra_strings_preserved_after_encode_ephemeris` test to assert the preservation invariant.
- Files modified: tests/test_engineering.py
- Commit: 296a6fa

**2. [Rule 2 - Enhancement] Added _make_full_nakshatra_df() test helper**
- Found during: Task 2
- Issue: `_make_minimal_ephe_df()` uses only one row with a single nakshatra per planet — not sufficient to fit an encoder covering all 27 nakshatras (required for the 351-column assertion). Using it would yield an encoder with only the nakshatras that appear, not all 27.
- Fix: Added `_make_full_nakshatra_df()` helper that builds 27 rows (one per nakshatra), ensuring all 27 vocabulary entries are present at fit time.
- Files modified: tests/test_engineering.py
- Commit: 296a6fa

**3. [Rule 2 - Enhancement] Expanded TestEncoderFitScope**
- Found during: Task 2
- Issue: Plan specified 2 test methods (fit_returns_encoder, unknown_nakshatra_zero_vector). These were insufficient to verify the 351-column count invariant.
- Fix: Added `test_encoder_has_13_features`, `test_encoder_produces_351_columns`, `test_apply_nakshatra_encoding_adds_351_cols` for full coverage of the must_haves truths.
- Files modified: tests/test_engineering.py
- Commit: 296a6fa

### Pre-existing Failures (Out of Scope)

`TestCountryParsing`, `TestEQIndicator`, `TestEQIndicatorCollapse` — 10 tests failing because their xfail markers were removed by the 02-02 partial execution (`efa72bc`) but `extract_country` and `build_eq_index` were never implemented. These are 02-02 concerns, not 02-03. Logged in deferred-items.

## Self-Check: PASSED

Files verified:
- [x] pipeline/features/engineering.py — FOUND
- [x] tests/test_engineering.py — FOUND
- [x] .planning/phases/02-feature-engineering/02-03-SUMMARY.md — FOUND

Commits verified:
- [x] 296a6fa — feat(02-03): implement encode_cyclic, compute_tithi, encode_ephemeris — FOUND
