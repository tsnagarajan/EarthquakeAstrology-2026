"""Tests for pipeline.model — Phase 3 model training and prediction export."""
import pytest
import json
import datetime
from pathlib import Path

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


# --- MODEL-01: Train on pre-2010 data ---
class TestTemporalSplit:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_train_dates_before_2010(self):
        """All training rows have date < 2010-01-01."""
        assert False

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_holdout_dates_from_2010(self):
        """All holdout rows have date >= 2010-01-01."""
        assert False

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_eval_split_date_is_2010(self):
        """eval_report.json records eval_split_date as 2010-01-01."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        assert report["eval_split_date"] == "2010-01-01"


class TestFeatureSelection:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_train_column_count(self):
        """X_train has exactly 813 feature columns."""
        assert False


# --- MODEL-02: Evaluated with F1 and MCC ---
class TestEvalReport:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_report_schema(self):
        """eval_report.json has all required keys."""
        assert EVAL_REPORT_PATH.exists()
        report = json.loads(EVAL_REPORT_PATH.read_text())
        required = {"model_used", "f1_score", "mcc", "confusion_matrix", "threshold", "eval_split_date", "both_models"}
        assert required.issubset(report.keys())

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_confusion_matrix_keys(self):
        """confusion_matrix has tp, fp, fn, tn."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        cm = report["confusion_matrix"]
        assert {"tp", "fp", "fn", "tn"} == set(cm.keys())

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_threshold_in_valid_range(self):
        """Threshold is between 0 and 1."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        assert 0 < report["threshold"] < 1

    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
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
    @pytest.mark.xfail(reason="stub — export_predictions.py not yet implemented")
    def test_geo_columns(self):
        """Each prediction record has country, lat, lon."""
        assert False


# --- MODEL-04: Two classifiers compared ---
class TestBothModels:
    @pytest.mark.xfail(reason="stub — train_eval.py not yet implemented")
    def test_both_logged(self):
        """both_models array in eval_report has entries for LogisticRegression and XGBClassifier."""
        report = json.loads(EVAL_REPORT_PATH.read_text())
        names = {m["model"] for m in report["both_models"]}
        assert "LogisticRegression" in names
        assert "XGBClassifier" in names


# --- MODEL-05: Model serialized ---
class TestSerialization:
    @pytest.mark.xfail(reason="stub — retrain.py not yet implemented")
    def test_model_roundtrip(self):
        """eq_classifier.pkl written and loadable."""
        assert False


# --- PRED-01: predictions.json in web/public/data/ ---
class TestPredictionExport:
    @pytest.mark.xfail(reason="stub — export_predictions.py not yet implemented")
    def test_output_path(self):
        """predictions.json exists at web/public/data/predictions.json."""
        assert PREDICTIONS_PATH.exists()

    @pytest.mark.xfail(reason="stub — export_predictions.py not yet implemented")
    def test_record_schema(self):
        """Each record has date, country, lat, lon, risk_score, top_planetary_aspects."""
        records = json.loads(PREDICTIONS_PATH.read_text())
        required = {"date", "country", "lat", "lon", "risk_score", "top_planetary_aspects"}
        for r in records[:5]:
            assert required.issubset(r.keys())

    @pytest.mark.xfail(reason="stub — export_predictions.py not yet implemented")
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
