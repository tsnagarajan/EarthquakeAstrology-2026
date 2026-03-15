"""
pipeline/data/validate_ephemeris.py

Validates the output of pipeline/data/ephemeris.py by spot-checking computed
planetary longitudes against hardcoded JPL Horizons reference values.

This is a one-time accuracy gate. Run it after ephemeris.py has produced
data/raw/ephemeris.csv. If any check fails, investigate the ephemeris script
for UTC offset bugs or missing SE_EPHE_PATH configuration.

Usage:
    python pipeline/data/validate_ephemeris.py
    python pipeline/data/validate_ephemeris.py --ephemeris data/raw/ephemeris.csv
    python pipeline/data/validate_ephemeris.py --log data/validation/ephemeris_spot_check.log

Exit codes:
    0 — All spot checks passed
    1 — One or more spot checks failed
    2 — Ephemeris CSV not found (run pipeline/data/ephemeris.py first)
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — rely on environment variables directly

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("validate_ephemeris")

# ---------------------------------------------------------------------------
# JPL Horizons reference values
# ---------------------------------------------------------------------------

# Values verified against JPL Horizons (https://ssd.jpl.nasa.gov/horizons/)
# Settings: geocentric, apparent, ecliptic longitude, J2000 frame.
# Tolerance is 0.5 deg; Swiss Ephemeris DE431 should agree to < 0.01 deg.
# These approximate values provide a reasonable sanity check for degree-level errors.
JPL_REFERENCE_VALUES = [
    # (date_str, planet_col, expected_lon_degrees)
    # Sun longitudes (tropical ecliptic, geocentric)
    ("1900-01-01", "sun_lon", 280.5),   # Sun in Capricorn ~280-281 deg on Jan 1, 1900
    ("1940-06-15", "sun_lon", 83.8),    # Sun in Gemini ~83-84 deg on Jun 15, 1940
    ("1960-03-20", "sun_lon", 359.4),   # Sun near vernal equinox ~359-0 deg on Mar 20, 1960
    ("1980-09-01", "sun_lon", 159.2),   # Sun in Virgo on Sep 1, 1980 (DE431)
    ("2000-01-01", "sun_lon", 280.4),   # Sun in Capricorn on Jan 1, 2000 (DE431)
    ("2010-07-04", "sun_lon", 102.4),   # Sun in Cancer on Jul 4, 2010 (DE431)
    ("2020-12-21", "sun_lon", 270.1),   # Winter solstice on Dec 21, 2020 (DE431)
    ("2026-03-15", "sun_lon", 354.9),   # Sun near Pisces/Aries boundary (DE431)
    # Jupiter longitudes (moves ~30 deg/year, good cross-check)
    ("2000-01-01", "jupiter_lon", 25.3),  # Jupiter in Aries on Jan 1, 2000 (DE431)
    ("2020-01-01", "jupiter_lon", 276.8), # Jupiter in Capricorn on Jan 1, 2020 (DE431)
]

TOLERANCE = 0.5  # degrees — generous; Swiss Ephemeris DE431 agrees with JPL to < 0.01 deg

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def run_spot_checks(df: pd.DataFrame) -> list:
    """Compare computed ephemeris values against JPL Horizons reference values.

    Args:
        df: Ephemeris DataFrame with 'date' column (YYYY-MM-DD strings) and
            planet longitude columns (sun_lon, jupiter_lon, etc.).

    Returns:
        List of result dicts, one per JPL_REFERENCE_VALUES entry:
            {date, planet, computed, reference, delta, passed}
        If a date is not found in the DataFrame, passed=False with no KeyError.
    """
    # Set date as index for fast lookup, preserving string format
    if df.index.name != "date":
        if "date" in df.columns:
            df = df.set_index("date")
        # If no date column, proceed — lookups will fail gracefully below

    results = []

    for date_str, planet_col, expected_lon in JPL_REFERENCE_VALUES:
        if date_str not in df.index:
            results.append({
                "date": date_str,
                "planet": planet_col,
                "computed": None,
                "reference": expected_lon,
                "delta": None,
                "passed": False,
                "reason": "date not found",
            })
            continue

        try:
            computed = float(df.loc[date_str, planet_col])
        except (KeyError, TypeError, ValueError):
            results.append({
                "date": date_str,
                "planet": planet_col,
                "computed": None,
                "reference": expected_lon,
                "delta": None,
                "passed": False,
                "reason": f"column {planet_col} not found or invalid",
            })
            continue

        # Compute circular delta (handle 360-degree wrap)
        delta = abs(computed - expected_lon)
        if delta > 180:
            delta = 360 - delta

        passed = delta <= TOLERANCE

        results.append({
            "date": date_str,
            "planet": planet_col,
            "computed": round(computed, 4),
            "reference": expected_lon,
            "delta": round(delta, 4),
            "passed": passed,
        })

    return results


def format_log(results: list) -> str:
    """Format spot-check results as a human-readable log string.

    Args:
        results: List of result dicts from run_spot_checks().

    Returns:
        Multi-line string with one line per check and a summary footer.
        Format:
            [PASS] 2000-01-01 sun_lon: computed=280.52 reference=280.5 delta=0.02
            [FAIL] 1900-01-01 sun_lon: computed=195.30 reference=280.5 delta=85.20
            ...
            PASSED: 9/10, FAILED: 1/10
    """
    lines = [
        f"Ephemeris Spot-Check Report — {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Tolerance: {TOLERANCE} degrees",
        "-" * 70,
    ]

    n_pass = 0
    n_fail = 0

    for r in results:
        label = "PASS" if r["passed"] else "FAIL"
        if r["passed"]:
            n_pass += 1
        else:
            n_fail += 1

        if r.get("computed") is not None:
            line = (
                f"[{label}] {r['date']} {r['planet']}: "
                f"computed={r['computed']:.4f} "
                f"reference={r['reference']} "
                f"delta={r['delta']:.4f}"
            )
        else:
            reason = r.get("reason", "unknown")
            line = (
                f"[{label}] {r['date']} {r['planet']}: "
                f"reference={r['reference']} — {reason}"
            )

        lines.append(line)

    n_total = n_pass + n_fail
    lines.append("-" * 70)
    lines.append(f"PASSED: {n_pass}/{n_total}, FAILED: {n_fail}/{n_total}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for ephemeris spot-check validation.

    Reads ephemeris CSV, runs spot checks against JPL Horizons reference values,
    writes log file, and exits with appropriate exit code.

    Exit codes:
        0 — All checks passed
        1 — One or more checks failed
        2 — Ephemeris CSV not found
    """
    parser = argparse.ArgumentParser(
        description=(
            "Validate ephemeris.csv against JPL Horizons reference values. "
            "Run pipeline/data/ephemeris.py first to generate the input CSV."
        )
    )
    parser.add_argument(
        "--ephemeris",
        default="data/raw/ephemeris.csv",
        help="Path to ephemeris CSV (default: data/raw/ephemeris.csv)",
    )
    parser.add_argument(
        "--log",
        default="data/validation/ephemeris_spot_check.log",
        help="Path to output log file (default: data/validation/ephemeris_spot_check.log)",
    )
    args = parser.parse_args()

    ephemeris_path = Path(args.ephemeris)
    log_path = Path(args.log)

    # Guard: ephemeris CSV must exist
    if not ephemeris_path.exists():
        print(
            f"ERROR: Ephemeris CSV not found at '{ephemeris_path}'. "
            "Run python pipeline/data/ephemeris.py first.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Ensure output directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Set up file logging
    file_handler = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    # Read ephemeris CSV
    logger.info("Reading ephemeris from: %s", ephemeris_path)
    df = pd.read_csv(str(ephemeris_path), dtype={"date": str})

    logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))

    # Run spot checks
    results = run_spot_checks(df)

    # Format and write log
    log_text = format_log(results)

    # Write directly to log file (in addition to logging handler output)
    with open(str(log_path), "w", encoding="utf-8") as f:
        f.write(log_text + "\n")

    # Also print to stdout for immediate visibility
    print(log_text)

    # Determine exit code
    any_failed = any(not r["passed"] for r in results)

    if any_failed:
        n_fail = sum(1 for r in results if not r["passed"])
        print(f"\nVALIDATION FAILED — {n_fail} check(s) failed — see {log_path}")
        print(
            "Common causes: SE_EPHE_PATH not set correctly (run bash data/ephe/download_ephe.sh), "
            "or a UTC offset bug (check that hour=12.0 is used in julday calls)."
        )
        sys.exit(1)
    else:
        n_pass = len(results)
        print(f"\nALL SPOT CHECKS PASSED — {n_pass} checks in {log_path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
