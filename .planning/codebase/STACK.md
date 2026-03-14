# Technology Stack

**Analysis Date:** 2026-03-14

## Languages

**Primary:**
- Python 3 - All computational and analysis work in Jupyter notebooks

**Scripting:**
- None at this stage - single language environment

## Runtime

**Environment:**
- Google Colab (Python 3.x) - Primary execution environment
- Jupyter Notebook - Local development and analysis

**Package Manager:**
- pip (implicit) - Dependencies installed via Google Colab or local environment
- Lockfile: Missing (no requirements.txt, environment.yml, or similar)

## Frameworks

**Data Processing & Analysis:**
- pandas - Core data manipulation and CSV/Excel file I/O
- numpy - Numerical computing and array operations
- xlrd - Reading Excel files for legacy data sources

**Machine Learning:**
- scikit-learn - ML models including LogisticRegression and KMeans clustering
- matplotlib - Data visualization for exploratory analysis

**Web Scraping & Data Collection:**
- requests - HTTP client for fetching data
- BeautifulSoup (bs4) - HTML parsing for astrology website scraping
- nltk - Natural language processing utilities

**Utilities:**
- re - Regular expression processing
- calendar - Date/time utilities
- math - Mathematical operations
- random - Randomization for ML splits
- datetime - Timestamp handling
- warnings - Python warning management

## Key Dependencies

**Critical:**
- pandas 1.x - Mandatory for data loading and transformation; processes CSV files with earthquake and astrology data
- scikit-learn 0.x/1.x - Required for machine learning models (LogisticRegression, KMeans); core to ML pipeline
- numpy 1.x - Required by pandas and scikit-learn; numerical operations

**Infrastructure:**
- google-colab (google.colab.drive, google.colab.files) - File mounting and download functionality in Google Colab environment
- requests - HTTP calls to astrology-seek website for data generation
- BeautifulSoup4 - Parsing HTML responses from web scraping

**Development:**
- xlrd - Reading legacy Excel prediction files (.xlsx format)
- matplotlib.pyplot - Inline visualization in notebooks (%matplotlib inline)

## Configuration

**Environment:**
- Google Colab filesystem with Google Drive mounting at `/content/gdrive`
- Data stored in Google Drive folder: `/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/`
- Local data directory (when run locally): Working directory contains CSV files

**Build:**
- No build system detected (notebook-based, no compilation)
- Jupyter notebook format (.ipynb) is the primary artifact

**Execution:**
- Cells execute sequentially in notebook order
- Output preserved in notebook format
- Data files referenced by relative path from notebook's root directory

## Platform Requirements

**Development:**
- Google Colab account (cloud-based) OR local Python 3 installation
- Google Drive account for data storage and retrieval
- Jupyter environment (Google Colab or local Jupyter server)
- Modern web browser (for Colab interface or Jupyter notebook UI)

**Production:**
- Deployment approach: Not defined; currently notebooks run on-demand in Google Colab
- No server/API deployment infrastructure detected
- Data pipelines are manual or Colab-triggered

## Version Information

**Python:** 3.x (specific version not pinned)

**No dependency versions pinned** - No requirements.txt, setup.py, environment.yml, or pyproject.toml found. Dependency versions managed implicitly by Google Colab or local environment.

---

*Stack analysis: 2026-03-14*
