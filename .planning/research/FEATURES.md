# Feature Research

**Domain:** Earthquake prediction ML system with astrology feature engineering + calendar prediction web UI
**Researched:** 2026-03-14
**Confidence:** MEDIUM

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Calendar heatmap view of 2026 predictions | Primary UI contract — users coming to see "which dates are high risk" | MEDIUM | Color-coded by risk intensity; GitHub-contribution-style or monthly grid. cal-heatmap or shadcn-calendar-heatmap libraries work well in Next.js |
| Per-date risk detail panel | Clicking a date must show something — blank click = broken | LOW | Slide-out or modal: risk score, region, planetary highlights for that date |
| Geographic region indicator per prediction | "High risk" without location is not useful | MEDIUM | Country/region label + approximate lat/long grid cell; full interactive map is differentiator, text label is table stakes |
| Model accuracy summary ("how well does this work?") | Any ML prediction app must disclose model performance to be credible | LOW | Headline metrics: accuracy, precision, recall on 2000–2026 holdout. A single "Model Performance" card is sufficient for MVP |
| Methodology / about page | Earthquake prediction is scientifically contested — transparency is table stakes for trust | LOW | Explain the astrological feature engineering approach, USGS data source, train/test split, and prominent disclaimer that this is an experimental research tool |
| Prominent scientific disclaimer | USGS explicitly states earthquakes cannot be reliably predicted. Omitting this is a credibility failure | LOW | Must appear on landing page and calendar. Legal/credibility necessity |
| Mobile-responsive layout | >50% of web traffic is mobile; a calendar that breaks on phone = broken product | MEDIUM | Tailwind CSS + responsive grid. Cal views need special handling for small screens |
| Fast page load (static-first) | Predictions are pre-computed — a slow load implies live inference and breaks trust | LOW | Next.js static generation + JSON served at build time. Already in architecture plan |
| Prediction data freshness indicator | Users need to know when predictions were last generated | LOW | "Predictions generated: [date]" footer label. Single timestamp from JSON manifest |

### Differentiators (Competitive Advantage)

Features that set this product apart from generic seismic hazard apps or basic ML showcases.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interactive world map with risk overlay | Visual geographic intuition — "where, not just when" | HIGH | Leaflet + Mapbox tiles; choropleth or point markers per predicted region. Significant effort but transforms the product from a calendar into a geospatial tool |
| Planetary position annotations on calendar | Explains WHY a date is flagged — unique to this product's astrological angle | MEDIUM | Show planetary aspect summaries (e.g., "Mars-Saturn opposition") for high-risk dates; draws from the same astrological feature data used in training |
| Model evaluation dashboard (full) | Credibility for data science audience — shows the ML work is rigorous | MEDIUM | Confusion matrix, ROC curve, precision-recall curve, per-year performance on 2000–2026 holdout. Links to STACK.md: use recharts or Chart.js in Next.js |
| Comparison: predicted vs. actual (post-event) | As 2026 progresses, the app can show which predictions came true — living validation | HIGH | Requires a data refresh pipeline or manual update workflow. Powerful for credibility but significant ongoing effort |
| Historical pattern explorer (1900–2000) | Show which planetary configurations correlated with major earthquakes — educational | HIGH | Data-heavy; requires server-side data or large client JSON. Defer to v2 |
| Confidence interval per prediction | Shows model uncertainty, not just binary risk | MEDIUM | Use prediction probability output (LogReg already outputs probability). Display as "Low / Moderate / High" tier or percentage |
| CSV / JSON export of predictions | Data scientists and researchers want raw data | LOW | Single static file download link. Trivial to implement since predictions are pre-computed JSON anyway |
| Astrological feature importance chart | Shows which planetary features drive predictions — bridges astrology and ML for skeptics | MEDIUM | Feature importance from trained model (LogReg coefficients or permutation importance). Bar chart in the evaluation section |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing but introduce risk, scope creep, or credibility problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time / live earthquake alerts | Users want to feel "warned" | Requires always-on backend, WebSocket infrastructure, and implies prediction capability we don't claim — contradicts the pre-computed static architecture | Show historical M5.5+ events from USGS as a read-only timeline; do not frame as alerts |
| Magnitude prediction display | "Will it be a 7.0 or a 6.0?" feels useful | The model is binary (risk yes/no). Displaying magnitude implies precision the model was not trained for and cannot support | Show only the risk tier (Low/Moderate/High) from prediction probability |
| User location tracking / personalized risk | "Tell me if MY city is at risk" | Adds privacy surface, requires geolocation permission flow, complicates static architecture, and overcomplicates MVP | Let users manually explore geographic regions on the map or filter the calendar by region |
| Push notifications / email alerts | Users may want to subscribe to high-risk date reminders | Full notification infrastructure (backend, auth, email/push provider) is a large separate system; out of scope for static Vercel deployment | Provide iCal export of high-risk dates so users can add to their own calendar app |
| Magnitude 4.0+ data | "More data means better predictions" | M4.0+ doubles or triples the event count, creates severe class imbalance problems, and the existing model was tuned on M5.5+. Changing threshold invalidates trained model | Keep M5.5+ threshold consistent with existing codebase; document the threshold choice |
| Chat / AI interpretation of predictions | Natural language explanation of astrological factors | GPT/LLM integration adds API cost, latency, and a live backend dependency. Incompatible with static Vercel deployment | Pre-generate static text summaries per high-risk date from templated planetary aspect descriptions |
| User accounts / saved favorites | Personalization feels natural | Auth system, database, and session management are entirely out of scope for a research tool on Vercel static hosting | Stateless bookmarking via URL params (e.g., ?date=2026-07-15) for shareable links |
| Social sharing / comments | Community engagement | Adds moderation burden and backend dependency. The product is a research showcase, not a social platform | Provide shareable URL per date; let users copy and share naturally |

---

## Feature Dependencies

```
[Predictions JSON (Python ML output)]
    └──required by──> [Calendar heatmap view]
                          └──required by──> [Per-date detail panel]
                          └──required by──> [Planetary annotations on calendar]

[Model evaluation metrics (Python output)]
    └──required by──> [Model accuracy summary card]
                          └──enhances──> [Full model evaluation dashboard]

[Geographic region labels in predictions JSON]
    └──required by──> [Region indicator per prediction]
                          └──required by──> [Interactive world map overlay]

[Prediction probability scores in JSON]
    └──required by──> [Confidence interval / risk tier display]
    └──required by──> [CSV / JSON export]

[Astrological feature data (planetary positions)]
    └──required by──> [Feature engineering (Python)]
                          └──required by──> [Planetary annotations on calendar]
                          └──required by──> [Astrological feature importance chart]

[Historical predictions + 2026 actual events]
    └──required by──> [Predicted vs. actual comparison view]  ← deferred to v1.x
```

### Dependency Notes

- **Calendar heatmap requires Predictions JSON:** The entire web UI is downstream of the Python ML pipeline. The web phase cannot begin without a predictions JSON file, even a stub version.
- **Per-date detail panel requires calendar:** The detail panel has no entry point without the calendar. Build them together.
- **Interactive map requires geographic region labels:** The map is useless if predictions JSON only contains dates without region identifiers. The ML pipeline must output country or lat/long grid cell.
- **Predicted vs. actual comparison requires time:** This feature can only be populated as 2026 progresses. Architecture should allow for prediction JSON to be augmented with actual events, but the feature is deferred.
- **Planetary annotations require astrological feature data in the JSON:** If the predictions JSON only contains risk scores, this feature cannot be built client-side. The Python pipeline must include the key planetary aspects for each high-risk date in the output.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the research and make the app credible.

- [ ] Calendar heatmap view (full year 2026, monthly grid, color by risk tier) — core promise of the product
- [ ] Per-date detail panel (risk score, region label, top planetary aspects) — makes calendar actionable
- [ ] Geographic region text label per prediction — "where" is half the value
- [ ] Model accuracy summary card (accuracy, precision, recall, F1 on holdout) — credibility for any ML audience
- [ ] Methodology / About page with scientific disclaimer — credibility and legal necessity
- [ ] Static predictions JSON served at build time — architecture foundation
- [ ] Mobile-responsive layout — non-negotiable for public web

### Add After Validation (v1.x)

Features to add once core is working and the model is validated.

- [ ] Interactive world map with risk overlay — add when geography proves valuable to users; requires Leaflet integration
- [ ] Confidence interval / risk tier (Low/Moderate/High) labels — add when probability threshold tuning is done
- [ ] CSV / JSON prediction export link — low effort, high value for data science audience
- [ ] Predicted vs. actual comparison section — enable once March–June 2026 events can be compared
- [ ] Planetary position annotations on calendar — enable after confirming astrological feature data is in the output JSON

### Future Consideration (v2+)

Features to defer until the concept has proven itself.

- [ ] Full model evaluation dashboard (ROC curve, confusion matrix, per-year breakdown) — high complexity; add if the project grows a technical audience
- [ ] Historical pattern explorer (1900–2000 training data) — substantial data and UI work
- [ ] iCal export of high-risk dates — nice-to-have convenience feature
- [ ] Astrological feature importance chart — valuable for research audience, requires model coefficient exposure

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Calendar heatmap view | HIGH | MEDIUM | P1 |
| Per-date detail panel | HIGH | LOW | P1 |
| Geographic region label | HIGH | LOW | P1 |
| Scientific disclaimer + About page | HIGH | LOW | P1 |
| Model accuracy summary card | MEDIUM | LOW | P1 |
| Mobile-responsive layout | HIGH | MEDIUM | P1 |
| Interactive world map | HIGH | HIGH | P2 |
| Confidence tier display | MEDIUM | LOW | P2 |
| CSV / JSON export | MEDIUM | LOW | P2 |
| Predicted vs. actual comparison | HIGH | MEDIUM | P2 |
| Planetary annotations on calendar | MEDIUM | MEDIUM | P2 |
| Full model evaluation dashboard | MEDIUM | HIGH | P3 |
| Historical pattern explorer | LOW | HIGH | P3 |
| iCal export | LOW | LOW | P3 |
| Astrological feature importance chart | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | USGS Earthquake Map | Temblor / ShakeMap | Our Approach |
|---------|---------------------|-------------------|--------------|
| Map visualization | Real-time GeoJSON map, depth/mag circles | Seismic hazard choropleth | Static predicted-risk overlay on world map (v1.x) |
| Temporal view | List/timeline of past events | Annual probability estimates | Calendar heatmap of future predicted risk dates |
| Model explanation | Science-backed, no ML visible | Statistical hazard model, some documentation | Full ML metrics card + methodology page |
| Astrological features | None | None | Core differentiator — planetary feature engineering |
| Magnitude prediction | Shows actual magnitude (post-event) | Probability of shaking level | Deliberately excluded — binary risk only |
| Mobile support | Responsive map | Responsive | Responsive Next.js with Tailwind |
| Prediction export | GeoJSON feed / API | Not applicable | Static JSON download |

---

## Sources

- [USGS Earthquake Hazards Software](https://www.usgs.gov/programs/earthquake-hazards/software) — benchmark for features in earthquake data visualization
- [USGS: Can you predict earthquakes?](https://www.usgs.gov/faqs/can-you-predict-earthquakes) — authoritative source on earthquake prediction limitations; informs disclaimer requirement
- [USGS ShakeMap](https://earthquake.usgs.gov/data/shakemap/) — interactive map features and layer patterns (Leaflet-based)
- [Cal-Heatmap library](https://cal-heatmap.com/v2/) — calendar heatmap component patterns
- [shadcn-calendar-heatmap](https://github.com/gurbaaz27/shadcn-calendar-heatmap) — React/Tailwind-compatible calendar heatmap for Next.js
- [Accio Analytics: Customizable Predictive Analytics Dashboards](https://accioanalytics.io/insights/ultimate-guide-to-customizable-predictive-analytics-dashboards/) — ML dashboard feature standards
- [Evidently AI: Accuracy, Precision, Recall](https://www.evidentlyai.com/classification-metrics/accuracy-precision-recall) — standard metrics to display for binary classification
- [Leaflet.js](https://leafletjs.com/) — standard open-source mapping library (2.0 alpha released August 2025)
- [GlobalQuake live earthquake detection](https://globalquake.net/) — real-time earthquake visualization reference (what NOT to build for our static use case)
- [HKUST Library: Evaluating Earthquake Prediction Credibility](https://library.hkust.edu.hk/blog/2025/07/04/evaluate-earthquake-prediction/) — validates need for transparency and disclaimers
- [Aditya-167 Realtime-Earthquake-Forecasting GitHub](https://github.com/aditya-167/Realtime-Earthquake-forecasting) — open-source earthquake forecasting app pattern reference
- [next-themes: Dark mode for Next.js](https://github.com/pacocoursey/next-themes) — dark mode implementation

---

*Feature research for: Earthquake Astrology Prediction 2026 — ML prediction system with calendar UI*
*Researched: 2026-03-14*
