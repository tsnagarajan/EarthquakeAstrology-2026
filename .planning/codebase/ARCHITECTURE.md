# Architecture

**Analysis Date:** 2026-03-14

## Pattern Overview

**Overall:** Jupyter-based ML pipeline with multi-stage data transformation and feature engineering

**Key Characteristics:**
- Notebook-centric architecture with sequential stages (Google Colab environment)
- Web scraping pipeline feeding into feature engineering and ML modeling
- Supervised learning (Logistic Regression) for binary earthquake prediction
- Unsupervised clustering (K-Means) for pattern discovery
- Astrology-based feature extraction from astrological calculations API

## Layers

**Data Ingestion Layer:**
- Purpose: Collect earthquake records and generate non-earthquake control samples
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 1-17
- Contains: CSV data loading, random non-event generation, date/time preparation
- Depends on: Pandas, local CSV files (eqclean10272019.csv, EarthQuakeInput20002020.csv)
- Used by: Link generation layer

**Link Generation Layer:**
- Purpose: Generate astrological calculation URLs based on earthquake metadata (date, time, location)
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 18-27
- Contains: URL template builder (`genLinkGivenInfo`), link list aggregation
- Depends on: Earthquake data (lat/long, date/time), string formatting
- Used by: Web scraping layer

**Web Scraping & Feature Extraction Layer:**
- Purpose: Fetch astrological charts from external service, parse HTML, extract planetary positions
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 28-55
- Contains: BeautifulSoup HTML parsing (`createDfFromLink`), constellation mapping, aspect table parsing (`processLinkResult`)
- Depends on: requests, BeautifulSoup, astro-seek.com API
- Used by: Feature engineering layer

**Feature Engineering Layer:**
- Purpose: Transform raw astrology data into machine learning features
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 56-126
- Contains: Planet filtering (major vs minor planets), aspect calculation (`planetAspectCalc`), house mapping, element/sign enumeration, star/naksatra extraction (`get_Star_Titthi`, `get_Planet_Star`)
- Depends on: Raw scraping output, astrological lookups (planet lists, house orders, sign mappings)
- Used by: ML preparation layer

**ML Data Preparation Layer:**
- Purpose: Clean, normalize, and select features for machine learning
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 114-142
- Contains: DataFrame slicing, column dropping (Place, Time), binary label assignment (EQIndicator)
- Depends on: Engineered features from feature layer
- Used by: ML training layer

**Machine Learning Layer:**
- Purpose: Train and evaluate predictive models
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cells 140-166
- Contains: Logistic Regression (supervised), K-Means clustering (unsupervised), model fitting, prediction
- Depends on: sklearn, prepared ML data
- Used by: Analysis/results interpretation

## Data Flow

**End-to-End Earthquake Prediction Pipeline:**

1. **Load Source Data** (cells 8-14)
   - Load earthquake events with date/time/location from `eqclean10272019.csv` and `EarthQuakeInput20002020.csv`
   - Load or create negative control samples (random dates, earthquake locations) - 2000 samples

2. **Generate Astrological Links** (cells 18-27)
   - For each event (EQ or non-EQ) with date/time/lat/long, construct URL to astro-seek.com sidereal chart calculator
   - Store full list of URLs with metadata

3. **Scrape Astrological Data** (cells 35-55)
   - Fetch each URL via requests library
   - Parse HTML response with BeautifulSoup to extract:
     - Planet positions (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Node, Lilith, Chiron)
     - House assignments (12 houses)
     - Aspects between planets (conjunction, opposition, trine, etc.)
     - Retrograde status
     - Naksatra (star) and Thithi (lunar phase)
     - House cusps and ascending degree
   - Store in DataFrame with 250+ columns

4. **Engineer Astrological Features** (cells 56-126)
   - Filter to major planets (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn)
   - Calculate aspect values (aspect type to numerical orb)
   - Map planetary degrees to zodiac signs
   - Extract elements (fire, earth, air, water) from signs
   - Map planet positions to naksatra (27 lunar mansions)
   - Create house position features
   - Add AscendingDegAbs for degree-based analysis

5. **Prepare for ML** (cells 114-142)
   - Select feature columns (index 2:19 and derived features)
   - Drop non-numeric columns (Place, Time)
   - Ensure target variable EQIndicator is binary (1=earthquake, 0=non-event)
   - Generate descriptive statistics on earthquake vs non-earthquake patterns

6. **Train ML Models** (cells 140-166)
   - **Supervised:** Fit LogisticRegression on feature set, target=EQIndicator
   - **Unsupervised:** Fit K-Means (n_clusters=2) to discover earthquake signature pattern
   - Evaluate through cluster distribution and regression coefficients

**State Management:**

- Local state: Variables stored in notebook kernel memory (eqCleanP1, eq20002020, eqAstroTableDf, eqAstroMajorPlanets, MLData)
- Persistent state: CSV files written to Google Drive at each major stage
- No explicit state machine; relies on cell execution order and variable naming conventions

## Key Abstractions

**Astrological Feature Set:**
- Purpose: Encapsulates planetary positions, aspects, and celestial configurations
- Examples: Columns like `Mars:Deg`, `Jupiter:Saturn:aspect`, `Moon:Element`, `star`, `thithi`
- Pattern: Prefix:SuffixPattern (e.g., PlanetName:PropertyType:AuxiliaryProperty)

**Link Builder:**
- Purpose: Maps earthquake metadata to astro-seek.com API query string
- Examples: `genLinkGivenInfo(day, month, year, hour, minute, lat, long)` in cell 19
- Pattern: Template-based URL construction with variable substitution

**DataFrame Transformer:**
- Purpose: Convert scraped HTML into structured feature columns
- Examples: `createDfFromLink()`, `processLinkResult()` in cells 35, 39
- Pattern: HTML parsing → intermediate DataFrame → final merged table

**Aspect Calculator:**
- Purpose: Compute angular relationships between planets
- Examples: `planetAspectCalc(planetName, diff)` in cell 70
- Pattern: Degree difference → aspect type lookup (0-360 range mapping)

## Entry Points

**Notebook Execution (Sequential):**
- Location: `Durga Copy of TSN ML Worksheet Full.ipynb` cell 0 onwards
- Triggers: Manual cell-by-cell execution or "Run All Cells" in Colab
- Responsibilities:
  - Mount Google Drive and set paths
  - Execute entire pipeline from data load through ML model training
  - Save intermediate results to CSV files for inspection

**Data Source - External Astrology API:**
- Location: astro-seek.com (URL pattern in cell 19)
- Triggers: Web scraping loop in cells 35-46
- Responsibilities: Provide sidereal astrological chart calculations for any datetime/location

**Data Source - Earthquake CSV Files:**
- Location: `eqclean10272019.csv`, `EarthQuakeInput20002020.csv` in project root
- Triggers: Cell 8 (pd.read_csv)
- Responsibilities: Provide ground truth earthquake event records with location/time data

## Error Handling

**Strategy:** Silent failure with warnings suppressed (warnings.simplefilter action='ignore')

**Patterns:**
- Network errors during web scraping: Not explicitly caught; partial data loss if astro-seek API fails mid-loop
- Parsing failures: BeautifulSoup fallback to empty values; missing columns handled by DataFrame initialization
- Data shape mismatches: Handled at DataFrame concatenation; columns added incrementally

**Risk:** No try/except blocks visible; pipeline brittle to API changes or missing data columns

## Cross-Cutting Concerns

**Logging:**
- Approach: Print statements for debugging (e.g., cell 9 `eqCleanP1.head()`, cell 22 `len(linkList)`)
- No structured logging; relies on notebook cell output inspection

**Validation:**
- Approach: Shape checks (e.g., cell 10 `eqCleanP1.shape`, cell 30 `eqAstroTableDf.shape`)
- No explicit data quality checks; assumes input CSVs are well-formed

**Authentication:**
- Approach: Google Colab mount (cell 5 `drive.mount()`) handles Drive auth
- No API key required for astro-seek.com public chart pages

**Feature Scaling:**
- Approach: Not visible in pipeline; raw astrology degrees (0-360) and ordinal aspects used directly
- Potential issue: Logistic Regression may benefit from normalization

---

*Architecture analysis: 2026-03-14*
