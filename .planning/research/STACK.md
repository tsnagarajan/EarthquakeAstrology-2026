# Stack Research

**Domain:** ML prediction pipeline + Next.js/Vercel static web app (earthquake astrology)
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH (core Python/Next.js stack HIGH; pyswisseph maintenance status requires attention)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | ML pipeline runtime | scikit-learn 1.8.0 ships Python 3.12 wheels; pandas 2.1+ fully supports it; safest for 2025/2026 ML work |
| scikit-learn | 1.8.0 | Classification models, pipelines, preprocessing | Latest stable (Dec 2025); native Array API; Lasso LogReg and KNN match existing model choices; Pipeline API is essential for reproducible train/predict splits |
| pandas | 2.2+ | Data loading, feature engineering, CSV I/O | Standard for tabular ML data; required for 265+ feature columns; v2.x brings Copy-on-Write and Arrow backend for performance |
| numpy | 2.x (2.4.0) | Numerical operations underlying all ML | Underpins scikit-learn and pandas; 2.x branch is stable and required for scikit-learn 1.8 |
| pysweph | 2.10.3.6 | Swiss Ephemeris Python bindings for planetary positions | See ephemeris section below — use this fork, NOT pyswisseph |
| requests | 2.32+ | USGS FDSNWS HTTP API calls | Simplest approach for direct USGS API queries with pagination loop |
| Next.js | 15.x | Web UI framework | First-party Vercel support; App Router SSG pattern; Server Components run at build time to read local JSON |
| React | 19.x | UI component library | Bundled with Next.js 15; required for calendar/interactive views |
| Node.js | 22 LTS | Next.js runtime (build only) | LTS as of Oct 2024; Vercel uses this by default for Next.js 15 builds |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| xgboost | 2.x | Gradient boosting classifier | Use instead of or alongside LogReg when class imbalance is severe; `scale_pos_weight` parameter handles imbalanced EQ vs. non-EQ days natively |
| imbalanced-learn (imblearn) | 0.14.1 | SMOTE and other resampling strategies | Use only with "weak" learners (LogReg, KNN, SVM); skip for XGBoost which handles imbalance internally |
| joblib | 1.4+ | Model serialization, parallel grid search | Part of scikit-learn install; use `joblib.dump()` to save trained models to disk |
| matplotlib | 3.9+ | Training diagnostics, confusion matrices | Offline only — validation plots during model development |
| seaborn | 0.13+ | Statistical plots for feature analysis | Offline only — retrograde/aspect distribution analysis |
| python-dotenv | 1.x | Environment config for scripts | Store USGS API keys and ephemeris paths out of source code |
| tqdm | 4.x | Progress bars for long data downloads | USGS API downloads span 120+ years; pagination loop will take minutes without progress feedback |
| Tailwind CSS | 3.4+ | Styling for Next.js app | Zero-config Vercel deploys; utility classes reduce custom CSS needed for calendar grid |
| date-fns | 3.x | Date manipulation in Next.js | Parse and display earthquake prediction dates; lighter than moment.js |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager and venv | Replaces pip+venv; dramatically faster installs; use `uv sync` from `pyproject.toml` |
| pyproject.toml | Python project config | Define all Python dependencies, Python version constraint, script entry points |
| pytest | Test runner for Python scripts | Unit-test feature engineering functions and data loading; critical for 265-column feature pipeline |
| black | Python code formatter | Enforced formatting; avoids style debates across scripts |
| ruff | Python linter | Fast; replaces flake8+isort; catches unused imports in feature engineering |
| ESLint | JS/TS linting for Next.js | Pre-configured in Next.js 15 scaffold; catches React hooks mistakes |
| TypeScript | 5.x | Type safety for Next.js components | Catches JSON shape mismatches between Python output and web display |

---

## Ephemeris Deep-Dive: pysweph vs. pyswisseph

This is the highest-risk library decision in the stack. Two packages exist on PyPI:

### pyswisseph (DO NOT USE for new code)
- **PyPI:** `pyswisseph` — latest version 2.10.3.2, released June 2023
- **Status:** Effectively unmaintained. Documentation went offline in mid-2025. Maintainer unresponsive to issues and PRs.
- **Risk:** No Python 3.12 wheels confirmed; build-from-source required on modern systems.

### pysweph (USE THIS)
- **PyPI:** `pysweph` — latest version 2.10.3.6, released February 19, 2026
- **Status:** Active community fork of pyswisseph; same `import swisseph as swe` API surface
- **Breaking changes:** Yes — consult migration guide before upgrading existing code
- **Same underlying engine:** Swiss Ephemeris v2.10.03 (JPL DE431, 13201 BC – AD 17191, sub-milli-arcsecond accuracy)
- **Required data files:** Download from `https://www.astro.com/ftp/swisseph/ephe/` — specifically `sepl_18.se1`, `semo_18.se1`, `seas_18.se1`, `sefstars.txt`. Set `SE_EPHE_PATH` env var to their directory.

**Key functions you will use:**
```python
import swisseph as swe
swe.set_ephe_path("/path/to/ephe/")
jd = swe.julday(year, month, day, hour)  # Julian day number
xx, ret = swe.calc_ut(jd, swe.SUN)       # returns [longitude, lat, distance, speed, ...]
# Planet constants: swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
#                  swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO
# For Chiron: swe.CHIRON; For Lilith (Mean Apogee): swe.MEAN_APOG
# Retrograde: xx[3] (speed) < 0 means retrograde
```

---

## USGS Earthquake Data Pipeline

### Recommended approach: Direct FDSNWS API + requests (not libcomcat)

**Why not libcomcat:**
- Original GitHub repo (`usgs/libcomcat`) appears to be the archived version; active version is on USGS GitLab (`code.usgs.gov/ghsc/esi/libcomcat-python`)
- PyPI package name is `usgs-libcomcat` — adds dependency complexity
- For this project's needs (CSV download of M5.5+ events), direct requests calls are simpler and more maintainable

**USGS FDSNWS endpoint:** `https://earthquake.usgs.gov/fdsnws/event/1/query`

**Critical constraint:** 20,000 events maximum per request. The M5.5+ catalog from 1900–2026 will exceed this. Pagination strategy required:

```python
# Paginate by year chunks to stay under 20k limit
# M5.5+ events run approximately 1,500–2,000/year globally
# Chunking by year or 5-year windows is sufficient
params = {
    "format": "csv",
    "minmagnitude": 5.5,
    "starttime": "1900-01-01",
    "endtime": "1900-12-31",
    "orderby": "time-asc"
}
```

---

## Python-to-Vercel Static Deployment Pattern

This is the architectural crux of the project. Python ML cannot run on Vercel. The handoff is a static JSON file.

### The Pattern

```
[Python ML pipeline]
       |
       v
predictions.json  (written to next-app/public/data/)
       |
       v
[next build]  (Server Component reads file from disk at build time)
       |
       v
[Vercel CDN]  (serves pre-rendered HTML + JSON)
```

### Next.js side implementation

In Next.js 15 App Router, Server Components run at build time during `next build`. You can use Node.js `fs` directly:

```typescript
// app/page.tsx (Server Component)
import { readFileSync } from "fs";
import { join } from "path";

export default function Home() {
  const data = JSON.parse(
    readFileSync(join(process.cwd(), "public/data/predictions.json"), "utf8")
  );
  // render calendar view with data
}
```

**Alternative (simpler):** Fetch the JSON from its public URL at build time using `fetch()` inside a Server Component — Vercel will cache it statically.

**Do NOT use `output: 'export'`** unless you need a pure static HTML dump for non-Vercel hosting. On Vercel, `next build` without `output: 'export'` is the correct approach — Vercel's build system handles SSG automatically and preserves edge caching.

### JSON structure recommendation (for Python to output)

```json
{
  "generated_at": "2026-03-14T00:00:00Z",
  "model_version": "1.0",
  "predictions": [
    {
      "date": "2026-03-20",
      "risk_level": "high",
      "probability": 0.82,
      "regions": [
        { "country": "Japan", "lat": 35.6, "lon": 139.7, "confidence": "high" }
      ]
    }
  ]
}
```

---

## Installation

### Python ML environment

```bash
# Using uv (recommended)
pip install uv
uv init earthquake-ml
cd earthquake-ml

# pyproject.toml dependencies
uv add pysweph requests pandas numpy scikit-learn xgboost imbalanced-learn joblib tqdm python-dotenv matplotlib seaborn

# Dev tools
uv add --dev pytest black ruff
```

### Swiss Ephemeris data files (manual step — not pip installable)

```bash
mkdir -p data/ephe
# Download from AstroDienst FTP:
# https://www.astro.com/ftp/swisseph/ephe/
# Required: sepl_18.se1, semo_18.se1, seas_18.se1, sefstars.txt
# Add to .env:
echo "SE_EPHE_PATH=./data/ephe" >> .env
```

### Next.js web app

```bash
npx create-next-app@15 web --typescript --tailwind --app
cd web
npm install date-fns
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pysweph | pyswisseph | Never for new code in 2026 — pyswisseph is unmaintained |
| pysweph | Astro Seek scraping | Only if you need data for dates pysweph cannot compute (it covers 13201 BC–17191 AD, so there is no such date) |
| Direct USGS requests | usgs-libcomcat | If you need product-level data (ShakeMap, moment tensors) beyond basic hypocenters — not needed here |
| scikit-learn Pipeline | Manual train/predict scripts | Never — Pipeline prevents data leakage between train and test sets; critical for temporal holdout |
| XGBoost | LightGBM | LightGBM is faster on very large datasets; at 126 years of daily records (~46K rows), XGBoost is fine |
| App Router SSG | `output: 'export'` (full static) | Use `output: 'export'` only if hosting on S3/Netlify/GitHub Pages instead of Vercel |
| uv | pip + virtualenv | uv is strictly superior for new projects; only fall back to pip if CI environment blocks uv |
| Tailwind CSS | CSS Modules | CSS Modules if the team dislikes utility-class patterns; no objective performance difference |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| pyswisseph | Last release June 2023; maintainer gone; docs offline since mid-2025; no confirmed Python 3.12 support | pysweph 2.10.3.6 (Feb 2026) — same `import swisseph as swe` API |
| Jupyter notebooks | Project spec explicitly bans them; non-reproducible as scripts; hard to test | Python `.py` scripts with argparse entry points |
| TensorFlow / PyTorch | Massively over-engineered for 265-feature tabular binary classification on 46K rows | scikit-learn + XGBoost — SOTA for tabular data at this scale |
| Vercel serverless Python functions | Python ML dependencies (numpy, scikit-learn) far exceed Vercel's 50MB Lambda limit | Pre-compute predictions offline; ship JSON to Vercel |
| `next export` (legacy command) | Removed in Next.js 13+; use `output: 'export'` in next.config.js or just `next build` on Vercel | `next build` on Vercel (no config needed) |
| moment.js | 67KB, deprecated in favor of lighter alternatives | date-fns 3.x (tree-shakeable, TypeScript-native) |
| SQLite / PostgreSQL | No persistent database needed — all data is pre-computed CSV/JSON | Flat CSV files for ML pipeline, JSON for web |
| Real-time model inference | Python ML stack can't run on Vercel; adds infra complexity | Offline prediction generation → static JSON |

---

## Stack Patterns by Variant

**If hosting on Vercel (this project):**
- Use `next build` without `output: 'export'`
- Place predictions JSON in `public/data/` directory
- Read with Server Component `fs.readFileSync` or `fetch('/data/predictions.json')` at build time
- Vercel auto-CDN-distributes everything in `public/`

**If hosting on GitHub Pages / S3 instead:**
- Add `output: 'export'` to next.config.js
- Run `next build` — outputs to `/out` directory
- Deploy `/out` contents directly

**If planetary data scraping is needed (fallback only):**
- Use Playwright or httpx + BeautifulSoup against Astro Seek
- Add 1–2 second delays between requests to avoid rate limits
- Cache results to CSV immediately — scraping is fragile
- Prefer pysweph computation — scraping should be last resort only

**If model shows poor recall on minority class (EQ days):**
- First try: XGBoost `scale_pos_weight = n_negative / n_positive`
- Second try: imblearn SMOTE with LogReg (not XGBoost)
- Evaluate with F1/Precision-Recall, not accuracy (class imbalance will make accuracy misleading)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| scikit-learn 1.8.0 | Python 3.9–3.12, numpy 2.x, pandas 2.x | Python 3.12 wheels included in release |
| pandas 2.2+ | Python 3.9–3.12, numpy 1.23+ or 2.x | Copy-on-Write default in 2.x; review `.loc` usage in existing code |
| pysweph 2.10.3.6 | Python 3.x | Check migration guide from pyswisseph; breaking changes from 2.10.3.2 |
| xgboost 2.x | scikit-learn 1.x, Python 3.8–3.12 | Full Pipeline API compatibility |
| imbalanced-learn 0.14.1 | scikit-learn 1.x | Must match scikit-learn minor version; check imblearn docs |
| Next.js 15.x | Node.js 18.18+ (Node 22 LTS recommended) | App Router is default; Pages Router still supported |
| Tailwind CSS 3.4 | Next.js 15, PostCSS 8 | v4 (alpha) has breaking config changes — stay on 3.4 until stable |

---

## Sources

- [pysweph PyPI page](https://pypi.org/project/pysweph/) — version 2.10.3.6, Feb 2026 release, fork status (HIGH confidence)
- [pyswisseph PyPI page](https://pypi.org/project/pyswisseph/) — version 2.10.3.2, June 2023, maintenance status (HIGH confidence)
- [pyswisseph GitHub](https://github.com/astrorigin/pyswisseph) — ephemeris data file requirements (HIGH confidence)
- [USGS FDSNWS Event API](https://earthquake.usgs.gov/fdsnws/event/1/) — query parameters, 20k limit, CSV format (HIGH confidence, official source)
- [libcomcat USGS GitLab](https://code.usgs.gov/ghsc/esi/libcomcat-python) — alternative Python wrapper (MEDIUM confidence)
- [scikit-learn release notes](https://scikit-learn.org/stable/whats_new.html) — v1.8.0 Dec 2025, Python 3.12 support (HIGH confidence)
- [imbalanced-learn docs](https://imbalanced-learn.org/stable/) — v0.14.1 current, SMOTE guidance (HIGH confidence)
- [Next.js Static Exports guide](https://nextjs.org/docs/app/guides/static-exports) — App Router SSG pattern (HIGH confidence, official)
- [Vercel Next.js framework page](https://vercel.com/docs/frameworks/full-stack/nextjs) — deployment integration (HIGH confidence, official)
- WebSearch: pyswisseph maintenance discontinuation, mid-2025 (MEDIUM confidence — multiple sources agree)
- WebSearch: Python 3.12 scikit-learn/pandas compatibility 2025 (MEDIUM confidence — verified against PyPI release notes)

---

*Stack research for: Earthquake Astrology ML Prediction + Next.js/Vercel web app*
*Researched: 2026-03-14*
