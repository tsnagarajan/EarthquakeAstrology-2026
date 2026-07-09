# Earthquake Model Retrain Design

## Context

`Retrain_Instructions_for_Aditya_July2026.md` asks for a full investigation and retrain after the Mexico/Peru/Chile reproducibility check failed to match the published hit rates. The two likely root causes are:

- `pipeline/model/train_eval.py` trains model-selection candidates on pre-2000 rows plus a downsampled 2000-2010 slice, then evaluates on 2010-2026.
- The published Phase 2 methodology mentions `scale_pos_weight=10.0` for XGBoost, but the current `XGBClassifier` call does not set it.

The user chose an end-to-end run instead of stopping for approval after each diagnostic step. The final workflow should still report each finding clearly, but it should not pause between Step 1 through Step 5 unless execution fails or evidence contradicts the design.

## Goal

Run one reproducible end-to-end retrain and validation pass that corrects the temporal split and missing XGBoost class weighting, then reports the corrected holdout metrics and Mexico/Peru/Chile sanity-check results without pushing to GitHub.

## Scope

In scope:

- Confirm `data/processed/feature_matrix_train.parquet` and `data/processed/feature_matrix_test.parquet` exist, are readable, and use the intended pre-2000/post-2000 split.
- Report row counts, date ranges, and positive/negative class rates for the current train and test matrices.
- Change `pipeline/model/train_eval.py` so model selection trains only on the downsampled pre-2000 training parquet and evaluates on all post-2000 test rows.
- Ensure `eval_report.json` records `eval_split_date` as `2000-01-01`.
- Add `scale_pos_weight=10.0` to the XGBoost model-selection classifier.
- Keep Logistic Regression as a comparison model with the existing parameters.
- Run model evaluation and report MCC, F1, threshold, confusion matrix, and both-model comparison.
- Retrain the final serialized model with the selected winner so downstream regional scoring uses the corrected winner and hyperparameters.
- Re-run the Mexico/Peru/Chile sanity check and report hit rate, base rate, and lift against the published hit rates.
- Run focused tests for temporal split metadata, XGBoost parameters, and regional scoring behavior.

Out of scope:

- Pushing to GitHub.
- Changing paper text or deciding how to handle already-published numbers.
- Rebuilding raw USGS or Swiss Ephemeris data unless the existing parquet files are missing, corrupt, or not split at `2000-01-01`.
- Adding new regions beyond the existing regional scoring output unless needed by the current scoring script.
- Tuning multiple alternative XGBoost hyperparameter sets.

## Architecture

The corrected workflow keeps the current pipeline shape:

- `pipeline/features/engineering.py` remains responsible for creating the canonical train/test matrices. It already documents and implements the `2000-01-01` split.
- `pipeline/model/train_eval.py` becomes the model-selection evaluator for the same canonical split: train on `feature_matrix_train.parquet`, evaluate on all rows in `feature_matrix_test.parquet`.
- `pipeline/model/retrain.py` remains responsible for serializing the final model, but it must instantiate the selected XGBoost model with the same corrected `scale_pos_weight=10.0` setting if XGBoost wins.
- `pipeline/model/add_regions.py` regenerates `data/processed/feature_matrix_test_with_regions.parquet` using the corrected serialized model.
- `pipeline/model/regional_scoring.py` computes country-level sanity checks for Mexico, Peru, and Chile from the regenerated region parquet.

No new broad abstraction is needed. The change is a narrow correction to split semantics, model parameters, and tests that protect those semantics.

## Data Flow

1. Inspect current parquet metadata and date/class distributions.
2. If parquets already satisfy `train.date < 2000-01-01` and `test.date >= 2000-01-01`, reuse them.
3. If either parquet violates the split, run `uv run python -m pipeline.features.engineering` to rebuild the canonical matrices.
4. Run `uv run python -m pipeline.model.train_eval` to evaluate candidates on the corrected holdout and write `data/models/eval_report.json`.
5. Run `uv run python -m pipeline.model.retrain` to serialize the final corrected classifier and feature importance.
6. Run `uv run python -m pipeline.model.add_regions` to attach corrected risk scores and region labels to the post-2000 test matrix.
7. Run `uv run python -m pipeline.model.regional_scoring` to write the regional validation JSON and report Mexico/Peru/Chile results.

## Artifact Policy

The workflow may update generated artifacts under `data/models/` and `data/processed/`. These updates are expected because the goal is to retrain and rescore. Existing uncommitted user work must not be reverted.

The final response should distinguish code changes from generated output and should list every changed artifact that matters for review.

## Error Handling

- If a required parquet file is missing or unreadable, rebuild feature matrices before training.
- If raw data required for a rebuild is missing, stop and report the missing files instead of fabricating results.
- If dependencies are missing, install or sync through the project toolchain only with user approval when network access is required.
- If the corrected workflow produces much worse or contradictory metrics, still report the results as observed and do not tune around them without a new design decision.

## Testing

Focused tests should cover:

- `train_eval.EVAL_SPLIT_DATE` is `datetime.date(2000, 1, 1)`.
- `select_winner_and_write_report()` records `eval_split_date` from the constant rather than a hard-coded 2010 string.
- The XGBoost factory or instantiation includes `scale_pos_weight=10.0`.
- Existing engineering temporal leakage tests still pass.
- Existing regional scoring tests or smoke checks still pass if present.

Runtime verification should include:

- `uv run pytest` for the relevant targeted tests before retraining.
- `uv run python -m pipeline.model.train_eval`.
- `uv run python -m pipeline.model.retrain`.
- `uv run python -m pipeline.model.add_regions`.
- `uv run python -m pipeline.model.regional_scoring`.

## Reporting

The final report should include:

- Current parquet row counts, date ranges, and class rates.
- Exact code corrections made.
- New `eval_report.json` values: selected model, MCC, F1, threshold, confusion matrix, and both-model metrics.
- Mexico/Peru/Chile hit rate, base rate, lift, and comparison to published hit rates of 61.9%, 45.8%, and 38.5%.
- Any command that could not be run and why.
