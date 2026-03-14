# External Integrations

**Analysis Date:** 2026-03-14

## APIs & External Services

**Astrology Data Generation:**
- astro-seek.com - Generates sidereal astrology charts for earthquake events
  - SDK/Client: HTTP requests + BeautifulSoup web scraping
  - Auth: None (public web form submission)
  - Endpoint: `https://horoscopes.astro-seek.com/calculate-sidereal-chart/?tradicni=1&send_calculation=1...`
  - Integration point: `genLinkGivenInfo()` function in main notebook
  - Purpose: Given earthquake date/time/location, calculates planetary positions and astrological data
  - Data extracted: Sidereal zodiac positions, planetary degrees, house placements

**Earthquake Data Source:**
- USGS or similar (not explicitly named but inferred from data)
  - Source files: `EarthQuakeInput20002020.csv`, `eqclean10272019.csv`
  - Format: CSV with columns [List of events, Date, Time, Lat, Long, Magnitude, Place]
  - Integration: Direct CSV file ingestion via pandas.read_csv()

## Data Storage

**Databases:**
- None detected - purely file-based storage

**File Storage:**
- **Primary:** Google Drive (cloud storage)
  - Connection: `from google.colab import drive` with `drive.mount('/content/gdrive')`
  - Path: `/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/`
  - Contents: All processed CSV files and intermediate datasets

- **Secondary:** Local filesystem
  - CSV files stored locally in project root directory
  - Files: `eqclean10272019.csv`, `EarthQuakeInput20002020.csv`, `2024_09_18 Astrology earthquake data processed_columns.csv`, etc.
  - Format: CSV files with earthquake + astrology feature datasets

**Intermediate Datasets Generated:**
- `eqAstroTableDf.to_csv()` - Combined earthquake + astrology data
- `eqAstroDropPlanets.to_csv()` - Filtered dataset excluding certain planets
- `eqAstroMajorPlanets.to_csv()` - Major planets only (sidereal zodiac positions)
- `2024_09_18 Astrology earthquake data processed_columns.csv` - Latest processed output

**Caching:**
- None detected - all data re-processed on each notebook run

## Authentication & Identity

**Auth Provider:**
- Google (implicit via Colab and Drive)
  - Implementation: Google Colab handles OAuth automatically; no explicit token management
  - Scope: Google Drive file access

**Public APIs:**
- astro-seek.com - No authentication required (form-based, not API)

## Monitoring & Observability

**Error Tracking:**
- None detected - no Sentry, Rollbar, or similar integration

**Logs:**
- `warnings.simplefilter(action='ignore', category=Warning)` - Suppresses Python warnings globally
- Print statements throughout notebook for debugging
- No structured logging framework

## CI/CD & Deployment

**Hosting:**
- Google Colab (notebooks run on Google's infrastructure)
- Not deployed as a service; run as manual interactive notebooks

**CI Pipeline:**
- None detected - no GitHub Actions, Jenkins, or similar

**Execution Model:**
- Manual: User runs notebook cells sequentially in Colab
- Triggers: User clicking "Run cell" or "Run all" button
- No scheduled/automated runs detected

## Environment Configuration

**Required env vars:**
- None explicitly defined
- Google Drive path is hardcoded: `'/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/'`

**Secrets location:**
- None required - no API keys or credentials used
- Authentication handled implicitly by Google Colab

**Data paths hardcoded:**
- Earthquake path: `/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/`
- CSV filenames: `'eqclean10272019.csv'`, `'EarthQuakeInput20002020.csv'`, etc.

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- File downloads via `from google.colab import files` for exporting processed data
- Not webhook-based; manual file download

## Data Flow Summary

**Input:**
1. Historical earthquake data (CSV) - downloaded from external source, stored in Google Drive
2. Dynamic astrology calculations - generated on-demand via astro-seek.com web scraping

**Processing:**
1. Load earthquake CSV via pandas
2. For each earthquake event, generate astro-seek URL with date/time/location
3. Scrape HTML response with BeautifulSoup
4. Extract planetary positions, zodiac degrees, house placements
5. Combine with earthquake data in master DataFrame

**Output:**
1. Processed CSV files written to Google Drive
2. ML models trained (LogisticRegression, KMeans)
3. Predictions and visualizations generated in notebook

**Dataset Lineage:**
```
EarthQuakeInput20002020.csv → [genLinkGivenInfo scraping] → eqAstroTableDf
→ [Feature filtering] → eqAstroDropPlanets / eqAstroMajorPlanets
→ [Final processing] → 2024_09_18 Astrology earthquake data processed_columns.csv
```

## Web Scraping Implementation Details

**Target:** `horoscopes.astro-seek.com/calculate-sidereal-chart/`

**Method:** Form submission via URL query parameters
- Parameters built from earthquake: day, month, year, hour, minute, latitude, longitude
- Example: `narozeni_d=DD&narozeni_m=MM&narozeni_r=YYYY&narozeni_h=HH&narozeni_min=MM`

**Response parsing:**
- HTML table with zodiac positions (planets, houses, angles)
- BeautifulSoup extracts values from `<td>` cells
- Regex cleaning to handle formatting variations

**Rate limiting:** Not detected (may cause 429 errors if too many requests)

---

*Integration audit: 2026-03-14*
