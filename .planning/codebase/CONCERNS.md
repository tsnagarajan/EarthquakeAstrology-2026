# Codebase Concerns

**Analysis Date:** 2026-03-14

## Tech Debt

**Google Colab Hard Dependencies:**
- Issue: Code requires Google Colab runtime with Google Drive mounted. Uses `from google.colab import drive` and hardcoded paths like `/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/`
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 5, 6, 62, 80, 81, 117, 118)
- Impact: Code cannot run on local machines, requires Google Colab environment. Breaks reproducibility and portability.
- Fix approach: Parameterize paths, remove Colab-specific imports, use relative paths or environment variables for data directory specification

**Duplicate Imports:**
- Issue: Libraries imported multiple times in same cell
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 0) - `import pandas as pd` appears twice, `import calendar` appears twice
- Impact: Code clutter, minor performance overhead, suggests incomplete refactoring
- Fix approach: Deduplicate imports in cell 0, establish single import block at notebook start

**Bare Exception Handlers with Silent Failures:**
- Issue: Multiple `except: pass` clauses that silently ignore errors during data processing
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 21, 23)
- Impact: Unknown data loss during web scraping and link generation. Rows with processing errors are silently dropped without logging. Cannot diagnose which earthquake records failed.
- Fix approach: Log caught exceptions, track failed rows, collect error statistics before proceeding

**Notebook Cell Organization:**
- Issue: Code split across multiple disconnected sections (Setup, Data Generation, Web Scraping, ML sections). Multiple cells re-import libraries and mount Google Drive.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 0, 79, 116 all re-import same libraries)
- Impact: Code repetition, hard to follow execution flow, easy to make mistakes when rerunning sections independently
- Fix approach: Consolidate imports to single location, create dependencies between cells, add execution order documentation

## Data Quality Issues

**Synthetic Non-Earthquake Data Generation:**
- Issue: 2000 random non-earthquake samples generated with arbitrary constraints (Cells 16-17)
  - Latitude/Longitude sampled from actual earthquake locations only
  - Years randomized between 1900-2000, not matching real-world earthquake distribution
  - Hours/minutes/days randomized uniformly, no seasonal or temporal patterns
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 16-17, 23)
- Impact: Synthetic negative class highly unrealistic. Model trains on implausible "non-earthquakes" that never reflect actual conditions. Predictions on real data will be unreliable.
- Fix approach: Generate synthetic data matching statistical distributions of actual earthquake data (temporal patterns, location clustering, seasonal variations)

**Incomplete Data Processing:**
- Issue: Silent row drops during web scraping (astro-seek.com parsing). Cells 21, 23 use `try/except: pass` with no logging of failure count
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 21, 23)
- Impact: Unknown percentage of original earthquake records excluded from analysis. Final dataset size may be artificially reduced. No audit trail of data loss.
- Fix approach: Log all exceptions, count successes/failures per batch, validate final dataset matches expected size

**Conflicting Earthquake Data Sources:**
- Issue: Project uses multiple earthquake CSV files with different formats:
  - `eqclean10272019.csv` - Original format (354 records, 2019 data)
  - `EarthQuakeInput20002020.csv` - Enhanced format with UTC times (2000-2020 data)
  - Notebook loads both but unclear which takes precedence
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 8, 13, 25)
- Impact: Potential double-counting, timestamp misalignment, unclear training data composition
- Fix approach: Establish single authoritative earthquake dataset, document version history, validate no duplicates across sources

**Missing Data Validation:**
- Issue: No validation that:
  - Latitude/longitude values are within valid ranges (±90°, ±180°)
  - Dates are valid calendar dates (e.g., no Feb 30)
  - Magnitudes are within seismic scale ranges (typically 0-10)
  - Web scraping extracted all required astrology fields correctly
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 21-25, 35)
- Impact: Invalid data silently included in training set. Model trained on corrupted coordinates or impossible dates.
- Fix approach: Add data validation step after each ETL stage, log validation failures, skip invalid rows

**Date/Time Format Inconsistencies:**
- Issue: Multiple date formats in use:
  - `eqclean10272019.csv`: M/D/YY format (e.g., "3/3/01")
  - `EarthQuakeInput20002020.csv`: Pandas datetime (UTC + local time columns)
  - Year conversion in Cell 21: `realDate = int(date[2]); realDate+=1900` assumes 2-digit years are 1900s
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 8, 13, 25)
- Impact: Earthquakes after 2000 mishandled (e.g., "05" becomes 1905, not 2005). Timezone conversions lost.
- Fix approach: Standardize all dates to ISO 8601, explicitly parse century, validate parsed dates match input

## ML Model Limitations

**Inadequate Model Validation:**
- Issue: Logistic regression and KMeans clustering trained on unspecified train/test split. No:
  - Cross-validation
  - Hold-out test set
  - Performance metrics (accuracy, precision, recall, F1)
  - Baseline comparison
  - Hyperparameter tuning
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 147, 149, 153)
- Impact: Cannot assess model generalization or predict real-world accuracy. Model may overfit random patterns in training data.
- Fix approach: Implement stratified train/test split (80/20), add cross-validation (5-fold), report standard metrics, establish baseline

**Class Imbalance Not Addressed:**
- Issue: Training data highly imbalanced:
  - ~350 real earthquakes (EQIndicator=1)
  - 2000 synthetic non-earthquakes (EQIndicator=0)
  - Ratio 1:5.7, but unclear if this reflects real-world earthquake rarity
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 16, 31, 128)
- Impact: Model biased toward predicting non-earthquake class. Precision/recall tradeoff not optimized for earthquake detection goal.
- Fix approach: Use class weights in LogisticRegression, evaluate on stratified metrics, consider SMOTE or undersampling

**Feature Engineering Lacking Documentation:**
- Issue: Astrology features extracted (planets in houses, degrees, aspects, thithis, nakshatras) but no explanation of:
  - Why these features matter for earthquake prediction
  - How they were selected (domain expert opinion? exhaustive search?)
  - Statistical significance testing
  - Correlation analysis between features and target
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 35-74, 120-127)
- Impact: Unknown if astrology features have predictive power. Model may learn spurious correlations from synthetic data.
- Fix approach: Add feature importance analysis, compute feature correlation with earthquake occurrence, document selection rationale

**Unsupervised Learning Ignored:**
- Issue: KMeans clustering trained but:
  - Results not compared to earthquake labels
  - No silhouette analysis or elbow method to validate K=2
  - Clusters not characterized in terms of earthquake vs. non-earthquake
  - Visualization suggests visual patterns but no quantitative evaluation
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 153-161)
- Impact: Unclear if clusters correspond to earthquake/non-earthquake or represent spurious structure. K=2 hardcoded without justification.
- Fix approach: Compute cluster purity (% of each cluster from target class), silhouette score, elbow method to determine optimal K

**No Temporal Validation:**
- Issue: Model trained on historical data (1900-2020) but:
  - No test set from recent years (2020+)
  - No evaluation of prediction capability on future unseen data
  - Temporal ordering of earthquakes ignored (sequential nature of time series)
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 128-161)
- Impact: Cannot assess if model generalizes to contemporary earthquakes. May fail on future data due to distribution shift.
- Fix approach: Use time-based train/test split (train on pre-2019, test on 2019-2020), implement time-series cross-validation

## Web Scraping & External Dependency Risks

**Brittle Web Scraping on astro-seek.com:**
- Issue: Project depends on web scraping from `horoscopes.astro-seek.com` to extract astrology data. Scraper uses hardcoded CSS class names:
  - `className = 'ascendent-vypocet-vpravo'` (Cell 35)
  - `c2Name = 'ascendent-vypocet-vlevo'` (Cell 35)
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 19, 35, 36)
- Impact: If website layout changes, scraper breaks silently (caught by bare except). No error notification. Cannot reproduce analysis or update data.
- Fix approach: Use astrology API instead of scraping, implement robust error handling with alerts, add website change monitoring, cache scraped results locally

**Network Dependency & Timeout Issues:**
- Issue: Code uses `requests.get()` without timeout, retry logic, or rate limiting
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 35)
- Impact: Requests may hang indefinitely. Processing 2500+ earthquakes vulnerable to network failures partway through. No recovery mechanism.
- Fix approach: Add request timeout (30s), implement exponential backoff retry (3 attempts), add request rate limiting (1s delay), checkpoint processed data

**Unvalidated HTML Parsing:**
- Issue: BeautifulSoup parses HTML without validating that expected elements exist or contain valid data
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 35)
- Impact: If astrology calculations unavailable (website down, bot detection, API changes), parser returns empty/null values silently
- Fix approach: Add validation to check all expected fields present, log parsing errors, validate extracted values are numeric and in valid ranges

## Security Considerations

**Hardcoded Credentials Path:**
- Issue: Google Drive path hardcoded: `/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/`
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 6, 81, 118)
- Impact: If pushed to GitHub, exposes Google account structure and folder organization
- Fix approach: Use environment variable or config file for paths, add `.env` to `.gitignore`, never hardcode personal account data

**External Data Source Trust:**
- Issue: Earthquake magnitude data loaded from CSV without validation of:
  - Source reliability (USGS vs. unofficial sources)
  - Data integrity (checksums, digital signatures)
  - Version control (which database version?)
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 8, 13, 25)
- Impact: Model trained on potentially incorrect earthquake data. Predictions inherit data quality issues.
- Fix approach: Use official USGS Earthquake Hazards Program API, implement data provenance tracking, validate against multiple sources

## Missing Critical Features

**No Model Persistence:**
- Issue: Trained models (LogisticRegression, KMeans) exist only in notebook memory. No saving/loading capability.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 147, 149, 153)
- Impact: Cannot export trained model for production use or share with collaborators. Must retrain from scratch each session.
- Fix approach: Save models using `joblib.dump()` or `pickle`, create model versioning system, document model hyperparameters

**No Production Pipeline:**
- Issue: Notebook is exploratory; no structured ETL pipeline for:
  - Automatic data ingestion from earthquake sources
  - Scheduled model retraining
  - Prediction serving endpoints
  - Result logging and monitoring
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (entire notebook)
- Impact: Cannot deploy model for real-time earthquake prediction. Manual rerun required for new data.
- Fix approach: Refactor to modular Python scripts, implement scheduler (Airflow/Cron), create Flask/FastAPI prediction service

**No Prediction Confidence/Uncertainty Quantification:**
- Issue: Model predictions lack:
  - Probability scores (logistic regression returns binary class only)
  - Confidence intervals
  - Uncertainty estimates
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 147)
- Impact: Cannot assess prediction confidence. Users don't know if prediction is 51% or 99% certain.
- Fix approach: Use `predict_proba()` instead of `predict()`, implement Bayesian uncertainty, add calibration curves

## Test Coverage Gaps

**No Automated Testing:**
- Issue: Zero unit tests, integration tests, or acceptance tests. Quality assurance relies entirely on manual notebook execution.
- Files: Entire project - no `.py` test files found
- Impact: Cannot detect regressions when code changes. Data processing errors discovered only after full run completion (hours).
- Fix approach: Create `tests/` directory with unit tests for data cleaning, feature engineering, model validation

**No Data Quality Tests:**
- Issue: No automated checks for:
  - Expected row counts after each processing stage
  - Valid coordinate ranges
  - Date format correctness
  - Null/NaN value thresholds
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb`
- Impact: Silent data loss or corruption not detected until analysis phase
- Fix approach: Create test fixtures with known-good data, implement data contract validation

## Fragile Areas

**Web Scraping Pipeline (Cells 19-25, 35-47):**
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 19-47)
- Why fragile: Depends on external website CSS structure, network reliability, rate limiting tolerance. Single site failure blocks entire dataset completion.
- Safe modification: Before changing, add comprehensive logging and retry logic. Test against known-good astro-seek responses. Cache results locally before relying on them.
- Test coverage: Missing - no tests for HTML parsing robustness or website changes

**Feature Engineering Logic (Cells 35-74):**
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 35-74)
- Why fragile: Complex astrology domain logic (planetary aspects, nakshatra calculations, thithi mapping). Hard to understand without astrology knowledge. Multiple nested dictionaries and coordinate transformations.
- Safe modification: Document astrology calculation methodology, add unit tests with known astrology reference data, validate output ranges
- Test coverage: Missing - no verification that aspect calculations (6°, 120°, 180° etc.) are correct

**Date/Time Processing (Cells 8, 13, 21, 25):**
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 8, 13, 21, 25)
- Why fragile: Manual string splitting and parsing. Year conversion assumes 1900s for 2-digit years. Timezone handling incomplete.
- Safe modification: Use `pd.to_datetime()` for all parsing, validate parsed dates against original input, add explicit century specification
- Test coverage: Missing - no tests for edge cases (leap years, daylight saving, historical timezone changes)

**Model Training (Cells 147, 149, 153):**
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 147, 149, 153)
- Why fragile: No random seed set, so results not reproducible. Train/test split not explicit (trains on all data?). Hyperparameters hardcoded.
- Safe modification: Set `random_state=42` in all sklearn calls, add explicit train/test split, create hyperparameter configuration file
- Test coverage: Missing - no tests for model stability across random seeds

## Performance Bottlenecks

**Serial Web Scraping:**
- Problem: Processes 2500+ earthquake records sequentially via `requests.get()` (Cells 21-25, 44-47). Single server request takes ~1-2 seconds, total time ~1-2+ hours.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 44-47)
- Cause: No parallelization, no async I/O, no request pooling
- Improvement path: Implement parallel requests using `concurrent.futures`, add local caching to skip already-scraped records, consider queue-based architecture

**In-Memory Data Processing:**
- Problem: Large astrology dataset (5.1MB CSV = ~50K rows) loaded entirely into Pandas DataFrame. Feature engineering operates on full dataset in memory.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 72-74, 123-127)
- Cause: No streaming or chunked processing
- Improvement path: Use chunked reads for large files, implement incremental feature engineering, add DataFrame partitioning for large datasets

**Unindexed Data Lookups:**
- Problem: Planet aspect calculations use list iteration and dictionary lookups (Cell 70: `planetAspectCalc`). With 100s of astrology columns, repeated calculations slow.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 70-71)
- Cause: No vectorization, calculations not optimized for pandas
- Improvement path: Vectorize calculations using NumPy, precompute aspect tables, cache intermediate results

## Known Data Issues

**Typos in Earthquake Place Names:**
- Issue: Place column contains spelling errors:
  - "Cheviot,New zelznd" (should be "New Zealand")
  - "Sanfrancisco,California" (should be "San Francisco")
  - Formatting inconsistent (some use commas, some use periods)
- Files: `/Users/tirunelvelynagarajan/Desktop/EarthquakeAstrology/Earthquake 2026/eqclean10272019.csv`
- Impact: May affect location-based analysis if earthquake place used as feature or for validation
- Fix approach: Add place name normalization and validation against gazetteer, standardize formatting

**Date Ambiguity in 1900s Data:**
- Issue: `eqclean10272019.csv` uses 2-digit year format (e.g., "01" for 1901). Code assumes 1900s:
  - "01" → 1901 ✓
  - "99" → 1999 ✓
  - But no validation that parsed year makes sense historically
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 21)
- Impact: If year parsing fails, earthquake events misaligned in time. Astrology calculations wrong for shifted dates.
- Fix approach: Validate all parsed years are within seismic record range (1900-2020), log conversions, cross-reference against USGS database

## Dependency & Version Issues

**Deprecated Library Usage:**
- Issue: Uses BeautifulSoup without specifying parser. Default parser varies by installed `html5lib` version.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 35)
- Impact: HTML parsing results may vary across environments or versions
- Fix approach: Explicitly specify parser: `BeautifulSoup(r.text, 'html.parser')`

**Missing Requirements Documentation:**
- Issue: No `requirements.txt` or `environment.yml`. Hard to reproduce environment.
- Files: Project root missing dependency specification
- Impact: Cannot guarantee same versions of pandas, sklearn, requests across machines/times
- Fix approach: Create `requirements.txt` with pinned versions, add Python version specification, document installation steps

**No Notebook Dependencies:**
- Issue: Notebook execution order not enforced. Cells can be run out of order, causing KeyErrors or undefined variables.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (multiple interdependent cells)
- Impact: If user runs cells in wrong order (e.g., skips data loading), analysis fails cryptically
- Fix approach: Document execution order in markdown cells, consolidate setup into single cell, use cell parameters to enforce dependencies

## Validation & Reproducibility Issues

**No Random Seed Control:**
- Issue: Random sampling (Cells 16-17) and KMeans (Cell 153) use default random state. Results non-reproducible.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 16, 153)
- Impact: Each run generates different synthetic earthquake samples and cluster assignments. Cannot reproduce published results.
- Fix approach: Set `random_state=42` in all random operations, document seed in methods section

**Lack of Results Artifacts:**
- Issue: No saved outputs (predictions, model files, evaluation plots) from notebook runs. Only CSV files manually saved.
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb`
- Impact: Cannot compare results across runs, no audit trail of model performance evolution
- Fix approach: Implement automatic result logging (model files, prediction CSVs, evaluation metrics), version outputs with timestamps

## Astrology Domain Concerns

**Unvalidated Astrology Calculations:**
- Issue: Nakshatra (stellar mansion) calculations in Cell 73 assume specific sidereal astrology system. Methodology not cited.
  - Quotient formula: `quotient = int(planetLong*3/40)` assumes 40° per sign × 12 signs = 360°
  - No reference to Lahiri, Fagan-Bradley, or other ayanamsha systems
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cell 73)
- Impact: If using wrong ayanamsha, all planetary positions off by 20-30°, rendering astrology features invalid
- Fix approach: Document which ayanamsha system used, cite astrology source (JPL Ephemeris, etc.), validate against reference calculations

**Planetary Aspects Not Validated:**
- Issue: Hard aspects (6°, 120°, 180° etc.) defined in Cell 71 but no tolerance or orb specification
  - Are exactly 180.0° or 175-185° counted as opposition?
  - Orb varies by planet (Sun-Moon has wider orb than Mars-Saturn)
- Files: `Durga Copy of TSN ML Worksheet Full.ipynb` (Cells 70-71)
- Impact: Aspect detection may miss real aspects (too strict orb) or create false positives (too loose)
- Fix approach: Document orb tolerances, validate against astrology references, add configurable orb parameters

**Correlation Between Astrology and Earthquakes Unproven:**
- Issue: Project assumes astrology features predict earthquakes but provides no literature justification or prior art
- Files: Entire project
- Impact: Scientific validity of approach unestablished. Model may learn random correlations from coincidental data
- Fix approach: Review published literature on astrology-earthquake correlations, establish statistical significance testing, compare to random baseline predictor

---

*Concerns audit: 2026-03-14*
