"""Classifier factories for model selection and retraining."""

from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

LOGISTIC_REGRESSION_MODEL = "LogisticRegression"
XGB_CLASSIFIER_MODEL = "XGBClassifier"
XGB_SCALE_POS_WEIGHT = 10.0


def build_logistic_regression() -> LogisticRegression:
    """Build the configured sparse logistic regression classifier."""
    return LogisticRegression(
        C=1,
        penalty="l1",
        solver="liblinear",
        max_iter=1000,
        random_state=42,
    )


def build_xgb_classifier() -> XGBClassifier:
    """Build the configured XGBoost classifier."""
    return XGBClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        eval_metric="logloss",
        scale_pos_weight=XGB_SCALE_POS_WEIGHT,
    )


def build_classifier(model_name: str):
    """Build the classifier named in eval_report.json."""
    if model_name == LOGISTIC_REGRESSION_MODEL:
        return build_logistic_regression()
    if model_name == XGB_CLASSIFIER_MODEL:
        return build_xgb_classifier()
    raise ValueError(f"Unknown model_used in eval_report.json: {model_name!r}")
