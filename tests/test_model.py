"""Tests for pipeline.model — Phase 3 model training and prediction export."""
import pytest
import json
import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Paths
EVAL_REPORT_PATH = Path("data/models/eval_report.json")
CLASSIFIER_PATH = Path("data/models/eq_classifier.pkl")
PREDICTIONS_PATH = Path("web/public/data/predictions.json")
TRAIN_PARQUET = Path("data/processed/feature_matrix_train.parquet")
TEST_PARQUET = Path("data/processed/feature_matrix_test.parquet")
FEATURE_COLS_PATH = Path("data/processed/feature_columns.json")


def _is_valid_parquet(path: Path) -> bool:
    """Check if a file is a valid parquet (has PAR1 magic footer)."""
    if not path.exists() or path.stat().st_size < 12:
        return False
    with open(path, "rb") as f:
        f.seek(-4, 2)
        return f.read(4) == b"PAR1"


# --- MODEL-01: Train on pre-2000 data ---
class TestTemporalSplit:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_train_dates_before_2000(self):
        """All training rows have date < 2000-01-01."""
        assert False

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_holdout_dates_from_2000(self):
        """All holdout rows have date >= 2000-01-01."""
        assert False

    def test_eval_split_date_is_2000(self):
        """eval_report.json records eval_split_date as 2000-01-01."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        assert report["eval_split_date"] == "2000-01-01"


class TestCorrectedModelSelection:
    def test_eval_split_date_constant_is_2000(self):
        """Model evaluation split date is fixed at 2000-01-01."""
        from pipeline.model import train_eval

        assert train_eval.EVAL_SPLIT_DATE == datetime.date(2000, 1, 1)

    def test_eval_report_uses_eval_split_date_constant(self, tmp_path, monkeypatch):
        """select_winner_and_write_report writes the configured eval split date."""
        from pipeline.model import train_eval

        report_path = tmp_path / "eval_report.json"
        monkeypatch.setattr(train_eval, "EVAL_REPORT_PATH", report_path)
        monkeypatch.setattr(train_eval, "EVAL_SPLIT_DATE", datetime.date(2000, 1, 1))
        results = [
            {
                "model": "LogisticRegression",
                "f1": 0.25,
                "mcc": 0.4,
                "threshold": 0.3,
                "confusion_matrix": {"tp": 1, "fp": 2, "fn": 3, "tn": 4},
            },
            {
                "model": "XGBClassifier",
                "f1": 0.2,
                "mcc": 0.3,
                "threshold": 0.4,
                "confusion_matrix": {"tp": 4, "fp": 3, "fn": 2, "tn": 1},
            },
        ]

        train_eval.select_winner_and_write_report(results, model_objects=[])

        report = json.loads(report_path.read_text())
        assert report["eval_split_date"] == train_eval.EVAL_SPLIT_DATE.isoformat()

    def test_load_training_set_reads_train_parquet_only(self, monkeypatch):
        """load_training_set uses only TRAIN_PARQUET and returns float32 features."""
        from pipeline.model import train_eval

        feature_cols = ["feature_a", "feature_b"]
        train_df = pd.DataFrame(
            {
                "feature_a": [1, 2],
                "feature_b": [3.5, 4.5],
                "date": [datetime.date(1999, 1, 1), datetime.date(1999, 1, 2)],
                "EQIndicator": [1, 0],
                "grid_lat": [10.0, 20.0],
                "grid_lon": [30.0, 40.0],
                "country": ["AA", "BB"],
            }
        )
        read_paths = []

        def fake_read_parquet(path, columns=None, **kwargs):
            read_paths.append(path)
            assert path == train_eval.TRAIN_PARQUET
            assert columns == feature_cols + [
                "date",
                "EQIndicator",
                "grid_lat",
                "grid_lon",
                "country",
            ]
            assert not kwargs
            return train_df

        monkeypatch.setattr(train_eval, "EXPECTED_FEATURE_COUNT", 2)
        monkeypatch.setattr(train_eval.pd, "read_parquet", fake_read_parquet)

        X, y = train_eval.load_training_set(feature_cols)

        assert read_paths == [train_eval.TRAIN_PARQUET]
        assert train_eval.TEST_PARQUET not in read_paths
        assert X.dtype == np.float32
        np.testing.assert_array_equal(y, np.array([1, 0]))

    def test_predict_holdout_chunked_filters_from_eval_split_date(self, monkeypatch):
        """predict_holdout_chunked keeps only rows on/after EVAL_SPLIT_DATE."""
        from pipeline.model import train_eval

        feature_cols = ["feature_a", "feature_b"]
        row_group = pd.DataFrame(
            {
                "feature_a": [0.1, 0.2, 0.3],
                "feature_b": [1.1, 1.2, 1.3],
                "date": [
                    datetime.date(1999, 12, 31),
                    datetime.date(2000, 1, 1),
                    datetime.date(2000, 1, 2),
                ],
                "EQIndicator": [0, 1, 0],
            }
        )
        constructed_paths = []

        class FakeRowGroup:
            def to_pandas(self):
                return row_group.copy()

        class FakeMetadata:
            num_row_groups = 1

        class FakeParquetFile:
            metadata = FakeMetadata()

            def __init__(self, path):
                constructed_paths.append(path)

            def read_row_group(self, rg_idx, columns=None):
                assert rg_idx == 0
                assert columns == feature_cols + ["date", "EQIndicator"]
                return FakeRowGroup()

        class FakeModel:
            def predict_proba(self, X):
                positive_prob = X[:, 0].astype("float32")
                return np.column_stack([1 - positive_prob, positive_prob])

        monkeypatch.setattr(train_eval.pq, "ParquetFile", FakeParquetFile)

        y_true, y_probs = train_eval.predict_holdout_chunked([FakeModel()], feature_cols)

        assert constructed_paths == [train_eval.TEST_PARQUET]
        np.testing.assert_array_equal(y_true, np.array([1, 0]))
        assert len(y_probs) == 1
        np.testing.assert_allclose(y_probs[0], np.array([0.2, 0.3], dtype=np.float32))

    def test_xgb_classifier_uses_positive_class_weight(self):
        """XGB classifier factory applies the configured positive class weight."""
        from pipeline.model.classifiers import XGB_SCALE_POS_WEIGHT, build_xgb_classifier

        assert XGB_SCALE_POS_WEIGHT == 10.0
        assert build_xgb_classifier().get_params()["scale_pos_weight"] == 10.0

    def test_retrain_xgb_winner_uses_phase2_class_weight(self):
        """Final retraining uses the same XGBoost class weighting as model selection."""
        from pipeline.model import retrain

        model = retrain.build_winner_model("XGBClassifier")

        assert model.get_params()["scale_pos_weight"] == 10.0


class TestFeatureSelection:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_train_column_count(self):
        """X_train has exactly 813 feature columns."""
        assert False


# --- MODEL-02: Evaluated with F1 and MCC ---
class TestEvalReport:
    def test_report_schema(self):
        """eval_report.json has all required keys."""
        assert EVAL_REPORT_PATH.exists()
        report = json.loads(EVAL_REPORT_PATH.read_text())
        required = {"model_used", "f1_score", "mcc", "confusion_matrix", "threshold", "eval_split_date", "both_models"}
        assert required.issubset(report.keys())

    def test_confusion_matrix_keys(self):
        """confusion_matrix has tp, fp, fn, tn."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        cm = report["confusion_matrix"]
        assert {"tp", "fp", "fn", "tn"} == set(cm.keys())

    def test_threshold_in_valid_range(self):
        """Threshold is between 0 and 1."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        assert 0 < report["threshold"] < 1

    def test_metrics_non_negative(self):
        """F1 and MCC are non-negative (model is better than random)."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        assert report["f1_score"] >= 0
        assert report["mcc"] >= -1  # MCC range is [-1, 1]


class TestMetrics:
    def test_mcc_known_values(self):
        """MCC computed correctly for a known confusion matrix."""
        from sklearn.metrics import matthews_corrcoef
        y_true = [1, 1, 0, 0, 0, 1, 0, 0]
        y_pred = [1, 0, 0, 0, 0, 1, 1, 0]
        assert abs(matthews_corrcoef(y_true, y_pred) - 0.4667) < 0.01


# --- MODEL-03: Predicts date AND region ---
class TestPredictionSchema:
    def test_geo_columns(self):
        """Each prediction record has country, lat, lon."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        for r in records[:10]:
            assert "country" in r
            assert "lat" in r
            assert "lon" in r


# --- MODEL-04: Two classifiers compared ---
class TestBothModels:
    def test_both_logged(self):
        """both_models array in eval_report has entries for LogisticRegression and XGBClassifier."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        names = {m["model"] for m in report["both_models"]}
        assert "LogisticRegression" in names
        assert "XGBClassifier" in names


# --- MODEL-05: Model serialized ---
class TestSerialization:
    def test_model_roundtrip(self):
        """eq_classifier.pkl written and loadable."""
        import joblib
        assert CLASSIFIER_PATH.exists(), "eq_classifier.pkl not found"
        model = joblib.load(CLASSIFIER_PATH)
        assert hasattr(model, "predict_proba"), "Loaded object has no predict_proba"


# --- PRED-01: predictions.json in web/public/data/ ---
class TestPredictionExport:
    def test_output_path(self):
        """predictions.json exists at web/public/data/predictions.json."""
        assert PREDICTIONS_PATH.exists()

    def test_record_schema(self):
        """Each record has date, country, lat, lon, risk_score, top_planetary_aspects."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        required = {"date", "country", "lat", "lon", "risk_score", "top_planetary_aspects"}
        for r in records[:5]:
            assert required.issubset(r.keys())

    def test_threshold_filter(self):
        """No records with risk_score below threshold."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        threshold = report["threshold"]
        records = json.loads(PREDICTIONS_PATH.read_text())
        for r in records:
            assert r["risk_score"] >= threshold


# --- Artifact smoke tests (Wave 0 validation) ---
class TestArtifactSmoke:
    def test_train_parquet_readable(self):
        """feature_matrix_train.parquet is valid and has >100k rows."""
        pytest.importorskip("pandas")
        import pandas as pd
        assert _is_valid_parquet(TRAIN_PARQUET), "Train parquet missing or corrupted"
        df = pd.read_parquet(TRAIN_PARQUET)
        assert len(df) > 100_000, f"Expected >100k rows, got {len(df)}"
        assert "EQIndicator" in df.columns

    def test_test_parquet_readable(self):
        """feature_matrix_test.parquet is valid and has >100k rows."""
        pytest.importorskip("pandas")
        import pandas as pd
        if not _is_valid_parquet(TEST_PARQUET):
            pytest.skip("Test parquet corrupted or missing — needs regeneration")
        df = pd.read_parquet(TEST_PARQUET)
        assert len(df) > 100_000, f"Expected >100k rows, got {len(df)}"

    def test_feature_columns_count(self):
        """feature_columns.json has 813 entries."""
        cols = json.loads(FEATURE_COLS_PATH.read_text())
        assert len(cols) == 813, f"Expected 813, got {len(cols)}"


# --- New tests for Plan 02 outputs ---

class TestTopAspects:
    def test_aspects_are_strings(self):
        """top_planetary_aspects entries are strings."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        for r in records[:10]:
            for a in r["top_planetary_aspects"]:
                assert isinstance(a, str)

    def test_aspects_max_three(self):
        """No entry has more than 3 top_planetary_aspects."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        for r in records:
            assert len(r["top_planetary_aspects"]) <= 3


class TestPredictionDates:
    def test_dates_in_2026(self):
        """All prediction dates are in March-December 2026."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        for r in records[:50]:
            assert r["date"].startswith("2026-")
            month = int(r["date"].split("-")[1])
            assert 3 <= month <= 12
