---
phase: 02-feature-engineering
plan: "04"
subsystem: feature-engineering
tags: [temporal-leakage, downsampling, matrix-builder, tdd]
dependency_graph:
  requires: [02-02, 02-03]
  provides: [assert_no_temporal_leakage, downsample_negatives, build_matrix_chunk, active_cells_list]
  affects: [02-05-matrix-assembly]
tech_stack:
  added: []
  patterns: [TDD red-green, MultiIndex reindex+fillna, date-type normalization]
key_files:
  created: []
  modified:
    - pipeline/features/engineering.py
    - tests/test_engineering.py
decisions:
  - "build_matrix_chunk normalizes ephe_row.name to datetime.date before eq_index reindex to handle str/Timestamp index inputs from callers"
  - "active_cells_list helper added to convert active-cells set to deterministic sorted list for chunked iteration"
  - "downsample_negatives clamps with min(ratio*n_pos, n_neg) so small negative pools are handled gracefully"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_modified: 2
---

# Phase 2 Plan 4: Temporal Split Enforcement and Matrix Chunk Builder Summary

Implemented three correctness-critical functions in engineering.py: `assert_no_temporal_leakage` (hard AssertionError guard on the 2000-01-01 temporal boundary), `downsample_negatives` (deterministic 10:1 negative sampling from the pre-2000 training pool), and `build_matrix_chunk` (broadcasts one ephemeris row to all 901 active grid cells, assigning EQIndicator from eq_index lookup).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Failing tests: temporal split + downsampling | 3ac7bdb | tests/test_engineering.py |
| 1 GREEN | Implement assert_no_temporal_leakage, downsample_negatives | a511bb3 | pipeline/features/engineering.py |
| 2 RED | Failing tests: build_matrix_chunk | 789e159 | tests/test_engineering.py |
| 2 GREEN | Implement build_matrix_chunk, active_cells_list | c864e6d | pipeline/features/engineering.py, tests/test_engineering.py |

## Verification Results

- `pytest tests/test_engineering.py::TestTemporalSplit tests/test_engineering.py::TestDownsamplingScope -x -q` — 11 passed
- `pytest tests/test_engineering.py::TestBuildMatrixChunk -q` — 7 passed
- All Wave 2 tests: 18 passed
- Smoke test: `assert_no_temporal_leakage([date(1999,12,31)], [date(2000,1,1)])` prints "temporal split assertion OK"
- Pre-existing Wave 1 failures (16): extract_country stub, build_eq_index stub, sklearn sparse_output compat — all pre-existed before this plan, no regressions introduced

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed date type mismatch in build_matrix_chunk eq_index lookup**
- **Found during:** Task 2 GREEN phase
- **Issue:** `ephe_row.name` when DataFrame is indexed from a string date yields a `str`, not a `datetime.date`. The eq_index MultiIndex uses `datetime.date` objects (from `build_eq_index`). The `reindex` lookup always returned 0 (no match) due to type mismatch.
- **Fix:** Added date normalization via `pd.Timestamp(raw_name).date()` before constructing the lookup MultiIndex; falls through directly if already a `datetime.date`.
- **Files modified:** pipeline/features/engineering.py
- **Commit:** c864e6d

**2. [Rule 1 - Bug] Fixed scoped `pd` import in test helper `_make_eq_index_for_date`**
- **Found during:** Task 2 GREEN phase first run
- **Issue:** `pd` was only imported inside the `if isinstance(date_val, str):` branch but used unconditionally after it, causing `UnboundLocalError` when date_val is a `datetime.date` object.
- **Fix:** Removed the conditional local import; test file already has top-level `import pandas as pd`.
- **Files modified:** tests/test_engineering.py
- **Commit:** c864e6d

## Decisions Made

- `build_matrix_chunk` normalizes `ephe_row.name` to `datetime.date` before eq_index reindex — handles str/Timestamp index inputs from callers without requiring callers to pre-convert
- `active_cells_list` added as a helper to convert the active-cells set to a deterministic sorted list for outer chunked iteration in Plan 05
- `downsample_negatives` uses `min(ratio * n_pos, n_neg)` clamping so the function degrades gracefully when the negative pool is smaller than the target sample size

## Self-Check: PASSED
