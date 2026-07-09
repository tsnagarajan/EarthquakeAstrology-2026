"""pipeline/model/add_regions.py

Adds a 'region' column (via assign_region_by_latlon on grid_lat/grid_lon) and
a 'risk_score' column (model predicted probability) to the 2000-2026 test
set, writing a lightweight output parquet for regional scoring.

feature_matrix_test.parquet has no predicted-probability column — the model
has never been run against the full 2000-2026 test set (train_eval.py only
scores the 2010-2026 holdout, and export_predictions.py only scores
March-Dec 2026). Generating risk_score requires one inference pass over all
8.89M rows, so it's folded into this same row-group read rather than reading
the 818-column, ~30MB-on-disk / multi-GB-decompressed parquet a second time.

The 813 raw feature columns are dropped from the output — only metadata,
region, and risk_score are kept — since nothing downstream needs them and
keeping them would make the output parquet far larger for no benefit.

Does NOT touch feature_matrix_train.parquet.
"""
import json
import logging
import os

import joblib
import pandas as pd
import pyarrow.parquet as pq

from pipeline.features.regions import assign_region_by_latlon

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_PARQUET = "data/processed/feature_matrix_test.parquet"
FEATURE_COLS_JSON = "data/processed/feature_columns.json"
CLASSIFIER_PATH = "data/models/eq_classifier.pkl"
OUTPUT_PATH = "data/processed/feature_matrix_test_with_regions.parquet"

META_COLS = ["date", "EQIndicator", "grid_lat", "grid_lon", "country"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.add_regions")


def main():
    with open(FEATURE_COLS_JSON) as f:
        feature_cols = json.load(f)
    logger.info("Loaded %d feature columns", len(feature_cols))

    logger.info("Loading model from %s", CLASSIFIER_PATH)
    model = joblib.load(CLASSIFIER_PATH)
    logger.info("Model loaded: %s", type(model).__name__)

    pf = pq.ParquetFile(TEST_PARQUET)
    chunks = []
    processed = 0

    for rg_idx in range(pf.metadata.num_row_groups):
        rg = pf.read_row_group(rg_idx, columns=feature_cols + META_COLS).to_pandas()

        X_chunk = rg[feature_cols].astype("float32").to_numpy(dtype="float32")
        risk_score = model.predict_proba(X_chunk)[:, 1].astype("float32")

        region = [
            assign_region_by_latlon(lat, lon)
            for lat, lon in zip(rg["grid_lat"], rg["grid_lon"])
        ]

        out_chunk = rg[META_COLS].copy()
        out_chunk["region"] = pd.Categorical(region)
        out_chunk["risk_score"] = risk_score
        chunks.append(out_chunk)

        processed += len(rg)
        logger.info(
            "Row group %d/%d processed (%d rows, %d total)",
            rg_idx + 1, pf.metadata.num_row_groups, len(rg), processed,
        )

    result = pd.concat(chunks, ignore_index=True)
    logger.info("Total rows: %d", len(result))

    region_counts = result["region"].value_counts()
    print("\nRegion value_counts:")
    print(region_counts.to_string())

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    result.to_parquet(OUTPUT_PATH, index=False)
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    logger.info("Wrote %s (%.1f MB)", OUTPUT_PATH, size_mb)

    return result


if __name__ == "__main__":
    main()
