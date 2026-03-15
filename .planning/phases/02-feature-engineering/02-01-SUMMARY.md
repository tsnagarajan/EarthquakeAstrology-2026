---
phase: 02-feature-engineering
plan: 01
subsystem: feature-engineering
tags: [pyarrow, tdd, test-stubs, wave-0, scaffold]
dependency_graph:
  requires: [01-03-ephemeris-validation]
  provides: [pipeline/features package, test stubs for Wave 1 and Wave 2, data/processed/ directory]
  affects: [02-02, 02-03, 02-04, 02-05]
tech_stack:
  added: [pyarrow==23.0.1]
  patterns: [TDD wave-0 stubs, xfail test markers, NotImplementedError stubs]
key_files:
  created:
    - pipeline/features/__init__.py
    - pipeline/features/engineering.py
    - tests/test_engineering.py
    - data/processed/.gitkeep
  modified:
    - pyproject.toml (added pyarrow dependency)
    - uv.lock
decisions:
  - "PLANETS constant redefined in engineering.py as a list to avoid importing swisseph C extension at test time"
  - "26 test methods across 10 classes (plan specified 10 stubs minimum; each class has 2-4 methods for clearer coverage)"
  - "xfail markers used (not skip) so pytest reports expected failures with traceable reason strings"
metrics:
  duration_minutes: 21
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 2 Plan 01: Feature Engineering Scaffold Summary

**One-liner:** Wave-0 gate — pyarrow installed, pipeline/features package scaffolded with 10 xfail test classes and 10 NotImplementedError stub functions for FEAT-01 through FEAT-05.

## What Was Built

### Task 1: Install pyarrow and create pipeline/features package
- `uv add pyarrow` installed pyarrow 23.0.1 into the project venv
- `pipeline/features/__init__.py` created as a proper Python package declaration
- `data/processed/` directory created (parquet output location for 8.5M-row dataset)
- Commit: `75d08ef`

### Task 2: Create test stubs and engineering.py module skeleton
- `tests/test_engineering.py`: 10 test classes, 26 test methods, all `pytest.mark.xfail`
- `pipeline/features/engineering.py`: 10 function stubs (all raise NotImplementedError)
- pytest collects all 26 tests without ImportError (exit code 0)
- Commit: `fce39c6`

## Test Classes Created

| Class | Requirement | Wave |
|---|---|---|
| TestGridCells | FEAT-01 | 1 |
| TestCountryParsing | FEAT-01 | 1 |
| TestEQIndicator | FEAT-02 | 1 |
| TestEQIndicatorCollapse | FEAT-02 | 1 |
| TestColumnInventory | FEAT-03 | 1 |
| TestNoRawColumns | FEAT-03 | 1 |
| TestCyclicalEncoding | FEAT-03 | 1 |
| TestTemporalSplit | FEAT-04 | 2 |
| TestEncoderFitScope | FEAT-04 | 2 |
| TestDownsamplingScope | FEAT-05 | 2 |

## Function Stubs in engineering.py

| Function | Wave |
|---|---|
| `compute_grid_coords(lat, lon) -> tuple[int, int]` | 1 |
| `build_active_cells(usgs_df) -> set[tuple[int, int]]` | 1 |
| `extract_country(place) -> str` | 1 |
| `build_eq_index(usgs_df) -> pd.Series` | 1 |
| `encode_cyclic(series, period) -> tuple[pd.Series, pd.Series]` | 1 |
| `compute_tithi(sun_lon, moon_lon) -> tuple[int, str]` | 1 |
| `encode_ephemeris(ephe_df) -> pd.DataFrame` | 1 |
| `fit_nakshatra_encoder(pre2000_df) -> object` | 2 |
| `assert_no_temporal_leakage(train_dates, test_dates) -> None` | 2 |
| `downsample_negatives(df, ratio, random_state) -> pd.DataFrame` | 2 |

## Decisions Made

1. **PLANETS as list in engineering.py**: The PLANETS constant in `ephemeris.py` is a dict mapping names to swisseph integer constants (requires C extension import). Engineering.py redefines PLANETS as `["sun", "moon", ...]` to allow tests to import without swisseph setup, avoiding missing .se1 file errors in CI.

2. **26 test methods vs 10 test classes**: Each test class has 2-4 focused test methods instead of a single monolithic test, matching best practice for granular failure reporting. The plan required 10 class stubs — all 10 are present.

3. **xfail over skip**: `pytest.mark.xfail(reason="...")` is used rather than `pytest.mark.skip` so that when a wave implements a function, the previously-xfail test becomes an xpass (automatic pass detection), alerting that the xfail marker should be removed.

## Verification Results

| Check | Result |
|---|---|
| `python -c "import pyarrow"` | PASS (23.0.1) |
| `pytest tests/test_engineering.py --collect-only` | PASS (26 tests collected, 0 errors) |
| `from pipeline.features.engineering import compute_grid_coords, ...` | PASS |
| `data/processed/` exists | PASS |

## Deviations from Plan

**1. [Rule 2 - Enhancement] Added more test methods per class**
- Found during: Task 2
- Issue: Plan specified "at minimum one test method" per class; single methods would not cover the behavioral spec written in `<behavior>` block
- Fix: Added 2-4 test methods per class matching exact behavior specs (26 total vs 10 minimum)
- Files modified: tests/test_engineering.py
- Commit: fce39c6

**2. [Rule 1 - Bug prevention] PLANETS redefined as list (not imported from ephemeris)**
- Found during: Task 2
- Issue: Importing PLANETS from pipeline/data/ephemeris.py imports swisseph C extension, which requires .se1 files and SE_EPHE_PATH env var — would cause ImportError in CI
- Fix: Redefined PLANETS as a plain list of strings in engineering.py; behavior is identical for column iteration
- Files modified: pipeline/features/engineering.py
- Commit: fce39c6

## Self-Check: PASSED

All files verified to exist:
- [x] pipeline/features/__init__.py — FOUND
- [x] pipeline/features/engineering.py — FOUND
- [x] tests/test_engineering.py — FOUND
- [x] data/processed/.gitkeep — FOUND

All commits verified:
- [x] 75d08ef — FOUND
- [x] fce39c6 — FOUND
