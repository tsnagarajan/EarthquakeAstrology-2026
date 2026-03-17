---
phase: 4
slug: web-app-and-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `npm run build` (Next.js 16 TypeScript build — primary gate) |
| **Config file** | `web/package.json` (Wave 0 creates via `create-next-app`) |
| **Quick run command** | `cd web && npm run build` |
| **Full suite command** | `cd web && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd web && npm run build`
- **After every plan wave:** Run `cd web && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green + Vercel deployment successful
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | WEB-01,WEB-05 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-01-02 | 01 | 0 | DEPLOY-01 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-02-01 | 02 | 1 | WEB-01 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-02-02 | 02 | 1 | WEB-02 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-03-01 | 03 | 1 | WEB-03 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-04-01 | 04 | 1 | WEB-04 | build smoke | `cd web && npm run build` | ❌ Wave 0 | ⬜ pending |
| 4-05-01 | 05 | 2 | DEPLOY-01,DEPLOY-02 | manual | N/A — Vercel deploy | Manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/package.json` — scaffold Next.js 16 app with `npx create-next-app@latest . --typescript --tailwind --eslint --app --no-src-dir` from within `web/`
- [ ] `web/next.config.ts` — created by `create-next-app`; verify no webpack config injected
- [ ] `web/app/layout.tsx` — created by `create-next-app`; will be replaced with disclaimer banner in Wave 1
- [ ] `web/public/data/eval_report.json` — copy from `data/models/eval_report.json` before any build attempts

*Wave 0 must complete before any `npm run build` validation is possible.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Detail panel slide-in on high-risk date click | WEB-02 | Requires browser interaction | Open deployed app, click an orange cell, verify panel slides in from right with risk score, regions, and planetary aspects |
| Panel closes on outside click | WEB-02 | Requires browser interaction | With panel open, click outside panel area; verify panel closes |
| Week highlight on normal date click | WEB-02 | Requires browser interaction | Click a white cell, verify high-risk dates in same week get visual highlight (ring/outline) |
| Vercel deployment from `web/` | DEPLOY-01 | Requires Vercel dashboard action | Set Root Directory to `web` in Vercel project settings; push to main; verify build log shows Next.js detection |
| All assets within Vercel size limits | DEPLOY-02 | Requires Vercel build output | Check Vercel deployment log for bundle size warnings; verify predictions.json served from CDN not bundled |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
