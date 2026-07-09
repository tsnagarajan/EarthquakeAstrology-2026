"""pipeline/model/retrain.py

Retrain the winning classifier (from eval_report.json) on the full 1900-2026
dataset and serialize it to data/models/eq_classifier.pkl.

Also writes data/models/feature_importance.json for use by export_predictions.py.

Memory strategy:
- Pre-2000 train parquet (already 10:1 downsampled in Phase 2): ~263k rows
- Post-2000 test parquet (not downsampled): load all, apply 10:1 downsampling
- Combined after downsampling: ~300-400k rows x 813 cols ≈ 1-2 GB at float32
  -> loaded fully into memory (manageable)
"""
import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from pipeline.features.engineering import downsample_negatives
from pipeline.model.classifiers import build_classifier

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRAIN_PARQUET = "data/processed/feature_matrix_train.parquet"
TEST_PARQUET = "data/processed/feature_matrix_test.parquet"
FEATURE_COLS_JSON = "data/processed/feature_columns.json"
EVAL_REPORT_PATH = "data/models/eval_report.json"
CLASSIFIER_PATH = "data/models/eq_classifier.pkl"
FEATURE_IMPORTANCE_PATH = "data/models/feature_importance.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.retrain")


def build_winner_model(model_name: str):
    """Return the configured winner model for final serialization."""
    return build_classifier(model_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Run the full retrain pipeline on 1900-2026 data and serialize the model."""
    os.makedirs("data/models", exist_ok=True)

    # Step 1: Load eval_report.json to find the winning model
    logger.info("Loading eval report from %s", EVAL_REPORT_PATH)
    with open(EVAL_REPORT_PATH) as f:
        report = json.load(f)
    model_name = report["model_used"]
    logger.info("Retraining winner model: %s", model_name)

    # Step 2: Load feature columns
    with open(FEATURE_COLS_JSON) as f:
        feature_cols = json.load(f)
    logger.info("Loaded %d feature columns", len(feature_cols))

    meta_cols = ["date", "EQIndicator", "grid_lat", "grid_lon", "country"]
    needed_cols = feature_cols + meta_cols

    # Step 3: Load both parquets and downsample post-2000 slice
    # Pre-2000 from train parquet (already 10:1 downsampled in Phase 2)
    logger.info("Reading train parquet (pre-2000, already downsampled): %s", TRAIN_PARQUET)
    pre2000 = pd.read_parquet(TRAIN_PARQUET, columns=needed_cols)
    pre2000[feature_cols] = pre2000[feature_cols].astype("float32")
    logger.info("Pre-2000 partition: %d rows", len(pre2000))

    # Post-2000 from test parquet — apply 10:1 downsampling here
    logger.info("Reading test parquet (post-2000, all dates): %s", TEST_PARQUET)
    post2000 = pd.read_parquet(TEST_PARQUET, columns=needed_cols)
    post2000[feature_cols] = post2000[feature_cols].astype("float32")
    logger.info(
        "Post-2000 partition before downsampling: %d rows "
        "(positive=%d, negative=%d)",
        len(post2000),
        (post2000["EQIndicator"] == 1).sum(),
        (post2000["EQIndicator"] == 0).sum(),
    )

    # Apply 10:1 downsampling to the post-2000 slice
    post2000_ds = downsample_negatives(post2000, ratio=10, random_state=42)
    del post2000
    logger.info("Post-2000 after downsampling: %d rows", len(post2000_ds))

    # Concatenate pre-2000 + downsampled post-2000 = full retrain dataset
    final_train = pd.concat([pre2000, post2000_ds], ignore_index=True)
    del pre2000
    del post2000_ds
    logger.info("Full retrain dataset: %d rows", len(final_train))

    # Step 4: Select feature columns and train
    X = final_train[feature_cols].to_numpy(dtype="float32")
    y = final_train["EQIndicator"].to_numpy()
    assert X.shape[1] == 813, f"Expected 813 features, got {X.shape[1]}"
    del final_train
    logger.info("Training arrays prepared: X=%s, y=%s", X.shape, y.shape)

    # Instantiate the winner model with the same hyperparameters used in train_eval.py
    model = build_winner_model(model_name)

    logger.info("Fitting %s on full 1900-2026 dataset ...", model_name)
    model.fit(X, y)
    logger.info("Training complete")
    del X
    del y

    # Step 5: Extract and save feature importance
    if model_name == "LogisticRegression":
        importances = np.abs(model.coef_[0])
    else:  # XGBClassifier
        importances = model.feature_importances_

    importance_map = dict(zip(feature_cols, importances.tolist()))
    with open(FEATURE_IMPORTANCE_PATH, "w") as f:
        json.dump(importance_map, f)
    logger.info("Feature importance written to %s", FEATURE_IMPORTANCE_PATH)

    # Step 6: Serialize the model
    joblib.dump(model, CLASSIFIER_PATH, compress=3)
    size_kb = Path(CLASSIFIER_PATH).stat().st_size / 1024
    logger.info(
        "Model serialized to %s (%.0f KB)", CLASSIFIER_PATH, size_kb
    )

    logger.info("Retrain complete.")


if __name__ == "__main__":
    main()
