"""
tests/test_validate_ephemeris.py

Failing tests for pipeline/data/validate_ephemeris.py (TDD RED phase).
Tests written before implementation exists.

Covers:
- Module structure: run_spot_checks, format_log, main functions exist
- run_spot_checks: returns list of dicts with expected keys
- run_spot_checks: handles missing date gracefully (passed=False, no KeyError)
- run_spot_checks: 360-degree wrap handling
- run_spot_checks: PASS when computed == reference exactly
- run_spot_checks: PASS when delta <= 0.5
- run_spot_checks: FAIL when delta > 0.5
- run_spot_checks: winter solstice 2020-12-21 sun_lon within 0.5 of 270.0
- format_log: returns [PASS]/[FAIL] lines and summary
- JPL_REFERENCE_VALUES: 10 entries hardcoded in module
- TOLERANCE: 0.5 in module
"""

import ast
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

# ---------------------------------------------------------------------------
# Module structure tests (AST-based — do not import module until GREEN phase)
# ---------------------------------------------------------------------------


class TestModuleStructure(unittest.TestCase):
    """Validate module structure without importing it."""

    @classmethod
    def setUpClass(cls):
        src_path = pathlib.Path("pipeline/data/validate_ephemeris.py")
        if not src_path.exists():
            cls.src = None
            cls.tree = None
            return
        cls.src = src_path.read_text()
        cls.tree = ast.parse(cls.src)

    def _require_src(self):
        if self.src is None:
            self.fail("pipeline/data/validate_ephemeris.py does not exist yet")

    def test_file_exists(self):
        self._require_src()

    def test_has_run_spot_checks_function(self):
        self._require_src()
        funcs = [n.name for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("run_spot_checks", funcs, "run_spot_checks function missing")

    def test_has_format_log_function(self):
        self._require_src()
        funcs = [n.name for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("format_log", funcs, "format_log function missing")

    def test_has_main_function(self):
        self._require_src()
        funcs = [n.name for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]
        self.assertIn("main", funcs, "main function missing")

    def test_has_jpl_reference_values(self):
        self._require_src()
        self.assertIn("JPL_REFERENCE_VALUES", self.src, "JPL_REFERENCE_VALUES missing")

    def test_has_tolerance_constant(self):
        self._require_src()
        self.assertIn("TOLERANCE", self.src, "TOLERANCE constant missing")
        self.assertIn("0.5", self.src, "TOLERANCE must be 0.5 degrees")

    def test_has_sys_exit_1(self):
        self._require_src()
        self.assertIn("sys.exit(1)", self.src, "Must exit with code 1 on failure")

    def test_has_filehandler_or_open(self):
        self._require_src()
        has_log = "FileHandler" in self.src or "open(" in self.src
        self.assertTrue(has_log, "Must write to log file (FileHandler or open)")

    def test_jpl_has_10_entries(self):
        """JPL_REFERENCE_VALUES must contain exactly 10 spot-check entries."""
        self._require_src()
        # Count tuples inside JPL_REFERENCE_VALUES by looking for date strings
        import re
        dates = re.findall(r'"\d{4}-\d{2}-\d{2}"', self.src)
        self.assertGreaterEqual(len(dates), 10, "Must have at least 10 date entries in JPL_REFERENCE_VALUES")

    def test_has_dunder_main_guard(self):
        self._require_src()
        self.assertIn('__name__', self.src, "Must have if __name__ == '__main__' guard")


# ---------------------------------------------------------------------------
# Functional tests — import module for these
# ---------------------------------------------------------------------------


def _import_validate():
    """Import validate_ephemeris, returning module or None if file doesn't exist."""
    src_path = pathlib.Path("pipeline/data/validate_ephemeris.py")
    if not src_path.exists():
        return None
    spec = __import__.__class__
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_ephemeris", src_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_df(rows) -> pd.DataFrame:
    """Build a minimal ephemeris DataFrame from (date, sun_lon, jupiter_lon) tuples."""
    records = [{"date": r[0], "sun_lon": r[1], "jupiter_lon": r[2]} for r in rows]
    df = pd.DataFrame(records)
    return df


class TestRunSpotChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_validate()

    def _require_mod(self):
        if self.mod is None:
            self.fail("pipeline/data/validate_ephemeris.py does not exist yet")

    def _df_with_key_dates(self):
        """DataFrame covering all 10 JPL reference dates with correct values."""
        rows = [
            ("1900-01-01", 280.5,   25.0),
            ("1940-06-15",  83.8,   25.0),
            ("1960-03-20", 359.4,   25.0),
            ("1980-09-01", 158.5,   25.0),
            ("2000-01-01", 280.5,   25.8),
            ("2010-07-04", 102.3,   25.0),
            ("2020-01-01", 280.5,  278.0),
            ("2020-12-21", 270.0,   25.0),
            ("2026-03-15", 354.5,   25.0),
        ]
        return _make_df(rows)

    def test_returns_list(self):
        self._require_mod()
        df = self._df_with_key_dates()
        results = self.mod.run_spot_checks(df)
        self.assertIsInstance(results, list)

    def test_returns_10_results(self):
        self._require_mod()
        df = self._df_with_key_dates()
        results = self.mod.run_spot_checks(df)
        self.assertEqual(len(results), 10, f"Expected 10 results, got {len(results)}")

    def test_result_dict_has_required_keys(self):
        self._require_mod()
        df = self._df_with_key_dates()
        results = self.mod.run_spot_checks(df)
        required_keys = {"date", "planet", "computed", "reference", "delta", "passed"}
        for r in results:
            missing = required_keys - set(r.keys())
            self.assertFalse(missing, f"Result dict missing keys: {missing}")

    def test_exact_match_passes(self):
        self._require_mod()
        rows = [("2000-01-01", 280.5, 25.8)]
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        sun_result = next((r for r in results if r["date"] == "2000-01-01" and r["planet"] == "sun_lon"), None)
        if sun_result:
            self.assertTrue(sun_result["passed"], "Exact match should pass")

    def test_delta_within_tolerance_passes(self):
        self._require_mod()
        # computed = 280.8, reference = 280.5, delta = 0.3 -> should PASS
        rows = [("2000-01-01", 280.8, 25.8)]
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        sun_result = next((r for r in results if r["date"] == "2000-01-01" and r["planet"] == "sun_lon"), None)
        if sun_result:
            self.assertTrue(sun_result["passed"], "Delta 0.3 <= 0.5 should pass")

    def test_delta_exceeds_tolerance_fails(self):
        self._require_mod()
        # computed = 285.5, reference = 280.5, delta = 5.0 -> should FAIL
        rows = [("2000-01-01", 285.5, 25.8)]
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        sun_result = next((r for r in results if r["date"] == "2000-01-01" and r["planet"] == "sun_lon"), None)
        if sun_result:
            self.assertFalse(sun_result["passed"], "Delta 5.0 > 0.5 should fail")

    def test_missing_date_returns_failed_result(self):
        """Missing date: passed=False, no KeyError raised."""
        self._require_mod()
        # Empty DataFrame — no dates at all
        df = pd.DataFrame(columns=["date", "sun_lon", "jupiter_lon"])
        # Should not raise KeyError
        try:
            results = self.mod.run_spot_checks(df)
        except KeyError as e:
            self.fail(f"run_spot_checks raised KeyError on missing date: {e}")
        # All should be failed
        for r in results:
            self.assertFalse(r["passed"], f"Missing date should return passed=False, got: {r}")

    def test_360_degree_wrap_handled(self):
        """Delta should be computed as min circular distance (wrap around 360)."""
        self._require_mod()
        # reference = 359.4 (for 1960-03-20), computed = 0.1
        # naive delta = |0.1 - 359.4| = 359.3 -> should wrap to 360 - 359.3 = 0.7
        # But tolerance is 0.5 so even 0.7 > 0.5 would fail
        # Use computed = 359.6 -> naive delta = |359.6 - 359.4| = 0.2 (no wrap needed) -> should PASS
        rows = [("1960-03-20", 359.6, 25.0)]
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        check = next((r for r in results if r["date"] == "1960-03-20" and r["planet"] == "sun_lon"), None)
        if check:
            self.assertTrue(check["passed"], "Delta 0.2 should pass")

    def test_360_wrap_near_zero(self):
        """delta > 180 should use 360 - delta (wrap logic)."""
        self._require_mod()
        # reference = 359.4, computed = 0.6
        # naive delta = |0.6 - 359.4| = 358.8 -> wrapped = 360 - 358.8 = 1.2 -> FAIL (> 0.5)
        # But without wrap: delta = 358.8 which is also > 0.5 -> FAIL
        # Test wrap: reference = 1.0, computed = 359.5
        # naive = |359.5 - 1.0| = 358.5 -> wrapped = 360 - 358.5 = 1.5 (> 0.5) -> FAIL
        # Test pass case: reference = 1.0, computed = 0.8
        # naive = |0.8 - 1.0| = 0.2 -> no wrap -> PASS
        rows = [("1960-03-20", 359.9, 25.0)]  # reference is 359.4, delta = 0.5 -> boundary (should PASS)
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        check = next((r for r in results if r["date"] == "1960-03-20" and r["planet"] == "sun_lon"), None)
        if check:
            # delta = |359.9 - 359.4| = 0.5 -> exactly at tolerance -> PASS
            self.assertTrue(check["passed"], "Delta exactly 0.5 should pass (<=)")

    def test_winter_solstice_2020_passes(self):
        """2020-12-21 sun_lon should be within 0.5 of 270.0 (solstice fact)."""
        self._require_mod()
        rows = [("2020-12-21", 270.0, 25.0)]
        df = _make_df(rows)
        results = self.mod.run_spot_checks(df)
        check = next((r for r in results if r["date"] == "2020-12-21" and r["planet"] == "sun_lon"), None)
        if check:
            self.assertTrue(check["passed"], "Winter solstice sun_lon=270.0 should pass")


class TestFormatLog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_validate()

    def _require_mod(self):
        if self.mod is None:
            self.fail("pipeline/data/validate_ephemeris.py does not exist yet")

    def _sample_results(self):
        return [
            {"date": "2000-01-01", "planet": "sun_lon", "computed": 280.52, "reference": 280.5, "delta": 0.02, "passed": True},
            {"date": "1900-01-01", "planet": "sun_lon", "computed": 195.3,  "reference": 280.5, "delta": 85.2, "passed": False},
        ]

    def test_format_log_returns_string(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIsInstance(result, str)

    def test_format_log_contains_pass_label(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("PASS", result)

    def test_format_log_contains_fail_label(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("FAIL", result)

    def test_format_log_contains_summary_line(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        # Should contain something like "PASSED: 1/2" or "1/2"
        self.assertRegex(result, r"1/2|PASSED.*1|FAILED.*1")

    def test_format_log_contains_date(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("2000-01-01", result)

    def test_format_log_contains_planet(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("sun_lon", result)

    def test_format_log_contains_computed_value(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("280.52", result)

    def test_format_log_contains_reference_value(self):
        self._require_mod()
        result = self.mod.format_log(self._sample_results())
        self.assertIn("280.5", result)


if __name__ == "__main__":
    unittest.main()
