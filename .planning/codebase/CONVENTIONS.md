# Coding Conventions

**Analysis Date:** 2026-03-14

## Naming Patterns

**Files:**
- Notebooks: PascalCase with descriptive title
  - Example: `Durga Copy of TSN ML Worksheet Full.ipynb`
  - Archive versions use date/version suffix: `Full Pipeline 10102019 TSN.ipynb`
- CSV data files: snake_case with semantic prefix
  - Example: `eqclean10272019.csv`, `2024_09_18 Astrology earthquake data processed.csv`
- Paths stored as constants with semantic naming: `earthquakePath`, `fileNameMajor`

**Variables:**
- DataFrame/object names use descriptive prefixes and suffixes
  - `eqAstroMajorPlanets`, `eqCleanP1`, `eqAstroTableDf`, `eqMLReady`
  - Suffix conventions: `_v#` for versions, `P#` for parts
- Intermediate/temporary variables: camelCase
  - Example: `numrandSamples`, `latLongSamp`, `randDatetime`, `linkList`
- Dictionary/mapping variables: camelCase with descriptive suffix
  - Example: `houseOrderDict`, `houseOrderFull`, `elementSignDict`, `starToElement`
- List variables: descriptive with List suffix
  - Example: `planetList`, `ListOfConstellations`, `ListOfThithis`, `linkList`

**Functions:**
- camelCase with descriptive verb-noun pattern
  - Example: `genLinkGivenInfo()`, `createDfFromLink()`, `processLinkResult()`, `planetAspectCalc()`
  - Simple utility functions: `get_Star_Titthi()`, `get_Planet_Star()`
- Parameters: lowercase with underscores for clarity where needed
  - Example: `genLinkGivenInfo(day,month,year,hour,minute,lat,long)`

**Types/Constants:**
- Astronomical/domain constants: UPPERCASE_WITH_UNDERSCORES or regular case for clarity
  - Example: `ListOfConstellations`, `ListOfThithis`, `planetList`, `houseOrder`
- Boolean flags and status fields: semantic, lowercase
  - Example: `EQIndicator`, `EQ_Happened`, `Retro`

## Code Style

**Formatting:**
- No explicit linting tool configured (notebook environment)
- Whitespace: Inconsistent indentation (2-4 spaces typical)
- Line breaks: Not enforced; code lines can exceed 80 characters
- Multi-line operations aligned for readability
  - Example: DataFrame operations use line breaks for `append`, `concat`, `drop` chaining

**Spacing:**
- Spaces around operators: inconsistent
  - Common: `= ` (assignment), `, ` (parameters)
  - Some parameters have no space: `(day,month,year,hour,minute,...)`
- List comprehensions: no space before brackets
  - Example: `[x for x,y in zip(...)]`

**Control Flow:**
- Indentation in functions: 2-4 spaces, inconsistent
- Nested loops: no extra blank lines between logic blocks
- Comments use `##` or `###` (markdown-style) for section breaks

## Import Organization

**Order:**
1. Standard library imports (requests, nltk, re, calendar, datetime, math, warnings)
2. Third-party data processing (pandas, numpy, bs4, xlrd)
3. ML/Data science (sklearn.cluster, sklearn.linear_model)
4. Visualization (matplotlib.pyplot)
5. Google Colab specific (google.colab.drive, google.colab.files)
6. Magic commands (%matplotlib inline)

**Path Aliases:**
- Not used (direct path strings instead)
- Example: `'/content/gdrive/My Drive/AstrologyEarthquakeTSN_AS/'` hardcoded as `earthquakePath` variable

**Import Style:**
- Module-level imports: `import pandas as pd`, `import numpy as np`
- Specific imports: `from sklearn.cluster import KMeans`, `from sklearn.linear_model import LogisticRegression`
- Warnings suppressed globally: `warnings.simplefilter(action='ignore', category=Warning)`

## Data Processing Patterns

**DataFrame Operations:**
- Read from CSV with path concatenation: `pd.read_csv(earthquakePath + fileName)`
- Column access: bracket notation `df['ColumnName']` or `.iloc[[index]]`
- Inspection: `.head()`, `.shape`, `.columns` pattern used frequently
- Modification: `.insert(position, column_name, values)` for adding columns
- Filtering: Boolean indexing `df[df['Column'] == value]`
- Concatenation: `pd.concat([df1, df2], ignore_index=True)`
- Dropping columns: `.drop(['col1', 'col2'], axis=1)`
- Value extraction: list comprehensions over columns

**String/Data Transformation:**
- String splitting: `.split('/')` for dates, `.split(':')` for times
- List comprehensions with conditional logic nested
  - Example: `[houseOrder[(houseOrderDict[x] + diff) % len(houseOrder)] for x in df[column]]`
- Type conversion: explicit via `int()`, `float()`, `str()` in list comprehensions
- Mathematical calculations inline in comprehensions
  - Example: `[(round(x) + 180) % 360 for x in series]`

## Error Handling

**Strategy:** Try-except blocks for data extraction operations

**Patterns:**
- Web scraping wrapped in try-except
  - `try: ... except: pass` (silent failures)
  - Example: Link generation and CSV parsing may fail for invalid data
- No explicit error logging; execution continues or prints skip message
- Partial commented-out error handling blocks (legacy approach)

**Example:**
```python
try:
    ### String Manipulation
    date = eqCleanP1.Date[i].split('/')
    time = eqCleanP1.Time[i].split(':')
    realDate = int(date[2])
    ...
except:
    pass  # Silent skip
```

## Logging

**Framework:** None (uses inline `print()` statements)

**Patterns:**
- Debug output: `print(i)` for loop progress tracking
- Inspection: `print(result.head())` for data validation
- Uncommented debug cells left in notebook (not removed)
- No structured logging; all output goes to notebook cell results

## Comments

**When to Comment:**
- Section breaks: `## Section Name` (markdown-style)
- Clarification of complex logic: `### The order of the houses`
- TODO/WIP notes: `## Needs to be updated based on Tbro progress...`
- Intent explanation: `#### Remove new line characters and empty characters so the data looks cleaner`

**Style:**
- Inline comments: `#` followed by space
- Block comments: `##` or `###` with extra emphasis
- Multi-line explanations: Multiple comment lines with consistent indentation
- Markdown cells used for major section separation (not code comments)

**JSDoc/Documentation:**
- Not used; no docstrings on functions
- Function intent must be inferred from name and code
- DataFrame structure documented inline via comments, not formal documentation

## Function Design

**Size:** Functions typically 10-40 lines
- Larger functions: `createDfFromLink()` (web scraping, 40+ lines)
- Smaller utilities: `planetAspectCalc()`, `get_Planet_Star()` (5-10 lines)

**Parameters:**
- Functions take explicit parameters: `def function(param1, param2, param3)`
- No default parameters observed
- No *args or **kwargs usage
- Type hints: None; Python untyped

**Return Values:**
- List return: `[planetName, remainder, starPada]` from `get_Planet_Star()`
- DataFrame return: `processLinkResult()` returns pandas DataFrame
- Modified DataFrame return: `createDfFromLink()` returns modified df with new columns
- Multiple return: rare; single return or list unpacking expected

## Module Design

**Exports:**
- No modules created; all code in notebook cells
- Functions defined at cell level, used in later cells
- Global variables (paths, constants) defined in early setup cells

**Barrel Files/Organization:**
- Not applicable (Jupyter notebook structure)
- Logical organization via markdown cells as section delimiters
- Related functions grouped by domain (astrology calculations, web scraping, ML)

## Notebook Structure

**Cell Organization:**
- Cell 0-5: Imports and path setup
- Cell 6-30: Data loading and web scraping setup
- Cell 31-50: Link generation and astrology data collection
- Cell 51-110: Data processing and feature engineering
- Cell 111-140: Exploratory data analysis
- Cell 141-166: Machine learning (supervised and unsupervised)

**Markdown Cells:** Used as section headers
- `## Setup`
- `## Link Generation`
- `## Creating Astrology Excel File`
- `## Prepare data: START HERE`
- `## Descriptive Analytics`
- `## Machine Learning Supervised`

---

*Convention analysis: 2026-03-14*
