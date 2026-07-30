# Stage 7A Closing Patch v2 — Theme Correctness, Visual Contrast & Verified Regional Heatmaps

> Plan — *what we are doing, why, and how we will know we are done*

## 1. Background

The independent Re-Gate run for Stage 7A v1 returned **FAIL**. The required closing
patch (v2) must close five independently-discovered defects plus one CRITICAL
invariant — *the regional heatmaps* — before the next Re-Gate can issue a
verdict.

This patch is deliberately narrow: theme hydration safety, contrast on the new
dark tokens, the MapLibre dark basemap no-op, two pages missing the region
boundary callout, a calculator cost-summary branch that is unreachable in current
data, and four `react-hooks/exhaustive-deps` disables. **Regional heatmaps are
blocked by data provenance, not silenced.** The directive's CRITICAL rule
("如果无法找到数据文件，或者无法确认来源、年份、单位和 join key：只阻塞热力图
子任务并报告。不得生成随机数或重新使用安全 70、就业 80 等默认值") is honoured
literally.

## 2. Scope

### In scope

| # | Defect | Severity | Owner file(s) |
|---|--------|----------|---------------|
| H-1 | ThemeToggle hydration mismatch on every page refresh | HIGH | `src/lib/theme.ts`, `src/components/ThemeToggle.tsx` |
| M-1 | MapLibre dark basemap no-op (both style constants → same URL) | MEDIUM | `src/components/map/MapCanvas.tsx` |
| M-2 | `/assessment` missing region-blocked callout (only `/match` had it) | MEDIUM | `src/app/assessment/page.tsx` |
| M-3 | Calculator missing-cost callout unreachable with current data | MEDIUM | `src/lib/legacy-mappers.ts` + new test |
| L-1 | 4× `eslint-disable-next-line react-hooks/exhaustive-deps` need audit | LOW | `MapCanvas`, `use-view-state-bridge`, `use-data-source` |
| R-1 | Regional heatmaps (income/safety/employment/chinese-community) | CRITICAL | `docs/STAGE7A-REGIONAL-DATA-PROVENANCE.md` |

### Out of scope

- Data pipeline (`data-pipeline/`) — read-only per directive
- Preview Bundle content (`manifest_sha=88f3dd60…0bd2`) — untouched
- Backend tracked files — untouched
- School data facts — untouched (`schoolCount=62` etc. must remain verbatim)
- Stage 6 tag `stage6-demo-pass-2026-07-25-2` — must not be moved
- "Production Data Export" toggle — must remain disabled
- Any forbidden action (pkill / killall / force / reset / clean / rebase /
  push / external port 3000 seizure / Stage 7B entry)

## 3. Invariants

Preserved verbatim from v1:

- `schoolCount=62`, `summaryCount=62`, `detailCount=62`, `verifiedRecordCount=904`
- `quarantine.exposed=0`, `rank 0=0`, `[0,0]=0`, `fixture fallback=false`,
  `dataMode=backend`
- `identityVerified=true`, `sourceLimited=true`, `incomplete=true`,
  `notFinal=true`, `Production Data Export=prohibited`
- Preview Bundle manifest SHA: `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Regional heatmap data (if any added) uses separate counters —
  `regionalDatasetId`, `regionalRecordCount`, etc. — and **does not** inflate
  `verifiedRecordCount=904`

## 4. Approach by defect

### H-1 — ThemeToggle hydration

**Root cause.** `useState(() => readStoredMode())` runs on the server
(`localStorage` undefined → `mode="system"`) and again on the client where
`matchMedia("(prefers-color-scheme: dark)")` is truthy → `mode="dark"` on first
client paint. React fires a hydration error for the icon/label divergence
inside `<button>` because `<html suppressHydrationWarning>` only suppresses
the root, not children.

**Fix.**

1. Move state into an external store (`subscribe/emit/Set<listener>`).
2. Bridge to React via `useSyncExternalStore(subscribe, getSnapshot,
   getServerSnapshot)`.
3. `getServerSnapshot` returns a frozen SSR snapshot `{ mode: "system",
   resolved: "light", isHydrated: false }` — first client commit matches SSR.
4. `ThemeToggle` renders deterministic placeholder (`label="切换主题"`,
   `Icon=Monitor`) until the post-mount effect calls `bootClient()`.
5. Expose `data-theme-mode`, `data-theme-resolved`, `data-hydrated` data
   attributes on the button so the test matrix can verify determinism.

### M-1 — MapLibre dark basemap

**Root cause.** Both `LIGHT_STYLE_URL` and `DARK_STYLE_URL` pointed at
`https://demotiles.maplibre.org/style.json`. Switching `data-theme` mutated
the URL string but `map.setStyle(same-url)` is a no-op.

**Fix.**

1. Replace URL constants with inline MapLibre `StyleSpecification` objects
   (`LIGHT_BASEMAP_STYLE`, `DARK_BASEMAP_STYLE`).
2. Light = CARTO Voyager raster tiles, 4 subdomains, OSM + CARTO attribution.
3. Dark  = CARTO Dark Matter raster tiles, 4 subdomains, OSM + CARTO attribution.
4. Constructor accepts `lightStyle` / `darkStyle` props; `style: isDark ?
   darkStyle : lightStyle`.
5. `MutationObserver` now filters `attributeFilter: ["data-theme"]` only
   (NOT `class`, to dodge iOS Safari spurious fires) and reads
   `documentElement.getAttribute("data-theme")`.
6. `map.setStyle(target)` is called directly — removed the broken
   `sprite !== undefined` gate.

### M-2 — `/assessment` region-blocked callout

**Root cause.** v1 only added the boundary statement to `/match`.

**Fix.** Insert the same AlertTriangle callout above the student-profile card
on `/assessment`, with copy reflecting the *current* state ("当前仅在地图上
作环境参考") rather than the historical "数据源尚未验证".

### M-3 — Calculator missing-cost branch

**Root cause.** With the production data, every school has a verified
`costSummary.minimumUsd`, so the UI never exercises the missing-cost branch.

**Fix.** Synthesize a test fixture in `stage7a-theme-heatmap.test.ts`
covering `null`, `0`, negative, `NaN`, `Infinity`. No production code
change to `tuitionRmbFromSummary` — it already returns `null` for these
inputs.

### L-1 — exhaustive-deps audit

| File | Line | Verdict | Action |
|------|------|---------|--------|
| `MapCanvas.tsx` | mount effect | **Keep** — boot-only init | rationale comment + targeted `disable-next-line` |
| `MapCanvas.tsx` | memo | **Fix** — include `mapReady, granularity, viewState` | dropped explicit `disable` |
| `use-view-state-bridge.ts` | write-back | **Fix** — include `writeUrl` in deps | dropped explicit `disable` |
| `use-data-source.ts` | effect | **Keep** — dynamic deps per resource | rationale comment + targeted `disable-next-line` |

Final: 2 disables (down from 4), both with multi-line rationale comments.

### R-1 — Regional heatmaps

The directive is explicit: **do not fabricate numbers.** We surveyed every
candidate source:

- Preview Bundle (`status: "blocked"`) — read-only, must not be modified.
- Handoff candidate CSV (339 rows) — every row flagged `candidate_only=true,
  preview_only=true, verified_against_backend=false,
  production_ready=false`, source = "Demonstration estimate".
- Legacy `frontend/src/data/region-metrics.json` placeholder — was already
  replaced with the empty shell in Stage 6.
- Read-only legacy dirs (`PathOS-db-ranking`,
  `PathOS合并-integration-baseline`,
  `PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`) — no verified
  provenance.

**Decision: REGIONAL HEATMAPS BLOCKED.** Recorded in
`docs/STAGE7A-REGIONAL-DATA-PROVENANCE.md`. Choropleth surface left empty
with a tile-only basemap; legend reads "区域数据未验证 · 暂不显示".

## 5. Test plan

| Layer | Coverage |
|-------|----------|
| Unit  | `stage7a-theme-heatmap.test.ts` (NEW, 75 tests) — hydration script shape, contrast matrix (12 fg × 3 bg × {4.5,3.0} × 2 themes), MapLibre distinctness (different objects, ≥4 hosts, attribution, version=8), calculator synthetic cost branch (null/0/neg/NaN/Inf/positive), region-boundary copy in `/match`, `/assessment`, `/portfolio` |
| Lint  | `next lint` — 0 errors, 0 warnings (down from 4 disables to 2 with rationale) |
| Type  | `tsc --noEmit` exit 0 |
| Build | `npm run build` — 15 routes generated |
| Server| `npm run dev` on port 3002, all 9 routes return 200 (404 page on `/404` and unknown paths) |
| HTML  | stable `data-theme-mode="system"`, `data-theme-resolved="light"`, `data-hydrated="false"`, `aria-label="切换主题"` across 3 renders of `/`, `/map`, `/calculator`, `/assessment`, `/match`, `/portfolio` |

## 6. Forbidden writes (re-stated)

- `/Users/jiayihuang/PathOS`
- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking`
- `/Users/jiayihuang/Downloads/PathOS合并-integration-baseline`
- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`

## 7. Definition of Done

1. All five defect categories addressed or explicitly blocked (R-1) with
   provenance documented.
2. Test count 151/151 passing.
3. Lint, type-check, build all green.
4. Dev server returns 200 on 9 routes × 3 fresh requests with stable SSR
   markup.
5. Four docs (`PLAN`, `DEVLOG`, `REPORT`, `CHANGEMANIFEST.json`) written.
6. Dev server stopped (kill known PID only — never pkill/killall/抢
   3000/未知PID).
7. Final report reads **READY FOR INDEPENDENT RE-GATE**.