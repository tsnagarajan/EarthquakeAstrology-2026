"""
Tests for pipeline/data/usgs.py

Behavior under test:
- Querying a single year returns a non-empty DataFrame with required columns
- No single decade chunk has exactly 20,000 rows (truncation guard raises RuntimeError)
- validate_result asserts required columns exist
- validate_result asserts mag >= 5.5
- validate_result warns (not errors) if row count < 50,000
- Rows with mag < 5.5 are absent (API filter enforced)
- Script structure: fetch_decade, fetch_all, validate_result, main functions exist
"""

import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

# Add project root to PYTHONPATH so we can import pipeline
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUsgsModuleStructure(unittest.TestCase):
    """Verify module-level structure before any network calls."""

    def test_module_imports(self):
        """usgs.py can be imported without errors."""
        from pipeline.data import usgs  # noqa: F401

    def test_required_functions_exist(self):
        """Module contains fetch_decade, fetch_all, validate_result, main."""
        from pipeline.data import usgs

        assert callable(usgs.fetch_decade), "fetch_decade must be callable"
        assert callable(usgs.fetch_all), "fetch_all must be callable"
        assert callable(usgs.validate_result), "validate_result must be callable"
        assert callable(usgs.main), "main must be callable"

    def test_truncation_limit_constant(self):
        """TRUNCATION_LIMIT is defined as 20_000."""
        from pipeline.data import usgs

        assert hasattr(usgs, "TRUNCATION_LIMIT"), "TRUNCATION_LIMIT constant must exist"
        assert usgs.TRUNCATION_LIMIT == 20_000, "TRUNCATION_LIMIT must be 20,000"

    def test_min_mag_constant(self):
        """MIN_MAG is defined as 5.5."""
        from pipeline.data import usgs

        assert hasattr(usgs, "MIN_MAG"), "MIN_MAG constant must exist"
        assert usgs.MIN_MAG == 5.5, "MIN_MAG must be 5.5"


class TestFetchDecade(unittest.TestCase):
    """Tests for fetch_decade function with mocked HTTP responses."""

    def _make_csv_response(self, n_rows: int, min_mag: float = 5.5) -> str:
        """Generate a minimal CSV string resembling USGS response."""
        rows = []
        for i in range(n_rows):
            rows.append(
                f"2000-01-{(i % 28) + 1:02d}T00:00:00.000Z,"
                f"{i * 0.1:.4f},{i * 0.1:.4f},10.0,{min_mag + i * 0.01:.2f},"
                f"Region {i},earthquake,{i}"
            )
        header = "time,latitude,longitude,depth,mag,place,type,id"
        return header + "\n" + "\n".join(rows) + "\n"

    def test_returns_dataframe_with_required_columns(self):
        """fetch_decade returns DataFrame with required columns on success."""
        from pipeline.data import usgs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self._make_csv_response(100)

        with patch("pipeline.data.usgs.requests.get", return_value=mock_response):
            df = usgs.fetch_decade(2000, 2000)

        assert isinstance(df, pd.DataFrame), "Must return a DataFrame"
        required_cols = {"time", "latitude", "longitude", "depth", "mag", "place", "type"}
        assert required_cols.issubset(set(df.columns)), (
            f"Missing columns: {required_cols - set(df.columns)}"
        )

    def test_raises_on_http_error(self):
        """fetch_decade raises RuntimeError on non-200 HTTP status."""
        from pipeline.data import usgs

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("pipeline.data.usgs.requests.get", return_value=mock_response):
            with self.assertRaises(RuntimeError):
                usgs.fetch_decade(2000, 2000)

    def test_truncation_guard_raises_on_20k_rows(self):
        """fetch_decade raises RuntimeError when response has exactly 20,000 rows."""
        from pipeline.data import usgs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self._make_csv_response(20_000)

        with patch("pipeline.data.usgs.requests.get", return_value=mock_response):
            with self.assertRaises(RuntimeError) as ctx:
                usgs.fetch_decade(2000, 2004)

        assert "20k" in str(ctx.exception).lower() or "limit" in str(ctx.exception).lower(), (
            "RuntimeError message should mention 20k limit"
        )

    def test_no_truncation_guard_on_19999_rows(self):
        """fetch_decade does NOT raise when response has 19,999 rows."""
        from pipeline.data import usgs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self._make_csv_response(19_999)

        with patch("pipeline.data.usgs.requests.get", return_value=mock_response):
            df = usgs.fetch_decade(2000, 2004)  # Should not raise

        assert len(df) == 19_999

    def test_returns_nonempty_for_active_year(self):
        """fetch_decade returns a non-empty DataFrame for an earthquake-active year."""
        from pipeline.data import usgs

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self._make_csv_response(500)

        with patch("pipeline.data.usgs.requests.get", return_value=mock_response):
            df = usgs.fetch_decade(1990, 1990)

        assert len(df) > 0, "Should return at least one event for active years"


class TestValidateResult(unittest.TestCase):
    """Tests for validate_result function."""

    def _make_valid_df(self, n_rows: int = 60_000) -> pd.DataFrame:
        """Create a valid DataFrame that should pass all checks."""
        import numpy as np

        return pd.DataFrame(
            {
                "time": pd.date_range("1900-01-01", periods=n_rows, freq="D").astype(str),
                "latitude": np.random.uniform(-90, 90, n_rows),
                "longitude": np.random.uniform(-180, 180, n_rows),
                "depth": np.random.uniform(0, 700, n_rows),
                "mag": np.random.uniform(5.5, 9.5, n_rows),
                "place": [f"Region {i}" for i in range(n_rows)],
                "type": ["earthquake"] * n_rows,
            }
        )

    def test_passes_on_valid_dataframe(self):
        """validate_result returns True for a valid DataFrame."""
        from pipeline.data import usgs

        df = self._make_valid_df()
        result = usgs.validate_result(df)
        assert result is True

    def test_raises_on_missing_columns(self):
        """validate_result raises AssertionError when required columns are missing."""
        from pipeline.data import usgs

        df = self._make_valid_df()
        df_missing = df.drop(columns=["mag"])

        with self.assertRaises((AssertionError, KeyError, ValueError)):
            usgs.validate_result(df_missing)

    def test_raises_on_low_magnitude(self):
        """validate_result raises AssertionError when min mag < 5.5."""
        from pipeline.data import usgs

        df = self._make_valid_df()
        df.loc[0, "mag"] = 3.0  # Introduce a low mag row

        with self.assertRaises(AssertionError):
            usgs.validate_result(df)

    def test_warns_but_does_not_raise_on_low_row_count(self):
        """validate_result warns but returns True when row count < 50,000."""
        from pipeline.data import usgs
        import logging

        df = self._make_valid_df(n_rows=30_000)

        with self.assertLogs(level=logging.WARNING) as log_ctx:
            result = usgs.validate_result(df)

        assert result is True, "Should still return True with low count"
        assert any("50" in msg or "warn" in msg.lower() for msg in log_ctx.output), (
            "Should emit a warning about low row count"
        )


class TestFetchAll(unittest.TestCase):
    """Tests for fetch_all function."""

    def _make_chunk_df(self, n: int = 200) -> pd.DataFrame:
        import numpy as np

        return pd.DataFrame(
            {
                "time": pd.date_range("1900-01-01", periods=n, freq="D").astype(str),
                "latitude": np.random.uniform(-90, 90, n),
                "longitude": np.random.uniform(-180, 180, n),
                "depth": np.random.uniform(0, 700, n),
                "mag": np.random.uniform(5.5, 9.0, n),
                "place": [f"Place {i}" for i in range(n)],
                "type": ["earthquake"] * n,
                "id": [f"usgs{i:05d}" for i in range(n)],
            }
        )

    def test_fetch_all_concatenates_chunks(self):
        """fetch_all returns concatenated DataFrame from multiple decade chunks."""
        from pipeline.data import usgs

        call_count = {"n": 0}

        def mock_fetch_decade(start, end):
            call_count["n"] += 1
            return self._make_chunk_df(100)

        with patch.object(usgs, "fetch_decade", side_effect=mock_fetch_decade):
            df = usgs.fetch_all(start_year=2000, end_year=2009, chunk_years=5)

        assert call_count["n"] >= 2, "Should call fetch_decade at least twice for 10-year range"
        assert len(df) > 0, "Result should be non-empty"

    def test_fetch_all_deduplicates_on_id(self):
        """fetch_all deduplicates rows with the same id."""
        from pipeline.data import usgs

        # Return the same chunk twice (simulating overlap)
        chunk = self._make_chunk_df(50)

        with patch.object(usgs, "fetch_decade", return_value=chunk):
            df = usgs.fetch_all(start_year=2000, end_year=2009, chunk_years=5)

        # Each id appears in chunk; after dedup, count should equal original chunk size
        assert df["id"].nunique() == len(df), "Duplicate ids should be removed"


if __name__ == "__main__":
    unittest.main()
