# Earthquake Model Corrected Retrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct model selection to train on pre-2000 data, evaluate all post-2000 rows, apply XGBoost `scale_pos_weight=10.0`, regenerate model/regional artifacts, and report the corrected metrics.

**Architecture:** Keep the existing pipeline shape and add only a small shared classifier factory so model selection and final retraining cannot drift. `train_eval.py` owns candidate evaluation on the canonical `2000-01-01` split; `retrain.py` owns final serialization; `add_regions.py` and `regional_scoring.py` regenerate downstream regional validation from the corrected serialized model.

**Tech Stack:** Python 3.12, pandas, pyarrow, scikit-learn, xgboost, joblib, pytest, uv.

---

## File Structure

- Create: `pipeline/model/classifiers.py`
  - Shared model-name constants and factory functions for Logistic Regression and XGBoost.
  - XGBoost factory sets `scale_pos_weight=10.0`.
- Modify: `pipeline/model/train_eval.py`
  - Set `EVAL_SPLIT_DATE = datetime.date(2000, 1, 1)`.
  - Simplify `load_training_set()` so it reads only `feature_matrix_train.parquet`.
  - Evaluate all rows in `feature_matrix_test.parquet` using `EVAL_SPLIT_DATE`.
  - Write `eval_split_date` with `EVAL_SPLIT_DATE.isoformat()`.
  - Use shared classifier factories.
- Modify: `pipeline/model/retrain.py`
  - Use the shared winner factory so the final serialized XGBoost model also receives `scale_pos_weight=10.0`.
- Modify: `tests/test_model.py`
  - Replace 2010 split expectations with 2000 split expectations.
  - Add focused unit tests for report metadata, train parquet-only loading, and XGBoost parameters.
- Modify: `tests/test_regions.py`
  - Add focused scoring tests for one prediction per month, hit-rate/base-rate/lift math, and `main()` output shape for Mexico/Peru/Chile.
- Generated artifacts:
  - Update: `data/models/eval_report.json`
  - Update: `data/models/eq_classifier.pkl`
  - Update: `data/models/feature_importance.json`
  - Update/Create: `data/processed/feature_matrix_test_with_regions.parquet`
  - Update/Create: `data/processed/regional_validation_extended.json`

---

### Task 1: Shared Classifier Factories And Model-Selection Tests

**Files:**
- Create: `pipeline/model/classifiers.py`
- Modify: `tests/test_model.py`
- Modify: `pipeline/model/train_eval.py`

- [ ] **Step 1: Write failing tests for the corrected split, report metadata, train-only loading, and XGBoost parameter**

Add these imports near the top of `tests/test_model.py`:

```python
import numpy as np
import pandas as pd
```

Add this test class after the path constants in `tests/test_model.py`:

```python
class TestCorrectedModelSelection:
    def test_eval_split_date_is_2000_constant(self):
        """Model selection evaluates on the canonical post-2000 holdout."""
        from pipeline.model import train_eval

        assert train_eval.EVAL_SPLIT_DATE == datetime.date(2000, 1, 1)

    def test_report_writes_eval_split_date_from_constant(self, monkeypatch, tmp_path):
        """eval_report.json records the EVAL_SPLIT_DATE constant."""
        from pipeline.model import train_eval

        report_path = tmp_path / "eval_report.json"
        monkeypatch.setattr(train_eval, "EVAL_REPORT_PATH", str(report_path))

        report = train_eval.select_winner_and_write_report(
            [
                {
                    "model": "LogisticRegression",
                    "f1": 0.25,
                    "mcc": 0.10,
                    "threshold": 0.40,
                    "confusion_matrix": {"tp": 1, "fp": 2, "fn": 3, "tn": 4},
                },
                {
                    "model": "XGBClassifier",
                    "f1": 0.50,
                    "mcc": 0.20,
                    "threshold": 0.60,
                    "confusion_matrix": {"tp": 5, "fp": 6, "fn": 7, "tn": 8},
                },
            ],
            model_objects=[],
        )

        assert report["model_used"] == "XGBClassifier"
        assert report["eval_split_date"] == train_eval.EVAL_SPLIT_DATE.isoformat()
        assert json.loads(report_path.read_text())["eval_split_date"] == "2000-01-01"

    def test_load_training_set_reads_only_train_parquet(self, monkeypatch):
        """Model-selection training does not append any post-2000 test rows."""
        from pipeline.model import train_eval

        feature_cols = ["feature_a", "feature_b"]
        calls = []

        train_df = pd.DataFrame(
            {
                "feature_a": [1.0, 2.0],
                "feature_b": [3.0, 4.0],
                "date": [datetime.date(1999, 12, 30), datetime.date(1999, 12, 31)],
                "EQIndicator": [0, 1],
                "grid_lat": [0, 5],
                "grid_lon": [10, 15],
                "country": ["A", "B"],
            }
        )

        def fake_read_parquet(path, columns=None, filters=None):
            calls.append((path, columns, filters))
            if path == train_eval.TEST_PARQUET:
                raise AssertionError("load_training_set must not read TEST_PARQUET")
            return train_df[columns].copy()

        monkeypatch.setattr(train_eval.pd, "read_parquet", fake_read_parquet)
        monkeypatch.setattr(train_eval, "EXPECTED_FEATURE_COUNT", 2)

        X_train, y_train = train_eval.load_training_set(feature_cols)

        assert calls == [
            (
                train_eval.TRAIN_PARQUET,
                feature_cols + ["date", "EQIndicator", "grid_lat", "grid_lon", "country"],
                None,
            )
        ]
        assert X_train.dtype == np.float32
        assert X_train.tolist() == [[1.0, 3.0], [2.0, 4.0]]
        assert y_train.tolist() == [0, 1]

    def test_xgb_factory_uses_phase2_class_weight(self):
        """XGBoost candidate uses the published Phase 2 class weighting."""
        from pipeline.model.classifiers import XGB_SCALE_POS_WEIGHT, build_xgb_classifier

        model = build_xgb_classifier()

        assert XGB_SCALE_POS_WEIGHT == 10.0
        assert model.get_params()["scale_pos_weight"] == 10.0
```

Update the existing split test in `tests/test_model.py`:

```python
def test_eval_split_date_is_2000(self):
    """eval_report.json records eval_split_date as 2000-01-01."""
    report = json.loads(EVAL_REPORT_PATH.read_text())
    assert report["eval_split_date"] == "2000-01-01"
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection tests/test_model.py::TestTemporalSplit::test_eval_split_date_is_2000 -v
```

Expected: FAIL because `pipeline.model.classifiers` does not exist, `EVAL_SPLIT_DATE` is still 2010, and report metadata is still hard-coded to 2010.

- [ ] **Step 3: Add shared classifier factories**

Create `pipeline/model/classifiers.py`:

```python
"""Shared classifier factories for model selection and final retraining."""

from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

LOGISTIC_REGRESSION_MODEL = "LogisticRegression"
XGB_CLASSIFIER_MODEL = "XGBClassifier"
XGB_SCALE_POS_WEIGHT = 10.0


def build_logistic_regression() -> LogisticRegression:
    """Return the Logistic Regression candidate used throughout the model pipeline."""
    return LogisticRegression(
        C=1,
        penalty="l1",
        solver="liblinear",
        max_iter=1000,
        random_state=42,
    )


def build_xgb_classifier() -> XGBClassifier:
    """Return the XGBoost candidate with the published Phase 2 class weighting."""
    return XGBClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        eval_metric="logloss",
        scale_pos_weight=XGB_SCALE_POS_WEIGHT,
    )


def build_classifier(model_name: str):
    """Return the configured classifier for a stored model name."""
    if model_name == LOGISTIC_REGRESSION_MODEL:
        return build_logistic_regression()
    if model_name == XGB_CLASSIFIER_MODEL:
        return build_xgb_classifier()
    raise ValueError(f"Unknown model_used in eval_report.json: {model_name!r}")
```

- [ ] **Step 4: Update `train_eval.py` minimally**

Change constants and imports in `pipeline/model/train_eval.py`:

```python
from pipeline.model.classifiers import (
    LOGISTIC_REGRESSION_MODEL,
    XGB_CLASSIFIER_MODEL,
    build_logistic_regression,
    build_xgb_classifier,
)

EVAL_SPLIT_DATE = datetime.date(2000, 1, 1)
EXPECTED_FEATURE_COUNT = 813
```

Replace `load_training_set()` body with:

```python
def load_training_set(feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Build X_train, y_train from the canonical pre-2000 training parquet only."""
    meta_cols = ["date", "EQIndicator", "grid_lat", "grid_lon", "country"]
    needed_cols = feature_cols + meta_cols

    logger.info("Reading train parquet (pre-2000): %s", TRAIN_PARQUET)
    train_df = pd.read_parquet(TRAIN_PARQUET, columns=needed_cols)
    train_df[feature_cols] = train_df[feature_cols].astype("float32")
    logger.info(
        "Training partition: %d rows (positive=%d, negative=%d)",
        len(train_df),
        (train_df["EQIndicator"] == 1).sum(),
        (train_df["EQIndicator"] == 0).sum(),
    )

    X_train = train_df[feature_cols].to_numpy(dtype="float32")
    y_train = train_df["EQIndicator"].to_numpy()
    assert X_train.shape[1] == EXPECTED_FEATURE_COUNT, (
        f"Expected {EXPECTED_FEATURE_COUNT} features, got {X_train.shape[1]}"
    )
    logger.info("X_train shape: %s", X_train.shape)
    return X_train, y_train
```

Replace the report split field:

```python
"eval_split_date": EVAL_SPLIT_DATE.isoformat(),
```

Replace model construction in `main()`:

```python
logreg = build_logistic_regression()
xgb = build_xgb_classifier()
model_names = [LOGISTIC_REGRESSION_MODEL, XGB_CLASSIFIER_MODEL]
```

- [ ] **Step 5: Run code-focused tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection -v
```

Expected: PASS. `tests/test_model.py::TestTemporalSplit::test_eval_split_date_is_2000` reads generated `data/models/eval_report.json`; it should pass after Task 5 regenerates that artifact.

- [ ] **Step 6: Commit**

Run:

```bash
git add pipeline/model/classifiers.py pipeline/model/train_eval.py tests/test_model.py docs/superpowers/plans/2026-07-09-earthquake-model-retrain.md
git commit -m "fix: align model selection with phase2 split"
```

---

### Task 2: Final Retrain Uses The Same Winner Factory

**Files:**
- Modify: `tests/test_model.py`
- Modify: `pipeline/model/retrain.py`

- [ ] **Step 1: Write failing retrain parity test**

Add this test to `TestCorrectedModelSelection` in `tests/test_model.py`:

```python
def test_retrain_xgb_winner_uses_phase2_class_weight(self):
    """Final retraining uses the same XGBoost class weighting as model selection."""
    from pipeline.model import retrain

    model = retrain.build_winner_model("XGBClassifier")

    assert model.get_params()["scale_pos_weight"] == 10.0
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection::test_retrain_xgb_winner_uses_phase2_class_weight -v
```

Expected: FAIL because `retrain.build_winner_model()` does not exist.

- [ ] **Step 3: Add retrain factory wrapper and use it**

In `pipeline/model/retrain.py`, replace direct Logistic Regression and XGBoost imports with:

```python
from pipeline.model.classifiers import build_classifier
```

Add this helper before `main()`:

```python
def build_winner_model(model_name: str):
    """Return the configured winner model for final serialization."""
    return build_classifier(model_name)
```

Replace the `if model_name == ...` block in `main()` with:

```python
model = build_winner_model(model_name)
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection::test_retrain_xgb_winner_uses_phase2_class_weight -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add pipeline/model/retrain.py tests/test_model.py
git commit -m "fix: reuse classifier parameters during retrain"
```

---

### Task 3: Regional Scoring Tests And Empty-Subset Guard

**Files:**
- Modify: `tests/test_regions.py`
- Modify: `pipeline/model/regional_scoring.py`

- [ ] **Step 1: Write failing regional scoring tests**

Append these tests to `tests/test_regions.py`:

```python
import json
import pandas as pd

from pipeline.model import regional_scoring


class TestRegionalScoring:
    def test_score_region_uses_one_highest_risk_prediction_per_month(self):
        rows = [
            {"date": "2000-01-01", "EQIndicator": 0, "risk_score": 0.20},
            {"date": "2000-01-10", "EQIndicator": 1, "risk_score": 0.90},
            {"date": "2000-02-01", "EQIndicator": 0, "risk_score": 0.95},
            {"date": "2000-02-20", "EQIndicator": 1, "risk_score": 0.10},
        ]

        result = regional_scoring.score_region(
            pd.DataFrame(rows),
            "Fixture",
            window_days=2,
        )

        assert result["n_predictions"] == 2
        assert result["hits"] == 1
        assert result["hit_rate"] == 0.5
        assert result["base_rate"] == 0.2414
        assert result["lift"] == 2.0714

    def test_score_region_handles_empty_subset(self):
        result = regional_scoring.score_region(
            pd.DataFrame(columns=["date", "EQIndicator", "risk_score"]),
            "Missing",
        )

        assert result == {
            "region": "Missing",
            "n_predictions": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "base_rate": 0.0,
            "lift": None,
            "p_value": None,
        }

    def test_main_writes_mexico_peru_chile_results(self, monkeypatch, tmp_path):
        rows = []
        for country in ["Mexico", "Peru", "Chile"]:
            rows.extend(
                [
                    {
                        "date": "2000-01-01",
                        "EQIndicator": 0,
                        "risk_score": 0.10,
                        "country": country,
                        "region": "Unclassified",
                    },
                    {
                        "date": "2000-01-05",
                        "EQIndicator": 1,
                        "risk_score": 0.90,
                        "country": country,
                        "region": "Unclassified",
                    },
                ]
            )

        output_path = tmp_path / "regional_validation_extended.json"
        monkeypatch.setattr(
            regional_scoring.pd,
            "read_parquet",
            lambda path: pd.DataFrame(rows),
        )
        monkeypatch.setattr(regional_scoring, "OUTPUT_PATH", str(output_path))

        results = regional_scoring.main()

        names = {r["region"] for r in results}
        assert {"Mexico", "Peru", "Chile"}.issubset(names)
        written_names = {r["region"] for r in json.loads(output_path.read_text())}
        assert {"Mexico", "Peru", "Chile"}.issubset(written_names)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
uv run pytest tests/test_regions.py::TestRegionalScoring -v
```

Expected: FAIL because empty subsets are not guarded and `main()` will hit empty region subsets.

- [ ] **Step 3: Add empty-subset guard**

At the start of `score_region()` after the docstring, add:

```python
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
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_regions.py::TestRegionalScoring -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add pipeline/model/regional_scoring.py pipeline/features/regions.py pipeline/model/add_regions.py tests/test_regions.py
git commit -m "test: cover regional scoring sanity checks"
```

---

### Task 4: Targeted Verification Before Retrain

**Files:**
- No production edits expected.
- May update tests if a legitimate TDD issue is discovered.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection tests/test_engineering.py::TestTemporalSplit tests/test_engineering.py::TestOutputArtifacts::test_temporal_split_in_parquets tests/test_regions.py -v
```

Expected: PASS. If failures occur, fix only the failing behavior using RED/GREEN steps before proceeding.

- [ ] **Step 2: Record current parquet metadata**

Run:

```bash
uv run python - <<'PY'
import pandas as pd
from pathlib import Path

for label, path in [
    ("train", Path("data/processed/feature_matrix_train.parquet")),
    ("test", Path("data/processed/feature_matrix_test.parquet")),
]:
    df = pd.read_parquet(path, columns=["date", "EQIndicator"])
    dates = pd.to_datetime(df["date"])
    positives = int((df["EQIndicator"] == 1).sum())
    negatives = int((df["EQIndicator"] == 0).sum())
    print(
        f"{label}: rows={len(df)} date_min={dates.min().date()} "
        f"date_max={dates.max().date()} positives={positives} "
        f"negatives={negatives} positive_rate={positives / len(df):.8f}"
    )
PY
```

Expected:

```text
train: rows=263681 date_min=1900-01-02 date_max=1999-12-31 positives=23971 negatives=239710 positive_rate=0.09090909
test: rows=8885662 date_min=2000-01-01 date_max=2026-12-31 positives=10975 negatives=8874687 positive_rate=0.00123514
```

---

### Task 5: End-To-End Retrain And Regional Rescore

**Files:**
- Update: `data/models/eval_report.json`
- Update: `data/models/eq_classifier.pkl`
- Update: `data/models/feature_importance.json`
- Update/Create: `data/processed/feature_matrix_test_with_regions.parquet`
- Update/Create: `data/processed/regional_validation_extended.json`

- [ ] **Step 1: Run corrected model selection**

Run:

```bash
uv run python -m pipeline.model.train_eval
```

Expected: writes `data/models/eval_report.json` with `eval_split_date` equal to `2000-01-01`, `model_used`, `mcc`, `f1_score`, `threshold`, `confusion_matrix`, and both model metrics.

- [ ] **Step 2: Run final retrain**

Run:

```bash
uv run python -m pipeline.model.retrain
```

Expected: updates `data/models/eq_classifier.pkl` and `data/models/feature_importance.json` using the selected winner and corrected parameters.

- [ ] **Step 3: Regenerate regional scoring parquet**

Run:

```bash
uv run python -m pipeline.model.add_regions
```

Expected: updates `data/processed/feature_matrix_test_with_regions.parquet` with `region` and `risk_score` from the corrected serialized model.

- [ ] **Step 4: Regenerate regional validation JSON**

Run:

```bash
uv run python -m pipeline.model.regional_scoring
```

Expected: updates `data/processed/regional_validation_extended.json` with region results plus Mexico, Peru, and Chile.

- [ ] **Step 5: Extract metrics for final report**

Run:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("data/models/eval_report.json").read_text())
print("model_used:", report["model_used"])
print("eval_split_date:", report["eval_split_date"])
print("mcc:", report["mcc"])
print("f1_score:", report["f1_score"])
print("threshold:", report["threshold"])
print("confusion_matrix:", report["confusion_matrix"])
print("both_models:", report["both_models"])

published = {"Mexico": 0.619, "Peru": 0.458, "Chile": 0.385}
regional = json.loads(Path("data/processed/regional_validation_extended.json").read_text())
for row in regional:
    if row["region"] in published:
        print(
            row["region"],
            "hit_rate=", row["hit_rate"],
            "base_rate=", row["base_rate"],
            "lift=", row["lift"],
            "published=", published[row["region"]],
        )
PY
```

Expected: prints all values needed in the final response.

- [ ] **Step 6: Run post-generation focused tests**

Run:

```bash
uv run pytest tests/test_model.py::TestCorrectedModelSelection tests/test_model.py::TestTemporalSplit::test_eval_split_date_is_2000 tests/test_model.py::TestEvalReport tests/test_model.py::TestBothModels tests/test_engineering.py::TestTemporalSplit tests/test_engineering.py::TestOutputArtifacts::test_temporal_split_in_parquets tests/test_regions.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit generated artifacts and final verification state**

Run:

```bash
git add data/models/eval_report.json data/models/eq_classifier.pkl data/models/feature_importance.json data/processed/feature_matrix_test_with_regions.parquet data/processed/regional_validation_extended.json
git commit -m "data: regenerate corrected model artifacts"
```

---

## Self-Review

- Spec coverage: the plan covers parquet split inspection, code correction, `eval_split_date`, XGBoost `scale_pos_weight`, final retrain, regional rescore, tests, generated artifacts, and final reporting.
- Placeholder scan: no `TBD`, `TODO`, or open-ended implementation instructions remain.
- Type consistency: tests and implementation use `datetime.date(2000, 1, 1)`, `EVAL_SPLIT_DATE.isoformat()`, `scale_pos_weight`, `risk_score`, `region`, and existing artifact paths consistently.
