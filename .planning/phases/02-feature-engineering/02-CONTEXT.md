# Phase 2: Feature Engineering - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform Phase 1 raw CSVs (`data/raw/ephemeris.csv`, `data/raw/usgs_earthquakes.csv`) into a single feature matrix at `data/processed/feature_matrix.csv`. The matrix joins daily planetary positions with earthquake events, encodes all cyclical features as sin/cos pairs, assigns geographic identifiers, derives the binary EQIndicator target, and enforces the temporal split. Model training and prediction export are out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Row Granularity
- Each row = one date × one seismically active grid cell (not one row per date globally, not one row per event)
- Grid cell unit: 5°×5° lat/lon bucket
- Only include grid cells where at least 1 M5.5+ event occurred in 1900–2026 (~200–400 active cells)
- Resulting matrix size: ~46,022 days × ~300 active cells before downsampling

### Geographic Join
- Country label: parse USGS `place` text field — extract last comma-delimited token (e.g., "Southern Sumatra, Indonesia" → "Indonesia")
- Grid cell assignment: floor method — `grid_lat = floor(lat/5)*5`, `grid_lon = floor(lon/5)*5`
- Grid cell label format: e.g., `lat-5_lon100` or `(-5, 100)` (Claude's discretion on exact string format)

### EQIndicator Construction
- Binary target: `EQIndicator = 1` if any M5.5+ event hit that grid cell on that date, else `0`
- Multiple events in same cell on same day collapse to `EQIndicator = 1`
- Downsampling: 10:1 negative-to-positive ratio applied to training data (pre-2000) only
  - Test data (2000–2026) is NOT downsampled — preserve all rows for evaluation
  - Fixed `random_state=42` for deterministic, reproducible matrix

### Column Selection (469 ephemeris columns → final matrix)
- Strategy: include all planetary features, then drop redundant raw columns after encoding
- **DROP** (explicit exclusions):
  - `*_sign_num` columns (raw integer 1–12) — replaced by sin/cos encoding per FEAT-02
  - `*_lon` raw longitude columns (e.g., `sun_lon`) — replaced by `sun_lon_sin` / `sun_lon_cos`
  - USGS metadata columns: `place`, `id`, `updated`, `type`, `net`, `magType`, `nst`, `gap`, `dmin`, `rms`, `horizontalError`, `depthError`, `magError`, `magNst`, `status`, `locationSource`, `magSource`
- **KEEP and ENCODE:**
  - Planetary longitudes → sin/cos pairs (`*_lon_sin`, `*_lon_cos`)
  - Zodiac sign numbers (1–12) → sin/cos pairs
  - Nakshatra numbers (1–27) → sin/cos pairs
  - Nakshatra name strings → one-hot encoded (27 binary columns per planet)
  - Retrograde flags (`*_retro`) → kept as boolean/int (already binary)
  - Aspect columns (e.g., `sun_moon_conjunction`) → kept as boolean/int
  - House placements → kept as-is (Claude's discretion on encoding if numeric)
- USGS columns to retain: `latitude`, `longitude`, `mag` (for EQIndicator derivation only — not features in the final matrix)

### Temporal Split Enforcement
- All downsampling logic is fit and applied exclusively on pre-2000 rows
- Assertion required: `max(X_train.index) < datetime(2000, 1, 1)` and `min(X_test.index) >= datetime(2000, 1, 1)`
- Grid cell discovery (which cells are "active") uses the full dataset but is purely a lookup — no leakage

### Claude's Discretion
- Exact string format for grid cell label column
- How to handle USGS events where `place` field is missing or unparseable (fallback to lat/lon-derived label)
- Exact column ordering in the final CSV
- House placement encoding approach (if columns exist in ephemeris.csv — audit needed)
- Whether to save a `feature_columns.json` manifest alongside the CSV for Phase 3 consumption

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/data/ephemeris.py`: Planet list, aspect computation patterns, nakshatra logic — can be referenced for column name conventions
- `pipeline/data/usgs.py`: USGS CSV structure and date parsing patterns
- `data/raw/ephemeris.csv`: 469 columns, 46,022 rows (1900–2026 daily) — Phase 2 reads this directly
- `data/raw/usgs_earthquakes.csv`: 39,514 rows, columns: `time`, `latitude`, `longitude`, `depth`, `mag`, `place`

### Established Patterns
- Date parsing: ephemeris uses `date` column (YYYY-MM-DD), USGS uses `time` column (ISO 8601 with Z suffix) — join key requires normalization to date-only
- pysweph 2.10.3.6 already imported in pipeline — no new ephemeris dependencies needed for Phase 2
- Logging pattern: `logging.basicConfig(...)` + `logger = logging.getLogger("module_name")` established in Phase 1 scripts

### Integration Points
- Phase 2 reads from `data/raw/` and writes to `data/processed/feature_matrix.csv` (directory must be created)
- Phase 3 will read `data/processed/feature_matrix.csv` and expects `EQIndicator` column + date index
- Grid cell columns (`grid_lat`, `grid_lon`) and `country` column must be present for Phase 3 prediction export schema (predictions.json requires `lat`, `lon`, `country`, `risk_score`)

</code_context>

<specifics>
## Specific Ideas

- Archive notebooks (e.g., `Archive/Full Pipeline 10102019 TSN.ipynb`) contain the original 265–309 column structure — worth auditing for any feature groups not covered by the current ephemeris.csv (e.g., Moon phase angle, inter-planetary distance features)
- STATE.md flags a required column-by-column audit against Archive notebooks before feature engineering begins
- The ~265-column target from the roadmap may shift once raw columns are dropped and one-hot nakshatras are added — the actual count should be documented in the script's docstring after implementation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-feature-engineering*
*Context gathered: 2026-03-15*
