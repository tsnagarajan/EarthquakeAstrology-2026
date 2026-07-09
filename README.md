# Earthquake Astrology Prediction 2026

A machine learning system that combines astrological planetary position data with historical earthquake records (M5.5+) to predict earthquake-risk dates and regions. Trains on 1900–2000 data, validates on 2000–2026, and produces predictions for the remainder of 2026. Predictions are served through a Next.js web app as an interactive calendar.

**Status: experimental / research project.** The current model (XGBoost) scores F1 = 0.0026 and MCC = 0.0009 on the 2000–2026 holdout — barely above chance. See [Methodology](#methodology--current-results) below before treating any prediction as reliable.

## How It Works

1. **Earthquake data** — M5.5+ events from the USGS FDSNWS Event API (1900–2026).
2. **Astrological data** — daily planetary positions (degrees, retrograde status, sign, house, nakshatra, aspects) computed with the Swiss Ephemeris.
3. **Feature engineering** — the two sources are joined into a per-date, per-grid-cell feature matrix (~813 columns).
4. **Model** — a binary classifier (XGBoost, compared against Logistic Regression) predicts earthquake risk per date/region.
5. **Web app** — pre-computed 2026 predictions are rendered as a static calendar, deployed on Vercel.

## Project Structure

```
pipeline/
  data/          USGS + Swiss Ephemeris data collection
  features/      Feature engineering (encoding, aspects, matrix building)
  model/         Training, evaluation, retraining, prediction export
data/
  raw/           Downloaded USGS + ephemeris CSVs (generated, not committed)
  processed/     Feature matrices, encoders, column lists
  models/        Trained model + eval report
web/             Next.js calendar app (deployed to Vercel)
tests/           pytest suite for the pipeline
```

## Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
cp .env.example .env   # set SE_EPHE_PATH to your Swiss Ephemeris data directory
```

## Running the Pipeline

```bash
# 1. Download earthquake catalog (1900–2026, M5.5+)
uv run python -m pipeline.data.usgs

# 2. Compute daily planetary positions
uv run python -m pipeline.data.ephemeris

# 3. Build feature matrices (train/test parquet, encoders, column list)
uv run python -m pipeline.features.engineering

# 4. Train and evaluate the model
uv run python -m pipeline.model.train_eval

# 5. Retrain on the full 1900–2026 range and serialize the final model
uv run python -m pipeline.model.retrain

# 6. Export 2026 predictions as JSON for the web app
uv run python -m pipeline.model.export_predictions
```

## Web App

```bash
cd web
npm install
npm run dev   # http://localhost:3000
```

## Tests

```bash
uv run pytest
```

## Methodology & Current Results

- Model: XGBoost (selected over Logistic Regression by MCC)
- Model selection train split: pre-2000 downsampled negatives; Eval: 2000–2026 holdout
- Decision threshold: 0.5285 (best F1 from PR curve)
- F1 = 0.0026, MCC = 0.0009 — the model performs close to random on the holdout set
- Full metrics: [`data/models/eval_report.json`](data/models/eval_report.json)
- The web app's Methodology page renders these numbers live from that report
- Regional Mexico/Peru/Chile scores are post-retrain sanity checks, not clean holdout validation, because the final serialized model is retrained on the full 1900–2026 range before regional scoring.

## Scope

- Binary risk classification only (no magnitude prediction)
- Static, pre-computed predictions — no live inference on the deployed web app
- Web-first, no mobile app
