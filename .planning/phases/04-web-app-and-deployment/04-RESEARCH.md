# Phase 4: Web App and Deployment - Research

**Researched:** 2026-03-17
**Domain:** Next.js 16 App Router, Tailwind CSS 4, Vercel deployment from subdirectory
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Calendar Layout**
- All 10 months (March–December 2026) displayed on a single scrollable page — no navigation controls needed
- Standard calendar grid: each date is a cell with the date number in the corner; no text inside cells
- Cell background color = risk tier (binary: normal or high-risk)
- Plain white/neutral cells for dates with no predictions above threshold

**Risk Tiers**
- 2 tiers only (binary): Normal (white/neutral) vs High-risk (colored)
- A date is high-risk if `predictions.json` has any entry for that date above the stored threshold
- No further subdivision into medium/low/high — a date either has a prediction or it doesn't

**Date Detail Panel**
- Slide-in side panel from the right when clicking a high-risk date
- Calendar stays visible on the left while panel is open
- Panel contents:
  - Risk score (numeric, e.g., 0.73 — or a visual bar alongside the number)
  - All predicted region(s) for that date, listed and sorted by `risk_score` descending (show all, not capped)
  - Each region entry: country name + lat/lon grid cell (e.g., "Indonesia — lat -5, lon 110")
  - Top planetary aspects (the `top_planetary_aspects` array from predictions.json — typically 3 strings)
- Panel closes when user clicks outside it or clicks another date

**Click Behavior on Normal Dates**
- Clicking a white/neutral (no-prediction) date highlights all high-risk dates in that same week — gives the user risk context for the surrounding week without a detail panel
- High-risk dates in that week get a visual highlight (e.g., ring or outline) that clears on the next interaction

**Disclaimer (WEB-04)**
- A prominent scientific disclaimer must be visible on the main page without any user interaction
- Must not be dismissable or hidden behind any toggle

**Methodology Page (WEB-03)**
- Reachable from the calendar page (e.g., nav link or footer link)
- Must display model evaluation metrics from `data/models/eval_report.json`:
  - Model used: XGBClassifier
  - F1 score: 0.002774
  - MCC: 0.001363
  - Confusion matrix (TP, FP, FN, TN) for 2010–2026 holdout period
  - Eval split date: 2010-01-01

**Build-Time Data Loading (WEB-05)**
- Next.js Server Component reads `predictions.json` at build time — no `fetch()` or client-side data loading
- `predictions.json` stays in `web/public/data/` and is served as a static asset — NOT imported into the serverless function bundle

### Claude's Discretion
- Color choice for high-risk cells (e.g., red, amber, orange)
- Typography, spacing, and exact styling
- Mobile/responsive layout
- Week highlight visual treatment (ring, outline, background)
- Methodology page explanation depth and prose
- Disclaimer exact wording beyond the required content (must state: experimental model, earthquakes cannot be reliably predicted)
- Next.js version and specific package choices (e.g., Tailwind vs CSS modules)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WEB-01 | Calendar view displays 2026 months (March–December) with dates color-coded by earthquake risk level | Next.js Server Component reads predictions.json at build time; Tailwind CSS grid for calendar layout |
| WEB-02 | Clicking a high-risk date shows a detail panel: risk score, predicted region(s), and top contributing planetary aspects | Client Component with useState for panel open/close state; slide-in via Tailwind translate + transition |
| WEB-03 | Methodology page explains the astrological ML approach and displays model evaluation metrics (F1, MCC, confusion matrix) from the 2000–2026 test period | Server Component reads eval_report.json at build time from `public/data/`; static route `/methodology` |
| WEB-04 | A prominent scientific disclaimer is displayed stating this is an experimental astrological model and earthquakes cannot be reliably predicted | Static banner in root layout or above calendar — no JavaScript required |
| WEB-05 | Next.js app reads predictions.json at build time via Server Component (no client-side fetch) | `fs.readFileSync(path.join(process.cwd(), 'public/data/predictions.json'))` in async Server Component |
| DEPLOY-01 | Next.js app deploys to Vercel from the `web/` directory with predictions.json committed in `web/public/data/` | Vercel Root Directory = `web` set in project settings (no vercel.json needed for basic case) |
| DEPLOY-02 | Vercel build succeeds with all static assets under size limits | predictions.json is 218 KB — well within Vercel Hobby 100 MB source limit; file stays in public/ not bundled |
</phase_requirements>

---

## Summary

Phase 4 builds a Next.js 16 App Router application in the `web/` directory. The app reads `predictions.json` (218 KB, 901 entries, currently only March 8 dates — see Data Reality below) at build time via a Server Component using `fs.readFileSync`, renders a 10-month scrollable calendar with binary risk coloring, and deploys to Vercel by setting Root Directory to `web` in the Vercel project settings.

The interaction layer (detail panel, week highlight) is a Client Component receiving pre-processed data as props from the parent Server Component. The methodology page is a separate static route that reads `eval_report.json` at build time and displays the honest, very-low metric scores (F1: 0.002774, MCC: 0.001363). The disclaimer is a non-dismissable static banner in the root layout.

The current Next.js latest is **16.1.7** (verified via npm registry, March 2026). Tailwind CSS latest is **4.2.1**. Both are significant version jumps from what training data assumed (15.x and 3.x respectively). The research below reflects the actual current state.

**Primary recommendation:** Use `npx create-next-app@latest` with `--typescript --tailwind --app` flags, targeting Next.js 16, set Vercel Root Directory to `web`, and use `fs.readFileSync` in a Server Component to embed predictions at build time.

---

## Data Reality Check

**Critical observation:** `web/public/data/predictions.json` currently contains 901 entries all dated `2026-03-08`. The date range is a single day, not March–December 2026.

This is a Phase 3 artifact issue — the prediction export only included one date's worth of entries. The web implementation must:
1. Handle whatever date range exists in the file without hardcoding
2. Gracefully render months with no prediction entries as all-white calendars
3. Not assume any minimum number of unique dates

**File size:** 218 KB — comfortably within all Vercel limits.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.1.7 | Framework with App Router, Server Components, static export | Current latest; Vercel-native |
| react | 19.2.4 | UI rendering | Peer dep of Next 16 |
| react-dom | 19.2.4 | DOM rendering | Peer dep of Next 16 |
| typescript | 5.9.3 | Type safety | Required by Next 16 (min 5.1.0) |
| tailwindcss | 4.2.1 | Utility-first CSS | Most common Next.js styling choice; supported by create-next-app |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/react | 19.2.14 | TypeScript types for React | Required with TypeScript |
| @types/react-dom | 19.2.14 | TypeScript types for React DOM | Required with TypeScript |
| @types/node | latest | TypeScript types for Node.js fs/path | Required for `fs` and `path` in Server Components |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tailwind CSS | CSS Modules | CSS Modules need more manual class naming; Tailwind faster for grid/layout |
| fs.readFileSync | JSON import | JSON import bundles into serverless function — violates WEB-05 requirement |
| Tailwind CSS | shadcn/ui | shadcn adds useful components but requires Radix UI overhead; not needed for this simple UI |

**Installation (from `web/` directory):**
```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --no-src-dir
```

**Version verification (confirmed 2026-03-17):**
```
npm view next version      → 16.1.7
npm view tailwindcss version → 4.2.1
npm view typescript version → 5.9.3
npm view react version     → 19.2.4
```

---

## Architecture Patterns

### Recommended Project Structure
```
web/
├── app/
│   ├── layout.tsx           # Root layout: disclaimer banner + nav
│   ├── page.tsx             # Calendar page (Server Component)
│   ├── methodology/
│   │   └── page.tsx         # Methodology page (Server Component)
│   └── globals.css          # Tailwind base styles
├── components/
│   ├── CalendarGrid.tsx      # Server Component: renders 10 months
│   ├── MonthGrid.tsx         # Server Component: single month grid
│   ├── CalendarInteractive.tsx  # Client Component: panel + week highlight
│   ├── DetailPanel.tsx       # Client Component: slide-in panel
│   └── Disclaimer.tsx        # Static banner (no client state needed)
├── lib/
│   └── predictions.ts        # Type definitions + data loading function
├── public/
│   └── data/
│       ├── predictions.json  # 901 entries (already committed)
│       └── eval_report.json  # Model metrics (copy from data/models/)
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Pattern 1: Server Component Data Loading (WEB-05)

**What:** Read predictions.json synchronously in an async Server Component using Node.js `fs` module. Data is embedded in the HTML at build time — no client fetch.

**When to use:** All data loading from local files. This is the ONLY correct approach for WEB-05.

**Example:**
```typescript
// Source: https://vercel.com/kb/guide/loading-static-file-nextjs-api-route
// app/page.tsx (Server Component — no 'use client')
import { promises as fs } from 'fs'
import path from 'path'

export interface Prediction {
  date: string
  country: string
  lat: number
  lon: number
  risk_score: number
  top_planetary_aspects: string[]
}

export default async function CalendarPage() {
  const filePath = path.join(process.cwd(), 'public/data/predictions.json')
  const raw = await fs.readFile(filePath, 'utf8')
  const predictions: Prediction[] = JSON.parse(raw)

  // Group by date for calendar rendering
  const byDate = new Map<string, Prediction[]>()
  for (const p of predictions) {
    const existing = byDate.get(p.date) ?? []
    existing.push(p)
    byDate.set(p.date, existing)
  }

  return <CalendarInteractive predictionsByDate={Object.fromEntries(byDate)} />
}
```

**Key constraint:** `public/data/predictions.json` is served as a static CDN asset — it is NOT imported/bundled. Reading it with `fs` at build time bakes the data into the HTML. The file also remains accessible at `https://your-app.vercel.app/data/predictions.json` for direct access.

### Pattern 2: Server + Client Component Split (WEB-01, WEB-02)

**What:** Server Component does the data loading and date/month computation. A single `CalendarInteractive` Client Component receives all data as props and manages panel open/close state + week highlight state. This is the standard Next.js 16 App Router pattern.

**When to use:** Any page with both build-time data and interactive state.

```typescript
// Source: https://nextjs.org/docs/app/getting-started/server-and-client-components
// components/CalendarInteractive.tsx
'use client'

import { useState } from 'react'
import type { Prediction } from '@/lib/predictions'

interface Props {
  predictionsByDate: Record<string, Prediction[]>
  months: Array<{ year: number; month: number; label: string }>
}

export function CalendarInteractive({ predictionsByDate, months }: Props) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [highlightedWeek, setHighlightedWeek] = useState<string[] | null>(null)

  function handleDateClick(date: string, isHighRisk: boolean) {
    if (isHighRisk) {
      setSelectedDate(date)
      setHighlightedWeek(null)
    } else {
      // Highlight all high-risk dates in the same week
      setSelectedDate(null)
      setHighlightedWeek(getWeekDates(date).filter(d => predictionsByDate[d]))
    }
  }

  // ... render calendar + panel
}
```

### Pattern 3: Slide-In Detail Panel (WEB-02)

**What:** Right-side panel using Tailwind `translate-x` transition. Panel opens when a high-risk date is clicked; closes on outside click or new date selection. Calendar layout uses CSS grid with `lg:pr-[400px]` when panel is open to prevent content shift.

```typescript
// Source: Tailwind CSS docs + standard React pattern
// components/DetailPanel.tsx
'use client'

interface Props {
  predictions: Prediction[]
  date: string
  onClose: () => void
}

export function DetailPanel({ predictions, date, onClose }: Props) {
  // Sort regions by risk_score descending
  const sorted = [...predictions].sort((a, b) => b.risk_score - a.risk_score)
  const maxRiskScore = sorted[0]?.risk_score ?? 0

  return (
    // Fixed right panel with slide-in animation
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl
                    transform transition-transform duration-300 ease-in-out
                    translate-x-0 overflow-y-auto z-50 p-6">
      {/* Overlay for outside click */}
      <div className="fixed inset-0 -z-10" onClick={onClose} />
      <h2 className="text-lg font-semibold">{date}</h2>
      <div className="mt-2">
        <span className="text-3xl font-bold">{maxRiskScore.toFixed(2)}</span>
        <div className="h-2 bg-orange-200 rounded mt-1">
          <div className="h-2 bg-orange-500 rounded"
               style={{ width: `${maxRiskScore * 100}%` }} />
        </div>
      </div>
      {sorted.map((p, i) => (
        <div key={i} className="mt-3 text-sm">
          <span className="font-medium">{p.country}</span>
          <span className="text-gray-500"> — lat {p.lat}, lon {p.lon}</span>
        </div>
      ))}
      {sorted[0]?.top_planetary_aspects && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase">
            Top Planetary Aspects
          </h3>
          <ul className="mt-1 space-y-1 text-sm">
            {sorted[0].top_planetary_aspects.map((aspect, i) => (
              <li key={i}>{aspect.replace(/_/g, ' ')}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

### Pattern 4: Vercel Subdirectory Deployment (DEPLOY-01)

**What:** Vercel project settings `Root Directory = web`. No vercel.json needed for the simple case — Vercel auto-detects Next.js from `web/package.json`.

**Configuration options (choose one):**

Option A — Vercel Dashboard (recommended for first deploy):
1. Import GitHub repository
2. In "Configure Project", set Root Directory to `web`
3. Vercel auto-fills Build Command: `next build`, Output Dir: `.next`

Option B — `vercel.json` in **repo root** (for CLI or programmatic control):
```json
{
  "buildCommand": "cd web && npm install && npm run build",
  "outputDirectory": "web/.next",
  "framework": "nextjs"
}
```

Option C — `web/vercel.json` (if root dir is set to `web` in dashboard):
No file needed — Vercel detects framework automatically.

**Critical:** `predictions.json` in `web/public/data/` is committed to Git and deployed as a static asset. Vercel serves it from the CDN. It does not count against serverless function bundle size.

### Pattern 5: Build-Time Eval Report Loading (WEB-03)

**What:** `data/models/eval_report.json` lives outside `web/`. Two options: copy it to `web/public/data/eval_report.json` as part of setup (simple), or import it directly using a relative path from the Server Component (fragile on Vercel if working directory is `web/`).

**Recommendation:** Copy `eval_report.json` to `web/public/data/eval_report.json` during project setup. This keeps all web data in `web/public/data/` and is served as a static asset alongside `predictions.json`. Read it with `fs` the same way.

### Anti-Patterns to Avoid

- **Importing predictions.json as a module:** `import data from '../public/data/predictions.json'` — this bundles the JSON into the serverless function, violating WEB-05 and potentially exceeding the 250 MB unzipped function limit.
- **Client-side fetch of predictions.json:** Using `useEffect` + `fetch('/data/predictions.json')` — violates WEB-05, causes loading flash, and makes the page empty on initial server render.
- **Using `fs` in Client Components:** `'use client'` components run in the browser and cannot use Node.js modules. `fs` calls must be in Server Components only.
- **Custom webpack config with Next.js 16:** Next.js 16 uses Turbopack by default. Adding a custom `webpack` config will cause `next build` to fail. Use `--webpack` flag only if absolutely needed.
- **Skipping `path.join(process.cwd(), ...)`:** Using relative paths like `'./public/data/...'` fails in production on Vercel because the working directory is not guaranteed to be the project root.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS grid calendar layout | Custom grid math | Tailwind `grid grid-cols-7` | Calendar is a 7-column grid; Tailwind handles responsive columns trivially |
| Slide-in panel animation | Custom CSS animations | Tailwind `transition-transform translate-x` | Tailwind has first-class transition utilities; animation timing built in |
| Outside-click detection | Custom event listeners | React `onClick` on overlay div + `stopPropagation` | Simple, idiomatic, no extra library needed for a single panel |
| Week date calculation | Complex date math | JS `Date` object + ISO week calculation | Week boundaries are `getDay()` arithmetic — 7 lines, no library needed |
| Month generation (Mar–Dec 2026) | Config-driven loop | Hardcoded array of 10 month objects | Only 10 months, fixed range — hardcoded is clearer and zero overhead |
| Font loading | `@font-face` CSS | `next/font/google` | Zero layout shift, build-time download, no Google request at runtime |

**Key insight:** This is a static data display app. Almost every "hard" problem (calendar layout, animations, data loading) has a trivial idiomatic solution in Next.js 16 + Tailwind 4.

---

## Common Pitfalls

### Pitfall 1: Next.js 16 Breaking Changes from 15

**What goes wrong:** Using `create-next-app` produces a Next.js 16 app. Patterns from tutorials assuming Next.js 15 (async APIs, Turbopack configuration) may differ.

**Why it happens:** Next.js 16 is a new major version released ~December 2025. Key changes relevant to this app:
- Turbopack is now **on by default** for both `next dev` and `next build` — no `--turbopack` flag needed
- `turbopack` config moves from `experimental.turbopack` to top-level `turbopack` in `next.config.ts`
- `next lint` command removed — use ESLint CLI directly
- `serverRuntimeConfig` / `publicRuntimeConfig` removed — use env vars or Server Components
- Node.js minimum version is 20.9.0 (LTS)

**How to avoid:** Start with `create-next-app@latest` to get a correct baseline. Do not copy-paste Next.js 15 config patterns.

**Warning signs:** Build fails immediately with "webpack config found" error — means a plugin injected a webpack config; use `--webpack` flag or remove the plugin.

### Pitfall 2: `fs` Module in Client Components

**What goes wrong:** Moving calendar cell or panel code to `'use client'` and trying to read `predictions.json` with `fs` — results in `Module not found: Can't resolve 'fs'` build error.

**Why it happens:** Client Components run in the browser. Node.js built-in modules are not available.

**How to avoid:** All `fs` reads must be in Server Components (no `'use client'` directive). Pass data down to Client Components as props. The Server Component tree is: `page.tsx` (Server) → passes props → `CalendarInteractive.tsx` (Client).

**Warning signs:** `Can't resolve 'fs'` or `Can't resolve 'path'` during build.

### Pitfall 3: Vercel Root Directory Not Set

**What goes wrong:** Pushing to Vercel deploys from repo root, not `web/`. Vercel cannot find `package.json` or `next.config.ts` and the build fails.

**Why it happens:** The repo root contains Python files, not a Next.js project. Vercel must be told the subdirectory.

**How to avoid:** Set Root Directory to `web` in Vercel project settings before first deploy. This is a one-time dashboard setting — not stored in code.

**Warning signs:** Vercel build log shows "No framework detected" or tries to install Python dependencies.

### Pitfall 4: Tailwind CSS 4 Configuration Changes

**What goes wrong:** Tailwind CSS 4 has a significantly different configuration approach vs Tailwind 3. If tutorials or snippets use `tailwind.config.js` with `content` arrays, they may not work with Tailwind 4's new CSS-first configuration.

**Why it happens:** Tailwind 4.x moved to a CSS-based config (`@import "tailwindcss"` in globals.css) rather than a JS config file. `create-next-app` with `--tailwind` flag handles this correctly.

**How to avoid:** Use `create-next-app@latest --tailwind` and do not manually copy Tailwind 3 config files. Let `create-next-app` scaffold the correct Tailwind 4 setup.

**Warning signs:** Tailwind classes not applying; `tailwind.config.js` not recognized.

### Pitfall 5: predictions.json Data Gaps

**What goes wrong:** The calendar attempts to render high-risk dates from March through December 2026, but `predictions.json` currently only has entries for 2026-03-08. All other calendar dates will be normal (white) cells.

**Why it happens:** Phase 3 prediction export appears to have only included one date's data. This may be correct (threshold filter removed all others) or may be a Phase 3 bug.

**How to avoid:** The web implementation must handle sparse data gracefully — iterate over actual dates in the JSON, never assume coverage. A date not in the JSON is normal/white. Do not block Phase 4 on this — the app works correctly whether there are 1 or 280 high-risk dates.

**Warning signs:** Any hardcoded assumptions about which months have predictions.

### Pitfall 6: eval_report.json Path Resolution

**What goes wrong:** `data/models/eval_report.json` is outside the `web/` directory. `process.cwd()` on Vercel resolves to `web/` (the Root Directory). Reading `path.join(process.cwd(), '../../data/models/eval_report.json')` will work locally but fail on Vercel.

**Why it happens:** Vercel's build runs inside the Root Directory. Files outside `web/` are not accessible.

**How to avoid:** Copy `eval_report.json` to `web/public/data/eval_report.json` as part of the web project setup (Wave 0 or Wave 1 task). Read it from `path.join(process.cwd(), 'public/data/eval_report.json')`.

**Warning signs:** Methodology page returns 404 or throws ENOENT on Vercel but works locally.

---

## Code Examples

Verified patterns from official sources:

### Reading JSON at Build Time (Server Component)
```typescript
// Source: https://vercel.com/kb/guide/loading-static-file-nextjs-api-route
// app/page.tsx — Server Component (no 'use client')
import { promises as fs } from 'fs'
import path from 'path'

export default async function Page() {
  const filePath = path.join(process.cwd(), 'public/data/predictions.json')
  const raw = await fs.readFile(filePath, 'utf8')
  const predictions = JSON.parse(raw)
  return <div>{/* render with data */}</div>
}
```

### Next.js 16 `next.config.ts` Baseline
```typescript
// Source: https://nextjs.org/docs/app/guides/upgrading/version-16
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Turbopack is on by default in Next.js 16 — no configuration needed
  // turbopack config is now top-level (not experimental.turbopack)
}

export default nextConfig
```

### Root Layout with Disclaimer Banner (WEB-04)
```typescript
// app/layout.tsx — Server Component
import Link from 'next/link'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap' })

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        {/* Non-dismissable disclaimer — always visible, no JS required */}
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 text-sm text-amber-900">
          <strong>Disclaimer:</strong> This is an experimental astrological model.
          Earthquakes cannot be reliably predicted. This tool is for research
          purposes only and should not be used for safety decisions.
        </div>
        <nav className="flex items-center justify-between px-6 py-4 border-b">
          <h1 className="font-semibold text-lg">Earthquake Astrology 2026</h1>
          <Link href="/methodology" className="text-sm text-blue-600 hover:underline">
            Methodology
          </Link>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  )
}
```

### Month Grid (7-column CSS Grid)
```typescript
// Source: Tailwind CSS docs grid utilities
// components/MonthGrid.tsx — Server Component
interface DateCell {
  date: string       // ISO string "2026-03-08"
  dayNum: number     // 1-31
  isHighRisk: boolean
  isEmpty: boolean   // padding cell before month starts
}

interface Props {
  label: string       // "March 2026"
  cells: DateCell[]   // pre-computed, 28-31 + leading padding
}

export function MonthGrid({ label, cells }: Props) {
  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold text-gray-600 mb-2">{label}</h2>
      <div className="grid grid-cols-7 gap-1">
        {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
          <div key={d} className="text-xs text-center text-gray-400 py-1">{d}</div>
        ))}
        {cells.map((cell, i) => (
          <div key={i} className={`
            aspect-square rounded text-sm flex items-start justify-start p-1
            ${cell.isEmpty ? '' : cell.isHighRisk ? 'bg-orange-400 cursor-pointer' : 'bg-gray-50 cursor-pointer'}
          `}>
            {!cell.isEmpty && <span className="text-xs">{cell.dayNum}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Vercel Project Settings Reference
```
Project Settings → Root Directory → web
Build Command:    next build       (auto-detected)
Output Directory: .next            (auto-detected)
Node.js Version:  20.x             (required by Next.js 16 — min 20.9.0)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getStaticProps` (Pages Router) | `async` Server Component (App Router) | Next.js 13+ | Server Components are the new default; `getStaticProps` only exists in Pages Router |
| `next export` | `output: 'export'` in next.config | Next.js 14 | CLI flag removed; config-based static export |
| `experimental.turbopack: true` | Turbopack on by default | Next.js 16 | No configuration needed; just `next build` |
| `experimental.turbopack: {}` | `turbopack: {}` (top-level) | Next.js 16 | Config namespace promoted out of experimental |
| Tailwind CSS 3 `tailwind.config.js` | Tailwind CSS 4 CSS-first config | Tailwind v4 (2025) | `@import "tailwindcss"` in globals.css replaces JS config |
| `next lint` | ESLint CLI directly | Next.js 16 | `next lint` command removed; run `eslint` directly |
| `serverRuntimeConfig` | Server Component env access | Next.js 16 | Config option fully removed |

**Deprecated/outdated:**
- `next/legacy/image`: deprecated in Next.js 16, use `next/image`
- `images.domains`: deprecated, use `images.remotePatterns`
- `middleware.ts` convention: renamed to `proxy.ts` in Next.js 16 (not relevant to this app)

---

## Open Questions

1. **predictions.json date coverage gap**
   - What we know: File has 901 entries all for 2026-03-08; date range should be March–December 2026
   - What's unclear: Whether this is intentional (threshold eliminated all other dates) or a Phase 3 export bug
   - Recommendation: Implement the web app to handle sparse/single-date data correctly. Do not fix Phase 3 as part of Phase 4. The calendar will show 1 high-risk date and 299 white cells — functionally correct per the spec.

2. **Tailwind 4 utility compatibility**
   - What we know: Tailwind 4 is a major version with CSS-first configuration; `create-next-app --tailwind` handles setup
   - What's unclear: Some Tailwind 3 patterns (JIT variants, plugin API) changed in v4
   - Recommendation: Use only core Tailwind utilities (grid, flex, colors, spacing, transitions) — these are stable across v3/v4. Avoid plugins. `create-next-app` scaffolding is the safe baseline.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing Python test suite in `tests/`) |
| Web framework | None currently — no Jest/Vitest exists |
| Config file | `pyproject.toml` (Python only) |
| Python quick run | `uv run pytest tests/ -x -q` |
| Python full suite | `uv run pytest tests/ -v` |

**Important:** The existing test infrastructure is Python only. There is no JavaScript/TypeScript test framework installed. Phase 4 is a Next.js web app — it requires a separate web test approach.

For this phase, validation is build-focused rather than unit-test-focused:

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01 | Calendar grid renders 10 months with correct date cells | Build smoke | `cd web && npm run build` | ❌ Wave 0 |
| WEB-02 | Detail panel opens on high-risk date click, closes on outside click | Manual browser verification | N/A — requires browser | Manual |
| WEB-03 | Methodology page renders metrics from eval_report.json | Build smoke | `cd web && npm run build` | ❌ Wave 0 |
| WEB-04 | Disclaimer visible without user interaction | Build smoke + visual | `cd web && npm run build` | ❌ Wave 0 |
| WEB-05 | No client-side fetch; predictions embedded at build time | Build smoke | `cd web && npm run build` | ❌ Wave 0 |
| DEPLOY-01 | App deploys from `web/` directory | Manual — Vercel deploy | N/A | Manual |
| DEPLOY-02 | Build succeeds, assets within limits | Build + size check | `cd web && npm run build` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd web && npm run build` (Next.js 16 build validates TypeScript, imports, and SSG)
- **Per wave merge:** `cd web && npm run build` (same — build is the primary automated gate)
- **Phase gate:** Successful Vercel deployment before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `web/package.json` — does not exist; Wave 0 must scaffold Next.js app with `create-next-app`
- [ ] `web/next.config.ts` — does not exist; created by `create-next-app`
- [ ] `web/app/layout.tsx` — does not exist; created by `create-next-app`
- [ ] `web/public/data/eval_report.json` — copy from `data/models/eval_report.json`

---

## Sources

### Primary (HIGH confidence)
- `npm view next version` → `16.1.7` (verified live, 2026-03-17)
- `npm view tailwindcss version` → `4.2.1` (verified live, 2026-03-17)
- `npm view react version` → `19.2.4` (verified live, 2026-03-17)
- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16) — Breaking changes, Turbopack default, Node.js requirement
- [Next.js Static Exports Guide](https://nextjs.org/docs/app/guides/static-exports) — Server Component SSG behavior, `output: 'export'` config
- [Vercel Knowledge Base: Loading Static Files](https://vercel.com/kb/guide/loading-static-file-nextjs-api-route) — `fs.readFile` + `process.cwd()` pattern
- [Vercel Limits](https://vercel.com/docs/limits) — 100 MB source upload (Hobby), 1 GB (Pro), 250 MB serverless function limit
- [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs) — Subdirectory root directory configuration

### Secondary (MEDIUM confidence)
- [Vercel Community: Root Directory Configuration](https://community.vercel.com/t/help-needed-configuring-root-directory/7436) — Dashboard Root Directory setting confirmed for subdirectory projects
- [Next.js create-next-app CLI](https://nextjs.org/docs/app/api-reference/cli/create-next-app) — Verified `--typescript --tailwind --app` flags

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against npm registry live
- Architecture: HIGH — patterns confirmed against official Next.js and Vercel docs
- Pitfalls: HIGH — Next.js 16 breaking changes from official upgrade guide; `fs` pattern from Vercel KB
- Data reality: HIGH — confirmed by direct inspection of `predictions.json`

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (30 days — stable framework, not fast-moving)
