# PathOS Stage 7A — Frontend UX Reconstruction Plan

> Branch: `feature/stage7-post-demo-development`
> Stage 6 baseline tree hash (`frontend/src`): `026f9859f4e00c2530a0acbc95ff8ba57c281cbe6f654909c652f255add91be4`
> Baseline dir: `/Users/jiayihuang/Downloads/PathOS合并-integration-baseline/stage7a-frontend-ux-prechange`
> Backend tree hash unchanged. Preview Bundle unchanged. DB facts unchanged.
> Dev server: `localhost:3002` (backend BFF at `/api/pathos/preview`, 62 schools, region-metrics BLOCKED).

## 1. Scope of Stage 7A

Stage 7A fixes **frontend-only** UX defects surfaced by Stage 6 demo. It does NOT change backend tracked files, the Preview Bundle, the quarantine gate, the 904 verified data facts, the Stage 6 checkpoint, or any artifact outside `frontend/src` and the documentation files listed in §11.

## 2. Problem Matrix (priority order)

| # | Severity | Where | Symptom | Plan |
|---|---|---|---|---|
| A1 | High | `MapCanvas.tsx:357` | Hover tooltip shows `N/A` when metric missing | Show `数据补充中` with FIPS code + zh/en name |
| A2 | High | `MapShell.tsx:618` | `UniversityPoiLayer` is rendered **without** `onHover`, so per-POI tooltip is never wired | Add `onHover` handler in MapShell; render floating tooltip |
| B1 | Critical | `UniversityPoiLayer.tsx` | POI circles have no text label (uses nonexistent `title` prop, opacity 0) | Set real `abbr` property on each feature; render symbol layer; deterministic 1–3 char abbrev |
| B2 | High | `UniversityPoiLayer.tsx` | No distinct selected/hover/compare/saved states | Add feature-state `selected`, `hover`, `compare`; paint expressions |
| C1 | Critical | `UniversityCard.tsx` | Reads `annualCostRmb`, `safetyScore`, `recognitionScore`, `chineseCommunity` — none on legacy POI from new mapper (always null) → card renders "数据补充中" everywhere | Add new `UniversityProfile` panel reading real `costSummary` / `rankingSummary` / `qualitySummary`; missing → "未报告" (never 0/N/A) |
| C2 | High | `UniversityCard.tsx` | No undergrad count / acceptance rate / majors / warnings | Add those rows; pass detail through `useUniversityDetail` |
| D1 | Critical | `MapShell.tsx:655-665` | Selected card is centered modal with backdrop-blur, blocking map | Replace with **edge-docked popover** (right-edge on desktop, bottom-sheet on mobile). Map stays draggable, escape closes, click empty closes, switch directly |
| D2 | High | `MapShell.tsx` | Sidebar fixed at 360px; no mobile bottom-sheet; no resize handle | Add ResizablePanel primitive (left filter, right detail), mobile bottom-sheet with collapsed/half/expanded snaps, persisted to localStorage |
| E1 | Critical | `calculator/page.tsx:281-285` | "添加更多大学对比" placeholder is a static `<div>`, not clickable | Replace with **button + dropdown** that opens a search-and-pick dialog (keyboard, dedupe, max 3, empty state, mobile-friendly) |
| E2 | High | `calculator/page.tsx` | `<select>` is the only add mechanism | Move to dialog-based picker; show cost row even when blocked |
| F1 | Critical | `match/page.tsx` | Reads `university.annualCostRmb/numericRank/safetyScore/admissionRate/recognitionScore` — **none exist** on summary shape; only `rankingTier` exists, and region metrics are BLOCKED | Read from real `costSummary.minimumUsd * 7.2`, `rankingSummary.nationalRank`, `rankingSummary.rankingTier`. Re-derive percentages only over present dims (already partly done — finish wiring) |
| F2 | High | `assessment/page.tsx:72` | `selectedIds` initialised from `all.slice(0,5)` when `all` is empty (data loads async) → first render shows 0 schools | Use effect to populate once data ready, or initialize after `summariesState.state.status === "ready"` |
| F3 | High | `match/page.tsx` | Weights wired but effect is limited (blocked metrics → mostly missing dims) | Already re-normalised; add **observable test**: ensure rank changes affect order where data present |
| G1 | High | `match/portfolio/assessment/calculator` | Each page renders its own header (duplicate menu bars) | Remove per-page title bars; rely on global NavBar + a sub-nav strip with current page name |
| G2 | High | `ProductJourney` rendered twice on portfolio/match/assessment | Keep one inline compact strip at top of each module page |
| H1 | Critical | `globals.css` / `tailwind.config.ts` / `layout.tsx` | No dark mode; `color-scheme: light` only; no toggle; no CSS variables | Add `data-theme` attribute on `<html>`; CSS variable tokens; dark-mode Tailwind variant `class`; persist to localStorage; no-flash script |
| H2 | High | All components | Tailwind colors hard-coded (no semantic vars) | Move to semantic CSS vars (`--bg-page`, `--bg-panel`, `--text-ink`, `--border-line`); both themes |
| I1 | High | Various | No mobile bottom-sheet; no drag/resize touch support | Add touch handlers + snap points |
| I2 | Medium | Various | Missing ARIA labels, focus management, keyboard | Audit + add roles |
| I3 | Medium | Map | Map width/height not responsive at 1280/1440/1920/390 breakpoints | Add responsive layout (`flex-col` mobile, `flex-row` desktop, sidebar drawer) |
| J1 | Medium | (Audit) | `globals.css` line 5–7 declares `color-scheme: light` only — needs both | Switch to `light dark` |
| J2 | Medium | (Audit) | No 404 page or backend-unavailable UI; PreviewErrorState component exists but not used everywhere | Use on /map & /calculator |
| J3 | Medium | (Audit) | `ProductJourney` is duplicated (header strip) when global NavBar exists | One global only |
| J4 | Medium | `lib/legacy-mappers.ts` | Legacy mapper zero-fills lat/lng; new summary does not. But `MapShell` still uses legacy mapper | Switch to direct summary reading; keep mapper for legacy callers |
| J5 | Medium | `MapShell` `selectedUniversity` POI vs Summary shape mismatch | Type-cast `(selectedUniversity as any)` — fragile | Type-safe bridge |

## 3. Implementation Phases

| Phase | Goal | Files touched |
|---|---|---|
| B | Map marker labels, hover tooltip, distinct states | `UniversityPoiLayer.tsx`, `MapShell.tsx` (add onHover) |
| C | New `UniversityProfile` panel (right-docked), real data fields, "未报告" empty states | NEW `UniversityProfile.tsx`, `MapShell.tsx` |
| D | Replace centered modal → edge popover; resizable panels; mobile bottom sheet | `MapShell.tsx`, NEW `ResizablePanel.tsx`, NEW `BottomSheet.tsx` |
| E | Calculator picker dialog (search, keyboard, dedupe, max 3) | `calculator/page.tsx` |
| F | Match / Assessment: real summary fields, observable weight changes, fix stale selection | `match/page.tsx`, `assessment/page.tsx` |
| G | One global nav; per-page sub-title strip; remove `ProductJourney` from match/portfolio/assessment | `NavBar.tsx`, `match/page.tsx`, `assessment/page.tsx`, `portfolio/page.tsx` |
| H | Dark mode: tokens, toggle, no-flash, all components | `tailwind.config.ts`, `globals.css`, `layout.tsx`, NEW `ThemeProvider.tsx` |
| I | Responsive / a11y / keyboard | All |
| J | Regression + docs | `/Users/jiayihuang/Downloads/PathOS合并/docs/*` |

## 4. Constraints (HARD)

- Do not modify backend tracked files, Preview Bundle, DB facts, fixtures, .env.local.
- Do not introduce a fixture/mock fallback.
- Do not change the 76/76 test baseline downward.
- 62 schools / 62 summaries / 62 details / 904 verified records must remain.
- `quarantine.exposed=0`, `rank 0=0`, `[0,0]=0`, `sourceLimited=true`, `incomplete=true`, `notFinal=true` must be preserved.
- Do NOT add verified AI context, Parent Mode, verified Choropleth, full international application module.
- Do NOT convert `unknown/not_reported/pending/source_limited/not_in_current_national_scope` into 0/false/N/A — always "未报告" / "数据补充中".
- Screenshots → `/tmp/pathos-stage7a-frontend-ux/`, NOT `frontend/public`.

## 5. Verification

For each fix, reproduce BEFORE-state, apply fix, capture AFTER screenshot. Then `npx tsc --noEmit`, `npm run lint`, `npm run test`, `npm run build`. Compute after-tree-hash, write change manifest, stop dev server (only after build verifies).