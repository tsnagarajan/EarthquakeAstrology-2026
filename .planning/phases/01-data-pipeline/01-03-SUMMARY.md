---
phase: 01-data-pipeline
plan: 03
subsystem: data
tags: [ephemeris, validation, jpl-horizons, spot-check, swiss-ephemeris, tdd, accuracy-gate]

# Dependency graph
requires:
  - phase: 01-data-pipeline
    plan: 02
    provides: pipeline/data/ephemeris.py producing data/raw/ephemeris.csv with sun_lon, jupiter_lon columns

provides:
  - pipeline/data/validate_ephemeris.py: JPL Horizons spot-check validation script
  - data/validation/.gitkeep: tracked output directory for validation logs
  - Tests: 28 tests covering run_spot_checks, format_log, module structure

affects:
  - 02-feature-engineering
  - 03-model-training

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD: 28 failing tests committed before implementation (RED -> GREEN)
    - Soft import of dotenv (try/except) so module loads without python-dotenv in test envs
    - Circular delta: abs(computed - reference) with 360-wrap if delta > 180
    - Exit codes: 0=all pass, 1=any fail, 2=ephemeris CSV not found

key-files:
  created:
    - pipeline/data/validate_ephemeris.py
    - data/validation/.gitkeep
    - tests/test_validate_ephemeris.py
  modified:
    - .gitignore (added data/validation/*.log)

key-decisions:
  - "dotenv import made optional (soft try/except) — validation script has no env var dependencies, dotenv only needed for ephemeris.py itself"
  - "Circular delta: if abs(computed - ref) > 180, use 360 - delta — handles vernal equinox edge case (reference 359.4, computed near 0.0)"

patterns-established:
  - "Validation script: always read CSV fresh, do not import ephemeris.py — keeps gate independent"
  - "Exit code 2 for missing prerequisite file (vs exit 1 for data failure) — allows CI to distinguish setup errors from accuracy failures"
  - "format_log(): returns string (not writes) — testable without filesystem side effects"

requirements-completed: [DATA-05]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 1 Plan 3: Ephemeris Spot-Check Validation Summary

**JPL Horizons accuracy gate comparing 10 hardcoded Sun+Jupiter positions (1900-2026) against computed ephemeris.csv with 0.5-degree tolerance and PASS/FAIL log output**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T16:47:19Z
- **Completed:** 2026-03-15T16:52:25Z
- **Tasks:** 1 complete + checkpoint awaiting human verify
- **Files modified:** 3 created, 1 modified

## Accomplishments

- `pipeline/data/validate_ephemeris.py` implemented with `run_spot_checks`, `format_log`, and `main` entry point
- 10 hardcoded JPL Horizons reference values spanning 1900-2026 (Sun + Jupiter longitudes)
- Full TDD cycle: 28 failing tests (RED) committed first, then implementation passes all 28 (GREEN)
- Script exits 0 on all-pass, 1 on any-fail, 2 on missing ephemeris CSV
- `data/validation/.gitkeep` tracks output directory; `data/validation/*.log` gitignored

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `34404b7` (test)
2. **Task 1 GREEN: Implementation** - `fd23618` (feat)

_Note: TDD task has separate test and feat commits per TDD protocol_

## Files Created/Modified

- `pipeline/data/validate_ephemeris.py` - JPL Horizons spot-check validator: run_spot_checks, format_log, main; 10 hardcoded reference values, 0.5-deg tolerance, circular delta wrap
- `data/validation/.gitkeep` - Tracks validation output directory in git
- `tests/test_validate_ephemeris.py` - 28 tests: 10 module structure (AST), 10 run_spot_checks behavior, 8 format_log output
- `.gitignore` - Added `data/validation/*.log` exclusion rule

## Decisions Made

- `dotenv` import made optional via `try/except ImportError` so the module can be imported in test environments without python-dotenv installed. The validation script has no env var dependencies of its own (it just reads a CSV).
- Circular delta: `if delta > 180: delta = 360 - delta` — handles the vernal equinox reference value `359.4` where a computed value of `0.1` would give a naive delta of `359.3` but true angular separation is `0.7`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made dotenv import optional to allow test environment loading**
- **Found during:** Task 1 GREEN (running tests)
- **Issue:** `from dotenv import load_dotenv` raised `ModuleNotFoundError` in the system Python 3.8 test environment. The test infrastructure doesn't have python-dotenv installed, and the tests dynamically import validate_ephemeris.py. The module failed to load, causing all 18 functional tests to ERROR.
- **Fix:** Wrapped dotenv import in `try/except ImportError: pass`. The validation script reads only a CSV path argument — it has no environment variable dependencies that require dotenv loading.
- **Files modified:** `pipeline/data/validate_ephemeris.py`
- **Verification:** All 28 tests pass after fix
- **Committed in:** `fd23618` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking)
**Impact on plan:** Fix necessary for test suite to pass. No behavior change — validation script behavior identical with or without dotenv in the execution environment.

## Issues Encountered

- Python 3.8 system interpreter used by pytest does not support `list[tuple]` type hint syntax in function signatures. Fixed by removing the type annotation from `_make_df()` helper in the test file before committing RED tests.

## User Setup Required

**Before running `python pipeline/data/validate_ephemeris.py`:**

```bash
# 1. Generate ephemeris CSV (required — takes 20-30 min)
python pipeline/data/ephemeris.py

# 2. Run validation
python pipeline/data/validate_ephemeris.py

# Expected output:
# ALL SPOT CHECKS PASSED — 10 checks in data/validation/ephemeris_spot_check.log
```

If validation fails:
- Check `data/validation/ephemeris_spot_check.log` for which planet/date failed
- Common cause: `SE_EPHE_PATH` not set correctly (run `bash data/ephe/download_ephe.sh`)
- Check `hour=12.0` in `swe.julday()` calls in `pipeline/data/ephemeris.py`

## Next Phase Readiness

- `pipeline/data/validate_ephemeris.py` ready to serve as pipeline gate after ephemeris.csv is generated
- Phase 1 complete pending human checkpoint verification (Task 2: human-verify)
- Human must run all 4 verification checks from the checkpoint and type "approved" to proceed
- Phase 2 (feature engineering) blocked until checkpoint approved

---
*Phase: 01-data-pipeline*
*Completed: 2026-03-15*
