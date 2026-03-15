"""
pipeline/features/engineering.py

Feature engineering for the Earthquake Astrology project (Phase 2).

Provides:
  - Grid cell helpers (compute_grid_coords, build_active_cells)
  - Country extraction from USGS place strings (extract_country)
  - EQ index construction (build_eq_index)
  - Ephemeris encoding with cyclic transforms (encode_ephemeris, encode_cyclic)
  - Tithi computation (compute_tithi)
  - Nakshatra encoder (fit_nakshatra_encoder)
  - Temporal leakage guard (assert_no_temporal_leakage)
  - Negative downsampling (downsample_negatives)

All functions raise NotImplementedError until Wave 1 / Wave 2 tasks implement them.
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


def extract_country(place) -> str:
    """Extract country from a USGS place string.

    Rules:
        - If place is None, NaN, or empty string → return "Unknown"
        - If place contains a comma → return the last token after the final comma (stripped)
        - Otherwise → return place as-is (e.g. "Bismarck Sea")
    """
    if place is None or (isinstance(place, float) and np.isnan(place)) or str(place).strip() == "":
        return "Unknown"
    parts = str(place).split(",")
    return parts[-1].strip()


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
    """
    df = usgs_df.copy()
    # Use dt.date to get datetime.date objects (not Timestamps) for consistent indexing
    df["date"] = pd.to_datetime(df["time"]).dt.date
    df["grid_lat"] = (np.floor(df["latitude"].to_numpy() / 5) * 5).astype(int).tolist()
    df["grid_lon"] = (np.floor(df["longitude"].to_numpy() / 5) * 5).astype(int).tolist()
    df = df.drop_duplicates(subset=["date", "grid_lat", "grid_lon"])
    # Use pd.Index with dtype=object to preserve datetime.date type (not coerce to Timestamp)
    index = pd.MultiIndex.from_arrays(
        [
            pd.Index(df["date"].tolist(), dtype=object),
            pd.Index(df["grid_lat"].tolist()),
            pd.Index(df["grid_lon"].tolist()),
        ],
        names=["date", "grid_lat", "grid_lon"],
    )
    return pd.Series(1, index=index, name="EQIndicator")


def build_country_map(usgs_df: pd.DataFrame) -> dict[tuple[int, int], str]:
    """Build a mapping from (grid_lat, grid_lon) cells to the most common country label.

    Args:
        usgs_df: DataFrame with 'latitude', 'longitude', and 'place' columns.

    Returns:
        Dict mapping (grid_lat, grid_lon) -> most common country string.
    """
    df = usgs_df.copy()
    df["grid_lat"] = (np.floor(df["latitude"].to_numpy() / 5) * 5).astype(int).tolist()
    df["grid_lon"] = (np.floor(df["longitude"].to_numpy() / 5) * 5).astype(int).tolist()
    df["country"] = df["place"].apply(extract_country)
    country_map = (
        df.groupby(["grid_lat", "grid_lon"])["country"]
        .agg(lambda x: x.value_counts().index[0])
        .to_dict()
    )
    # Convert numpy int keys to Python int tuples
    return {(int(k[0]), int(k[1])): v for k, v in country_map.items()}


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

    Raises:
        NotImplementedError: Until Wave 1 implements this function.
    """
    raise NotImplementedError("encode_cyclic not yet implemented (Wave 1)")


def compute_tithi(sun_lon: float, moon_lon: float) -> tuple[int, str]:
    """Compute the Vedic lunar day (tithi) from sun and moon longitudes.

    Tithi = floor((moon_lon - sun_lon) % 360 / 12), values 0-29.

    Args:
        sun_lon: Sun tropical longitude (degrees 0-360).
        moon_lon: Moon tropical longitude (degrees 0-360).

    Returns:
        Tuple of (tithi_num 0-29, tithi_name str).

    Raises:
        NotImplementedError: Until Wave 1 implements this function.
    """
    raise NotImplementedError("compute_tithi not yet implemented (Wave 1)")


def encode_ephemeris(ephe_df: pd.DataFrame) -> pd.DataFrame:
    """Encode raw ephemeris DataFrame into ML-ready cyclic and binary features.

    Transformations applied per planet p in PLANETS:
        - {p}_lon      → {p}_lon_sin, {p}_lon_cos  (period=360)
        - {p}_sign_num → {p}_sign_num_sin, {p}_sign_num_cos  (period=12)
        - {p}_retro    → {p}_retro  (boolean kept as-is, cast to int)
        - {p}_nakshatra_num → {p}_nakshatra_num_sin, {p}_nakshatra_num_cos  (period=27)

    Additional:
        - tithi_sin, tithi_cos from compute_tithi(sun_lon, moon_lon)
        - All aspect columns ({p1}_{p2}_{aspect}) are passed through as-is

    Raw columns removed:
        - {p}_lon (raw float)
        - {p}_sign_num (raw int)
        - {p}_sign (text)
        - {p}_nakshatra (text)
        - {p}_nakshatra_num (raw int, replaced by sin/cos)

    Args:
        ephe_df: Raw ephemeris DataFrame from pipeline/data/ephemeris.py.

    Returns:
        Encoded DataFrame with only cyclic, binary, and aspect columns.

    Raises:
        NotImplementedError: Until Wave 1 implements this function.
    """
    raise NotImplementedError("encode_ephemeris not yet implemented (Wave 1)")


# ---------------------------------------------------------------------------
# Nakshatra encoder
# ---------------------------------------------------------------------------


def fit_nakshatra_encoder(pre2000_df: pd.DataFrame) -> object:
    """Fit a OneHotEncoder on nakshatra columns using only pre-2000 training data.

    Encoder is fit on the closed vocabulary of 27 nakshatras seen in training data.
    At transform time, unknown categories (post-2000 data) produce a zero vector
    (handle_unknown='ignore').

    Args:
        pre2000_df: Ephemeris DataFrame restricted to dates before 2000-01-01.

    Returns:
        Fitted sklearn OneHotEncoder instance.

    Raises:
        NotImplementedError: Until Wave 2 implements this function.
    """
    raise NotImplementedError("fit_nakshatra_encoder not yet implemented (Wave 2)")


# ---------------------------------------------------------------------------
# Temporal leakage guard
# ---------------------------------------------------------------------------


def assert_no_temporal_leakage(train_dates, test_dates) -> None:
    """Assert that no test date appears in the training set.

    Args:
        train_dates: Iterable of dates in the training split.
        test_dates: Iterable of dates in the test split.

    Raises:
        AssertionError: If any test date is present in train_dates.
        NotImplementedError: Until Wave 2 implements this function.
    """
    raise NotImplementedError("assert_no_temporal_leakage not yet implemented (Wave 2)")


# ---------------------------------------------------------------------------
# Negative downsampling
# ---------------------------------------------------------------------------


def downsample_negatives(
    df: pd.DataFrame, ratio: int, random_state: int
) -> pd.DataFrame:
    """Downsample negative (EQIndicator=0) rows to achieve target positive:negative ratio.

    All positive rows are preserved. Negatives are randomly sampled without replacement
    to yield len(positives) * ratio negative rows.

    Args:
        df: DataFrame with 'EQIndicator' column (1=positive, 0=negative).
        ratio: Target number of negatives per positive (e.g. 10 → 10:1).
        random_state: Random seed for reproducibility.

    Returns:
        DataFrame with all positives and downsampled negatives,
        total rows = len(positives) * (ratio + 1).

    Raises:
        NotImplementedError: Until Wave 2 implements this function.
    """
    raise NotImplementedError("downsample_negatives not yet implemented (Wave 2)")
