# Testing Patterns

**Analysis Date:** 2026-03-14

## Test Framework

**Runner:**
- None formally configured
- Notebook cells serve as implicit tests via output inspection
- Manual execution and visual inspection of results

**Assertion Library:**
- No assertions used in codebase
- Validation via `Counter()` from collections for distribution checking
- Manual inspection: `.head()`, `.shape`, `.columns` for data validation

**Run Commands:**
```bash
# Not applicable - Jupyter notebook execution
# Cells executed sequentially in Google Colab environment
# Re-run all cells: Ctrl+F9 (or menu: Runtime > Run all)
# Run single cell: Ctrl+Enter
# Run cell and advance: Shift+Enter
```

## Test File Organization

**Location:**
- All testing embedded in notebook cells alongside production code
- No separate test files or test directory
- Code and validation mixed in same cells

**Structure:**
```
Durga Copy of TSN ML Worksheet Full.ipynb
├── Cell 0-5: Import tests (run imports without error)
├── Cell 9-14: Data loading validation (.head(), .shape)
├── Cell 45-52: Data processing output inspection
├── Cell 119-126: Feature engineering validation
├── Cell 128-139: Exploratory data analysis (Counter distributions)
├── Cell 143-161: Model training and visualization
└── Cell 161: Final visualization (parallel_coordinates)
```

## Test Structure

**Pattern: Manual Inspection via Output Cells**

Most validation is implicit:
```python
# Cell 9: Data inspection after loading
eqCleanP1.head()  # Visual inspection of first 5 rows

# Cell 10: Shape validation
eqCleanP1.shape  # Returns (354, 7) - confirms dimensions

# Cell 22: Count validation after data processing
len(linkList)  # Returns count to verify generation completed
```

**Pattern: Counter Distribution Checks**

For categorical data, distributions examined via Counter:
```python
# Cell 130: Check aspect distribution
Counter(eqDf['Moon:Mercury:aspect'])
# Output: Counter({1.0: 45, 0.0: 120, nan: 15})

# Cell 137: Check planet position distribution
Counter(eqDf['Mars:Sign'])
# Output: Counter({'Aries': 12, 'Taurus': 8, ...})

# Cell 31: Check label balance in training data
(eqAstroTableDf['EQ_Happened'] == 0).sum()  # Count non-earthquake samples
```

**Descriptive Analytics Cells (128-139):**

```python
# Filter to earthquake events only
eqDf = eqAstroMajorPlanets[eqAstroMajorPlanets['EQIndicator'] == 1]

# List all columns to validate data structure
[x for x in eqDf.columns]

# Counter-based validation for specific patterns
Counter([x for x,y,z in
         zip(eqDf['Mercury:CurrentStar'], eqDf['Moon:CurrentStar'], eqDf['Moon:Mercury:aspect'])
         if x == y and z==1.0])
```

## Mocking

**Framework:** None

**Patterns:**
- No mock objects used
- Real data from CSV files used for testing
- Hard-coded test paths: `earthquakePath = '/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/'`

**Data Fixtures:**
- Sample earthquake data: `eqclean10272019.csv` (354 events)
- Generated non-earthquake data: `numrandSamples = 2000`
- Test data created via random sampling:
  ```python
  latLongSamp = random.choices([(x,y) for x,y in zip(eqCleanP1.Lat,eqCleanP1.Long)], k=numrandSamples)
  ```

## Validation Patterns

**Data Integrity Checks:**
```python
# Shape validation
MLData.shape  # Confirms rows × columns after transformation

# Column existence verification
[x for x in eqDf.columns]  # Lists all columns for inspection

# Value distribution via Counter
Counter(eqAstroMajorPlanets['Jupiter:Retro'])  # Check binary/categorical values

# Null/NaN detection (implicit, not tested)
eqAstroMajorPlanets.info()  # Shows dtype and non-null counts
```

**Model Validation Approach:**

No formal cross-validation or test sets defined. Models evaluated via:

```python
# Cell 149: Logistic Regression fitting
clf = LogisticRegression(random_state=0, solver="liblinear").fit(
    MLData.drop('EQIndicator', axis=1),
    MLData['EQIndicator']
)
# No explicit accuracy, precision, recall metrics computed
# No train/test split

# Cell 153: K-Means clustering
KM = KMeans(n_clusters=2, random_state=0).fit(MLData)
Counter(KM.labels_)  # Check cluster distribution

# Cell 157: Cluster inspection
MLData[KMeans.labels_ == 0]  # Manual inspection of cluster composition
```

## Test Types

**Unit Tests:**
- Not formally implemented
- Individual function validation via cell output
- Example: `genLinkGivenInfo()` tested by printing generated link, checked manually

**Data Validation Tests:**
- Implicit: `.head()` and `.shape` calls verify data structure after each transformation
- Location: Lines 9-10, 30, 46, 120, 143 in notebook cells
- Purpose: Ensure data integrity through pipeline stages

**Integration Tests:**
- Implicit: Data flows from CSV → web scraping → feature engineering → ML
- Validated via output inspection at each stage
- No automated validation; manual "looks correct" approach

**End-to-End Validation:**
- Cell 161: Parallel coordinates visualization
  ```python
  listOfAttrs = ['Mars:Deg', 'Saturn:Deg', 'KMean2Label']
  pd.plotting.parallel_coordinates(MLData[listOfAttrs], 'KMean2Label', color=['blue','red'])
  ```
- Cell 158: Histogram comparison of features across clusters
  ```python
  plt.hist(MLData[planetDeg])
  plt.hist(MLData[KM.labels_ == 0][planetDeg])
  plt.hist(MLData[KM.labels_ == 1][planetDeg])
  plt.show()
  ```

**E2E Tests:**
- Not formally defined
- Visualization serves as smoke test (does the plot render?)
- Data completeness checked via `.head()` and `.shape`

## Test Data Strategy

**Training Data:**
- Real earthquake data: `eq20002020` from `EarthQuakeInput20002020.csv`
- Non-earthquake baseline: 2000 randomly generated lat/long/datetime samples
- No explicit train/test split
- All data used for model training

**Test Data:**
- None reserved for testing; models trained on all available data
- Validation via visual inspection of outputs and cluster distributions

**Data Generation:**
```python
# Random non-earthquake data generation
numrandSamples = 2000
latLongSamp = random.choices([(x,y) for x,y in zip(eqCleanP1.Lat, eqCleanP1.Long)],
                              k=numrandSamples)
randDatetime = zip(np.random.randint(1,28,numrandSamples),
                   np.random.randint(1,12,numrandSamples),
                   np.random.randint(1900,2020,numrandSamples),
                   ...)
```

## Coverage

**Requirements:** None enforced

**Approach:**
- 100% coverage implicit (all code in notebook executed)
- No code branches excluded or marked as untested
- Visual validation of output

**Analysis:**
- 166 cells executed sequentially
- Coverage measured by: does it run without error?
- No branch coverage analysis

## Model Validation

**Supervised Learning (Logistic Regression):**
- No train/test split
- No cross-validation
- No metrics computed (accuracy, precision, recall, F1)
- Model object created and stored: `clf`
- No predictions or performance evaluation in code

**Unsupervised Learning (K-Means):**
- Cluster distribution checked: `Counter(KM.labels_)`
- Cluster composition inspected manually: `MLData[KM.labels_ == 0]`
- Feature distribution across clusters visualized via histograms
- Parallel coordinates plot shows separation by cluster label

## Data Validation in ML Pipeline

**Feature Engineering:**
```python
# Cell 122-126: Degree calculation and transformation
ascendingHouseCalc = [round(int(x.split('°')[0]) + 1.0 * int(x.split('°')[1][:2]) / 60, 2)
                      for x in eqAstroMajorPlanets.AscHouseDeg]
ascendingHouseDegColumn = [houseOrderFull[x.split()[0]] * 30 + y
                           for x,y in zip(eqAstroMajorPlanets.AscendingHouse, ascendingHouseCalc)]

# Validation: insert into dataframe and inspect
eqAstroMajorPlanets.insert(17, "AscendingDegAbs", ascendingHouseDegColumn)
eqAstroMajorPlanets.head()  # Manual visual inspection
```

**Feature Selection:**
```python
# Cell 143: Select features for ML
MLData = eqAstroMajorPlanets.iloc[0:, 2:19].drop(['Place', 'Time'], axis=1)
# Validation: display to ensure correct columns selected
MLData
```

## Missing Critical Tests

**Issues Not Tested:**
1. **Web scraping robustness** - `createDfFromLink()` error handling commented out/incomplete
2. **Data type consistency** - No validation of numeric vs categorical columns
3. **Missing value handling** - No explicit handling of NaN/None values
4. **Model performance** - No accuracy, confusion matrix, or ROC metrics
5. **Hyperparameter tuning** - Fixed parameters only; no GridSearchCV
6. **Cross-validation** - No train/test split or k-fold validation
7. **Feature scaling** - LogisticRegression used without standardization (may impact results)
8. **Data drift** - No comparison of old vs new astrology data predictions

## Recommended Testing Additions

**For Robustness:**
- Try-except with logging around web scraping: `createDfFromLink()` at `Durga Copy of TSN ML Worksheet Full.ipynb` Cell 35
- Assert column names after DataFrame transformations: Cell 143
- Assert no NaN values in training features before model fitting: Cell 149

**For ML Validation:**
- Add train/test split: `from sklearn.model_selection import train_test_split`
- Compute metrics: `accuracy_score()`, `confusion_matrix()`, `classification_report()`
- Cross-validation: `cross_val_score()` with k=5

**For Data Quality:**
- Add data profiling cell after data load to check distributions
- Add feature correlation matrix: `corr_matrix = MLData.corr()`
- Add outlier detection for astrology degree features (0-360 range validation)

---

*Testing analysis: 2026-03-14*
