"""pipeline/model/export_predictions.py

Generate 2026 feature rows (March-December), run inference with the retrained
classifier, and write web/public/data/predictions.json.

The 2026 feature rows are loaded from data/processed/feature_matrix_test.parquet
(row group 26 contains all of 2026) which already has the 813 features encoded
by the same Phase 2 pipeline that produced the training data — no risk of
inconsistency vs. re-running encoding from raw ephemeris.

Predictions schema per record:
  date (ISO string), country, lat (grid_lat), lon (grid_lon),
  risk_score (float 0-1), top_planetary_aspects (list of <=3 strings)

Only records with risk_score >= threshold (from eval_report.json) are included.
"""
import datetime
import json
import logging
import os
from pathlib import Path

import joblib
import pandas as pd
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASSIFIER_PATH = "data/models/eq_classifier.pkl"
EVAL_REPORT_PATH = "data/models/eval_report.json"
FEATURE_IMPORTANCE_PATH = "data/models/feature_importance.json"
FEATURE_COLS_JSON = "data/processed/feature_columns.json"
NAKSHATRA_ENCODER_PATH = "data/processed/nakshatra_encoder.pkl"
EPHEMERIS_CSV = "data/raw/ephemeris.csv"
USGS_CSV = "data/raw/usgs_earthquakes.csv"
TEST_PARQUET = "data/processed/feature_matrix_test.parquet"
PREDICTIONS_PATH = "web/public/data/predictions.json"
PUBLIC_EVAL_REPORT_PATH = "web/public/data/eval_report.json"

PRED_START = datetime.date(2026, 3, 1)
PRED_END = datetime.date(2026, 12, 31)
ASPECT_SUFFIXES = ("_conjunction", "_opposition", "_trine", "_square", "_sextile")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.export_predictions")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def top_aspects(row_dict: dict, aspect_cols: list, importance_map: dict) -> list:
    """Return top <=3 active aspect column names sorted by feature importance."""
    active = [c for c in aspect_cols if row_dict.get(c, 0) == 1]
    ranked = sorted(active, key=lambda c: importance_map.get(c, 0), reverse=True)
    return ranked[:3]


def load_2026_features(feature_cols: list) -> pd.DataFrame:
    """Load March-December 2026 feature rows from the test parquet.

    The test parquet was produced by the same Phase 2 pipeline that generated
    training data, so all 813 features are already correctly encoded.
    We read only the last row group (row group 26 contains all 2026 dates).
    """
    logger.info("Loading 2026 features from test parquet: %s", TEST_PARQUET)
    meta_cols = ["date", "EQIndicator", "grid_lat", "grid_lon", "country"]
    needed_cols = feature_cols + meta_cols

    pf = pq.ParquetFile(TEST_PARQUET)
    n_rgs = pf.metadata.num_row_groups

    # Find row groups containing 2026 data (typically the last one)
    pred_rows_list = []
    for rg_idx in range(n_rgs):
        rg = pf.read_row_group(rg_idx, columns=["date"]).to_pandas()
        has_2026 = rg["date"].apply(lambda d: d.year >= 2026).any()
        if not has_2026:
            continue
        # Load full row group with needed columns
        rg_full = pf.read_row_group(rg_idx, columns=needed_cols).to_pandas()
        rg_full[feature_cols] = rg_full[feature_cols].astype("float32")
        # Filter to March-December 2026
        mask = rg_full["date"].apply(lambda d: PRED_START <= d <= PRED_END)
        pred_rows_list.append(rg_full[mask])

    if not pred_rows_list:
        raise RuntimeError(
            f"No rows found for {PRED_START} to {PRED_END} in {TEST_PARQUET}"
        )

    pred_rows = pd.concat(pred_rows_list, ignore_index=True)
    logger.info(
        "Prediction matrix: %d rows (%d date-cells for March-Dec 2026)",
        len(pred_rows),
        len(pred_rows),
    )

    # Confirm 306 unique dates (March 1 to December 31, 2026)
    unique_dates = pred_rows["date"].unique()
    assert len(unique_dates) == 306, (
        f"Expected 306 unique dates (March-Dec 2026), got {len(unique_dates)}"
    )

    return pred_rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Generate predictions.json for March-December 2026."""
    os.makedirs("web/public/data", exist_ok=True)

    # Step 1: Load model, eval report, feature importance, feature columns
    logger.info("Loading model from %s", CLASSIFIER_PATH)
    model = joblib.load(CLASSIFIER_PATH)
    logger.info("Model loaded: %s", type(model).__name__)

    with open(EVAL_REPORT_PATH) as f:
        report = json.load(f)
    threshold = report["threshold"]
    logger.info("Threshold from eval_report.json: %.6f", threshold)
    Path("web/public/data").mkdir(parents=True, exist_ok=True)
    with open(PUBLIC_EVAL_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Public eval report written to %s", PUBLIC_EVAL_REPORT_PATH)

    with open(FEATURE_IMPORTANCE_PATH) as f:
        importance_map: dict = json.load(f)
    logger.info("Feature importance map loaded (%d entries)", len(importance_map))

    with open(FEATURE_COLS_JSON) as f:
        feature_cols: list = json.load(f)
    assert len(feature_cols) == 813, f"Expected 813 feature cols, got {len(feature_cols)}"

    # Derive aspect column list
    aspect_cols = [c for c in feature_cols if c.endswith(ASPECT_SUFFIXES)]
    logger.info("Aspect columns: %d", len(aspect_cols))

    # Step 2-3: Load 2026 feature rows from the test parquet
    pred_rows = load_2026_features(feature_cols)

    # Step 4: Run inference
    X_pred = pred_rows[feature_cols].to_numpy(dtype="float32")
    assert X_pred.shape[1] == 813, f"Expected 813 cols, got {X_pred.shape[1]}"
    logger.info("Running inference on %d rows ...", len(X_pred))
    risk_scores = model.predict_proba(X_pred)[:, 1]
    pred_rows = pred_rows.copy()
    pred_rows["risk_score"] = risk_scores
    logger.info("Inference complete")

    # Step 5: Apply the evaluation threshold before selecting display records.
    above_threshold = pred_rows[pred_rows["risk_score"] >= threshold].copy()
    logger.info(
        "Rows at or above threshold %.6f: %d",
        threshold,
        len(above_threshold),
    )
    if above_threshold.empty:
        Path("web/public/data").mkdir(parents=True, exist_ok=True)
        with open(PREDICTIONS_PATH, "w") as f:
            json.dump([], f, indent=2)
        logger.warning("No prediction rows met threshold; wrote empty predictions.json")
        return

    # Step 6: Select top N days per calendar month by per-date max risk score.
    # This ensures year-round coverage rather than letting globally high months
    # (e.g. March, November) dominate the output.
    TOP_DAYS_PER_MONTH = 3
    date_str_series = above_threshold["date"].apply(
        lambda d: d.isoformat() if hasattr(d, "isoformat") else str(d)
    )
    date_max_scores = above_threshold.groupby(date_str_series)["risk_score"].max().reset_index()
    date_max_scores.columns = ["date", "max_risk_score"]
    date_max_scores["month"] = date_max_scores["date"].str[:7]
    high_risk_dates = set(
        date_max_scores
        .sort_values("max_risk_score", ascending=False)
        .groupby("month")
        .head(TOP_DAYS_PER_MONTH)["date"]
    )
    above = above_threshold[date_str_series.isin(high_risk_dates)].copy()
    logger.info(
        "High-risk dates (top %d per month): %d dates across %d months, %d rows",
        TOP_DAYS_PER_MONTH, len(high_risk_dates),
        date_max_scores[date_max_scores["date"].isin(high_risk_dates)]["month"].nunique(),
        len(above),
    )

    # Step 7: Keep only top 10 rows per date (UI shows top 3 locations; 10 gives buffer)
    above = (
        above.sort_values("risk_score", ascending=False)
        .groupby(date_str_series[above.index], sort=False)
        .head(10)
    )
    logger.info("After top-10 per date cap: %d rows", len(above))

    # Step 8: Assemble JSON records
    records = []
    for _, row in above.iterrows():
        d = row["date"]
        records.append({
            "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
            "country": row["country"],
            "lat": int(row["grid_lat"]),
            "lon": int(row["grid_lon"]),
            "risk_score": round(float(row["risk_score"]), 4),
            "top_planetary_aspects": top_aspects(row.to_dict(), aspect_cols, importance_map),
        })

    # Step 9: Write predictions.json
    Path("web/public/data").mkdir(parents=True, exist_ok=True)
    with open(PREDICTIONS_PATH, "w") as f:
        json.dump(records, f, indent=2)
    size_kb = Path(PREDICTIONS_PATH).stat().st_size / 1024
    logger.info(
        "predictions.json: %d records, %.0f KB", len(records), size_kb
    )
    if len(records) > 5000:
        logger.warning(
            "predictions.json has %d records (> 5000 threshold) — consider raising threshold",
            len(records),
        )
    if size_kb > 2048:
        logger.warning(
            "predictions.json is %.0f KB (> 2MB threshold) — consider raising threshold",
            size_kb,
        )

    logger.info("Export complete. predictions.json written to %s", PREDICTIONS_PATH)


if __name__ == "__main__":
    main()
