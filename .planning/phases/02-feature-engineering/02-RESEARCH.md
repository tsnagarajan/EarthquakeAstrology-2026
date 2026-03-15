# Phase 2: Feature Engineering - Research

**Researched:** 2026-03-15
**Domain:** pandas cross-join, cyclical encoding, temporal-split-aware downsampling, scikit-learn preprocessing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Row grain: date x seismically active 5°x5° grid cell
- Grid cell: floor(lat/5)*5, floor(lon/5)*5; only cells with at least 1 historical M5.5+
- Country: parsed from USGS place field (last comma-delimited token)
- EQIndicator: binary 1/0 per date x cell
- Downsample: 10:1 negative:positive ratio applied to training data (pre-2000) only
  - Test data (2000–2026) is NOT downsampled — preserve all rows for evaluation
  - Fixed random_state=42 for deterministic, reproducible matrix
- DROP: *_sign_num, *_lon raw columns, USGS metadata columns (place, id, updated, type, net, magType, nst, gap, dmin, rms, horizontalError, depthError, magError, magNst, status, locationSource, magSource)
- KEEP+ENCODE: lon→sin/cos, nakshatra_num→sin/cos, nakshatra_name→one-hot (27 per planet), retrograde+aspects→boolean
- Temporal split assertion: max(X_train.index) < 2000-01-01, min(X_test.index) >= 2000-01-01

### Claude's Discretion
- Exact string format for grid cell label column
- How to handle USGS events where `place` field is missing or unparseable (fallback to lat/lon-derived label)
- Exact column ordering in the final CSV
- House placement encoding approach (if columns exist in ephemeris.csv — audit needed)
- Whether to save a `feature_columns.json` manifest alongside the CSV for Phase 3 consumption

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FEAT-01 | Feature matrix with planetary degrees, retrograde flags, zodiac signs (one-hot encoded), house placements, aspects, nakshatras — matching ~265-column structure | Column audit section documents actual structure; Archive audit identifies gaps; column count will exceed 265 due to nakshatra one-hot expansion |
| FEAT-02 | All cyclical features encoded as sin/cos — no raw integer degree or sign columns in final matrix | Sin/cos pattern documented; sign_num, lon, nakshatra_num all get sin/cos pairs; raw columns dropped |
| FEAT-03 | Train/test split at 2000-01-01 — all scalers, encoders, samplers fit exclusively on pre-2000 data | Temporal split section documents assertion pattern; downsampler applied to pre-2000 only; one-hot encoder fit on pre-2000 column vocabulary |
| FEAT-04 | EQIndicator target: 1 for M5.5+ earthquake dates, 0 for non-earthquake dates | EQIndicator construction section; binary at date x cell grain; multiple events collapse to 1 |
| FEAT-05 | Regional geographic identifiers (country, lat/long grid cell) as prediction dimensions | Grid cell computation verified; country parsing from place field documented; 901 active cells confirmed |
</phase_requirements>

---

## Summary

Phase 2 transforms two raw CSVs (ephemeris.csv at 46,022 rows x 469 cols; usgs_earthquakes.csv at 39,514 rows) into a single feature matrix at `data/processed/feature_matrix.csv`. The central engineering challenge is scale: 901 active grid cells x 46,022 dates = 41.4 million potential rows before downsampling. The solution is to **never materialize the full cross-join in RAM**. Instead, build the matrix date-by-date (or in date chunks), expanding only to active cells, writing in batches, and applying downsampling to pre-2000 rows before writing.

After downsampling the pre-2000 training set at 10:1, the training portion shrinks to ~263,681 rows — easily handled in RAM (~0.44 GB at mixed uint8/float32). The test set (post-2000) contains ~8.5 million rows. This **cannot be held in memory simultaneously** and must be written in date-range chunks. The output format should be parquet (not CSV) for acceptable file sizes; pyarrow is not currently installed and must be added, or fastparquet used as an alternative.

The 469 ephemeris columns divide cleanly into 13 lon, 13 sign_num, 13 sign_name, 13 retro, 13 nakshatra_num, 13 nakshatra_name, and 390 aspect boolean columns. After encoding (drop lon/sign_num raw, sin/cos both, one-hot nakshatra_name with 27 classes), the final feature count is approximately 836 feature columns plus 4 identifier/target columns. The Archive notebooks reveal several feature groups not in ephemeris.csv: tithi (moon phase bracket), nakshatra pada (subdivision 1-4), star element classification (Vayu/Agni/Indra/Varuna), and planetary sign-based "house aspects" (HA). House placements from ephemeris are NOT applicable (require a birth location; ephemeris.py computes no house system).

**Primary recommendation:** Build the matrix via a chunked loop (outer loop: date ranges; inner join: ephemeris row broadcast to all active cells). Apply per-chunk downsampling with a seeded numpy RNG for pre-2000 chunks. Write each chunk to parquet. Merge chunks at the end. Validate with assertions before writing.

---

## Discovered Data Realities

**IMPORTANT: Several CONTEXT.md estimates are inaccurate — planner must use these corrected values.**

| Metric | CONTEXT.md Estimate | Actual Value | Source |
|--------|---------------------|-------------|--------|
| Active grid cells | ~200–400 | **901 all-time; 839 pre-2000** | Computed from usgs_earthquakes.csv with floor(lat/5)*5, floor(lon/5)*5 |
| Full matrix rows before downsample | ~14M (46k x 300) | **41.4M (46022 x 901)** | Direct calculation |
| Training positive date-cell combos | not specified | **23,971** | Unique (date, grid_lat, grid_lon) triples with M5.5+ in pre-2000 data |
| Training rows after 10:1 downsample | not specified | **~263,681** (23,971 pos + 239,710 neg) | 23,971 * 11 |
| Test rows (2000–2026, not downsampled) | not specified | **~8.56M** (901 x ~9,496 days) | Too large for in-memory at full column width |
| House placement columns | "audit needed" | **ABSENT** — ephemeris.py does not compute houses | Confirmed via ephemeris.csv column audit; no house system columns exist |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.1 (installed) | DataFrame operations, merge, groupby, date handling | Already installed; 3.x has better Copy-on-Write semantics |
| numpy | 2.4.3 (installed) | sin/cos encoding, floor/ceil for grid cells, random downsampling | Already installed |
| scikit-learn | 1.8.0 (installed) | OneHotEncoder (for nakshatra one-hot), pipeline utilities if needed | Already installed; 1.8.x has stable `set_output(transform="pandas")` |
| imbalanced-learn | 0.14.1 (installed) | RandomUnderSampler for downsampling | Already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyarrow | NOT INSTALLED — must add | Parquet write/read engine for pandas `to_parquet()` | Required to write feature_matrix.parquet; add to pyproject.toml |
| joblib | 1.4 (installed) | Saving encoders/scalers for Phase 3 reuse | Save fit OneHotEncoder so Phase 3 can transform future dates consistently |
| tqdm | installed | Progress bars on chunked loop | Same pattern as ephemeris.py and usgs.py |

### Installation
```bash
uv add pyarrow
```
pyarrow is the pandas-recommended parquet engine and installs cleanly on Python 3.13.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Parquet output | CSV output | CSV for ~263K train rows is fine (~200MB). CSV for 8.5M test rows is ~7GB uncompressed — not practical. Parquet compresses boolean-heavy data 10–20x |
| RandomUnderSampler (imbalanced-learn) | pandas `.sample()` with frac | Both work for random downsampling. `pandas.sample(n=..., random_state=42)` is simpler, avoids an extra dependency for this use case |
| scikit-learn OneHotEncoder | pandas `get_dummies()` | `get_dummies()` is simpler but does NOT handle unseen categories at inference time (2026 dates). OneHotEncoder with `handle_unknown='ignore'` is safer for Phase 3 |

---

## Architecture Patterns

### Recommended Project Structure
```
pipeline/
├── data/            # Phase 1 (existing)
│   ├── ephemeris.py
│   └── usgs.py
└── features/        # Phase 2 (create this directory)
    └── engineering.py
data/
├── raw/             # Phase 1 outputs (read-only for Phase 2)
│   ├── ephemeris.csv
│   └── usgs_earthquakes.csv
└── processed/       # Phase 2 outputs (create this directory)
    ├── feature_matrix_train.parquet  # or feature_matrix.parquet with train col
    └── feature_columns.json          # column manifest for Phase 3
```

### Pattern 1: Chunked Matrix Build — Never Full Cross-Join in RAM

**What:** Outer loop iterates over date ranges (e.g., yearly chunks). For each chunk, broadcast the ephemeris row to all 901 active cells, join EQIndicator from USGS, apply downsampling to pre-2000 chunk, append to running parquet file.

**When to use:** Any time the cross-join exceeds available RAM (~16GB). With 901 cells and 836 columns, even a single year (365 x 901 = ~329K rows) is ~0.5GB in-memory — manageable as a chunk.

**Example (conceptual):**
```python
import numpy as np
import pandas as pd

# Pre-compute active cells (discovery uses full dataset — no leakage, lookup only)
active_cells = compute_active_cells(usgs_df)  # set of (grid_lat, grid_lon) tuples

# Pre-compute EQ events as a lookup: (date, grid_lat, grid_lon) -> 1
eq_index = build_eq_index(usgs_df)  # pd.Series with MultiIndex (date, grid_lat, grid_lon)

rng = np.random.default_rng(42)  # seeded for reproducibility

for year_start, year_end in year_chunks(1900, 2026):
    ephe_chunk = ephemeris_df[year_start:year_end]  # date-indexed slice

    # Broadcast: repeat each date row for all 901 cells
    chunk = ephe_chunk.loc[ephe_chunk.index.repeat(len(active_cells))].copy()
    chunk[['grid_lat', 'grid_lon']] = np.tile(list(active_cells), (len(ephe_chunk), 1))

    # Assign EQIndicator
    chunk['EQIndicator'] = chunk.set_index(['date', 'grid_lat', 'grid_lon']) \
        .index.map(eq_index).fillna(0).astype(int).values

    # Downsample pre-2000 negatives only
    if year_end < 2000:
        positives = chunk[chunk['EQIndicator'] == 1]
        negatives = chunk[chunk['EQIndicator'] == 0]
        n_neg = len(positives) * 10
        negatives = negatives.sample(n=min(n_neg, len(negatives)), random_state=42)
        chunk = pd.concat([positives, negatives])

    # Write/append to parquet
    write_parquet_chunk(chunk, output_path)
```

**Note:** `np.tile` + `repeat` for the broadcast is O(n_cells * n_days). For a yearly chunk of 365 days: 365 * 901 = ~329K rows — fast and memory-safe.

### Pattern 2: Sin/Cos Cyclical Encoding

**What:** Replace any periodic numeric column with two columns: `sin(value * 2π / period)` and `cos(value * 2π / period)`.

**When to use:** Planetary longitude (period=360), zodiac sign number (period=12), nakshatra number (period=27).

```python
import numpy as np

def encode_cyclic(series: pd.Series, period: float) -> tuple[pd.Series, pd.Series]:
    """Encode a cyclic numeric feature as sin/cos pair.

    Args:
        series: Numeric series with values in [0, period).
        period: Full cycle value (360 for degrees, 12 for zodiac, 27 for nakshatras).

    Returns:
        Tuple of (sin_series, cos_series).
    """
    radians = series * (2 * np.pi / period)
    return np.sin(radians), np.cos(radians)

# Usage:
df['sun_lon_sin'], df['sun_lon_cos'] = encode_cyclic(df['sun_lon'], 360.0)
df['sun_sign_num_sin'], df['sun_sign_num_cos'] = encode_cyclic(df['sun_sign_num'], 12.0)
df['sun_nakshatra_num_sin'], df['sun_nakshatra_num_cos'] = encode_cyclic(df['sun_nakshatra_num'], 27.0)
df.drop(columns=['sun_lon', 'sun_sign_num'], inplace=True)
```

### Pattern 3: Temporal-Split-Aware OneHotEncoder

**What:** Fit the OneHotEncoder only on pre-2000 nakshatra names, then transform both train and test. This prevents any post-2000 category distributions from influencing encoding.

**When to use:** Any categorical encoder that learns from data (OneHotEncoder, OrdinalEncoder, LabelEncoder) — always fit on train split only.

```python
from sklearn.preprocessing import OneHotEncoder

# CORRECT: fit on pre-2000 only
nakshatra_cols = [f'{p}_nakshatra' for p in PLANETS]
encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.uint8)
encoder.fit(train_df[nakshatra_cols])  # train_df is pre-2000 only

# Transform both splits
train_encoded = encoder.transform(train_df[nakshatra_cols])
test_encoded = encoder.transform(test_df[nakshatra_cols])  # unknown categories -> all zeros

# Save encoder for Phase 3 (predict 2026 future dates)
import joblib
joblib.dump(encoder, 'data/processed/nakshatra_encoder.pkl')
```

### Pattern 4: Temporal Split Assertion

**What:** Hard assertion after building the split — assert raises, it doesn't log. The script must exit non-zero if leakage is detected.

```python
from datetime import datetime

def assert_no_temporal_leakage(train_dates, test_dates):
    """Assert strict temporal boundary at 2000-01-01.

    Raises:
        AssertionError: If any training row is on or after 2000-01-01,
                        or any test row is before 2000-01-01.
    """
    SPLIT_DATE = datetime(2000, 1, 1).date()

    max_train = pd.to_datetime(train_dates).max().date()
    min_test = pd.to_datetime(test_dates).min().date()

    assert max_train < SPLIT_DATE, (
        f"Temporal leakage: training set contains rows on/after 2000-01-01. "
        f"max(train.date) = {max_train}"
    )
    assert min_test >= SPLIT_DATE, (
        f"Temporal leakage: test set contains rows before 2000-01-01. "
        f"min(test.date) = {min_test}"
    )
```

### Pattern 5: Country from USGS Place Field

**What:** Parse `place` as a comma-delimited string and take the last token. Handle no-comma rows as their own region label.

```python
def extract_country(place: str) -> str:
    """Extract country/region from USGS place field.

    'Southern Sumatra, Indonesia' -> 'Indonesia'
    'Bismarck Sea' -> 'Bismarck Sea'
    None/NaN -> 'Unknown'
    """
    if pd.isna(place) or not str(place).strip():
        return 'Unknown'
    parts = str(place).split(',')
    return parts[-1].strip()
```

**Known place field patterns from actual data:**
- `"Southern Sumatra, Indonesia"` -> `"Indonesia"` (works)
- `"Bismarck Sea"` -> `"Bismarck Sea"` (no comma; handled as-is)
- `"Near the coast of Venezuela"` -> `"Venezuela"` (last token has region info)
- `"Kodiak Island region, Alaska"` -> `"Alaska"` (works)
- `None/NaN` -> `"Unknown"` (fallback)

**Design decision (Claude's discretion):** Accept last-token parsing. For multi-word last tokens like "Bismarck Sea", treat as the region label — do not attempt further normalization.

### Anti-Patterns to Avoid

- **Full cross-join materialization:** Never `df1.merge(df2, how='cross')` on the full 901-cell x 46,022-day dataset. At float64, this is 57GB+ RAM.
- **Fitting encoders on the full dataset:** Fitting OneHotEncoder on all 46K rows before splitting means post-2000 nakshatra distributions influence the fit — leakage.
- **Fitting RandomUnderSampler before split:** imbalanced-learn's RandomUnderSampler must be called only on the pre-2000 slice. If called on the full DataFrame, it will undersample test rows.
- **Using pandas `get_dummies()` for nakshatra encoding:** `get_dummies()` has no `handle_unknown` concept — if a test row has a nakshatra name not seen in training (e.g., due to column set differences), the transform silently misaligns columns.
- **Storing feature matrix as CSV:** With 8.5M test rows and 836 columns, CSV would be ~7GB uncompressed. Use parquet.
- **Using random_state only in some downsample calls:** The seeded numpy RNG (`np.random.default_rng(42)`) must be passed consistently across all chunks to ensure the full matrix is deterministic. Using `random_state=42` in `pandas.DataFrame.sample()` is fine but only reproducible within a single call — use the same seed for all calls.

---

## Column Inventory: ephemeris.csv (469 columns)

Confirmed via column audit of `data/raw/ephemeris.csv`:

| Group | Count | Column Pattern | Disposition |
|-------|-------|----------------|-------------|
| `date` | 1 | `date` | Keep as index |
| Planetary longitude | 13 | `{p}_lon` | DROP raw; ADD `{p}_lon_sin`, `{p}_lon_cos` |
| Zodiac sign number | 13 | `{p}_sign_num` | DROP raw; ADD `{p}_sign_num_sin`, `{p}_sign_num_cos` |
| Zodiac sign name | 13 | `{p}_sign` | DROP (same info as sign_num; text string) |
| Retrograde flag | 13 | `{p}_retro` | KEEP as int (0/1); already bool |
| Nakshatra number | 13 | `{p}_nakshatra_num` | DROP raw; ADD `{p}_nakshatra_num_sin`, `{p}_nakshatra_num_cos` |
| Nakshatra name | 13 | `{p}_nakshatra` | DROP raw string; ADD 27 one-hot cols per planet |
| Aspect booleans | 390 | `{p1}_{p2}_{aspect}` | KEEP as int (0/1) |

**House placement columns: ABSENT.** ephemeris.py does not compute any house system. The columns `{p}_house` referenced in FEAT-01 do not exist in ephemeris.csv. House placement is architecturally inapplicable for a global model (house systems require a specific geographic location). This requirement detail in FEAT-01 is satisfied by the geographic grid cell columns instead.

### Encoded Column Count
| Group | Raw Cols | Encoded Cols | Delta |
|-------|----------|-------------|-------|
| Planetary lon (sin/cos) | 13 dropped | 26 added | +13 |
| Sign num (sin/cos) | 13 dropped | 26 added | +13 |
| Sign name (text) | 13 dropped | 0 added | -13 |
| Retro flags | 13 kept | 13 kept | 0 |
| Nakshatra num (sin/cos) | 13 dropped | 26 added | +13 |
| Nakshatra name (one-hot 27) | 13 dropped | 351 added (13x27) | +338 |
| Aspect booleans | 390 kept | 390 kept | 0 |
| **Total feature cols** | **469** | **832** | **+363** |

Plus identifier/target columns: `date` (index), `grid_lat`, `grid_lon`, `country`, `EQIndicator` = 4 non-feature columns.

**Total columns in final matrix: ~836** (not ~265 as originally estimated). The ~265 number from the Archive reflects the smaller original dataset with only major planets and a different encoding. The current matrix is substantially larger due to full 13-planet nakshatra one-hot expansion (351 cols) and 390 aspect booleans.

---

## Archive Notebook Audit: Features NOT in ephemeris.csv

The Archive notebooks (specifically `Full Pipeline 10102019 TSN.ipynb`) reveal these feature groups absent from the current ephemeris output:

| Feature | Archive Name | Compute Method | Include in Phase 2? |
|---------|-------------|----------------|---------------------|
| Tithi (moon phase bracket) | `thithi` | `floor((moon_lon - sun_lon) % 360 / 12)` → 30 categories (SP1-SP15, KP1-KP15) | **YES** — computable from existing columns; adds 1 categorical (30 cat → 30 one-hot or sin/cos of index) |
| Nakshatra pada (subdivision) | `pada` | `floor(nakshatra_remainder * 3/10) + 1` → 1-4 | **YES** — computable from moon nakshatra position; adds 1 column per planet (4-level) |
| Star element classification | `star element` | lookup: nakshatra_name → Vayu/Agni/Indra/Varuna | **OPTIONAL** — derivative of nakshatra_name; adds no new information if nakshatra is already one-hot encoded |
| Planetary house aspects (HA) | `Mars:HA:6` etc. | `(sign_num + n) % 12` → sign 6 houses forward | **OPTIONAL** — derived from sign_num; already captured if sign_num encoded; skip for Phase 2 |
| Ascendant house/degree | `AscendingHouse`, `AscHouseDeg` | Requires location → Placidus houses | **NOT APPLICABLE** — global model has no single location |
| Sign modality/polarity | `astrologymatrix` | Lookup: sign → +/-, Cardinal/Fixed/Mutable, element | **OPTIONAL** — fully derivative of sign; skip |
| 13x13 aspect matrix (continuous) | `{p1}{p2}aspect` | Continuous aspect angle value (not binary) | **SKIP** — current implementation already has binary 5-type aspects (390 cols); continuous adds redundancy |

**Recommendation:** Include **tithi** as a derived feature (computable from existing sun_lon/moon_lon). Skip all other archive-only features — they are either inapplicable (houses), fully derivative (star element, modality), or already well-covered (continuous aspect matrix vs binary aspect matrix).

**Tithi computation:**
```python
def compute_tithi(sun_lon: float, moon_lon: float) -> tuple[int, str]:
    """Compute Vedic tithi (lunar day, 1-30) from tropical longitudes.

    SP1-SP15 = Shukla Paksha (waxing) 1-15
    KP1-KP14 + NM = Krishna Paksha (waning) 1-15 (NM = New Moon, FM = Full Moon)
    """
    TITHIS = (
        ['SP1','SP2','SP3','SP4','SP5','SP6','SP7','SP8','SP9','SP10',
         'SP11','SP12','SP13','SP14','FM',
         'KP1','KP2','KP3','KP4','KP5','KP6','KP7','KP8','KP9','KP10',
         'KP11','KP12','KP13','KP14','NM']
    )
    diff = (moon_lon - sun_lon) % 360
    tithi_idx = int(diff / 12)
    return tithi_idx, TITHIS[tithi_idx]
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Categorical encoding with unknown handling | Custom dict-based one-hot | `sklearn.preprocessing.OneHotEncoder(handle_unknown='ignore')` | Handles unseen categories at inference (2026 dates), saves/loads with joblib for Phase 3 |
| Downsampling to ratio | Custom index masking | `pandas.DataFrame.sample(n=..., random_state=42)` | Simpler than imbalanced-learn for this use case; no fitting needed; deterministic with seed |
| Parquet chunked writing | Custom binary format | `pandas.to_parquet()` + `pyarrow` | Standard format; Phase 3 reads with `pd.read_parquet()` |
| Sin/cos encoding | Custom trig wrapper | 2-line numpy: `np.sin(x * 2*np.pi/period)` | Trivial; no library needed |
| Date normalization (ISO 8601 to date) | String slicing | `pd.to_datetime(df['time']).dt.date` or `.dt.normalize()` | Handles timezone 'Z' suffix correctly via pandas |

**Key insight:** The heavy dependencies (sklearn, imbalanced-learn) are already installed but most of Phase 2 is pure pandas + numpy operations. Avoid overengineering with sklearn Pipeline — this phase produces a static artifact (the CSV/parquet), not a fitted transformer chain. Save the OneHotEncoder fit separately for Phase 3 reuse.

---

## Common Pitfalls

### Pitfall 1: Materializing the Full Cross-Join in RAM

**What goes wrong:** `pd.merge(ephemeris_df, active_cells_df, how='cross')` on 46,022 rows x 901 cells = 41.4M rows. At float64, this allocates 57+ GB of RAM and crashes.

**Why it happens:** The cross-join pattern is natural but ignores scale.

**How to avoid:** Outer loop over date chunks (annual or monthly). For each chunk, use `np.repeat` + `np.tile` to broadcast ephemeris rows to cells, then join EQIndicator.

**Warning signs:** Script starts using swap space / memory pressure within seconds of the cross-join call.

### Pitfall 2: Applying Downsampling Before Split

**What goes wrong:** If `pandas.sample()` is called on the full 41M-row matrix (pre and post 2000 combined) before the temporal split, the sampling removes both training and test rows — corrupting the test set.

**Why it happens:** Natural tendency to downsample the full dataset, then split.

**How to avoid:** Split into pre-2000 and post-2000 chunks first. Downsample only the pre-2000 chunk's negatives. Never touch post-2000 rows.

**Warning signs:** `min(test_df['date'])` < 2000-01-01 after downsampling.

### Pitfall 3: Fitting OneHotEncoder on the Full Dataset (Leakage)

**What goes wrong:** Fitting `OneHotEncoder` on all 46,022 dates before splitting means the encoder "sees" post-2000 category frequencies during fitting — temporal leakage.

**Why it happens:** Standard ML tutorials show `encoder.fit(X)` on the full dataset.

**How to avoid:** Filter to pre-2000 dates first, then `encoder.fit(pre2000_df[nakshatra_cols])`. This makes no practical difference for nakshatra names (all 27 nakshatras cycle within any decade) but is required for correctness and assertion compliance.

**Warning signs:** Encoder is fit after the chunked loop completes (when all data is assembled), rather than during the pre-2000 chunk.

### Pitfall 4: place Field Parsing Edge Cases

**What goes wrong:** The USGS `place` field contains entries like `"Bismarck Sea"`, `"Near the coast of Venezuela"`, `"Santa Cruz Islands"` — no comma means the last-token parser returns the full string as the country label. This is acceptable behavior but must be consistent.

**Why it happens:** The `place` field is free text entered by USGS reviewers, not a structured geocode.

**How to avoid:** The `extract_country()` function above handles no-comma entries by returning the full string. Test with the known edge cases: `"Bismarck Sea"` should return `"Bismarck Sea"` (not crash). Also handle `None`/`NaN` (common in early catalog rows).

**Warning signs:** `KeyError` or `AttributeError` when processing rows with null `place`.

### Pitfall 5: Grid Cell Count Is Much Larger Than Expected

**What goes wrong:** CONTEXT.md estimates "~200–400 active cells" but the actual count is **901 all-time** (839 pre-2000). Any code that pre-allocates arrays sized for 300 cells will be undersized.

**Why it happens:** The original estimate was based on intuition about seismically active zones; the actual USGS catalog with M5.5+ since 1900 covers a much larger area.

**How to avoid:** Compute `active_cells` dynamically from the USGS data at runtime — never hardcode the count. Log the count at startup.

**Warning signs:** `active_cells` has exactly 300 members (hardcoded) rather than being derived from data.

### Pitfall 6: Boolean/String columns Preventing Parquet Write

**What goes wrong:** `ephemeris.csv` contains Python `bool` (True/False) for `*_retro` and string categories for `*_sign`, `*_nakshatra`. After encoding, retro columns should be int (0/1) and string columns should be dropped. If a string column survives into the parquet write, pyarrow writes it fine, but scikit-learn will reject it later.

**How to avoid:** After all encoding, assert `df.select_dtypes(include='object').columns.tolist() == []` before writing — no object-dtype columns should remain except `country` which is a categorical string (encode separately or keep as category dtype).

**Warning signs:** `ValueError: could not convert string to float` in Phase 3 during model fitting (exact error from Archive notebook cell-91).

### Pitfall 7: `random_state=42` in `pandas.sample()` Is Not Globally Reproducible Across Chunks

**What goes wrong:** Calling `df.sample(n=N, random_state=42)` in a loop produces different results depending on the order of chunks and what has been sampled before — the state resets per call.

**Why it happens:** `random_state=42` in pandas creates a new RandomState each call, not a continuing RNG.

**How to avoid:** For chunked downsampling, either (a) collect all pre-2000 data, then do one final downsample call (if RAM allows — ~32M rows before downsample is too much), or (b) use a global `np.random.default_rng(42)` and pass `.integers()` derived seeds to each chunk's sample call. The simplest approach: build the EQ index first (23,971 positive rows), then sample 239,710 negatives from the complete pre-2000 negative pool in one call.

---

## Scale Strategy: Recommended Build Order

Given the scale constraints, the recommended build strategy is:

```
1. Load ephemeris.csv into memory as date-indexed DataFrame (46022 x 469 = ~170MB float64)
   - Apply all encoding transformations in-place (produces ~832 feature columns)
   - Drop raw columns (lon, sign_num, sign_name, nakshatra_name, nakshatra_num raw)
   - Result: ephemeris_encoded_df (46022 x 832, ~300MB mixed types)

2. Load usgs_earthquakes.csv, compute grid_lat/grid_lon/date, extract country
   - Build eq_index: pd.Series indexed by (date, grid_lat, grid_lon) with value=1

3. Compute active_cells: set of (grid_lat, grid_lon) from all USGS rows (result: 901 cells)
   - Build active_cells_df: DataFrame with grid_lat, grid_lon columns (901 rows)
   - Build country_map: dict (grid_lat, grid_lon) -> most_common_country for that cell

4. Build pre-2000 full matrix (no downsample yet):
   - For each date in 1900-1999: broadcast ephemeris row to 901 cells
   - Assign EQIndicator from eq_index
   - Result: pre2000_full (36,524 days x 901 cells = ~32.9M rows) — TOO LARGE for RAM

   Better: Use pandas merge approach with pre-2000 ephemeris slice:
   - pre2000_ephe = ephemeris_encoded_df[:'1999-12-31']  (36,524 rows)
   - Merge with active_cells_df using key=1 (cross-join via temporary key column)
   - pd.merge approach: add col=1 to both, merge on col, drop col
   - This cross-join: 36,524 x 901 = 32.9M rows x 832 cols = ~55GB RAM — still too much

   FINAL APPROACH: Chunked year-by-year
   - Each year: 365 x 901 = 328,965 rows x 832 cols ~ 550MB (manageable)
   - Collect pre-2000 positives and all negatives across years
   - Apply final 10:1 downsample on complete pre-2000 pool using one sample() call

5. Build post-2000 matrix in annual chunks, append to parquet directly

6. Validate and save manifest
```

**Practical chunked approach with memory safety:**
```python
pre2000_chunks = []
for year in range(1900, 2000):
    year_df = build_year_chunk(year, ephemeris_encoded_df, active_cells, eq_index)
    pre2000_chunks.append(year_df)

pre2000_full = pd.concat(pre2000_chunks, ignore_index=True)
# pre2000_full is ~32.9M rows — may be feasible at ~2GB with uint8 for booleans
# If OOM: do per-year downsampling at 10:1 per year chunk
positives = pre2000_full[pre2000_full['EQIndicator'] == 1]   # ~23,971 rows
negatives = pre2000_full[pre2000_full['EQIndicator'] == 0]
train_neg = negatives.sample(n=len(positives)*10, random_state=42)
train_df = pd.concat([positives, train_neg]).sort_values('date').reset_index(drop=True)
```

**For the post-2000 test set (8.5M rows):** Write annual chunks directly to parquet, never holding more than one year in memory. pyarrow supports appending to parquet with `write_to_dataset`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0 (installed as dev dependency) |
| Config file | `pyproject.toml` (no `[tool.pytest]` section yet — no config file needed) |
| Quick run command | `pytest tests/test_engineering.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEAT-01 | Feature matrix contains planetary degrees, retrograde, aspects, nakshatras | unit | `pytest tests/test_engineering.py::TestColumnInventory -x` | Wave 0 |
| FEAT-01 | No raw `*_lon`, `*_sign_num`, `*_nakshatra_name` string columns in final matrix | unit | `pytest tests/test_engineering.py::TestNoRawColumns -x` | Wave 0 |
| FEAT-02 | All cyclical features have sin/cos pairs, none have raw integer columns | unit | `pytest tests/test_engineering.py::TestCyclicalEncoding -x` | Wave 0 |
| FEAT-03 | max(train.date) < 2000-01-01 AND min(test.date) >= 2000-01-01 | unit | `pytest tests/test_engineering.py::TestTemporalSplit -x` | Wave 0 |
| FEAT-03 | OneHotEncoder fit only on pre-2000 rows | unit | `pytest tests/test_engineering.py::TestEncoderFitScope -x` | Wave 0 |
| FEAT-04 | EQIndicator = 1 for known M5.5+ event dates/cells, 0 otherwise | unit | `pytest tests/test_engineering.py::TestEQIndicator -x` | Wave 0 |
| FEAT-04 | Multiple events in same cell/date collapse to EQIndicator=1 | unit | `pytest tests/test_engineering.py::TestEQIndicatorCollapse -x` | Wave 0 |
| FEAT-05 | grid_lat, grid_lon columns present with correct floor-division values | unit | `pytest tests/test_engineering.py::TestGridCells -x` | Wave 0 |
| FEAT-05 | country column present, derived from last comma-delimited place token | unit | `pytest tests/test_engineering.py::TestCountryParsing -x` | Wave 0 |
| FEAT-03 | Downsampling applied only to pre-2000 rows; test rows unmodified | integration | `pytest tests/test_engineering.py::TestDownsamplingScope -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engineering.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engineering.py` — all Phase 2 test cases (file does not yet exist)
- [ ] `pipeline/features/__init__.py` — make features a package
- [ ] `pipeline/features/engineering.py` — main module under test
- [ ] `data/processed/` directory — must be created by the script (or Wave 0 test setup)
- [ ] `pyarrow` install: `uv add pyarrow` — required for `pd.to_parquet()`

---

## Code Examples

Verified patterns from the existing codebase and standard library docs:

### Date normalization: USGS time column to date
```python
# Source: usgs.py pattern (established in Phase 1)
# USGS 'time' column: '1900-01-05T19:00:00.000Z'
usgs_df['date'] = pd.to_datetime(usgs_df['time']).dt.normalize().dt.date
# Result: datetime.date(1900, 1, 5) — timezone 'Z' handled by pandas
```

### Grid cell floor computation
```python
import numpy as np
# Source: CONTEXT.md decision, verified with numpy floor behavior
usgs_df['grid_lat'] = (np.floor(usgs_df['latitude'] / 5) * 5).astype(int)
usgs_df['grid_lon'] = (np.floor(usgs_df['longitude'] / 5) * 5).astype(int)
# Verified: lat=-3.0 -> grid_lat=-5; lat=35.7 -> grid_lat=35
```

### Cross-join a single ephemeris row to N cells (chunked broadcast)
```python
import numpy as np
import pandas as pd

def broadcast_to_cells(ephe_row: pd.Series, active_cells: list[tuple]) -> pd.DataFrame:
    """Broadcast a single ephemeris row to all active grid cells."""
    n = len(active_cells)
    # Repeat the row n times
    df = pd.DataFrame([ephe_row.values] * n, columns=ephe_row.index)
    cell_arr = np.array(active_cells)
    df['grid_lat'] = cell_arr[:, 0]
    df['grid_lon'] = cell_arr[:, 1]
    return df
```

### OneHotEncoder for nakshatra names (temporal-split-safe)
```python
from sklearn.preprocessing import OneHotEncoder
import numpy as np

# Fit on pre-2000 only
NAKSHATRA_COLS = [f'{p}_nakshatra' for p in PLANETS]  # 13 columns
encoder = OneHotEncoder(
    handle_unknown='ignore',  # post-2000 unknowns -> zero vector
    sparse_output=False,
    dtype=np.uint8,  # saves memory vs float64
)
encoder.fit(pre2000_df[NAKSHATRA_COLS])

# Column names for the output
ohe_feature_names = encoder.get_feature_names_out(NAKSHATRA_COLS)
# e.g. ['sun_nakshatra_Ashwini', 'sun_nakshatra_Bharani', ..., 'node_nakshatra_Revati']
# Total: 13 planets x 27 nakshatras = 351 columns
```

### Writing parquet in chunks (pyarrow)
```python
import pyarrow as pa
import pyarrow.parquet as pq

def write_chunk_to_parquet(df: pd.DataFrame, path: str, schema=None):
    """Append a DataFrame chunk to a parquet file.

    First call creates the file; subsequent calls append.
    """
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    if not Path(path).exists():
        writer = pq.ParquetWriter(path, table.schema, compression='snappy')
    else:
        writer = pq.ParquetWriter(path, table.schema, compression='snappy')
    writer.write_table(table)
    writer.close()
```

**Note:** The simpler pattern for chunked writing is to collect all chunks in memory and write once with `df.to_parquet(path, engine='pyarrow', compression='snappy')`. For the training set (~263K rows), this is fine. For the test set (8.5M rows), use `pq.ParquetWriter` in append mode or write per-year files and merge in Phase 3.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas `get_dummies()` for one-hot | `sklearn.preprocessing.OneHotEncoder` with `handle_unknown='ignore'` | sklearn 0.20+ | Handles unseen categories; saves/loads with joblib; required for inference |
| pandas 1.x `append()` (deprecated) | `pd.concat([df1, df2])` | pandas 2.0 | `DataFrame.append()` removed in pandas 2.0; use concat |
| `sparse=True` in OneHotEncoder | `sparse_output=False` | sklearn 1.2+ | Parameter renamed from `sparse` to `sparse_output` in sklearn 1.2 |
| pandas `DataFrame.sample(frac=)` for downsample | `pandas.DataFrame.sample(n=..., random_state=42)` | — | `n=` (absolute count) is more deterministic for 10:1 ratio than `frac=` |
| CSV for large feature matrices | Parquet (pyarrow, snappy compression) | pandas 1.0+ | 10-20x compression on boolean-heavy data; faster read/write; preserves dtypes |

**Deprecated/outdated:**
- `pd.DataFrame.append()`: Removed in pandas 2.0. Use `pd.concat()`.
- `OneHotEncoder(sparse=True)`: Renamed to `sparse_output=True` in sklearn 1.2. The installed version is 1.8.0 — use `sparse_output=False`.
- `imbalanced-learn.RandomUnderSampler` with `sampling_strategy='majority'`: Works but more complex than needed for a simple 10:1 ratio; `pandas.sample()` is sufficient.

---

## Open Questions

1. **Test set memory: build fully in RAM or chunked write?**
   - What we know: 901 cells x ~9,496 test days = ~8.5M rows. At mixed uint8/float (avg 2 bytes), ~14GB in RAM.
   - What's unclear: Is 14GB available on the target machine? If not, must chunk-write.
   - Recommendation: Assume chunk-write is required. Build and write one year at a time for the test set. Phase 3 reads with `pd.read_parquet()` with column selection or `chunksize` via pyarrow filters.

2. **Single file vs train/test split files?**
   - What we know: The roadmap says `feature_matrix.csv` (one file). But storing 8.5M + 263K rows in one file is awkward for memory.
   - What's unclear: Does Phase 3 expect one file or two?
   - Recommendation: Write two files: `feature_matrix_train.parquet` and `feature_matrix_test.parquet`. Save a `feature_columns.json` manifest for Phase 3 to reference column names without loading the data.

3. **Tithi encoding: categorical one-hot (30 cols) or numeric sin/cos (2 cols)?**
   - What we know: Tithi is periodic (30 tithis per lunar cycle). Sin/cos (2 cols) is more compact; one-hot (30 cols) is more interpretable for the archive compatibility.
   - Recommendation: Use sin/cos (2 cols) for tithi index (0-29) with period=30. Consistent with FEAT-02 cyclical encoding principle.

4. **Active cells: discover from full dataset or pre-2000 only?**
   - CONTEXT.md says: "only cells with at least 1 M5.5+ event in 1900–2026" — this uses the full dataset.
   - This is a lookup (no statistical fit), not leakage. Pre-computing active cells from the full dataset is correct.
   - Confirmed: The assertion in CONTEXT.md explicitly permits this: "Grid cell discovery... uses the full dataset but is purely a lookup — no leakage."

---

## Sources

### Primary (HIGH confidence)
- Direct audit of `data/raw/ephemeris.csv` — column inventory (469 cols, confirmed groups)
- Direct audit of `data/raw/usgs_earthquakes.csv` — 39,514 rows, place field samples, grid cell computation
- `pipeline/data/ephemeris.py` — PLANETS dict (13 planets), NAKSHATRAS list (27), column naming conventions
- `pyproject.toml` — installed library versions (pandas 3.0.1, numpy 2.4.3, sklearn 1.8.0, imbalanced-learn 0.14.1, xgboost 3.2.0)

### Secondary (MEDIUM confidence)
- `Archive/Full Pipeline 10102019 TSN.ipynb` — original feature structure audit; confirmed tithi, pada, house aspects, star element features present in archive; confirmed 246-column original structure
- pandas 3.0 documentation: `DataFrame.sample()`, `pd.concat()`, `to_parquet()` API stable
- scikit-learn 1.8.0: `OneHotEncoder(sparse_output=False, handle_unknown='ignore')` parameter naming confirmed from installed version

### Tertiary (LOW confidence — flag for validation)
- pyarrow memory/compression estimates: 10-20x compression on boolean-heavy parquet is from community knowledge; actual compression ratio depends on data entropy (aspect booleans are sparse -> high compression likely)
- Test set size estimate (8.5M rows): based on 901 cells x 9,496 days from 2000-01-01 to 2026-03-15; actual test window end date (2026-12-31 per roadmap) gives 9,861 days -> ~8.9M rows

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed via .venv inspection; versions exact
- Column inventory: HIGH — confirmed by reading actual CSV header
- Architecture patterns: HIGH — chunked pattern derived from confirmed row counts
- Scale estimates: HIGH — computed from actual USGS data (901 cells, 23,971 positives)
- Archive audit: MEDIUM — Archive notebook read directly; column counts from cell outputs
- Pitfalls: MEDIUM — based on code patterns and known pandas/sklearn breaking changes

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable libraries; data is static)
