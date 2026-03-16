# Phase 3: Model Training and Prediction Export - Research

**Researched:** 2026-03-16
**Domain:** scikit-learn Pipeline, XGBoost classifier, precision-recall threshold selection, joblib serialization, JSON export
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Training Data Strategy**
- Two-stage training: model selection uses 1900–2010 train / 2010–2026 holdout; final prediction model retrains on full 1900–2026 data
- Phase 3 re-splits internally: read both Phase 2 parquets (`feature_matrix_train.parquet` + `feature_matrix_test.parquet`), concatenate, then partition at `2010-01-01`
- Temporal split constant: `EVAL_SPLIT_DATE = datetime.date(2010, 1, 1)` — rows with `date < 2010-01-01` = model selection train set; `date >= 2010-01-01` = holdout
- Downsampling: 10:1 negative-to-positive ratio applied to the training partition, consistent with Phase 2. Final retrain (1900–2026) also uses 10:1 downsampling. Test/holdout is never downsampled.
- Class imbalance handling: downsampling only — no additional SMOTE or class_weight='balanced' in the classifier

**Model Selection**
- Candidates: Lasso Logistic Regression (C=1, penalty='l1', solver='liblinear') vs XGBoost (n_estimators=100, max_depth=6, use_label_encoder=False)
- Winner criterion: highest MCC on the 2010–2026 holdout
- No cross-validation / hyperparameter tuning — train once with fixed params
- Both models evaluated and logged to eval_report.json

**Evaluation Report**
- Format: JSON at `data/models/eval_report.json`
- Contents: `model_used`, `f1_score`, `mcc`, `confusion_matrix` (object with `tp`, `fp`, `fn`, `tn`), `threshold`, `eval_split_date`, `both_models` (array with f1/mcc for each candidate)
- Threshold stored here — prediction export script reads threshold from eval_report.json; no hard-coding

**Risk Threshold Selection**
- Method: Precision-recall curve on the 2010–2026 holdout; threshold selected at best F1 operating point (argmax of F1 across all PR threshold values)
- Stored in eval_report.json as `threshold` field

**top_planetary_aspects Derivation**
- Source: aspect boolean columns that are True/1 for the given date row in the feature matrix
- Count: top 3 aspects per entry; if fewer than 3 are active, include all active ones
- Ranking: sort active aspects by the winning model's feature importance (`coef_` for LogReg, `feature_importances_` for XGBoost) — highest-importance active aspects listed first
- Feature importance computed once after training and reused for all prediction rows; no per-row SHAP

**Final Prediction Export**
- Scope: March–December 2026 (2026-03-01 through 2026-12-31)
- Model: winning model retrained on full 1900–2026 data (10:1 downsampled)
- Schema per entry: `date` (ISO string), `country`, `lat` (grid_lat), `lon` (grid_lon), `risk_score` (float 0–1), `top_planetary_aspects` (array of ≤3 strings)
- Filter: only entries with `risk_score >= threshold` (threshold from eval_report.json)
- Output path: `web/public/data/predictions.json`

### Claude's Discretion
- Exact scikit-learn Pipeline wrapping (whether to use Pipeline API or fit models directly)
- How to generate 2026 feature rows (whether to reuse Phase 2 logic or inline ephemeris reads)
- File size monitoring / warning if predictions.json exceeds a reasonable size
- Logging verbosity and progress reporting during training runs

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODEL-01 | Model trains on 1900–2000 earthquake + astrological feature data | Two-stage split: CONTEXT.md locks 1900–2010 for model selection train; feature_matrix_train.parquet (pre-2000, downsampled) + portion of feature_matrix_test.parquet (2000–2010) form the model selection train set after internal re-split |
| MODEL-02 | Model evaluated on 2000–2026 held-out test data using F1 score and MCC (not accuracy) | CONTEXT.md locks 2010–2026 holdout for evaluation; `sklearn.metrics.f1_score`, `matthews_corrcoef`, `confusion_matrix` cover this; threshold from PR curve |
| MODEL-03 | Model predicts both date AND geographic region (country + lat/lon grid cell) | Feature matrix already has grid_lat, grid_lon, country at row level — prediction output carries these through; no architectural change needed |
| MODEL-04 | At least two classifier types compared with class imbalance handling | Lasso LogReg + XGBoost with fixed params; downsampling (10:1) is the imbalance mechanism; both logged in eval_report.json |
| MODEL-05 | Trained model saved to disk (joblib/pickle) for reproducible prediction runs | joblib 1.5.3 available; `joblib.dump(pipeline, 'data/models/eq_classifier.pkl')`; load via `joblib.load` at predict time |
| PRED-01 | Predictions for March–December 2026 exported as predictions.json in Next.js public/data/ | 2026 feature rows must be generated from ephemeris.csv (dates 2026-03-01–2026-12-31); encoding must reuse nakshatra_encoder.pkl; output to web/public/data/predictions.json |
| PRED-02 | Predictions JSON schema: date, country, lat, lon, risk_score, top_planetary_aspects | Schema locked in CONTEXT.md; top_planetary_aspects derived from aspect boolean columns ranked by feature importance |
| PRED-03 | Only predictions above risk threshold included in export | Threshold from eval_report.json; filter `risk_score >= threshold` before writing JSON |
</phase_requirements>

---

## Summary

Phase 3 is a three-script pipeline: (1) train two classifiers on the model-selection split, evaluate on holdout, write eval_report.json; (2) retrain the winner on full 1900–2026 data and serialize to eq_classifier.pkl; (3) generate 2026 feature rows from raw ephemeris, run inference, and write predictions.json. All three stages re-use the 813-column feature_columns.json manifest and the nakshatra_encoder.pkl from Phase 2 to guarantee column alignment.

The critical implementation concern is **2026 feature row generation**. The Phase 2 parquets do not extend past 2026 dates present in ephemeris.csv (ephemeris.csv covers the full date range including 2026). Phase 3 must read ephemeris.csv, apply the same `encode_ephemeris` + `apply_nakshatra_encoding(encoder)` pipeline used in Phase 2, broadcast each encoded day to all active grid cells (from usgs_earthquakes.csv), then slice to exactly the 813 feature columns in feature_columns.json. The `nakshatra_encoder.pkl` must be **loaded, not re-fit** to prevent test leakage.

The second concern is the **internal temporal re-split**. The Phase 2 parquets were split at 2000-01-01 (FEAT-03), but Phase 3's model selection split is at 2010-01-01. This means Phase 3 concatenates both parquets, then re-partitions at 2010-01-01. The train portion (1900–2010) needs **additional downsampling** applied to the 2000–2010 slice because `feature_matrix_test.parquet` is not downsampled. The pre-2000 slice is already downsampled at 10:1 and must not be downsampled again.

**Primary recommendation:** Implement three scripts — `pipeline/model/train_eval.py` (model selection + eval report), `pipeline/model/retrain.py` (full retrain + serialize), `pipeline/model/export_predictions.py` (2026 inference + JSON). Share helpers in `pipeline/model/__init__.py` or a `utils.py` module.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.8.0 | Pipeline, LogisticRegression, metrics, precision_recall_curve | Already installed; Pipeline API prevents leakage; all metrics built-in |
| xgboost | 3.2.0 | XGBClassifier | Already installed; `use_label_encoder=False` required in older API; not needed in 3.x |
| joblib | 1.5.3 | Model serialization (`dump`/`load`) | Already installed; preferred over pickle for sklearn; handles numpy arrays efficiently |
| pandas | 3.0.1 | Parquet reads, feature selection, JSON export | Already installed; `read_parquet`, boolean masking |
| numpy | 2.4.3 | Array ops, argmax for threshold selection | Already installed |
| pyarrow | 23.0.1 | Parquet engine for pandas | Already installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sklearn.metrics.matthews_corrcoef | (in scikit-learn 1.8.0) | MCC computation | Winner selection criterion |
| sklearn.metrics.precision_recall_curve | (in scikit-learn 1.8.0) | PR curve for threshold selection | Threshold derivation step |
| sklearn.metrics.f1_score | (in scikit-learn 1.8.0) | F1 evaluation metric | Both model comparison and threshold argmax |
| sklearn.linear_model.LogisticRegression | (in scikit-learn 1.8.0) | Lasso LogReg candidate | C=1, penalty='l1', solver='liblinear' |
| xgboost.XGBClassifier | (in xgboost 3.2.0) | Gradient boosting candidate | n_estimators=100, max_depth=6 |
| json (stdlib) | Python 3.12 | eval_report.json and predictions.json output | Standard library; no dependency needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| joblib.dump | pickle | joblib is preferred for sklearn objects — handles numpy arrays, compression; pickle works but joblib is the sklearn-recommended path |
| Fixed params (no tuning) | GridSearchCV / Optuna | Tuning is out of scope per CONTEXT.md; fixed params are reproducible and avoid temporal leakage risk from CV |
| 10:1 downsampling only | class_weight='balanced' | CONTEXT.md locks downsampling as the sole imbalance mechanism |

**Installation:** No new packages needed — all are already in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure

```
pipeline/
├── model/
│   ├── __init__.py
│   ├── train_eval.py        # Wave 1: model selection, eval_report.json
│   ├── retrain.py           # Wave 2: full retrain on 1900–2026, eq_classifier.pkl
│   └── export_predictions.py # Wave 3: 2026 inference, predictions.json
data/
├── models/                  # Created by Phase 3 (mkdir -p)
│   ├── eq_classifier.pkl    # Serialized winning model pipeline
│   └── eval_report.json     # Evaluation metrics + threshold
web/
└── public/
    └── data/
        └── predictions.json # Phase 4 reads this at build time
```

### Pattern 1: Internal Temporal Re-Split

**What:** Load both Phase 2 parquets, concatenate, then partition at 2010-01-01. The pre-2000 slice is already downsampled (10:1). The 2000–2010 slice from feature_matrix_test.parquet is not downsampled and needs downsampling before model selection training.

**When to use:** Every training run in Phase 3.

**Example:**
```python
import datetime
import pandas as pd
from pipeline.features.engineering import downsample_negatives

EVAL_SPLIT_DATE = datetime.date(2010, 1, 1)

train_df = pd.read_parquet("data/processed/feature_matrix_train.parquet")  # pre-2000, downsampled
test_df  = pd.read_parquet("data/processed/feature_matrix_test.parquet")   # 2000–2026, not downsampled

# CRITICAL: date column is datetime.date objects (not Timestamp) — use .apply for comparison
combined = pd.concat([train_df, test_df], ignore_index=True)
sel_train = combined[combined["date"].apply(lambda d: d < EVAL_SPLIT_DATE)]
holdout   = combined[combined["date"].apply(lambda d: d >= EVAL_SPLIT_DATE)]

# Downsample the 2000–2010 slice from sel_train (pre-2000 is already downsampled)
sel_train_2000_2010 = sel_train[sel_train["date"].apply(lambda d: d >= datetime.date(2000, 1, 1))]
sel_train_pre2000   = sel_train[sel_train["date"].apply(lambda d: d < datetime.date(2000, 1, 1))]
sel_train_2000_2010_ds = downsample_negatives(sel_train_2000_2010, ratio=10, random_state=42)
sel_train_final = pd.concat([sel_train_pre2000, sel_train_2000_2010_ds], ignore_index=True)
```

**Critical pitfall:** `feature_matrix_test.parquet` was noted in STATE.md as potentially corrupted in a committed artifact (ParquetWriter.close() not called). Verify the parquet reads without error as a Wave 0 check. If corrupted, it must be regenerated before Phase 3 can proceed.

### Pattern 2: Feature Column Selection

**What:** Select exactly the 813 columns from feature_columns.json before fitting or predicting. This prevents column-order mismatches between train and predict paths.

**When to use:** Both training and inference paths.

**Example:**
```python
import json

with open("data/processed/feature_columns.json") as f:
    feature_cols = json.load(f)  # 813 feature column names in order

X_train = sel_train_final[feature_cols].to_numpy(dtype="float32")
y_train = sel_train_final["EQIndicator"].to_numpy()
```

### Pattern 3: Classifier Training with Fixed Params

**What:** Train both candidates with fixed hyperparameters. No Pipeline wrapping is required since all encoding was done in Phase 2 — the parquet features are already scaled/encoded. However, scikit-learn Pipeline can still be used as a container for serialization consistency.

**When to use:** Model selection phase.

**Example:**
```python
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

logreg = LogisticRegression(C=1, penalty="l1", solver="liblinear", max_iter=1000, random_state=42)
logreg.fit(X_train, y_train)

xgb = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    random_state=42,
    eval_metric="logloss",  # suppress deprecation warning in xgboost 3.x
)
xgb.fit(X_train, y_train)
```

**Note:** In xgboost 3.x (3.2.0 in this project), `use_label_encoder` is no longer a valid parameter and must be omitted. The CONTEXT.md specifies `use_label_encoder=False` which was valid in xgboost 1.x/2.x — drop it for 3.x or xgboost will raise a `TypeError`.

### Pattern 4: Threshold Selection from Precision-Recall Curve

**What:** Compute PR curve on holdout probabilities, then select the threshold at the argmax of the F1 array.

**When to use:** After model selection, to derive `threshold` for eval_report.json.

**Example:**
```python
import numpy as np
from sklearn.metrics import precision_recall_curve, f1_score, matthews_corrcoef

y_prob = winner_model.predict_proba(X_holdout)[:, 1]
precision, recall, thresholds = precision_recall_curve(y_holdout, y_prob)

# thresholds has len(precision) - 1 entries; last precision/recall pair has no threshold
f1_scores = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-8)
best_idx = np.argmax(f1_scores)
threshold = float(thresholds[best_idx])

# Evaluate at chosen threshold
y_pred = (y_prob >= threshold).astype(int)
mcc = matthews_corrcoef(y_holdout, y_pred)
f1 = f1_score(y_holdout, y_pred)
```

### Pattern 5: Feature Importance for top_planetary_aspects

**What:** Build a mapping from column name to importance score. For each prediction row, find aspect columns that are 1, sort by importance descending, take top 3.

**When to use:** Prediction export step.

**Example:**
```python
# For LogisticRegression: coef_ is shape (1, n_features) for binary
if hasattr(model, "coef_"):
    importances = np.abs(model.coef_[0])  # absolute value for "importance"
else:
    importances = model.feature_importances_

importance_map = dict(zip(feature_cols, importances))

# Aspect column names (subset of feature_cols ending with aspect type suffixes)
ASPECT_SUFFIXES = ("_conjunction", "_opposition", "_trine", "_square", "_sextile")
aspect_cols = [c for c in feature_cols if c.endswith(ASPECT_SUFFIXES)]

def top_aspects(row_dict: dict) -> list[str]:
    """Return top ≤3 active aspect column names sorted by feature importance."""
    active = [c for c in aspect_cols if row_dict.get(c, 0) == 1]
    ranked = sorted(active, key=lambda c: importance_map.get(c, 0), reverse=True)
    return ranked[:3]
```

### Pattern 6: 2026 Feature Row Generation

**What:** Read ephemeris.csv, filter to 2026-03-01 through 2026-12-31, encode using the same Phase 2 logic, broadcast to active grid cells, select feature columns.

**When to use:** Prediction export step.

**Example:**
```python
import pandas as pd
from pipeline.features.engineering import (
    encode_ephemeris, apply_nakshatra_encoding, load_encoder,
    active_cells_list, build_active_cells, build_country_map, build_matrix_year
)

encoder = load_encoder("data/processed/nakshatra_encoder.pkl")  # LOAD, never re-fit
ephe_df = pd.read_csv("data/raw/ephemeris.csv", parse_dates=["date"])
ephe_df = ephe_df.set_index("date")

# Filter to prediction window
mask = (ephe_df.index >= pd.Timestamp("2026-03-01")) & (ephe_df.index <= pd.Timestamp("2026-12-31"))
ephe_2026 = ephe_df[mask]

# Encode
encoded_2026 = encode_ephemeris(ephe_2026)
encoded_2026 = apply_nakshatra_encoding(encoded_2026, encoder)

# Build grid rows using existing build_matrix_year helper
usgs_df = pd.read_csv("data/raw/usgs_earthquakes.csv")
active_cells = active_cells_list(build_active_cells(usgs_df))
country_map  = build_country_map(usgs_df)
# eq_index passed as empty Series — 2026 has no known EQ labels yet
import pandas as pd
empty_eq = pd.Series(dtype=int)
pred_rows = build_matrix_year(encoded_2026, active_cells, empty_eq, country_map)
```

**Alternative:** If raw ephemeris.csv is unavailable at runtime, the fallback is to read from feature_matrix_test.parquet which should contain 2026 dates if ephemeris.csv covered them during Phase 2. Verify coverage before committing to either approach.

### Pattern 7: predictions.json Assembly

**What:** Run inference with the retrained model, filter by threshold, serialize to JSON.

**When to use:** Prediction export step.

**Example:**
```python
import json
from pathlib import Path
import numpy as np

X_pred = pred_rows[feature_cols].to_numpy(dtype="float32")
risk_scores = retrained_model.predict_proba(X_pred)[:, 1]
pred_rows["risk_score"] = risk_scores

# Filter
threshold = eval_report["threshold"]
above = pred_rows[pred_rows["risk_score"] >= threshold].copy()

# Build output records
records = []
for _, row in above.iterrows():
    records.append({
        "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
        "country": row["country"],
        "lat": int(row["grid_lat"]),
        "lon": int(row["grid_lon"]),
        "risk_score": round(float(row["risk_score"]), 4),
        "top_planetary_aspects": top_aspects(row.to_dict()),
    })

Path("web/public/data").mkdir(parents=True, exist_ok=True)
with open("web/public/data/predictions.json", "w") as f:
    json.dump(records, f, indent=2)
```

### Anti-Patterns to Avoid

- **Re-fitting the nakshatra encoder on 2026 data:** Must call `load_encoder("data/processed/nakshatra_encoder.pkl")` and use `.transform()` only. Re-fitting introduces leakage from future data.
- **Using `use_label_encoder=False` in XGBClassifier with xgboost 3.x:** This parameter was removed in xgboost 3.0. Passing it raises `TypeError`. The CONTEXT.md spec is for an older API version.
- **Downsampling the holdout set:** `feature_matrix_test.parquet` (2010–2026 portion) must never be downsampled. Downsampling the holdout inflates F1/MCC.
- **Double-downsampling the pre-2000 slice:** `feature_matrix_train.parquet` is already downsampled at 10:1. Applying `downsample_negatives` again would corrupt the training set.
- **Hard-coding the threshold in export_predictions.py:** Threshold must be read from eval_report.json. Hard-coding breaks the eval→export contract.
- **Using accuracy as a model selection metric:** MCC is the winner criterion. Accuracy is misleading with severe class imbalance.
- **Fitting a scikit-learn StandardScaler inside the Pipeline on the combined data:** All features are already encoded/scaled in Phase 2. No additional scaling is needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Precision-recall curve | Custom threshold sweep loop | `sklearn.metrics.precision_recall_curve` | Handles edge cases (last threshold, tied probabilities); numerically stable |
| MCC computation | Manual 2x2 confusion matrix math | `sklearn.metrics.matthews_corrcoef` | Handles edge cases (zero TP, all-same predictions) without division-by-zero |
| Model serialization | `pickle.dump(model, ...)` directly | `joblib.dump(model, path, compress=3)` | joblib handles large numpy arrays in sklearn objects efficiently; pickle can produce large/slow files |
| Confusion matrix extraction | Manual boolean masking | `sklearn.metrics.confusion_matrix` | Then index as `[[tn, fp],[fn, tp]] = cm.ravel()` |
| Feature importance ranking | SHAP or manual weight extraction | `coef_[0]` (LogReg) or `feature_importances_` (XGBoost) | SHAP is per-row and expensive; static importance is sufficient and already locked by CONTEXT.md |

**Key insight:** The hardest part of this phase is data plumbing (re-split logic, 2026 feature generation, column alignment), not the ML itself. The sklearn/xgboost APIs handle all numeric complexity — don't re-implement metrics.

---

## Common Pitfalls

### Pitfall 1: date Column Comparison with Mixed Types

**What goes wrong:** `combined["date"] < EVAL_SPLIT_DATE` raises `TypeError` or silently produces wrong results when the parquet date column contains `datetime.date` objects but the comparison operand is a `pd.Timestamp` or string.

**Why it happens:** `feature_matrix_train.parquet` stores date as `datetime.date` objects (established in Phase 2 — "object-dtype date index"). pandas 3.x does not automatically coerce `datetime.date` to `pd.Timestamp` for comparisons.

**How to avoid:** Use `.apply(lambda d: d < EVAL_SPLIT_DATE)` where `EVAL_SPLIT_DATE = datetime.date(2010, 1, 1)`. Do not compare against `pd.Timestamp("2010-01-01")` or the string `"2010-01-01"`.

**Warning signs:** `TypeError: '<' not supported between instances of 'datetime.date' and 'Timestamp'`

### Pitfall 2: xgboost 3.x API Changes

**What goes wrong:** Passing `use_label_encoder=False` to `XGBClassifier()` raises `TypeError: __init__() got an unexpected keyword argument 'use_label_encoder'` in xgboost 3.x (3.2.0 is installed).

**Why it happens:** `use_label_encoder` was deprecated in xgboost 1.6 and removed in 3.0. The CONTEXT.md spec (`use_label_encoder=False`) was written for an older version.

**How to avoid:** Omit `use_label_encoder` entirely. Use `eval_metric="logloss"` to suppress the default console warnings.

**Warning signs:** `TypeError: __init__() got an unexpected keyword argument 'use_label_encoder'` at training time.

### Pitfall 3: precision_recall_curve Off-by-One

**What goes wrong:** `precision_recall_curve` returns arrays of length `n+1` for precision and recall, but only `n` for thresholds. Using `thresholds[best_idx]` against `precision[best_idx]` may access the wrong index if F1 is computed naively.

**Why it happens:** sklearn's `precision_recall_curve` appends a final (precision=1, recall=0) point with no corresponding threshold.

**How to avoid:** Compute F1 using `precision[:-1]` and `recall[:-1]` (dropping the last no-threshold point), then use `thresholds[best_idx]` where `best_idx = np.argmax(f1_scores)`.

**Warning signs:** `IndexError` on `thresholds[best_idx]` or unexpectedly high threshold values.

### Pitfall 4: Column Mismatch Between Train and Predict

**What goes wrong:** 2026 feature rows have different column count or order than training rows, causing XGBoost or LogReg to silently use wrong features or raise a shape error.

**Why it happens:** `build_matrix_year` with an empty `eq_index` will not include an `EQIndicator` column (it will try to reindex against an empty series and produce zeros). Column order may also differ depending on how pandas concatenates.

**How to avoid:** Always select exactly `feature_cols = json.load("data/processed/feature_columns.json")` as the final step before `.to_numpy()`. Assert `X.shape[1] == len(feature_cols)` before calling `.predict_proba()`.

**Warning signs:** `ValueError: X has N features, but model was trained with M features` at inference time.

### Pitfall 5: Corrupted feature_matrix_test.parquet

**What goes wrong:** `pd.read_parquet("data/processed/feature_matrix_test.parquet")` raises `ArrowInvalid` or reads a truncated/empty DataFrame.

**Why it happens:** STATE.md records: "test parquet corrupted in committed artifact — ParquetWriter.close() not finalized; needs re-run with raw data on original machine." The raw CSV files (ephemeris.csv, usgs_earthquakes.csv) are not committed to the repo.

**How to avoid:** Add a Wave 0 verification task that reads both parquets and asserts expected shape (>100k rows for test), fails fast with a clear error if corrupted. The regeneration path requires raw data files present locally.

**Warning signs:** Empty DataFrame or `ArrowInvalid: Parquet magic bytes not found in footer` when reading feature_matrix_test.parquet.

### Pitfall 6: File Size of predictions.json

**What goes wrong:** predictions.json becomes very large (10MB+) if the threshold is too low, making it slow to parse in the Next.js build.

**Why it happens:** 901 active grid cells × 306 days (March–December 2026) = 275,706 potential entries before threshold filtering. At a low threshold, many entries survive.

**How to avoid:** Log the number of records written and the file size. Add a warning if > 5,000 entries or > 2MB. The threshold from the PR curve should naturally limit this, but verify after export.

**Warning signs:** Vercel build timeout or Next.js slow page loads in Phase 4.

### Pitfall 7: LogisticRegression max_iter Convergence

**What goes wrong:** `ConvergenceWarning: lbfgs failed to converge` (or liblinear equivalent) — model trains but may not have converged, leading to unreliable coefficients.

**Why it happens:** 813 features with L1 penalty may need more iterations than the sklearn default (100).

**How to avoid:** Set `max_iter=1000` (or higher). Log the convergence warning if it appears. The model will still train and produce predictions; convergence is a quality concern, not a hard failure.

---

## Code Examples

Verified patterns from official sources and project code:

### Joblib Save/Load (consistent with Phase 2 pattern)
```python
# Source: sklearn documentation, joblib 1.5.3
import joblib

joblib.dump(model, "data/models/eq_classifier.pkl", compress=3)
model_loaded = joblib.load("data/models/eq_classifier.pkl")
```

### eval_report.json Structure
```python
# Source: CONTEXT.md locked spec
import json

report = {
    "model_used": "LogisticRegression",   # or "XGBClassifier"
    "f1_score": 0.312,
    "mcc": 0.287,
    "threshold": 0.42,
    "eval_split_date": "2010-01-01",
    "confusion_matrix": {"tp": 1240, "fp": 890, "fn": 680, "tn": 45320},
    "both_models": [
        {"model": "LogisticRegression", "f1": 0.312, "mcc": 0.287},
        {"model": "XGBClassifier",      "f1": 0.298, "mcc": 0.271},
    ],
}

with open("data/models/eval_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

### Confusion Matrix Extraction
```python
# Source: sklearn.metrics documentation
from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_true, y_pred)
tn, fp, fn, tp = cm.ravel()
```

### Logging Pattern (consistent with Phase 1/2)
```python
# Source: established project pattern (pipeline/features/engineering.py)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline.model.train_eval")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `use_label_encoder=False` in XGBClassifier | Parameter removed; omit entirely | xgboost 3.0 (2024) | Must remove from the CONTEXT.md-specified hyperparams |
| `sklearn.pipeline.Pipeline` with scaler | No scaling needed (Phase 2 pre-encoded) | N/A for this project | Pipeline is optional here; can use it as a container for serialization |
| `coef_` as 2D array | `coef_` still 2D for binary: `model.coef_[0]` | sklearn 1.x | Use index [0] for binary classification |
| `get_feature_names()` for sklearn encoders | `get_feature_names_out()` | sklearn 1.0 | Already handled in engineering.py with version check |

**Deprecated/outdated:**
- `use_label_encoder=False` in XGBClassifier: removed in xgboost 3.0; this project uses 3.2.0
- `XGBClassifier(use_label_encoder=True)` default: never apply; labels are pre-encoded as 0/1 integers

---

## Open Questions

1. **Is feature_matrix_test.parquet readable?**
   - What we know: STATE.md records it may be corrupted (ParquetWriter.close() not called)
   - What's unclear: Whether the re-run has been done or whether the committed artifact is valid
   - Recommendation: Wave 0 must include a `verify_artifacts.py` smoke test that reads both parquets and asserts row counts > 10,000 before any training begins

2. **Does ephemeris.csv cover 2026-03-01 through 2026-12-31?**
   - What we know: Phase 2 main() slices `range(2000, 2027)` suggesting ephemeris.csv has 2026 rows; raw files are not committed
   - What's unclear: Whether ephemeris.csv was generated to include all of 2026 or only through the Phase 1 run date
   - Recommendation: Add an assertion in the prediction export script: `assert len(ephe_2026) == 306, f"Expected 306 days for 2026-03-01 to 2026-12-31, got {len(ephe_2026)}"`

3. **Memory budget for concatenating both parquets**
   - What we know: feature_matrix_train.parquet is ~263k rows × 813 float32 cols ≈ 0.8GB; feature_matrix_test.parquet is ~8.5M rows which at full float32 is ~27GB
   - What's unclear: Whether the test parquet was written as float32 or float64; pandas 3.x default
   - Recommendation: Read test parquet with `dtype_backend="numpy_nullable"` or explicitly cast to float32 after loading; process in chunks if full concat exceeds available RAM. Alternative: filter the test parquet to only 2010–2026 rows before concatenating with the train parquet.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | none (uses pyproject.toml dev-dependencies; no [tool.pytest.ini_options] section) |
| Quick run command | `uv run pytest tests/test_model.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | Train set contains only dates < 2010-01-01 | unit | `uv run pytest tests/test_model.py::TestTemporalSplit::test_train_dates_before_2010 -x` | ❌ Wave 0 |
| MODEL-01 | X_train has exactly 813 feature columns | unit | `uv run pytest tests/test_model.py::TestFeatureSelection::test_train_column_count -x` | ❌ Wave 0 |
| MODEL-02 | eval_report.json written with required keys | unit | `uv run pytest tests/test_model.py::TestEvalReport::test_report_schema -x` | ❌ Wave 0 |
| MODEL-02 | MCC and F1 computed correctly (smoke with known labels) | unit | `uv run pytest tests/test_model.py::TestMetrics::test_mcc_known_values -x` | ❌ Wave 0 |
| MODEL-03 | Predictions include grid_lat, grid_lon, country columns | unit | `uv run pytest tests/test_model.py::TestPredictionSchema::test_geo_columns -x` | ❌ Wave 0 |
| MODEL-04 | Both models trained and both appear in both_models array | unit | `uv run pytest tests/test_model.py::TestBothModels::test_both_logged -x` | ❌ Wave 0 |
| MODEL-05 | eq_classifier.pkl written and loadable | unit | `uv run pytest tests/test_model.py::TestSerialization::test_model_roundtrip -x` | ❌ Wave 0 |
| PRED-01 | predictions.json written to web/public/data/ | unit | `uv run pytest tests/test_model.py::TestPredictionExport::test_output_path -x` | ❌ Wave 0 |
| PRED-02 | Each record in predictions.json has required schema keys | unit | `uv run pytest tests/test_model.py::TestPredictionExport::test_record_schema -x` | ❌ Wave 0 |
| PRED-03 | No records with risk_score < threshold in predictions.json | unit | `uv run pytest tests/test_model.py::TestPredictionExport::test_threshold_filter -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_model.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_model.py` — covers MODEL-01 through MODEL-05, PRED-01 through PRED-03 (all test stubs)
- [ ] `pipeline/model/__init__.py` — module init for the new model package
- [ ] `data/models/` directory — must exist before any training script writes artifacts
- [ ] `web/public/data/` directory — must exist before prediction export writes predictions.json
- [ ] Artifact smoke test: read both parquets, assert row counts and column counts are valid before any training begins (addresses known corrupted test parquet concern)

---

## Sources

### Primary (HIGH confidence)

- Project source: `pipeline/features/engineering.py` — column naming conventions, aspect suffix patterns, `downsample_negatives` signature, `build_matrix_year` API, `load_encoder` function
- Project source: `data/processed/feature_columns.json` — confirmed 813 feature columns; first 10 are retro flags; aspect columns follow `{p1}_{p2}_{aspect_type}` pattern
- Project source: `pyproject.toml` + `uv.lock` — confirmed package versions: scikit-learn 1.8.0, xgboost 3.2.0, joblib 1.5.3, pandas 3.0.1, numpy 2.4.3, pyarrow 23.0.1
- Project source: `.planning/phases/03-model-training-and-prediction-export/03-CONTEXT.md` — all locked decisions and schemas

### Secondary (MEDIUM confidence)

- sklearn.metrics documentation pattern for `precision_recall_curve` off-by-one — standard sklearn API behavior verified by project code inspection and well-documented in sklearn source
- xgboost 3.x API change removing `use_label_encoder` — this is a known breaking change from xgboost 3.0; project uses 3.2.0 per uv.lock

### Tertiary (LOW confidence)

- File size estimate for predictions.json (901 cells × 306 days = 275k max entries) — based on active cell count from Phase 2 research (901 cells) and date math; actual post-threshold count is unknown until the model is trained

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed from uv.lock with exact versions
- Architecture: HIGH — split pattern, feature selection, aspect derivation all grounded in Phase 2 source code
- Pitfalls: HIGH (xgboost API) / MEDIUM (file size, memory) — xgboost 3.x change is a known breaking change; memory and file size estimates are projections

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable libraries; xgboost API change already accounted for)
