"""
pipeline/features/engineering.py

Feature engineering for the Earthquake Astrology project (Phase 2).

Provides:
  - Grid cell helpers (compute_grid_coords, build_active_cells)
  - Country extraction from USGS place strings (extract_country)
  - EQ index construction (build_eq_index)
  - Ephemeris encoding with cyclic transforms (encode_ephemeris, encode_cyclic)
  - Tithi computation (compute_tithi)
  - Nakshatra encoder (fit_nakshatra_encoder, apply_nakshatra_encoding)
  - Encoder persistence (save_encoder, load_encoder)
  - Temporal leakage guard (assert_no_temporal_leakage)
  - Negative downsampling (downsample_negatives)
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("pipeline.features.engineering")

# ---------------------------------------------------------------------------
# Constants — replicated from pipeline/data/ephemeris.py to avoid importing
# the swisseph C extension at test time (which requires .se1 files).
# ---------------------------------------------------------------------------

PLANETS = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "chiron",
    "lilith",
    "node",
]

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Tithi names: SP1..SP14, FM (full moon, idx 14), KP1..KP14, NM (new moon, idx 29)
TITHIS = (
    ["SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "SP7",
     "SP8", "SP9", "SP10", "SP11", "SP12", "SP13", "SP14", "FM"]
    + ["KP1", "KP2", "KP3", "KP4", "KP5", "KP6", "KP7",
       "KP8", "KP9", "KP10", "KP11", "KP12", "KP13", "KP14", "NM"]
)

# Nakshatra string column names (one per planet)
NAKSHATRA_COLS = [f"{p}_nakshatra" for p in PLANETS]

# Aspect type suffixes used in ephemeris column naming
_ASPECT_TYPES = {"conjunction", "opposition", "trine", "square", "sextile"}


# ---------------------------------------------------------------------------
# Grid cell helpers
# ---------------------------------------------------------------------------


def compute_grid_coords(lat: float, lon: float) -> tuple[int, int]:
    """Map a (lat, lon) coordinate to the nearest 5-degree grid cell.

    Returns:
        (grid_lat, grid_lon) where grid_lat = floor(lat/5)*5, grid_lon = floor(lon/5)*5.
    """
    grid_lat = int(np.floor(lat / 5) * 5)
    grid_lon = int(np.floor(lon / 5) * 5)
    return (grid_lat, grid_lon)


def build_active_cells(usgs_df: pd.DataFrame) -> set[tuple[int, int]]:
    """Return the set of 5-degree grid cells that contain at least one M5.5+ event.

    Args:
        usgs_df: DataFrame with 'latitude' and 'longitude' columns.

    Returns:
        Set of (grid_lat, grid_lon) tuples.
    """
    grid_lats = (np.floor(usgs_df["latitude"].to_numpy() / 5) * 5).astype(int)
    grid_lons = (np.floor(usgs_df["longitude"].to_numpy() / 5) * 5).astype(int)
    cells = set(zip(grid_lats.tolist(), grid_lons.tolist()))
    logger.info(f"Active cells (all-time): {len(cells)}")
    return cells


# ---------------------------------------------------------------------------
# Country parsing
# ---------------------------------------------------------------------------


def extract_country(place: str | None) -> str:
    """Extract country from a USGS place string.

    Rules:
        - If place is None or empty string → return "Unknown"
        - If place contains a comma → return the last token after the final comma (stripped)
        - Otherwise → return place as-is (e.g. "Bismarck Sea")

    Raises:
        NotImplementedError: Until Wave 1 implements this function.
    """
    raise NotImplementedError("extract_country not yet implemented (Wave 1)")


# ---------------------------------------------------------------------------
# EQ indicator index
# ---------------------------------------------------------------------------


def build_eq_index(usgs_df: pd.DataFrame) -> pd.Series:
    """Build a binary earthquake indicator Series indexed by (date, grid_lat, grid_lon).

    Each unique (date, cell) pair maps to 1, regardless of how many events occurred.

    Args:
        usgs_df: DataFrame with 'time' (datetime-parseable), 'latitude', 'longitude' columns.

    Returns:
        pd.Series with MultiIndex (date, grid_lat, grid_lon) and integer value 1.

    Raises:
        NotImplementedError: Until Wave 1 implements this function.
    """
    raise NotImplementedError("build_eq_index not yet implemented (Wave 1)")


# ---------------------------------------------------------------------------
# Ephemeris encoding
# ---------------------------------------------------------------------------


def encode_cyclic(series: pd.Series, period: float) -> tuple[pd.Series, pd.Series]:
    """Encode a cyclic feature using sin/cos transformation.

    Args:
        series: Numeric Series (e.g. longitude 0-360, sign_num 0-11).
        period: The full period of the cycle (e.g. 360.0 for longitudes, 12.0 for signs).

    Returns:
        Tuple of (sin_series, cos_series).
    """
    radians = series * (2 * np.pi / period)
    return np.sin(radians), np.cos(radians)


def compute_tithi(sun_lon: float, moon_lon: float) -> tuple[int, str]:
    """Compute the Vedic lunar day (tithi) from sun and moon longitudes.

    Tithi = floor((moon_lon - sun_lon) % 360 / 12), values 0-29.

    Args:
        sun_lon: Sun tropical longitude (degrees 0-360).
        moon_lon: Moon tropical longitude (degrees 0-360).

    Returns:
        Tuple of (tithi_num 0-29, tithi_name str).
    """
    diff = (moon_lon - sun_lon) % 360
    tithi_idx = int(diff / 12)
    return tithi_idx, TITHIS[tithi_idx]


def encode_ephemeris(ephe_df: pd.DataFrame) -> pd.DataFrame:
    """Encode raw ephemeris DataFrame into ML-ready cyclic and binary features.

    Transformations applied per planet p in PLANETS:
        - {p}_lon      → {p}_lon_sin, {p}_lon_cos  (period=360)
        - {p}_sign_num → {p}_sign_num_sin, {p}_sign_num_cos  (period=12)
        - {p}_retro    → {p}_retro  (boolean cast to int)
        - {p}_nakshatra_num → {p}_nakshatra_num_sin, {p}_nakshatra_num_cos  (period=27)

    Additional:
        - tithi_sin, tithi_cos derived from sun_lon and moon_lon via compute_tithi
        - All aspect columns ({p1}_{p2}_{aspect}) converted to int (0/1)

    Raw columns removed (only these four groups):
        - {p}_lon (raw float)
        - {p}_sign_num (raw int)
        - {p}_sign (text)
        - {p}_nakshatra_num (raw int, replaced by sin/cos)

    PRESERVED:
        - {p}_nakshatra string columns — NOT dropped here.
          apply_nakshatra_encoding() (Plan 05) reads these and drops them after one-hot encoding.

    Args:
        ephe_df: Raw ephemeris DataFrame from pipeline/data/ephemeris.py.

    Returns:
        Encoded DataFrame with cyclic, binary, aspect columns, and nakshatra name strings.
        Column count: 26 lon sin/cos + 26 sign_num sin/cos + 26 nakshatra_num sin/cos
                      + 13 retro + 390 aspect + 2 tithi + 13 nakshatra strings = 496 + date
    """
    df = ephe_df.copy()

    # Compute tithi sin/cos from sun and moon longitudes (before dropping lon columns)
    sun_lons = df["sun_lon"].astype(float)
    moon_lons = df["moon_lon"].astype(float)

    # Vectorised tithi: diff = (moon - sun) % 360, idx = int(diff / 12)
    diff = (moon_lons - sun_lons) % 360.0
    tithi_idx = (diff / 12.0).astype(int)
    tithi_sin, tithi_cos = encode_cyclic(tithi_idx.astype(float), period=30.0)
    df["tithi_sin"] = tithi_sin.values
    df["tithi_cos"] = tithi_cos.values

    # Per-planet cyclic encoding
    cols_to_drop: list[str] = []
    for p in PLANETS:
        # Longitude (period=360)
        sin_lon, cos_lon = encode_cyclic(df[f"{p}_lon"].astype(float), period=360.0)
        df[f"{p}_lon_sin"] = sin_lon.values
        df[f"{p}_lon_cos"] = cos_lon.values
        cols_to_drop.append(f"{p}_lon")

        # Sign number (period=12)
        sin_sign, cos_sign = encode_cyclic(df[f"{p}_sign_num"].astype(float), period=12.0)
        df[f"{p}_sign_num_sin"] = sin_sign.values
        df[f"{p}_sign_num_cos"] = cos_sign.values
        cols_to_drop.append(f"{p}_sign_num")

        # Nakshatra number (period=27)
        sin_nak, cos_nak = encode_cyclic(df[f"{p}_nakshatra_num"].astype(float), period=27.0)
        df[f"{p}_nakshatra_num_sin"] = sin_nak.values
        df[f"{p}_nakshatra_num_cos"] = cos_nak.values
        cols_to_drop.append(f"{p}_nakshatra_num")

        # Sign text column — drop
        cols_to_drop.append(f"{p}_sign")

        # Retro — cast bool to int
        df[f"{p}_retro"] = df[f"{p}_retro"].astype(int)

        # NOTE: {p}_nakshatra string columns are intentionally NOT dropped here.
        # apply_nakshatra_encoding() (called in Plan 05) reads those columns.

    # Convert aspect bool columns to int (0/1)
    # Aspect columns follow pattern: {p1}_{p2}_{aspect_type}
    for col in df.columns:
        if col.endswith(tuple(_ASPECT_TYPES)):
            df[col] = df[col].astype(int)

    # Drop raw columns
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    return df


# ---------------------------------------------------------------------------
# Nakshatra encoder
# ---------------------------------------------------------------------------


def fit_nakshatra_encoder(pre2000_df: pd.DataFrame):
    """Fit a OneHotEncoder on nakshatra columns using only pre-2000 training data.

    Encoder is fit on the closed vocabulary of 27 nakshatras seen in training data.
    At transform time, unknown categories (post-2000 data) produce a zero vector
    (handle_unknown='ignore').

    Args:
        pre2000_df: Ephemeris DataFrame restricted to dates before 2000-01-01.
                    Must contain {p}_nakshatra string columns for all planets.

    Returns:
        Fitted sklearn OneHotEncoder instance.
    """
    from sklearn.preprocessing import OneHotEncoder

    encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        dtype=np.uint8,
    )
    encoder.fit(pre2000_df[NAKSHATRA_COLS])
    return encoder


def apply_nakshatra_encoding(df: pd.DataFrame, encoder) -> pd.DataFrame:
    """Apply fitted nakshatra one-hot encoding to the DataFrame.

    Transforms the 13 nakshatra name string columns into 351 uint8 one-hot columns
    and drops the original string columns.

    Args:
        df: DataFrame that still contains {p}_nakshatra string columns
            (i.e., the output of encode_ephemeris before this step).
        encoder: Fitted sklearn OneHotEncoder from fit_nakshatra_encoder().

    Returns:
        DataFrame with 351 nakshatra one-hot columns added and original
        nakshatra string columns removed.
    """
    ohe_array = encoder.transform(df[NAKSHATRA_COLS])
    ohe_col_names = encoder.get_feature_names_out(NAKSHATRA_COLS)
    ohe_df = pd.DataFrame(ohe_array, columns=ohe_col_names, index=df.index)

    result = df.drop(columns=NAKSHATRA_COLS)
    result = pd.concat([result, ohe_df], axis=1)
    return result


def save_encoder(encoder, path: str) -> None:
    """Persist a fitted encoder to disk using joblib.

    Args:
        encoder: Fitted sklearn encoder (e.g. OneHotEncoder from fit_nakshatra_encoder).
        path: File path to write (e.g. 'data/processed/nakshatra_encoder.pkl').
    """
    import joblib
    joblib.dump(encoder, path)
    logger.info(f"Encoder saved to {path}")


def load_encoder(path: str):
    """Load a fitted encoder from disk.

    Args:
        path: File path to read (e.g. 'data/processed/nakshatra_encoder.pkl').

    Returns:
        The deserialized encoder object.
    """
    import joblib
    return joblib.load(path)


# ---------------------------------------------------------------------------
# Temporal leakage guard
# ---------------------------------------------------------------------------


def assert_no_temporal_leakage(train_dates, test_dates) -> None:
    """Assert that training data is strictly before 2000-01-01 and test data is >= 2000-01-01.

    The 2000-01-01 split date is the hard temporal boundary for this project:
    train on 1900-1999, test on 2000-2026.

    Args:
        train_dates: Iterable of dates (datetime.date, pd.Timestamp, or str) in the training split.
        test_dates: Iterable of dates in the test split.

    Raises:
        AssertionError: If max(train_dates) >= 2000-01-01 (training data leaks into test era).
        AssertionError: If min(test_dates) < 2000-01-01 (test data contains pre-2000 rows).
    """
    from datetime import date as date_type

    SPLIT = date_type(2000, 1, 1)
    max_train = pd.to_datetime(pd.Series(list(train_dates))).max().date()
    min_test = pd.to_datetime(pd.Series(list(test_dates))).min().date()

    assert max_train < SPLIT, (
        f"Temporal leakage: training set contains rows on/after 2000-01-01. "
        f"max(train.date) = {max_train}"
    )
    assert min_test >= SPLIT, (
        f"Temporal leakage: test set contains rows before 2000-01-01 (pre-train era). "
        f"min(test.date) = {min_test}"
    )


# ---------------------------------------------------------------------------
# Negative downsampling
# ---------------------------------------------------------------------------


def downsample_negatives(
    df: pd.DataFrame, ratio: int = 10, random_state: int = 42
) -> pd.DataFrame:
    """Downsample negative (EQIndicator=0) rows to achieve target positive:negative ratio.

    All positive rows are preserved. Negatives are randomly sampled without replacement
    to yield min(ratio * n_positives, n_negatives) negative rows.

    The caller must ensure df is restricted to the pre-2000 training pool before calling.
    This function does not enforce the temporal boundary itself.

    Args:
        df: DataFrame with 'EQIndicator' column (1=positive, 0=negative).
        ratio: Target number of negatives per positive (e.g. 10 → 10:1). Default 10.
        random_state: Random seed for reproducibility. Default 42.

    Returns:
        DataFrame with all positives and downsampled negatives, reset index.
        Total rows = n_positives + min(ratio * n_positives, n_negatives).

    Raises:
        ValueError: If df does not contain an 'EQIndicator' column.
    """
    if "EQIndicator" not in df.columns:
        raise ValueError(
            "DataFrame must contain an 'EQIndicator' column (1=positive, 0=negative)."
        )

    positives = df[df["EQIndicator"] == 1]
    negatives = df[df["EQIndicator"] == 0]

    n_sample = min(ratio * len(positives), len(negatives))
    negatives_sampled = negatives.sample(n=n_sample, random_state=random_state)

    return pd.concat([positives, negatives_sampled]).reset_index(drop=True)
