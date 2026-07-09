"""pipeline/model/train_eval.py

Model selection: train Lasso LogisticRegression and XGBClassifier on the
pre-2000 internal training set, evaluate both on the post-2000 holdout
using MCC and F1, select the winner by highest MCC, derive threshold from
the precision-recall curve, and write data/models/eval_report.json.

Memory strategy:
- Training set (pre-2000, after 10:1 downsampling): ~300k rows × 813 cols ≈ 1GB at float32
  → loaded fully into memory
- Holdout (post-2000): 8.8M rows × 813 cols → too large for 16GB RAM
  → predicted in row-group chunks using pyarrow; only probabilities + labels accumulated
"""
import datetime
import json
import logging
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
)

from pipeline.model.classifiers import (
    LOGISTIC_REGRESSION_MODEL,
    XGB_CLASSIFIER_MODEL,
    build_logistic_regression,
    build_xgb_classifier,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_SPLIT_DATE = datetime.date(2000, 1, 1)
PHASE2_SPLIT_DATE = datetime.date(2000, 1, 1)
TRAIN_PARQUET = "data/processed/feature_matrix_train.parquet"
TEST_PARQUET = "data/processed/feature_matrix_test.parquet"
FEATURE_COLS_JSON = "data/processed/feature_columns.json"
EVAL_REPORT_PATH = "data/models/eval_report.json"
EXPECTED_FEATURE_COUNT = 813

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.train_eval")


# ---------------------------------------------------------------------------
# Step 1: Load the preprocessed training set
# ---------------------------------------------------------------------------

def load_training_set(feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Build X_train, y_train from the canonical pre-2000 training parquet."""
    meta_cols = ["date", "EQIndicator", "grid_lat", "grid_lon", "country"]
    needed_cols = feature_cols + meta_cols

    logger.info("Reading train parquet (pre-2000): %s", TRAIN_PARQUET)
    train_df = pd.read_parquet(TRAIN_PARQUET, columns=needed_cols)
    train_df[feature_cols] = train_df[feature_cols].astype("float32")
    logger.info(
        "Training set: %d rows (positive=%d, negative=%d)",
        len(train_df),
        int((train_df["EQIndicator"] == 1).sum()),
        int((train_df["EQIndicator"] == 0).sum()),
    )

    X_train = train_df[feature_cols].to_numpy(dtype="float32")
    y_train = train_df["EQIndicator"].to_numpy()
    assert X_train.shape[1] == EXPECTED_FEATURE_COUNT, (
        f"Expected {EXPECTED_FEATURE_COUNT} features, got {X_train.shape[1]}"
    )
    logger.info("X_train shape: %s", X_train.shape)
    return X_train, y_train


# ---------------------------------------------------------------------------
# Step 2: Chunked holdout prediction (avoids loading 17GB at once)
# ---------------------------------------------------------------------------

def predict_holdout_chunked(
    models: list, feature_cols: list[str]
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Predict probabilities for the post-2000 holdout in row-group chunks.

    The post-2000 holdout parquet is 8.8M rows × 813 float32 cols — too large
    for 16GB RAM. We iterate over pyarrow row groups, predict in chunks, and
    accumulate only the probabilities (float32) + labels.

    Args:
        models: List of fitted sklearn/xgboost models to evaluate.
        feature_cols: Ordered list of 813 feature column names.

    Returns:
        y_true: array of shape (n_holdout,) with EQIndicator labels
        y_probs: list of arrays of shape (n_holdout,), one per model
    """
    pf = pq.ParquetFile(TEST_PARQUET)
    n_models = len(models)

    y_true_parts: list[np.ndarray] = []
    y_prob_parts: list[list[np.ndarray]] = [[] for _ in range(n_models)]

    holdout_rows = 0
    for rg_idx in range(pf.metadata.num_row_groups):
        # Read row group (only needed columns)
        rg = pf.read_row_group(
            rg_idx, columns=feature_cols + ["date", "EQIndicator"]
        ).to_pandas()

        # Filter to holdout rows (post-2000)
        rg = rg[rg["date"].apply(lambda d: d >= EVAL_SPLIT_DATE)]
        if len(rg) == 0:
            continue

        rg[feature_cols] = rg[feature_cols].astype("float32")
        X_chunk = rg[feature_cols].to_numpy(dtype="float32")
        y_chunk = rg["EQIndicator"].to_numpy()
        y_true_parts.append(y_chunk)

        for m_idx, model in enumerate(models):
            prob_chunk = model.predict_proba(X_chunk)[:, 1].astype("float32")
            y_prob_parts[m_idx].append(prob_chunk)

        holdout_rows += len(rg)
        if holdout_rows % 500_000 < len(rg):
            logger.info("Holdout prediction progress: %d rows processed", holdout_rows)

    logger.info("Holdout prediction complete: %d total rows", holdout_rows)

    y_true = np.concatenate(y_true_parts)
    y_probs = [np.concatenate(parts) for parts in y_prob_parts]
    return y_true, y_probs


# ---------------------------------------------------------------------------
# Step 3: Evaluate metrics for each model
# ---------------------------------------------------------------------------

def evaluate_model(
    model_name: str, y_true: np.ndarray, y_prob: np.ndarray
) -> dict:
    """Compute PR-curve threshold, F1, MCC, confusion matrix for one model."""
    # Threshold selection: argmax F1 from precision-recall curve
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    # precision/recall have len(thresholds)+1 entries; slice [:-1] to align
    f1_scores = (
        2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-8)
    )
    best_idx = int(np.argmax(f1_scores))
    threshold = float(thresholds[best_idx])

    # Evaluate at chosen threshold
    y_pred = (y_prob >= threshold).astype(int)
    f1 = float(f1_score(y_true, y_pred))
    mcc = float(matthews_corrcoef(y_true, y_pred))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    logger.info(
        "%s — MCC=%.4f  F1=%.4f  threshold=%.4f", model_name, mcc, f1, threshold
    )

    return {
        "model": model_name,
        "f1": f1,
        "mcc": mcc,
        "threshold": threshold,
        "confusion_matrix": {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)},
    }


# ---------------------------------------------------------------------------
# Step 4: Select winner and write eval_report.json
# ---------------------------------------------------------------------------

def select_winner_and_write_report(
    results: list[dict], model_objects: list
) -> dict:
    """Select the model with highest MCC; write eval_report.json."""
    winner = max(results, key=lambda r: r["mcc"])
    winner_name = winner["model"]
    logger.info(
        "Winner: %s (MCC=%.4f, F1=%.4f)", winner_name, winner["mcc"], winner["f1"]
    )

    report = {
        "model_used": winner_name,
        "f1_score": round(winner["f1"], 6),
        "mcc": round(winner["mcc"], 6),
        "threshold": round(winner["threshold"], 6),
        "eval_split_date": EVAL_SPLIT_DATE.isoformat(),
        "confusion_matrix": winner["confusion_matrix"],
        "both_models": [
            {"model": r["model"], "f1": round(r["f1"], 6), "mcc": round(r["mcc"], 6)}
            for r in results
        ],
    }

    os.makedirs("data/models", exist_ok=True)
    with open(EVAL_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Evaluation report written to %s", EVAL_REPORT_PATH)
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Run the full model selection and evaluation pipeline."""
    os.makedirs("data/models", exist_ok=True)

    # Load feature column names
    with open(FEATURE_COLS_JSON) as f:
        feature_cols = json.load(f)
    logger.info("Loaded %d feature columns", len(feature_cols))

    # Build training arrays from the canonical pre-2000 parquet.
    X_train, y_train = load_training_set(feature_cols)

    # Train both models
    logger.info("Training LogisticRegression ...")
    logreg = build_logistic_regression()
    logreg.fit(X_train, y_train)
    logger.info("LogisticRegression training complete")

    logger.info("Training XGBClassifier ...")
    xgb = build_xgb_classifier()
    xgb.fit(X_train, y_train)
    logger.info("XGBClassifier training complete")

    del X_train
    del y_train

    # Chunked holdout prediction (avoids OOM)
    model_names = [LOGISTIC_REGRESSION_MODEL, XGB_CLASSIFIER_MODEL]
    models = [logreg, xgb]
    logger.info("Running chunked holdout prediction for both models ...")
    y_true, y_probs = predict_holdout_chunked(models, feature_cols)

    # Evaluate each model
    results = [
        evaluate_model(name, y_true, y_prob)
        for name, y_prob in zip(model_names, y_probs)
    ]

    # Select winner and write report
    report = select_winner_and_write_report(results, models)

    # Return winner model object and feature_cols for potential downstream reuse
    winner_name = report["model_used"]
    winner_model = models[model_names.index(winner_name)]
    return winner_model, feature_cols


if __name__ == "__main__":
    main()
