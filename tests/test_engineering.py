"""
tests/test_engineering.py

Phase 2 feature engineering test stubs — Wave 0 gate.

All test classes are marked xfail so pytest collects without error.
Wave 1 and Wave 2 tasks will remove xfail markers and implement assertions
as the corresponding functions are completed.

Test naming follows VALIDATION.md exactly:
  FEAT-01 → TestGridCells, TestCountryParsing
  FEAT-02 → TestEQIndicator, TestEQIndicatorCollapse
  FEAT-03 → TestColumnInventory, TestNoRawColumns, TestCyclicalEncoding
  FEAT-04 → TestTemporalSplit, TestEncoderFitScope
  FEAT-05 → TestDownsamplingScope
"""

import math

import pandas as pd
import pytest

from pipeline.features.engineering import (
    assert_no_temporal_leakage,
    build_active_cells,
    build_eq_index,
    compute_grid_coords,
    downsample_negatives,
    encode_ephemeris,
    extract_country,
    fit_nakshatra_encoder,
)


# ---------------------------------------------------------------------------
# FEAT-01: Grid cells
# ---------------------------------------------------------------------------


class TestGridCells:
    """FEAT-01: 5-degree grid cell helpers."""

    def test_compute_grid_coords_basic(self):
        """compute_grid_coords returns (floor(lat/5)*5, floor(lon/5)*5) as ints."""
        # lat=37.5, lon=-122.4 → (35, -125)
        result = compute_grid_coords(37.5, -122.4)
        assert result == (35, -125)
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)

    def test_compute_grid_coords_negative_lat(self):
        """compute_grid_coords handles negative latitudes correctly."""
        # lat=-3.0, lon=100.5 → (-5, 100)
        result = compute_grid_coords(-3.0, 100.5)
        assert result == (-5, 100)
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)

    def test_compute_grid_coords_zero(self):
        """compute_grid_coords handles zero coordinates."""
        result = compute_grid_coords(0.0, 0.0)
        assert result == (0, 0)

    def test_compute_grid_coords_japan(self):
        """compute_grid_coords handles Japan region coords."""
        result = compute_grid_coords(35.7, 139.2)
        assert result == (35, 135)

    def test_build_active_cells_returns_set_of_tuples(self):
        """build_active_cells returns a set of (int, int) tuples."""
        usgs_df = pd.DataFrame(
            {"latitude": [37.5, -3.1], "longitude": [-122.4, 130.2]}
        )
        result = build_active_cells(usgs_df)
        assert isinstance(result, set)
        for cell in result:
            assert isinstance(cell, tuple)
            assert len(cell) == 2
            assert isinstance(cell[0], int)
            assert isinstance(cell[1], int)

    def test_build_active_cells_known_values(self):
        """build_active_cells produces correct cells for known lat/lon pairs."""
        usgs_df = pd.DataFrame(
            {"latitude": [37.5, -3.1], "longitude": [-122.4, 130.2]}
        )
        result = build_active_cells(usgs_df)
        # 37.5/-122.4 → (35, -125); -3.1/130.2 → (-5, 130)
        assert (35, -125) in result
        assert (-5, 130) in result


# ---------------------------------------------------------------------------
# FEAT-01: Country parsing
# ---------------------------------------------------------------------------


class TestCountryParsing:
    """FEAT-01: extract_country from USGS place strings."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_extract_country_standard(self):
        """Comma-separated place returns the last token."""
        assert extract_country("Southern Sumatra, Indonesia") == "Indonesia"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_extract_country_no_comma(self):
        """Place with no comma is returned as-is."""
        assert extract_country("Bismarck Sea") == "Bismarck Sea"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_extract_country_none(self):
        """None input returns 'Unknown'."""
        assert extract_country(None) == "Unknown"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_extract_country_empty_string(self):
        """Empty string returns 'Unknown'."""
        assert extract_country("") == "Unknown"


# ---------------------------------------------------------------------------
# FEAT-02: EQ indicator
# ---------------------------------------------------------------------------


class TestEQIndicator:
    """FEAT-02: build_eq_index returns binary MultiIndex Series."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_build_eq_index_returns_series(self):
        """build_eq_index returns a pd.Series."""
        usgs_df = pd.DataFrame(
            {
                "time": ["2000-01-15"],
                "latitude": [37.5],
                "longitude": [-122.4],
            }
        )
        result = build_eq_index(usgs_df)
        assert isinstance(result, pd.Series)

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_build_eq_index_multiindex(self):
        """Result Series has 3-level MultiIndex: (date, grid_lat, grid_lon)."""
        usgs_df = pd.DataFrame(
            {
                "time": ["2000-01-15"],
                "latitude": [37.5],
                "longitude": [-122.4],
            }
        )
        result = build_eq_index(usgs_df)
        assert isinstance(result.index, pd.MultiIndex)
        assert result.index.names == ["date", "grid_lat", "grid_lon"]

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_build_eq_index_value_is_1(self):
        """Known event date+cell maps to value 1."""
        usgs_df = pd.DataFrame(
            {
                "time": ["2000-01-15"],
                "latitude": [37.5],
                "longitude": [-122.4],
            }
        )
        result = build_eq_index(usgs_df)
        # 2000-01-15 at lat=37.5, lon=-122.4 → grid (35, -125)
        key = (pd.Timestamp("2000-01-15").date(), 35, -125)
        assert result[key] == 1


# ---------------------------------------------------------------------------
# FEAT-02: EQ indicator collapse
# ---------------------------------------------------------------------------


class TestEQIndicatorCollapse:
    """FEAT-02: Multiple events on same date+cell collapse to single EQIndicator=1."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_two_events_same_cell_same_date_collapse(self):
        """Two USGS events on same date in same cell produce a single EQIndicator=1."""
        usgs_df = pd.DataFrame(
            {
                "time": ["2000-01-15", "2000-01-15"],
                "latitude": [37.5, 37.8],    # both map to grid_lat=35
                "longitude": [-122.4, -122.1],  # both map to grid_lon=-125
            }
        )
        result = build_eq_index(usgs_df)
        # Should have only one entry for this date+cell, value=1 (not 2)
        assert result.shape[0] == 1
        assert result.iloc[0] == 1


# ---------------------------------------------------------------------------
# FEAT-03: Column inventory
# ---------------------------------------------------------------------------


class TestColumnInventory:
    """FEAT-03: encode_ephemeris output must contain expected encoded columns."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_encoded_columns_present(self):
        """Output contains _lon_sin/_lon_cos, _sign_num_sin/_cos, _retro, _nakshatra_num_sin/_cos."""
        from pipeline.features.engineering import PLANETS

        # Minimal ephemeris DataFrame — just enough for encode_ephemeris to run
        ephe_df = _make_minimal_ephe_df()

        result = encode_ephemeris(ephe_df)
        cols = set(result.columns)

        for p in PLANETS:
            assert f"{p}_lon_sin" in cols, f"Missing {p}_lon_sin"
            assert f"{p}_lon_cos" in cols, f"Missing {p}_lon_cos"
            assert f"{p}_sign_num_sin" in cols, f"Missing {p}_sign_num_sin"
            assert f"{p}_sign_num_cos" in cols, f"Missing {p}_sign_num_cos"
            assert f"{p}_retro" in cols, f"Missing {p}_retro"
            assert f"{p}_nakshatra_num_sin" in cols, f"Missing {p}_nakshatra_num_sin"
            assert f"{p}_nakshatra_num_cos" in cols, f"Missing {p}_nakshatra_num_cos"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_aspect_columns_present(self):
        """Aspect columns are passed through to the output."""
        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        # At least one aspect column should be present
        aspect_cols = [c for c in result.columns if "_conjunction" in c or "_opposition" in c]
        assert len(aspect_cols) > 0


# ---------------------------------------------------------------------------
# FEAT-03: No raw columns
# ---------------------------------------------------------------------------


class TestNoRawColumns:
    """FEAT-03: encode_ephemeris must drop raw scalar and text columns."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_raw_lon_absent(self):
        """Raw {p}_lon column must not appear in output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_lon" not in result.columns, f"Raw {p}_lon should be removed"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_raw_sign_num_absent(self):
        """Raw {p}_sign_num column must not appear in output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_sign_num" not in result.columns, f"Raw {p}_sign_num should be removed"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_text_sign_absent(self):
        """Text {p}_sign column must not appear in output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_sign" not in result.columns, f"Text {p}_sign should be removed"

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_text_nakshatra_absent(self):
        """Text {p}_nakshatra column must not appear in output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_nakshatra" not in result.columns, f"Text {p}_nakshatra should be removed"


# ---------------------------------------------------------------------------
# FEAT-03: Cyclical encoding correctness
# ---------------------------------------------------------------------------


class TestCyclicalEncoding:
    """FEAT-03: Verify sin/cos encoding produces correct values for known inputs."""

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_sun_lon_zero(self):
        """sun_lon=0.0 → sun_lon_sin==0.0, sun_lon_cos==1.0."""
        ephe_df = _make_minimal_ephe_df(sun_lon=0.0)
        result = encode_ephemeris(ephe_df)
        assert result["sun_lon_sin"].iloc[0] == pytest.approx(0.0, abs=1e-6)
        assert result["sun_lon_cos"].iloc[0] == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_sun_lon_ninety(self):
        """sun_lon=90.0 → sun_lon_sin≈1.0, sun_lon_cos≈0.0."""
        ephe_df = _make_minimal_ephe_df(sun_lon=90.0)
        result = encode_ephemeris(ephe_df)
        assert result["sun_lon_sin"].iloc[0] == pytest.approx(1.0, abs=1e-6)
        assert result["sun_lon_cos"].iloc[0] == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.xfail(reason="not implemented — Wave 1")
    def test_tithi_columns_present(self):
        """tithi_sin and tithi_cos columns are present in encode_ephemeris output."""
        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        assert "tithi_sin" in result.columns
        assert "tithi_cos" in result.columns


# ---------------------------------------------------------------------------
# FEAT-04: Temporal split
# ---------------------------------------------------------------------------


class TestTemporalSplit:
    """FEAT-04: assert_no_temporal_leakage raises on leaking dates."""

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_raises_on_leaking_dates(self):
        """assert_no_temporal_leakage raises AssertionError when dates overlap."""
        train_dates = pd.date_range("1990-01-01", "2000-01-01", freq="D")
        test_dates = pd.date_range("1999-01-01", "2001-01-01", freq="D")  # overlaps!
        with pytest.raises(AssertionError):
            assert_no_temporal_leakage(train_dates, test_dates)

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_passes_on_clean_split(self):
        """assert_no_temporal_leakage does not raise when split is clean."""
        train_dates = pd.date_range("1990-01-01", "1999-12-31", freq="D")
        test_dates = pd.date_range("2000-01-01", "2026-12-31", freq="D")
        # Should NOT raise — clean split
        assert_no_temporal_leakage(train_dates, test_dates)


# ---------------------------------------------------------------------------
# FEAT-04: Encoder fit scope
# ---------------------------------------------------------------------------


class TestEncoderFitScope:
    """FEAT-04: fit_nakshatra_encoder fits on pre-2000 vocabulary only."""

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_fit_returns_encoder(self):
        """fit_nakshatra_encoder returns a fitted sklearn OneHotEncoder."""
        from sklearn.preprocessing import OneHotEncoder

        pre2000_df = _make_minimal_ephe_df()
        encoder = fit_nakshatra_encoder(pre2000_df)
        assert isinstance(encoder, OneHotEncoder)

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_unknown_nakshatra_zero_vector(self):
        """Transforming post-2000 df with unknown nakshatra produces zero vector (no error)."""
        from sklearn.preprocessing import OneHotEncoder

        pre2000_df = _make_minimal_ephe_df()
        encoder = fit_nakshatra_encoder(pre2000_df)

        # Build a DataFrame with an unseen nakshatra string
        unseen_df = _make_minimal_ephe_df()
        # Overwrite all nakshatra columns with an unseen value
        for col in unseen_df.columns:
            if "_nakshatra" in col and "num" not in col:
                unseen_df[col] = "__UNSEEN__"

        # Transform should return zeros, not raise
        nakshatra_cols = [c for c in unseen_df.columns if "_nakshatra" in c and "num" not in c]
        result = encoder.transform(unseen_df[nakshatra_cols])
        assert result.sum() == 0  # all zeros — unknown category handled gracefully


# ---------------------------------------------------------------------------
# FEAT-05: Downsampling scope
# ---------------------------------------------------------------------------


class TestDownsamplingScope:
    """FEAT-05: downsample_negatives preserves all positives and down-samples negatives."""

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_downsample_row_count(self):
        """Applied to pre-2000 chunk: returns len(positives)*11 rows."""
        n_pos = 10
        n_neg = 500
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        expected_rows = n_pos * (10 + 1)  # positives + 10x negatives
        assert len(result) == expected_rows

    @pytest.mark.xfail(reason="not implemented — Wave 2")
    def test_downsample_all_positives_preserved(self):
        """All positive rows are preserved after downsampling."""
        n_pos = 10
        n_neg = 500
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        assert result["EQIndicator"].sum() == n_pos


# ---------------------------------------------------------------------------
# Shared fixture helper
# ---------------------------------------------------------------------------


def _make_minimal_ephe_df(sun_lon: float = 45.0, moon_lon: float = 90.0) -> pd.DataFrame:
    """Build a minimal single-row ephemeris DataFrame for encoding tests.

    Creates all columns that pipeline/data/ephemeris.py would produce:
      {p}_lon, {p}_sign_num, {p}_sign, {p}_retro, {p}_nakshatra_num, {p}_nakshatra
    plus one sample aspect column.
    """
    from pipeline.features.engineering import NAKSHATRAS, PLANETS, SIGN_NAMES

    row: dict = {"date": "2000-01-01"}

    for i, p in enumerate(PLANETS):
        lon = (sun_lon + i * 30.0) % 360.0 if p != "moon" else moon_lon
        sign_num = int(lon / 30) % 12
        nakshatra_num = int(lon / (360.0 / 27)) % 27
        row[f"{p}_lon"] = lon
        row[f"{p}_sign_num"] = sign_num
        row[f"{p}_sign"] = SIGN_NAMES[sign_num]
        row[f"{p}_retro"] = False
        row[f"{p}_nakshatra_num"] = nakshatra_num
        row[f"{p}_nakshatra"] = NAKSHATRAS[nakshatra_num]

    # Add a sample aspect column
    row["sun_moon_conjunction"] = 0

    return pd.DataFrame([row])
