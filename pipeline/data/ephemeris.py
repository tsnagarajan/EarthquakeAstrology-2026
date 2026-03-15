"""
pipeline/data/ephemeris.py

Computes daily planetary positions (longitude, sign, retrograde), Vedic nakshatra positions,
and planetary aspects for 1900-2026 using pysweph (Swiss Ephemeris).

Output: data/raw/ephemeris.csv (46,022 rows x ~200 columns)

Usage:
    python pipeline/data/ephemeris.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--output PATH]

One-time setup (run once before first use):
    bash data/ephe/download_ephe.sh
    cp .env.example .env  # set SE_EPHE_PATH

NOTE on pysweph 2.10.3.6 API:
    calc_ut() returns a 3-tuple: (xx, iflag, serr)
    where xx is a tuple of 6 floats: [longitude, latitude, distance, speed_long, speed_lat, speed_dist]
    This differs from pyswisseph 2.10.3.2 which returned a 2-tuple (xx, ret).
    Always unpack as: xx, _iflag, _serr = swe.calc_ut(jd, planet_id)
"""

import argparse
import itertools
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import swisseph as swe
from dotenv import load_dotenv
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Environment / logging setup
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ephemeris")

SE_EPHE_PATH = os.getenv("SE_EPHE_PATH", "./data/ephe")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
    "chiron": swe.CHIRON,
    "lilith": swe.MEAN_APOG,
    "node": swe.MEAN_NODE,
}

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

ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

ORBS = 6.0  # degrees — standard orb for all aspects

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup_ephemeris() -> None:
    """Configure Swiss Ephemeris data path.

    Must be called before any swe.calc_ut() invocation.

    Raises:
        RuntimeError: If SE_EPHE_PATH directory does not exist.
    """
    ephe_path = Path(SE_EPHE_PATH)
    if not ephe_path.exists():
        raise RuntimeError(
            f"SE_EPHE_PATH '{SE_EPHE_PATH}' does not exist. "
            "Run 'bash data/ephe/download_ephe.sh' to download ephemeris files, "
            "then copy .env.example to .env and set SE_EPHE_PATH to the correct path."
        )

    swe.set_ephe_path(str(ephe_path))
    logger.info("Swiss Ephemeris path set to: %s", ephe_path.resolve())

    # Check for .se1 files — log warning if absent (Moshier fallback is lower precision)
    se1_files = list(ephe_path.glob("*.se1"))
    if not se1_files:
        logger.warning(
            "No .se1 ephemeris files found in '%s'. "
            "Swiss Ephemeris will use Moshier fallback (lower precision). "
            "Run 'bash data/ephe/download_ephe.sh' to download required files.",
            ephe_path,
        )
    else:
        logger.info("Found %d .se1 ephemeris file(s): %s", len(se1_files),
                    [f.name for f in se1_files])


# ---------------------------------------------------------------------------
# Core computation functions
# ---------------------------------------------------------------------------


def compute_nakshatra(jd: float, planet_id: int) -> tuple[int, str]:
    """Compute Vedic nakshatra for a planet on a given Julian Day.

    Uses Lahiri ayanamsha (sidereal). Resets to tropical mode after computation.

    Args:
        jd: Julian Day number (UTC noon).
        planet_id: Swiss Ephemeris planet constant.

    Returns:
        Tuple of (nakshatra_num 0-26, nakshatra_name str).
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    xx_sid, _iflag, _serr = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
    sidereal_lon = xx_sid[0] % 360.0
    nakshatra_num = int(sidereal_lon / (360.0 / 27)) % 27
    swe.set_sid_mode(0)  # Reset to tropical for subsequent calculations
    return nakshatra_num, NAKSHATRAS[nakshatra_num]


def compute_day(date_str: str) -> dict:
    """Compute planetary positions for a single calendar day at UTC noon.

    Args:
        date_str: Date in 'YYYY-MM-DD' format.

    Returns:
        Dict with 'date' key plus per-planet columns:
            {prefix}_lon, {prefix}_sign, {prefix}_sign_num,
            {prefix}_retro, {prefix}_nakshatra_num, {prefix}_nakshatra
        for each planet in PLANETS (13 planets total = 78 columns + 1 date).
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # ALWAYS use hour=12.0 (UTC noon) to avoid midnight boundary ambiguity
    jd = swe.julday(dt.year, dt.month, dt.day, 12.0)

    row: dict = {"date": date_str}

    for prefix, planet_id in PLANETS.items():
        # Tropical position — use calc_ut (UT input), never calc (TT input)
        # pysweph 2.10.3.6 returns 3-tuple: (xx, iflag, serr)
        xx, _iflag, _serr = swe.calc_ut(jd, planet_id)

        longitude: float = xx[0] % 360.0
        speed: float = xx[3]  # degrees/day; negative = retrograde

        sign_num: int = int(longitude / 30) % 12
        sign_name: str = SIGN_NAMES[sign_num]
        is_retro: bool = speed < 0

        nakshatra_num, nakshatra_name = compute_nakshatra(jd, planet_id)

        row[f"{prefix}_lon"] = longitude
        row[f"{prefix}_sign_num"] = sign_num
        row[f"{prefix}_sign"] = sign_name
        row[f"{prefix}_retro"] = is_retro
        row[f"{prefix}_nakshatra_num"] = nakshatra_num
        row[f"{prefix}_nakshatra"] = nakshatra_name

    return row


def compute_aspects(row: dict) -> dict:
    """Compute planetary aspect columns for a single day's row dict.

    For each pair of planets and each of the 5 major aspects, returns 1 if
    the angular separation is within ORBS of the aspect angle, else 0.

    Args:
        row: Dict from compute_day() containing {prefix}_lon values.

    Returns:
        Dict of aspect columns: {p1}_{p2}_{aspect_name} -> 0 or 1.
        Total: C(13,2) x 5 = 78 x 5 = 390 columns.
    """
    aspects_row: dict = {}
    planet_names = list(PLANETS.keys())

    for p1, p2 in itertools.combinations(planet_names, 2):
        lon1: float = row[f"{p1}_lon"]
        lon2: float = row[f"{p2}_lon"]

        # Compute angular difference — normalize to 0-180 range
        angular_diff = abs((lon1 - lon2) % 360)
        if angular_diff > 180:
            angular_diff = 360 - angular_diff

        for aspect_name, aspect_angle in ASPECTS.items():
            is_aspect: int = 1 if abs(angular_diff - aspect_angle) <= ORBS else 0
            aspects_row[f"{p1}_{p2}_{aspect_name}"] = is_aspect

    return aspects_row


def compute_date_range(start_date: str, end_date: str) -> list[dict]:
    """Compute planetary data for all dates in range (inclusive).

    Args:
        start_date: Start date as 'YYYY-MM-DD'.
        end_date: End date as 'YYYY-MM-DD' (inclusive).

    Returns:
        List of row dicts, each combining compute_day + compute_aspects output.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    rows = []

    for dt in tqdm(dates, desc="Computing ephemeris", unit="day"):
        date_str = dt.strftime("%Y-%m-%d")
        day_row = compute_day(date_str)
        aspect_cols = compute_aspects(day_row)
        day_row.update(aspect_cols)
        rows.append(day_row)

    return rows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for ephemeris computation.

    Parses CLI arguments, sets up ephemeris, computes date range, writes CSV.

    Usage:
        python pipeline/data/ephemeris.py
        python pipeline/data/ephemeris.py --start-date 1900-01-01 --end-date 2026-12-31
        python pipeline/data/ephemeris.py --output data/raw/ephemeris.csv
    """
    parser = argparse.ArgumentParser(
        description="Compute daily planetary positions using Swiss Ephemeris (1900-2026)"
    )
    parser.add_argument(
        "--start-date",
        default="1900-01-01",
        help="Start date in YYYY-MM-DD format (default: 1900-01-01)",
    )
    parser.add_argument(
        "--end-date",
        default="2026-12-31",
        help="End date in YYYY-MM-DD format (default: 2026-12-31)",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("EPHEMERIS_OUTPUT", "data/raw/ephemeris.csv"),
        help="Output CSV path (default: data/raw/ephemeris.csv)",
    )

    args = parser.parse_args()

    setup_ephemeris()

    logger.info(
        "Computing ephemeris from %s to %s → %s",
        args.start_date,
        args.end_date,
        args.output,
    )

    rows = compute_date_range(args.start_date, args.end_date)

    # Build DataFrame and ensure output directory exists
    df = pd.DataFrame(rows)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(
        f"Computed {len(df)} days. Columns: {len(df.columns)}. Saved to {output_path}"
    )


if __name__ == "__main__":
    main()
