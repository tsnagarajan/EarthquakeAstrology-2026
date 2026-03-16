# Phase 3: Model Training and Prediction Export - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Train a classifier on pre-2010 data, evaluate on 2010–2026 holdout using F1 and MCC, then retrain the winning model on the full 1900–2026 dataset and export predictions.json covering March–December 2026. Model artifacts live in `data/models/`. Predictions go to `web/public/data/predictions.json`. Web app and deployment are out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Training Data Strategy
- **Two-stage training:** model selection uses 1900–2010 train / 2010–2026 holdout; final prediction model retrains on full 1900–2026 data
- **Phase 3 re-splits internally:** read both Phase 2 parquets (`feature_matrix_train.parquet` + `feature_matrix_test.parquet`), concatenate, then partition at `2010-01-01` (date-only comparison — no timestamp needed since both parquets use date index)
- **Temporal split constant:** `EVAL_SPLIT_DATE = datetime.date(2010, 1, 1)` — rows with `date < 2010-01-01` = model selection train set; `date >= 2010-01-01` = holdout
- **Downsampling:** 10:1 negative-to-positive ratio applied to the training partition, consistent with Phase 2. Final retrain (1900–2026) also uses 10:1 downsampling. Test/holdout is never downsampled.
- **Class imbalance handling:** downsampling (already applied in Phase 2 train parquet) — no additional SMOTE or class_weight='balanced' in the classifier

### Model Selection
- **Candidates:** Lasso Logistic Regression (C=1, penalty='l1', solver='liblinear') vs XGBoost (n_estimators=100, max_depth=6, use_label_encoder=False)
- **Winner criterion:** highest MCC on the 2010–2026 holdout — MCC is most reliable for severe class imbalance (most rows are EQIndicator=0)
- **No cross-validation / hyperparameter tuning** — train once with fixed params. Reproducible and avoids temporal leakage within the training period. Tuning is out of scope for this phase.
- **Both models evaluated and logged** to eval_report.json for Phase 4 methodology page

### Evaluation Report
- **Format:** JSON at `data/models/eval_report.json`
- **Contents:** `model_used` (name of winner), `f1_score`, `mcc`, `confusion_matrix` (object with `tp`, `fp`, `fn`, `tn`), `threshold`, `eval_split_date`, `both_models` (array with f1/mcc for each candidate)
- **Threshold stored here** — prediction export script reads threshold from eval_report.json; no hard-coding, no re-running PR curve at export time

### Risk Threshold Selection
- **Method:** Precision-recall curve on the 2010–2026 holdout; threshold selected at the best F1 operating point (argmax of F1 across all PR threshold values)
- **Stored in eval_report.json** as `threshold` field — single source of truth for prediction filtering
- **No per-day cap** — all (date, grid_cell) pairs with `risk_score >= threshold` are included in predictions.json. File size is naturally controlled by the threshold itself.

### top_planetary_aspects Derivation
- **Source:** aspect boolean columns (e.g., `sun_moon_conjunction`, `mars_saturn_square`) that are `True` / `1` for the given date row in the feature matrix
- **Count:** top 3 aspects per entry; if fewer than 3 are active, include all active ones
- **Ranking:** sort active aspects by the winning model's feature importance (`coef_` for LogReg, `feature_importances_` for XGBoost) — highest-importance active aspects listed first
- **Feature importance is computed once after training** and reused for all prediction rows; no per-row SHAP computation

### Final Prediction Export
- **Scope:** March–December 2026 (2026-03-01 through 2026-12-31)
- **Model:** winning model retrained on full 1900–2026 data (10:1 downsampled)
- **Schema per entry:** `date` (ISO string), `country`, `lat` (grid_lat), `lon` (grid_lon), `risk_score` (float 0–1), `top_planetary_aspects` (array of ≤3 strings)
- **Filter:** only entries with `risk_score >= threshold` (threshold from eval_report.json)
- **Output path:** `web/public/data/predictions.json` — Next.js app reads this at build time

### Claude's Discretion
- Exact scikit-learn Pipeline wrapping (whether to use Pipeline API or fit models directly)
- How to generate 2026 feature rows (whether to reuse Phase 2 logic or inline ephemeris reads)
- File size monitoring / warning if predictions.json exceeds a reasonable size
- Logging verbosity and progress reporting during training runs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §ML Model (MODEL-01 through MODEL-05) — training, evaluation, comparison, and serialization requirements
- `.planning/REQUIREMENTS.md` §Prediction Export (PRED-01 through PRED-03) — predictions.json path, schema, and threshold filtering rules

### Phase 2 Artifacts (inputs to Phase 3)
- `data/processed/feature_matrix_train.parquet` — pre-2000 rows, 10:1 downsampled, 813 feature columns + EQIndicator + grid_lat + grid_lon + country
- `data/processed/feature_matrix_test.parquet` — post-2000 rows, not downsampled, same schema
- `data/processed/feature_columns.json` — list of 813 feature column names in order
- `data/processed/nakshatra_encoder.pkl` — fitted OneHotEncoder for nakshatra columns (may be needed if 2026 rows are generated from raw ephemeris)

### Phase 2 Source (reference for column conventions)
- `pipeline/features/engineering.py` — column naming conventions, aspect column patterns, grid cell logic

No external specs beyond the above — all requirements are captured in REQUIREMENTS.md and this context file.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/features/engineering.py`: grid cell assignment logic, aspect column naming (`{planet1}_{planet2}_{aspect_type}`), country parsing — needed when generating 2026 feature rows
- `data/processed/feature_columns.json`: exact 813-column list — Phase 3 must select exactly these columns from the combined parquet before fitting/predicting
- `data/processed/nakshatra_encoder.pkl`: fitted encoder — must be loaded (not re-fit) when encoding 2026 ephemeris rows to avoid test leakage

### Established Patterns
- Logging: `logging.basicConfig(...)` + `logger = logging.getLogger("module_name")` pattern established in Phase 1/2 scripts
- Date index: parquets use `datetime.date` objects as index level — Phase 3 split comparison must use `datetime.date(2010, 1, 1)`, not a pandas Timestamp
- Scikit-learn pipeline: REQUIREMENTS.md MODEL-01 specifies scikit-learn Pipeline API so no scaler/encoder is fit on post-train rows

### Integration Points
- Phase 3 reads from `data/processed/` (Phase 2 outputs)
- Phase 3 writes to `data/models/` (must be created): `eq_classifier.pkl`, `eval_report.json`
- Phase 3 writes `web/public/data/predictions.json` — requires `web/public/data/` directory to exist (Phase 4 creates the Next.js app but the directory can be created by Phase 3)
- Phase 4 reads `data/models/eval_report.json` at build time for the methodology page (F1, MCC, confusion matrix, threshold)

</code_context>

<specifics>
## Specific Ideas

- Two-stage training is intentional: use 1900–2010 → 2010–2026 to pick the best estimator (clean holdout), then retrain on all available data (1900–2026) before generating future predictions — this is the standard "full retrain before forecasting" practice
- The 2026 prediction rows need planetary features for dates that don't exist in the Phase 2 parquets — the plan should specify how these future rows are generated (likely by reading `data/raw/ephemeris.csv` for dates in March–December 2026 and applying the same encoding)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-model-training-and-prediction-export*
*Context gathered: 2026-03-16*
