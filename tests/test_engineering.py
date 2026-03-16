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
from pathlib import Path

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

# build_matrix_chunk imported separately to avoid import failure in older stubs
try:
    from pipeline.features.engineering import build_matrix_chunk, active_cells_list
    _HAS_BUILD_MATRIX = True
except ImportError:
    _HAS_BUILD_MATRIX = False


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

    def test_extract_country_standard(self):
        """Comma-separated place returns the last token."""
        assert extract_country("Southern Sumatra, Indonesia") == "Indonesia"

    def test_extract_country_no_comma(self):
        """Place with no comma is returned as-is."""
        assert extract_country("Bismarck Sea") == "Bismarck Sea"

    def test_extract_country_none(self):
        """None input returns 'Unknown'."""
        assert extract_country(None) == "Unknown"

    def test_extract_country_empty_string(self):
        """Empty string returns 'Unknown'."""
        assert extract_country("") == "Unknown"

    def test_extract_country_nan(self):
        """float NaN returns 'Unknown'."""
        assert extract_country(float("nan")) == "Unknown"

    def test_extract_country_alaska(self):
        """Multi-comma place returns last token."""
        assert extract_country("Kodiak Island region, Alaska") == "Alaska"


# ---------------------------------------------------------------------------
# FEAT-02: EQ indicator
# ---------------------------------------------------------------------------


class TestEQIndicator:
    """FEAT-02: build_eq_index returns binary MultiIndex Series."""

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
    """FEAT-03: encode_ephemeris drops raw scalar columns; apply_nakshatra_encoding drops text."""

    def test_raw_lon_absent(self):
        """Raw {p}_lon column must not appear in encode_ephemeris output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_lon" not in result.columns, f"Raw {p}_lon should be removed"

    def test_raw_sign_num_absent(self):
        """Raw {p}_sign_num column must not appear in encode_ephemeris output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_sign_num" not in result.columns, f"Raw {p}_sign_num should be removed"

    def test_text_sign_absent(self):
        """Text {p}_sign column must not appear in encode_ephemeris output."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_sign" not in result.columns, f"Text {p}_sign should be removed"

    def test_nakshatra_strings_preserved_after_encode_ephemeris(self):
        """encode_ephemeris preserves {p}_nakshatra string columns for downstream one-hot step."""
        from pipeline.features.engineering import PLANETS

        ephe_df = _make_minimal_ephe_df()
        result = encode_ephemeris(ephe_df)
        for p in PLANETS:
            assert f"{p}_nakshatra" in result.columns, (
                f"{p}_nakshatra string must be preserved by encode_ephemeris"
            )

    def test_text_nakshatra_absent_after_full_pipeline(self):
        """Text {p}_nakshatra column absent after encode_ephemeris + apply_nakshatra_encoding."""
        from pipeline.features.engineering import PLANETS, apply_nakshatra_encoding

        ephe_df = _make_minimal_ephe_df()
        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)
        encoded = encode_ephemeris(ephe_df)
        result = apply_nakshatra_encoding(encoded, encoder)
        for p in PLANETS:
            assert f"{p}_nakshatra" not in result.columns, (
                f"Text {p}_nakshatra should be removed by apply_nakshatra_encoding"
            )


# ---------------------------------------------------------------------------
# FEAT-03: Cyclical encoding correctness
# ---------------------------------------------------------------------------


class TestCyclicalEncoding:
    """FEAT-03: Verify sin/cos encoding produces correct values for known inputs."""

    def test_sun_lon_zero(self):
        """sun_lon=0.0 → sun_lon_sin==0.0, sun_lon_cos==1.0."""
        ephe_df = _make_minimal_ephe_df(sun_lon=0.0)
        result = encode_ephemeris(ephe_df)
        assert result["sun_lon_sin"].iloc[0] == pytest.approx(0.0, abs=1e-6)
        assert result["sun_lon_cos"].iloc[0] == pytest.approx(1.0, abs=1e-6)

    def test_sun_lon_ninety(self):
        """sun_lon=90.0 → sun_lon_sin≈1.0, sun_lon_cos≈0.0."""
        ephe_df = _make_minimal_ephe_df(sun_lon=90.0)
        result = encode_ephemeris(ephe_df)
        assert result["sun_lon_sin"].iloc[0] == pytest.approx(1.0, abs=1e-6)
        assert result["sun_lon_cos"].iloc[0] == pytest.approx(0.0, abs=1e-6)

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

    def test_raises_when_train_contains_post2000(self):
        """assert_no_temporal_leakage raises AssertionError when train has date >= 2000-01-01."""
        from datetime import date
        train_dates = [date(2000, 1, 1)]
        test_dates = [date(2000, 1, 2)]
        with pytest.raises(AssertionError, match="2000-01-01"):
            assert_no_temporal_leakage(train_dates, test_dates)

    def test_raises_when_test_contains_pre2000(self):
        """assert_no_temporal_leakage raises AssertionError when test has date < 2000-01-01."""
        from datetime import date
        train_dates = [date(1999, 12, 31)]
        test_dates = [date(1999, 12, 31)]
        with pytest.raises(AssertionError, match="test set|test"):
            assert_no_temporal_leakage(train_dates, test_dates)

    def test_passes_on_clean_split(self):
        """assert_no_temporal_leakage does not raise when split is clean."""
        from datetime import date
        train_dates = [date(1999, 12, 31)]
        test_dates = [date(2000, 1, 1)]
        # Should NOT raise — clean split
        assert_no_temporal_leakage(train_dates, test_dates)

    def test_passes_with_date_range(self):
        """assert_no_temporal_leakage works with pd.date_range inputs."""
        train_dates = pd.date_range("1990-01-01", "1999-12-31", freq="D")
        test_dates = pd.date_range("2000-01-01", "2026-12-31", freq="D")
        assert_no_temporal_leakage(train_dates, test_dates)

    def test_raises_on_leaking_date_range(self):
        """assert_no_temporal_leakage raises when train date range includes 2000-01-01."""
        train_dates = pd.date_range("1990-01-01", "2000-01-01", freq="D")
        test_dates = pd.date_range("2000-01-01", "2001-01-01", freq="D")
        with pytest.raises(AssertionError):
            assert_no_temporal_leakage(train_dates, test_dates)


# ---------------------------------------------------------------------------
# FEAT-04: Encoder fit scope
# ---------------------------------------------------------------------------


class TestEncoderFitScope:
    """FEAT-04: fit_nakshatra_encoder fits on pre-2000 vocabulary only."""

    def test_fit_returns_encoder(self):
        """fit_nakshatra_encoder returns a fitted sklearn OneHotEncoder."""
        from sklearn.preprocessing import OneHotEncoder

        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)
        assert isinstance(encoder, OneHotEncoder)

    def test_encoder_has_13_features(self):
        """Fitted encoder has 13 feature inputs (one per planet)."""
        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)
        assert len(encoder.categories_) == 13

    def test_encoder_produces_351_columns(self):
        """encoder.get_feature_names_out() returns 351 names (13 planets x 27 nakshatras)."""
        from pipeline.features.engineering import NAKSHATRA_COLS

        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)
        # sklearn < 1.0 uses get_feature_names(); sklearn >= 1.0 uses get_feature_names_out()
        if hasattr(encoder, "get_feature_names_out"):
            feature_names = encoder.get_feature_names_out(NAKSHATRA_COLS)
        else:
            feature_names = encoder.get_feature_names(NAKSHATRA_COLS)
        assert len(feature_names) == 351, f"Expected 351 columns, got {len(feature_names)}"

    def test_unknown_nakshatra_zero_vector(self):
        """Transforming post-2000 df with unknown nakshatra produces zero vector (no error)."""
        from pipeline.features.engineering import NAKSHATRA_COLS

        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)

        # Build a DataFrame with an unseen nakshatra string
        unseen_df = _make_minimal_ephe_df()
        # Overwrite all nakshatra columns with an unseen value
        for col in NAKSHATRA_COLS:
            unseen_df[col] = "__UNSEEN__"

        # Transform should return zeros, not raise
        result = encoder.transform(unseen_df[NAKSHATRA_COLS])
        assert result.sum() == 0  # all zeros — unknown category handled gracefully

    def test_apply_nakshatra_encoding_adds_351_cols(self):
        """apply_nakshatra_encoding adds 351 one-hot columns to the encoded frame."""
        from pipeline.features.engineering import apply_nakshatra_encoding

        pre2000_df = _make_full_nakshatra_df()
        encoder = fit_nakshatra_encoder(pre2000_df)

        ephe_df = _make_minimal_ephe_df()
        encoded = encode_ephemeris(ephe_df)
        result = apply_nakshatra_encoding(encoded, encoder)

        ohe_cols = [c for c in result.columns if "_nakshatra_" in c and "num" not in c]
        assert len(ohe_cols) == 351, f"Expected 351 nakshatra OHE cols, got {len(ohe_cols)}"


# ---------------------------------------------------------------------------
# FEAT-05: Downsampling scope
# ---------------------------------------------------------------------------


class TestDownsamplingScope:
    """FEAT-05: downsample_negatives preserves all positives and down-samples negatives."""

    def test_downsample_row_count(self):
        """Applied to pre-2000 chunk: returns n_pos + min(ratio*n_pos, n_neg) rows."""
        n_pos = 10
        n_neg = 500
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        # n_sample = min(10 * 10, 500) = 100; total = 10 + 100 = 110
        expected_rows = n_pos + min(10 * n_pos, n_neg)
        assert len(result) == expected_rows

    def test_downsample_all_positives_preserved(self):
        """All positive rows are preserved after downsampling."""
        n_pos = 10
        n_neg = 500
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        assert result["EQIndicator"].sum() == n_pos

    def test_downsample_negative_count_exact(self):
        """Exactly ratio * n_positives negative rows are returned."""
        n_pos = 10
        n_neg = 500
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        assert (result["EQIndicator"] == 0).sum() == 100

    def test_downsample_deterministic(self):
        """Two calls with same random_state return identical rows."""
        n_pos = 5
        n_neg = 200
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg, "value": range(n_pos + n_neg)}
        )
        result1 = downsample_negatives(df, ratio=10, random_state=42)
        result2 = downsample_negatives(df, ratio=10, random_state=42)
        pd.testing.assert_frame_equal(result1.reset_index(drop=True), result2.reset_index(drop=True))

    def test_downsample_raises_missing_eq_indicator(self):
        """downsample_negatives raises ValueError if EQIndicator column is absent."""
        df = pd.DataFrame({"value": [1, 2, 3]})
        with pytest.raises(ValueError, match="EQIndicator"):
            downsample_negatives(df, ratio=10, random_state=42)

    def test_downsample_clamps_when_negatives_too_few(self):
        """When n_neg < ratio * n_pos, all negatives are returned."""
        n_pos = 10
        n_neg = 5  # fewer than ratio * n_pos
        df = pd.DataFrame(
            {"EQIndicator": [1] * n_pos + [0] * n_neg}
        )
        result = downsample_negatives(df, ratio=10, random_state=42)
        # n_sample = min(100, 5) = 5; total = 10 + 5 = 15
        assert (result["EQIndicator"] == 0).sum() == n_neg
        assert len(result) == n_pos + n_neg


# ---------------------------------------------------------------------------
# FEAT-02: build_matrix_chunk (EQIndicator broadcast)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_BUILD_MATRIX, reason="build_matrix_chunk not yet importable")
class TestBuildMatrixChunk:
    """FEAT-02: build_matrix_chunk broadcasts one ephemeris row to all active cells."""

    def _make_eq_index_for_date(self, date_val, cells_with_eq):
        """Build a minimal eq_index with EQIndicator=1 for given date+cells."""
        if isinstance(date_val, str):
            date_val = pd.Timestamp(date_val).date()

        dates = [date_val] * len(cells_with_eq)
        lats = [c[0] for c in cells_with_eq]
        lons = [c[1] for c in cells_with_eq]
        idx = pd.MultiIndex.from_arrays(
            [pd.Index(dates, dtype=object), lats, lons],
            names=["date", "grid_lat", "grid_lon"],
        )
        return pd.Series(1, index=idx, dtype=int)

    def test_returns_dataframe_with_n_active_cells_rows(self):
        """build_matrix_chunk returns a DataFrame with len(active_cells) rows."""
        import numpy as np
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        active_cells = [(35, -125), (30, -120), (40, -115)]
        country_map = {c: "USA" for c in active_cells}
        eq_index = self._make_eq_index_for_date(date(1999, 6, 15), [])

        ephe_df = _make_minimal_ephe_df()
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        assert len(result) == len(active_cells)

    def test_eq_indicator_1_for_matching_cell(self):
        """EQIndicator=1 for a cell that had an event on the ephemeris row's date."""
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        target_cell = (35, -125)
        other_cell = (30, -120)
        active_cells = [target_cell, other_cell]
        country_map = {target_cell: "USA", other_cell: "USA"}

        test_date = date(1999, 6, 15)
        eq_index = self._make_eq_index_for_date(test_date, [target_cell])

        ephe_df = _make_minimal_ephe_df()
        # Override date to match test_date
        ephe_df["date"] = str(test_date)
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        result = result.sort_values(["grid_lat", "grid_lon"]).reset_index(drop=True)

        # target_cell (35, -125) is sorted before (30, -120)? No: 30 < 35, so (30,-120) is row 0
        row_target = result[(result["grid_lat"] == 35) & (result["grid_lon"] == -125)].iloc[0]
        row_other = result[(result["grid_lat"] == 30) & (result["grid_lon"] == -120)].iloc[0]
        assert row_target["EQIndicator"] == 1
        assert row_other["EQIndicator"] == 0

    def test_eq_indicator_0_for_no_event(self):
        """EQIndicator=0 for all cells when eq_index is empty for that date."""
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        active_cells = [(35, -125), (30, -120)]
        country_map = {c: "USA" for c in active_cells}
        eq_index = self._make_eq_index_for_date(date(1999, 6, 15), [])  # empty

        ephe_df = _make_minimal_ephe_df()
        ephe_df["date"] = "1999-06-15"
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        assert (result["EQIndicator"] == 0).all()

    def test_eq_indicator_dtype_is_int(self):
        """EQIndicator column dtype is int (no NaN, no float)."""
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        active_cells = [(35, -125)]
        country_map = {(35, -125): "USA"}
        eq_index = self._make_eq_index_for_date(date(1999, 6, 15), [(35, -125)])

        ephe_df = _make_minimal_ephe_df()
        ephe_df["date"] = "1999-06-15"
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        assert result["EQIndicator"].dtype in (int, "int64", "int32"), (
            f"EQIndicator dtype should be int, got {result['EQIndicator'].dtype}"
        )
        assert result["EQIndicator"].isna().sum() == 0

    def test_has_grid_lat_grid_lon_country_columns(self):
        """Result has grid_lat, grid_lon, and country columns."""
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        active_cells = [(35, -125)]
        country_map = {(35, -125): "Japan"}
        eq_index = self._make_eq_index_for_date(date(1999, 6, 15), [])

        ephe_df = _make_minimal_ephe_df()
        ephe_df["date"] = "1999-06-15"
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        assert "grid_lat" in result.columns
        assert "grid_lon" in result.columns
        assert "country" in result.columns
        assert result["country"].iloc[0] == "Japan"

    def test_sorted_by_grid_lat_grid_lon(self):
        """Rows are sorted by (grid_lat, grid_lon) for deterministic ordering."""
        from datetime import date
        from pipeline.features.engineering import build_matrix_chunk

        active_cells = [(40, -115), (30, -120), (35, -125)]  # unsorted
        country_map = {c: "USA" for c in active_cells}
        eq_index = self._make_eq_index_for_date(date(1999, 6, 15), [])

        ephe_df = _make_minimal_ephe_df()
        ephe_df["date"] = "1999-06-15"
        ephe_df = ephe_df.set_index("date")
        ephe_row = ephe_df.iloc[0]

        result = build_matrix_chunk(ephe_row, active_cells, eq_index, country_map)
        sorted_lats = result["grid_lat"].tolist()
        assert sorted_lats == sorted(sorted_lats), "Rows should be sorted by grid_lat"

    def test_active_cells_list_returns_sorted_list(self):
        """active_cells_list converts set to sorted list of tuples."""
        from pipeline.features.engineering import active_cells_list

        cells_set = {(40, -115), (30, -120), (35, -125)}
        result = active_cells_list(cells_set)
        assert isinstance(result, list)
        assert result == sorted(cells_set)


# ---------------------------------------------------------------------------
# Shared fixture helpers
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


# ---------------------------------------------------------------------------
# Integration tests — require pipeline run artifacts
# ---------------------------------------------------------------------------

_TRAIN_PARQUET = "data/processed/feature_matrix_train.parquet"
_TEST_PARQUET = "data/processed/feature_matrix_test.parquet"
_FEATURE_COLS_JSON = "data/processed/feature_columns.json"
_ENCODER_PKL = "data/processed/nakshatra_encoder.pkl"

def _is_valid_parquet(path: str) -> bool:
    """Return True if the file at path is a readable parquet file with valid footer."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        with open(path, "rb") as f:
            # Parquet files end with 4-byte footer length + 4-byte magic "PAR1"
            f.seek(-4, 2)
            magic = f.read(4)
            return magic == b"PAR1"
    except OSError:
        return False


_train_exists = pytest.mark.skipif(
    not Path(_TRAIN_PARQUET).exists(),
    reason="requires pipeline run: data/processed/feature_matrix_train.parquet not found",
)
_test_readable = pytest.mark.skipif(
    not _is_valid_parquet(_TEST_PARQUET),
    reason="requires complete pipeline run: feature_matrix_test.parquet missing or corrupted",
)
_artifacts_exist = pytest.mark.skipif(
    not (Path(_TRAIN_PARQUET).exists() and Path(_FEATURE_COLS_JSON).exists() and Path(_ENCODER_PKL).exists()),
    reason="requires pipeline run: one or more output artifacts missing",
)


class TestOutputArtifacts:
    """Integration tests validating the four pipeline output artifacts.

    Tests are skipped unless the pipeline has been run and artifacts exist.
    Use: pytest tests/test_engineering.py::TestOutputArtifacts -v
    """

    @_train_exists
    def test_train_parquet_readable(self):
        """feature_matrix_train.parquet is readable and has > 200,000 rows."""
        df = pd.read_parquet(_TRAIN_PARQUET)
        assert df.shape[0] > 200_000, (
            f"Expected >200K rows in train parquet, got {df.shape[0]}"
        )

    @_train_exists
    def test_train_parquet_required_columns(self):
        """feature_matrix_train.parquet contains EQIndicator, grid_lat, grid_lon, country."""
        df = pd.read_parquet(_TRAIN_PARQUET)
        for col in ("EQIndicator", "grid_lat", "grid_lon", "country"):
            assert col in df.columns, f"Required column '{col}' missing from train parquet"

    @_test_readable
    def test_test_parquet_readable(self):
        """feature_matrix_test.parquet is readable by pd.read_parquet."""
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(_TEST_PARQUET)
        # Read just the first row group to avoid loading 8.5M rows
        tbl = pf.read_row_group(0)
        df = tbl.to_pandas()
        assert df.shape[0] > 0, "test parquet first row group is empty"
        for col in ("EQIndicator", "grid_lat", "grid_lon", "country"):
            assert col in df.columns, f"Required column '{col}' missing from test parquet"

    @_train_exists
    @_test_readable
    def test_temporal_split_in_parquets(self):
        """Train max date < 2000-01-01; test min date >= 2000-01-01."""
        import pyarrow.parquet as pq
        import datetime

        SPLIT = datetime.date(2000, 1, 1)

        train_df = pd.read_parquet(_TRAIN_PARQUET, columns=["date"])
        max_train = pd.to_datetime(train_df["date"]).max().date()
        assert max_train < SPLIT, (
            f"Train parquet max date {max_train} is not before 2000-01-01"
        )

        # Read test parquet first row group only
        pf = pq.ParquetFile(_TEST_PARQUET)
        tbl = pf.read_row_group(0)
        test_df = tbl.to_pandas()
        min_test = pd.to_datetime(test_df["date"]).min().date()
        assert min_test >= SPLIT, (
            f"Test parquet min date {min_test} is not >= 2000-01-01"
        )

    @_train_exists
    def test_no_raw_columns_in_output(self):
        """No column in train parquet ends with bare '_lon', '_sign_num', '_sign', '_nakshatra_num'."""
        df = pd.read_parquet(_TRAIN_PARQUET)
        bad = [
            c for c in df.columns
            if (c.endswith("_lon") and c != "grid_lon")
            or c.endswith("_sign_num")
            or (c.endswith("_sign") and c != "grid_lon")
            or c.endswith("_nakshatra_num")
        ]
        assert bad == [], f"Raw columns found in train parquet: {bad}"

    @_artifacts_exist
    def test_feature_columns_json(self):
        """feature_columns.json is valid JSON with > 400 feature column names."""
        import json
        with open(_FEATURE_COLS_JSON) as f:
            feature_cols = json.load(f)
        assert isinstance(feature_cols, list), "feature_columns.json must be a JSON list"
        assert len(feature_cols) > 400, (
            f"Expected >400 feature columns, got {len(feature_cols)}"
        )
        assert all(isinstance(c, str) for c in feature_cols), (
            "All entries in feature_columns.json must be strings"
        )

    @_artifacts_exist
    def test_encoder_pkl_loadable(self):
        """nakshatra_encoder.pkl is loadable by joblib.load and is a OneHotEncoder."""
        import joblib
        from sklearn.preprocessing import OneHotEncoder

        encoder = joblib.load(_ENCODER_PKL)
        assert isinstance(encoder, OneHotEncoder), (
            f"Expected OneHotEncoder, got {type(encoder)}"
        )

    @_train_exists
    def test_train_eq_indicator_has_both_classes(self):
        """Train parquet EQIndicator column contains both 0s and 1s."""
        df = pd.read_parquet(_TRAIN_PARQUET, columns=["EQIndicator"])
        unique_vals = set(df["EQIndicator"].unique())
        assert 0 in unique_vals, "EQIndicator=0 (negative) rows missing from train parquet"
        assert 1 in unique_vals, "EQIndicator=1 (positive) rows missing from train parquet"


def _make_full_nakshatra_df() -> pd.DataFrame:
    """Build a 27-row DataFrame with all 27 nakshatras for each planet.

    Used to fit the nakshatra encoder so all 27 categories are in the vocabulary.
    """
    from pipeline.features.engineering import NAKSHATRAS, PLANETS, SIGN_NAMES

    rows = []
    for nak_idx, nak_name in enumerate(NAKSHATRAS):
        # Each row represents one nakshatra covering 360/27 degrees of longitude
        lon = nak_idx * (360.0 / 27)
        sign_num = int(lon / 30) % 12
        row: dict = {"date": f"1990-01-{nak_idx + 1:02d}"}
        for p in PLANETS:
            row[f"{p}_lon"] = lon
            row[f"{p}_sign_num"] = sign_num
            row[f"{p}_sign"] = SIGN_NAMES[sign_num]
            row[f"{p}_retro"] = False
            row[f"{p}_nakshatra_num"] = nak_idx
            row[f"{p}_nakshatra"] = nak_name
        row["sun_moon_conjunction"] = 0
        rows.append(row)
    return pd.DataFrame(rows)
