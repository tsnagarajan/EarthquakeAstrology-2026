"""pipeline/model/regional_scoring.py

Regional validation scoring: for a given region (or country), find the
model's single highest-confidence prediction per calendar month, check
whether an actual M5.5+ earthquake occurred anywhere in the region within
+/- window_days of that date, and compare the resulting hit rate against
the region's own historical base rate via a one-sided binomial test.

This methodology does not exist anywhere else in the codebase (no prior
partial implementation was found in pipeline/, tests/, or the legacy
top-level scripts/notebook) — implemented fresh per project spec.

No prediction/probability column exists in feature_matrix_test.parquet
(confirmed by inspecting its schema), so pipeline/model/add_regions.py runs
inference once to produce data/processed/feature_matrix_test_with_regions.parquet,
which is what score_region() expects as input.
"""
import json
import logging
import os

import pandas as pd
from scipy.stats import binomtest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGIONS_PARQUET = "data/processed/feature_matrix_test_with_regions.parquet"
OUTPUT_PATH = "data/processed/regional_validation_extended.json"
WINDOW_DAYS = 7

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.regional_scoring")


def _daily_eq_occurred(region_df: pd.DataFrame) -> pd.Series:
    """Boolean series indexed by every calendar day in the region's date
    range: True if >=1 actual M5.5+ earthquake occurred anywhere in the
    region on that day."""
    dates = pd.to_datetime(region_df["date"])
    eq_dates = set(dates[region_df["EQIndicator"] == 1].dt.date)

    full_range = pd.date_range(dates.min(), dates.max(), freq="D")
    occurred = pd.Series(
        [d.date() in eq_dates for d in full_range],
        index=full_range,
    )
    return occurred


def _window_has_eq(occurred: pd.Series, center_date, window_days: int) -> bool:
    """True if any day in occurred is True within +/- window_days of center_date."""
    center = pd.Timestamp(center_date)
    start = center - pd.Timedelta(days=window_days)
    end = center + pd.Timedelta(days=window_days)
    window = occurred[(occurred.index >= start) & (occurred.index <= end)]
    return bool(window.any())


def _centered_window_base_rate(occurred: pd.Series, window_days: int) -> float:
    """Return the share of centered +/- windows with at least one event."""
    if occurred.empty:
        return 0.0

    base_hits = sum(_window_has_eq(occurred, d, window_days) for d in occurred.index)
    return base_hits / len(occurred)


def score_region(region_df: pd.DataFrame, region_name: str, window_days: int = WINDOW_DAYS) -> dict:
    """Score one region's predictions against its own historical base rate.

    Args:
        region_df: rows already filtered to a single region/country, with
            columns 'date', 'grid_lat', 'grid_lon', 'EQIndicator', 'risk_score'.
        region_name: label used in the returned dict and log messages.
        window_days: +/- day window for hit and base-rate checks.

    Returns:
        dict with region, n_predictions, hits, hit_rate, base_rate, lift, p_value.
    """
    if region_df.empty:
        result = {
            "region": region_name,
            "n_predictions": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "base_rate": 0.0,
            "lift": None,
            "p_value": None,
        }
        logger.info("%s: no rows available for scoring", region_name)
        return result

    region_df = region_df.copy()
    region_df["date"] = pd.to_datetime(region_df["date"]).dt.date
    region_df["month"] = region_df["date"].apply(lambda d: (d.year, d.month))

    occurred = _daily_eq_occurred(region_df)

    # Step 1: single highest-risk-score row per calendar month -> "the prediction"
    idx = region_df.groupby("month")["risk_score"].idxmax()
    predictions = region_df.loc[idx]
    n_predictions = len(predictions)

    # Step 2: hit = actual EQ anywhere in region within +/- window_days of predicted date
    hits = sum(
        _window_has_eq(occurred, row["date"], window_days)
        for _, row in predictions.iterrows()
    )
    hit_rate = hits / n_predictions if n_predictions else 0.0

    # Step 4: base_rate = fraction of all centered +/- windows with >=1 actual EQ
    base_rate = _centered_window_base_rate(occurred, window_days)

    lift = hit_rate / base_rate if base_rate > 0 else float("nan")

    p_value = (
        binomtest(hits, n=n_predictions, p=base_rate, alternative="greater").pvalue
        if n_predictions and base_rate > 0
        else float("nan")
    )

    result = {
        "region": region_name,
        "n_predictions": n_predictions,
        "hits": hits,
        "hit_rate": round(hit_rate, 4),
        "base_rate": round(base_rate, 4),
        "lift": round(lift, 4) if lift == lift else None,  # NaN check
        "p_value": p_value if p_value == p_value else None,
    }
    logger.info(
        "%s: n=%d hits=%d hit_rate=%.4f base_rate=%.4f lift=%s p_value=%s",
        region_name, n_predictions, hits, hit_rate, base_rate,
        result["lift"], result["p_value"],
    )
    return result


def main():
    df = pd.read_parquet(REGIONS_PARQUET)

    new_regions = [
        "Caribbean",
        "Mediterranean",
        "South Asia",
        "Middle East",
        "Pacific Ring Asia/Oceania",
    ]
    sanity_check_countries = ["Mexico", "Peru", "Chile"]

    results = []
    for region_name in new_regions:
        subset = df[df["region"] == region_name]
        results.append(score_region(subset, region_name))

    for country in sanity_check_countries:
        subset = df[df["country"] == country]
        results.append(score_region(subset, country))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Wrote %s", OUTPUT_PATH)

    return results


if __name__ == "__main__":
    main()
