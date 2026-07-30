# Stage 7B-A.3 — UI Collision Audit, Responsive Stabilization & Visual QA

> Date: 2026-07-26
> Phase: Stage 7B-A.3
> Predecessor: Stage 7B-A.2 Phase 4B (Choropleth Interior Fill PROVEN)
> Goal: Submit the /map page to user for **real visual review** with **Critical=0, High=0** UI collisions across 12 viewports × 3 themes × 5 regional metrics × all panel states.
> Status: **Plan ready — awaiting ExitPlanMode**

---

## 1. Context

Stage 7B-A.2 Phase 4B already proved the choropleth interior renders (51/51 states, 4 metrics, real-browser pixel sampling). What remains before user visual review is the broader UI quality of /map:

- **Toolbar collisions** — `MapToolbar` (top-right, `right-3 top-3 z-map-toolbar`) and the city-drilldown card (top-left, `left-4 top-4 z-map-control`) sit in opposite corners but a desktop `RegionalLegend` (bottom-right, `bottom-4 right-4 z-map-legend`) collides with both desktop `UniversityProfile` (`right-3 top-3 z-map-profile w-[360px]`) and mobile `BottomSheet` (`fixed inset-x-0 bottom-0 z-40`) at narrow widths.
- **Stale z-index literals** — `UniversityHoverTooltip` uses raw `z-30`, `RegionalHoverTooltip` uses raw `z-50`, despite the `map-zindex.ts` token system and Tailwind `z-map-tooltip: 28` being defined. The two tooltips can stack on top of each other.
- **Tooltip edge handling** — both tooltips position with `left: x + 12, top: y + 12` (absolute / fixed) and never flip when near the right or bottom edge of the viewport. At 320×568, they overflow the screen.
- **Mobile/Desktop exclusivity** — `MapShell` mounts both the desktop `UniversityProfile` (gated `hidden md:block`) and the mobile `BottomSheet` (gated `md:hidden`) plus the `ResizablePanel` sidebar (`hidden md:block`). The directive forbids simultaneous render and the source-text scan confirms the gating is currently correct — we must keep it that way while adding test coverage.
- **No safe-area-inset, no `clamp()`, no container queries** — confirmed in `tailwind.config.ts` (no overrides, defaults only) and `globals.css` (no `@container` or `env(safe-area-*)` anywhere). Mobile BottomSheet has no `padding-bottom: env(safe-area-inset-bottom)` guard, so iOS home indicator can cover the drag handle.
- **No responsive / collision test coverage exists** — the existing 357 tests are all source-text contracts or pure logic. No test asserts toolbar exclusivity, legend 0/1, profile/sheet exclusivity, z-index literal leakage, pointer-events on tooltips, or viewport layout.
- **Choropleth / Marker / Map drag must not regress** — the source-text invariants pinned by `stage7b-a1-closing-patch-v3.test.ts` block K, `stage7baf-regional-styleload-lifecycle.test.ts`, and `stage7ba-baidu-pilot.test.ts` must all stay green.

Stage 7B-A.3 must NOT modify Regional data, 204 records, 62 university facts, Match algorithm, Backend, Preview Bundle, 原始工作簿, FIPS Join, Choropleth palette logic, URL Store semantics, 百度 Runtime, Stage 7B-B, new city metrics, or new region/city detail features.

---

## 2. UI Inventory (existing /map surface)

### Top Right
- `MapToolbar` (`MapShell.tsx:802` → `MapToolbar.tsx:82`) — `absolute right-3 top-3 z-map-toolbar flex max-w-[calc(100vw-1.5rem)] flex-wrap items-center gap-2`. Hosts `<RegionalLayerControl>` + State selector dropdown + view-mode pill.

### Top Left
- City drilldown card (`MapShell.tsx:822`) — `absolute left-4 top-4 z-map-control w-[280px]`. Renders only when `cityDrilldownEnabled && selectedStateFips && visibleCities.length > 0`.

### Bottom Right
- `RegionalLegend` wrapper (`MapShell.tsx:779`) — `absolute bottom-4 right-4 z-map-legend max-w-[320px]`. Renders only when `activeRegionalMetric !== null`.

### Bottom Left / Bottom Center
- MapLibre native attribution (`MapCanvas.tsx:626`) — `pointer-events-none absolute bottom-3 right-3 z-10` (raw z-10, should be `z-map-basemap:0`).
- MapLibre navigation control (zoom +/−, compass) — `maplibregl.NavigationControl`, default bottom-right inside canvas.

### Right Side (desktop only)
- Desktop `UniversityProfile` wrapper (`MapShell.tsx:749`) — `absolute right-3 top-3 z-map-profile hidden h-[calc(100%-1.5rem)] w-[360px] md:block`. Overlaps `MapToolbar` anchor when profile is open.
- `ResizablePanel` sidebar (`MapShell.tsx:871`) — `hidden md:block` wrapper around the right sidebar (region detail / news / city detail / empty state).

### Mobile Bottom
- `BottomSheet` (`MapShell.tsx:761` via `md:hidden` wrapper at 760) — `pointer-events-auto fixed inset-x-0 bottom-0 z-40 flex flex-col`. `role="dialog"`, no `Escape` key handler.

### Full-bleed / Map-overlay
- `MapCanvas` (`MapShell.tsx:676`) — `flex-1 min-h-0` container with `<UniversityPoiLayer>`, `<CaliforniaRoadLayer>`, `<CityLayer>`, `<RegionalStateLayer>` children. Loading overlay (`MapCanvas.tsx:582`) — `absolute inset-0 z-20` (raw z-20).
- `<MapCanvas>` full-bleed attr div (`MapCanvas.tsx:626`) — `pointer-events-none absolute bottom-3 right-3 z-10 select-none` (raw z-10, should be `z-map-basemap:0`).

### Floating Tooltips
- `UniversityHoverTooltip` (`UniversityHoverTooltip.tsx:28`) — `pointer-events-none absolute z-30 max-w-[260px]` with `left: x+14, top: y`. Raw z-30 (should be `z-map-tooltip:28`).
- `RegionalHoverTooltip` (`RegionalHoverTooltip.tsx:26`) — `pointer-events-none fixed z-50 max-w-[260px]` with `left: x+12, top: y+12`. Raw z-50 (should be `z-map-tooltip:28`).

### Header
- Compact header (`MapShell.tsx:613`) — `flex shrink-0 items-center gap-3 border-b border-line bg-panel px-5 py-3` with title + Compass icon + ViewModeToggle (`hidden md:block`) + Calculator/Sparkles + panel toggle. Above the map; not overlaid.

### Global Navigation
- `NavBar` (`app/layout.tsx` → `NavBar.tsx:61`) — `sticky top-0 z-50 h-nav`.

---

## 3. UI Zone Model

| Zone | Anchor | Token | Element |
|---|---|---|---|
| Top Left | `left-4 top-4` | `z-map-control` (20) | City drilldown card |
| Top Right | `right-3 top-3` | `z-map-toolbar` (22) | MapToolbar |
| Center Right (profile) | `right-3 top-3` | `z-map-profile` (30) | UniversityProfile (desktop) — must yield to MapToolbar by sitting **below** the toolbar in DOM order with `top-3` + `top-` offset |
| Bottom Right | `bottom-4 right-4` | `z-map-legend` (24) | RegionalLegend |
| Bottom Center/Right (basemap) | `bottom-3 right-3` | `z-map-basemap` (0) | MapLibre attribution |
| Floating Tooltips | cursor-anchored | `z-map-tooltip` (28) | Both HoverTooltips |
| Mobile Bottom | `inset-x-0 bottom-0` | `z-40` (shared) | BottomSheet |
| Full-bleed modal | `inset-0` | `z-map-modal` (50) | ComparePanel / loading overlay |
| Sidebar (desktop) | right edge | DOM-flow | ResizablePanel (no absolute positioning) |
| Sticky header | `top-0` | `z-50` (shared) | NavBar |

Rule: **no two overlays occupy the same corner at the same breakpoint**. Anchor `top-3 right-3` is shared between MapToolbar and UniversityProfile — to resolve, the profile must shift down (e.g. `top-[calc(theme(spacing.nav)+1rem)]` or `top-14`) or be moved off-corner.

---

## 4. Z-Index Token Cleanup

| File:line | Current | Target | Reason |
|---|---|---|---|
| `MapCanvas.tsx:582` (loading overlay) | `z-20` | `z-map-modal` | Loading is full-bleed; promote to modal rail |
| `MapCanvas.tsx:626` (attribution placeholder) | `z-10` | `z-map-basemap` (0) | Should be at the bottom |
| `UniversityHoverTooltip.tsx:28` | `z-30` | `z-map-tooltip` (28) | Unify with regional tooltip |
| `RegionalHoverTooltip.tsx:26` | `z-50` | `z-map-tooltip` (28) | Unify with university tooltip |

`BottomSheet`'s `z-40` is out of the map-zindex system; it stays `z-40` (or gets a shared `z-sheet` token — out of scope for this stage; do not change).

---

## 5. Critical Fixes (priority order)

1. **Tooltip edge-flip** — both `UniversityHoverTooltip` and `RegionalHoverTooltip` must detect viewport bounds (via `useEffect` + `ResizeObserver` or `window.innerWidth/innerHeight`) and flip to `left - tooltipWidth - 12` when within 280px of the right edge, flip `top - tooltipHeight - 12` when within 200px of the bottom edge. Use `fixed` positioning consistently (already on `RegionalHoverTooltip`, change `UniversityHoverTooltip` from `absolute` to `fixed`).

2. **Tooltip z-index unification** — replace raw `z-30` / `z-50` with `z-map-tooltip`.

3. **MapToolbar ↔ UniversityProfile collision on desktop** — give UniversityProfile a top offset (e.g. `top-14` = 56px nav + 1rem) so the toolbar sits clear. Add a `data-testid="map-profile"` anchor for tests.

4. **MapCanvas raw z-10/z-20 cleanup** — replace `z-10` attribution placeholder → `z-map-basemap`, `z-20` loading overlay → `z-map-modal`. These don't change runtime order but make the policy consistent.

5. **MapToolbar compactness on Tablet (768–1023px)** — current `flex-wrap` works but at 768px the three controls stretch ~640px and pin the legend to the bottom right corner. Add `flex-wrap` (already present) + cap inner widths via `min-w-0` + `truncate` so long labels shrink instead of overflowing.

6. **BottomSheet safe-area** — wrap the drag handle + content with `pb-[max(env(safe-area-inset-bottom),0.5rem)]` so iOS home indicator doesn't cover the collapse button.

7. **BottomSheet Escape handler** — add `useEffect` listening for Escape and closing the parent (currently only the arrow button collapses; map-level Escape should also close).

8. **ComparePanel collision check** — `ComparePanel` is rendered (`MapShell.tsx:728`) but its position was not yet inventoried. Will be inventoried in Phase 1; ensure it doesn't collide with the legend at narrow viewports.

9. **City drilldown card top-left vs Mobile BottomSheet** — on mobile the BottomSheet sits at `inset-x-0 bottom-0`; the city card sits at `left-4 top-4`. They don't share corner space (one top-left, one bottom-fully). On mobile when `cityDrilldownEnabled` is true, the city card is overlapped by the BottomSheet. Fix: hide city card on mobile (`hidden md:block`), or render it inside the BottomSheet. The simplest fix is `hidden md:block` since the mobile flow doesn't need a separate floating card.

10. **ViewModeToggle visibility** — currently `hidden md:block` (`MapShell.tsx:633`). Keep, but ensure on tablet it doesn't squeeze the header (add `shrink-0`).

---

## 6. Files to Modify

### Source (10 files max)

| File | Change |
|---|---|
| `src/components/map/UniversityHoverTooltip.tsx` | `absolute z-30` → `fixed z-map-tooltip`; add viewport edge-flip via `useEffect` |
| `src/components/map/regional/RegionalHoverTooltip.tsx` | `z-50` → `z-map-tooltip`; same edge-flip (DRY into a shared `useEdgeFlippedPosition` hook) |
| `src/components/map/MapShell.tsx` | Desktop `UniversityProfile` wrapper offset (line 749): `top-3` → `top-14` to clear toolbar. City drilldown card (line 822) `md:hidden` already gates desktop; add `hidden md:block` to also hide on mobile. ViewModeToggle: add `shrink-0` |
| `src/components/map/MapCanvas.tsx` | Loading overlay `z-20` → `z-map-modal` (line 582); attribution placeholder `z-10` → `z-map-basemap` (line 626) |
| `src/components/shared/BottomSheet.tsx` | Add Escape handler; add `pb-safe` for safe-area-inset-bottom; add `data-testid="bottom-sheet"` |
| `src/components/map/MapToolbar.tsx` | Add `data-testid` is already present; ensure each child (RegionalLayerControl, state-selector-button, state-selector-dropdown, view-mode) carries `min-w-0` and `truncate`; confirm `flex-wrap` works at 768–1023px |

### New files

| File | Purpose |
|---|---|
| `src/components/shared/useEdgeFlippedPosition.ts` | Shared hook for tooltip / dropdown edge-flip (window bounds + element size) |
| `src/test/unit/stage7b-a3-ui-collision.test.ts` | 23+ tests covering toolbar exclusivity, legend 0/1, profile/sheet exclusivity, z-index token audit, dropdown clipping, tooltip pointer-events, breakpoint gates, focus ring, aria-label, long labels, choropleth/marker/drag preservation |

### Docs (5 files)

| File | Purpose |
|---|---|
| `docs/STAGE7B-A3-UI-COLLISION-AUDIT-PLAN.md` | This plan, packaged |
| `docs/STAGE7B-A3-UI-COLLISION-AUDIT-DEVLOG.md` | Implementation log |
| `docs/STAGE7B-A3-UI-COLLISION-AUDIT-REPORT.md` | 31-section final report |
| `docs/STAGE7B-A3-UI-COLLISION-AUDIT-CHANGE-MANIFEST.json` | SHA-256 manifest |
| `docs/STAGE7B-A3-UI-COLLISION-MATRIX.json` | Collision matrix (viewport × theme × metric × panel × control × overlap × severity) |

---

## 7. Test Strategy (23+ tests)

Source-text + token-shape idioms (matches existing 357 tests under `environment: "node"` — no jsdom installed). New file `src/test/unit/stage7b-a3-ui-collision.test.ts`. The 21 categories from the directive map to **describe blocks**:

| # | Block | Approx tests |
|---|---|---|
| A | Toolbar exclusivity (one and only one `MapToolbar` mounted; `flex-wrap` present; `max-w-[calc(100vw-1.5rem)]` present) | 3 |
| B | Desktop / Mobile toolbar exclusivity (Mobile toolbar absent in source OR `md:hidden` gate on every mobile-only block; desktop block uses `md:` prefix) | 3 |
| C | Legend 0/1 (count `<RegionalLegend` mounts in `MapShell.tsx` = 1; wrapper gated on `activeRegionalMetric`; component returns `null` on null metric) | 3 |
| D | Profile / BottomSheet exclusivity (`MapShell.tsx` wraps each in `md:` / `hidden md:` mutually exclusive gates) | 2 |
| E | Z-index token audit (`MAP_Z` tokens unique + ordered; Tailwind `z-map-*` utilities defined; no raw `z-10/20/30/40/50` in production map code except `BottomSheet z-40` which is out of map-zindex scope) | 4 |
| F | Dropdown clipping (state selector dropdown has `max-h-[320px]` + `overflow-y-auto`; sits above map (`z-map-control`); toggle button has `aria-haspopup` + `aria-expanded`) | 3 |
| G | Tooltip pointer-events (both tooltips have `pointer-events-none`; no `pointer-events-auto`) | 2 |
| H | Profile close button + a11y (`UniversityProfile` close button has `aria-label="关闭学校详情"`; uses `X` icon; supports Escape) | 2 |
| I | Breakpoint gates (320/390/768/1280/150%) — source-text checks for: `min-w-0`, `flex-1 min-h-0`, `flex-wrap`, `truncate`, `md:`, `hidden md:block`, `md:hidden` | 4 |
| J | Long labels (Chinese + English) — assert long labels in source (e.g. "不显示区域热力图", chinese_population label) and that parent containers have `truncate` or bounded `max-w-` | 2 |
| K | Focus ring (assert focus-visible utilities on buttons/selects; global focus-visible in `globals.css`) | 2 |
| L | aria-label coverage (count interactive elements vs `aria-label` occurrences per component) | 2 |
| M | Choropleth + Marker preservation (refer to / extend v1/v2/v3/4B invariants; assert 4 regional metrics still present, `pathos-regional-states-fill` still installed, `pathos-regional-states-line` still installed, `UniversityPoiLayer` still unconditionally mounted in `MapShell.tsx`) | 4 |
| N | Map drag not blocked (assert `<MapCanvas>` has `pointer-events-auto`; tooltips have `pointer-events-none`; toolbar/profile are `pointer-events-auto` so user can click them but their wrapper doesn't extend beyond their visible bounds) | 3 |
| **Total** | | **~38** |

Final target: ≥380 tests passing (357 existing + ~23 new).

---

## 8. Verification Plan

### 8.1 Code quality

```bash
cd frontend
npx tsc --noEmit                    # 0 errors
npx next lint --max-warnings 0      # 0 warnings
npx vitest run                      # ≥380 tests pass (357 + ≥23 new)
npx next build                      # 15 routes, no regression
```

### 8.2 Source-text invariants for tooltips

- `UniversityHoverTooltip.tsx` contains `fixed` (was `absolute`), `z-map-tooltip` (was `z-30`), `pointer-events-none`
- `RegionalHoverTooltip.tsx` contains `z-map-tooltip` (was `z-50`), `pointer-events-none`
- `MapCanvas.tsx` line ~582 contains `z-map-modal` (was `z-20`)
- `MapCanvas.tsx` line ~626 contains `z-map-basemap` (was `z-10`)

### 8.3 Real Browser Matrix (12 captures)

Required by directive §十七:

| # | Viewport | Theme | Metric | Panel | Toolbar |
|---|---|---|---|---|---|
| 1 | 1920×1080 | Light | income | closed | — |
| 2 | 1440×900 | Dark | safety | closed | — |
| 3 | 1366×768 | Light | income | Profile open | — |
| 4 | 1280×720 | Light | chinese_population | closed | Dropdown open |
| 5 | 1024×768 | Light | income | closed | — |
| 6 | 768×1024 | Light | income | closed | — |
| 7 | 430×932 | Light | employment | closed | — |
| 8 | 390×844 | Light | income | closed | BottomSheet |
| 9 | 375×812 | Light | income | Legend active | — |
| 10 | 320×568 | Light | income | closed | — |
| 11 | 1280×720 125% zoom | Light | income | closed | — |
| 12 | 1280×720 150% zoom | Light | income | closed | — |

Per capture: collision count, horizontal overflow, clipped controls, unreadable labels, inaccessible buttons, duplicated UI, blocked map area.

### 8.4 Collision Matrix (JSON artifact)

Required fields per the directive §十八: viewport, theme, metric, panelState, controlState, elementA, elementB, overlapPixels, severity, beforeScreenshot, afterScreenshot, resolution.

### 8.5 Acceptance

- **Critical = 0**
- **High = 0**
- **Medium ≤ 0 (with documented justification if any retained)**
- **All 4 metrics render with choropleth intact**
- **University markers remain interactive**
- **Map drag / wheel / touch pan work everywhere**
- **Dev server starts on 3002 with `.env.local`; production build succeeds on 3003**
- **Backend / Bundle / Workbook / 62 university facts / Match algorithm / Stage 6 tag unchanged**

---

## 9. Sequencing

1. Phase 1 — UI inventory + UI Zone model (write into REPORT, no code change yet)
2. Phase 2 — Collision scan against the 20 listed concerns
3. Phase 3 — Create `useEdgeFlippedPosition` shared hook
4. Phase 4 — Fix `UniversityHoverTooltip` (fixed + z-map-tooltip + edge-flip)
5. Phase 5 — Fix `RegionalHoverTooltip` (z-map-tooltip + edge-flip)
6. Phase 6 — Fix `MapCanvas` (z-map-modal, z-map-basemap)
7. Phase 7 — Fix `MapShell` UniversityProfile top offset + city drilldown `hidden md:block`
8. Phase 8 — Fix `BottomSheet` (Escape handler, safe-area, data-testid)
9. Phase 9 — Fix `MapToolbar` tablet layout (min-w-0, truncate)
10. Phase 10 — Add `stage7b-a3-ui-collision.test.ts` (~38 cases)
11. Phase 11 — Run tsc / lint / vitest / build, all green
12. Phase 12 — Dev (3002) + Prod (3003) Browser Matrix 12 captures
13. Phase 13 — Write 5 docs
14. Phase 14 — Stop dev/prod servers; report `READY FOR USER VISUAL REVIEW` or `NOT READY`

---

## 10. Out of Scope (Hard Constraints)

- Regional data, 204 records, 62 university facts, Match algorithm (Stage 6) — DO NOT MODIFY
- Backend / Preview Bundle / 原始工作簿 — DO NOT MODIFY
- FIPS Join / Choropleth palette data logic — DO NOT MODIFY
- URL Store semantics — DO NOT MODIFY
- 百度 Runtime / Stage 7B-B — DO NOT MODIFY
- New city-level indicators / region detail / state detail — DO NOT ADD
- SelectedMapEntity state unification (Stage 7B-A.2 Phase 3) — DEFERRED
- CityLayer beforeId fix (Stage 7B-A.2 Phase 5) — DEFERRED
- Region detail panel rewrite (Stage 7B-A.2 Phase 6) — DEFERRED
- URL state for state/place (Stage 7B-A.2 Phase 8) — DEFERRED
- 31+ T-series tests (Stage 7B-A.2 Phase 9) — DEFERRED
- jsdom / `@testing-library/react` install — DEFERRED (no need this stage; source-text + token tests cover all requirements)
- Tailwind safe-area-inset utility additions — optional; if added, must be in `tailwind.config.ts` only

---

## 11. Final Status

`READY FOR USER VISUAL REVIEW` (when Critical=0, High=0, all 12 captures clean, all 380+ tests green, build 15 routes, no backend/bundle mutation)

or

`NOT READY` (with documented residual + remediation plan)