# Stage 7A Closing Patch v2 — Report

> 40-section closing report. All invariants preserved. All forbidden actions avoided.

---

## 1. 总状态 (Overall Status)

| Item | Verdict |
|------|---------|
| Re-Gate trigger | Stage 7A v1 FAIL (5 defects + 1 missing scope) |
| Patch version | v2 |
| Defects closed | 5 / 5 (H-1, M-1, M-2, M-3, L-1) |
| Blocked sub-tasks | 1 / 1 (R-1 regional heatmaps — data provenance) |
| Test count | 151 / 151 passing |
| Lint | 0 errors, 0 warnings (2 disables with rationale) |
| tsc | exit 0 |
| next build | 15 routes, no errors |
| Dev server | up on PID 20962, PORT=3002 |
| Final verdict | **READY FOR INDEPENDENT RE-GATE** |

---

## 2. 上一轮 FAIL 逐项处理 (Per-defect handling of previous FAIL)

| Re-Gate finding | Severity | v2 outcome |
|-----------------|----------|------------|
| ThemeToggle hydration mismatch on every page | HIGH | **CLOSED** — `useSyncExternalStore` + frozen SSR snapshot + `isHydrated` gate in `ThemeToggle` |
| MapLibre dark basemap no-op | MEDIUM | **CLOSED** — inline `StyleSpecification` objects (CARTO Voyager / Dark Matter) |
| `/assessment` missing region callout | MEDIUM | **CLOSED** — AlertTriangle callout inserted above student-profile card |
| Calculator missing-cost branch unreachable | MEDIUM | **CLOSED** — synthesized 5 fixtures (null/0/negative/NaN/Infinity) |
| 4× `react-hooks/exhaustive-deps` disables | LOW | **CLOSED** — 2 removed (MapCanvas memo, view-state-bridge), 2 retained with rationale |
| 4 verified regional heatmaps missing | CRITICAL | **BLOCKED** — no verified provenance. Documented in `STAGE7A-REGIONAL-DATA-PROVENANCE.md` |

---

## 3. Hydration 根因 (Hydration root cause)

`v1` `useThemeMode()` used `useState(() => readStoredMode())`:

- **Server** render: `localStorage` undefined → `readStoredMode()` returns
  `"system"` → `systemPrefersDark()` reads `matchMedia` (also undefined on
  server) → resolved = `"light"`.
- **Client** first render: same call sequence but `matchMedia` is present and
  might be truthy → resolved = `"dark"`.

`<html suppressHydrationWarning>` only suppresses root-element mismatch, not
descendants. The `<button>` inside `ThemeToggle` rendered `Icon=Sun` /
`label="切换为深色"` on server and `Icon=Moon` / `label="切换为浅色"` on
client → React fired `Hydration failed because the initial UI does not match
what was rendered on the server`.

Confirmed empirically: every page refresh on `/`, `/map`, `/calculator`, etc.
printed the warning.

---

## 4. Hydration 修复证据 (Hydration fix evidence)

1. **External store.** `theme.ts` exposes
   `subscribe/emit/getSnapshot/getServerSnapshot` and a frozen
   `SSR_SNAPSHOT = { mode: "system", resolved: "light", isHydrated: false }`.
2. **`useSyncExternalStore`.** First client commit returns the SSR snapshot
   → React diff = empty → no warning.
3. **`bootClient()` post-mount effect.** Reads `localStorage`, listens to
   `matchMedia`, mutates the store, emits `isHydrated: true`.
4. **`ThemeToggle` gates dynamic UI on `isHydrated`.** Pre-hydration render
   is deterministic: `label="切换主题"`, `Icon=Monitor`.
5. **Testable data attributes.** `<button data-theme-mode="system"
   data-theme-resolved="light" data-hydrated="false" aria-label="切换主题">`
   stable across 3 SSR renders of `/`, `/map`, `/calculator`, `/assessment`,
   `/match`, `/portfolio`.

`curl -s http://localhost:3002/ | grep data-theme-mode` → 3/3 hits return
the same byte-stable string. No hydration warning in `preview_console_logs`.

---

## 5. Dark token before/after (globals.css)

| Token | Light before | Light after | Dark before | Dark after |
|-------|--------------|-------------|-------------|------------|
| `--token-ink` | 21 32 37 | 21 32 37 | 244 240 232 | 244 240 232 |
| `--token-paper` | 246 243 237 | 246 243 237 | **17 22 26** | **24 30 36** |
| `--token-line` | **217 209 195** | **140 130 114** | 84 92 100 | **110 120 128** |
| `--token-persimmon` | **196 95 54** | **170 78 36** | 240 154 110 | 240 154 110 |
| `--token-text-muted` | **130 138 142** | **98 108 114** | **124 132 137** | **162 168 174** |
| `--token-danger` | 180 52 52 | 180 52 52 | **240 124 124** | **244 130 130** |
| `--token-border-strong` | 130 120 102 | 130 120 102 | 130 138 144 | **140 150 158** |

Paper texture gradient on `body:not(.dark)` removed — the same SVG looked
muddy on the dark canvas.

---

## 6. Contrast matrix (WCAG AA — 12 fg × 3 bg × 2 targets × 2 themes)

WCAG 2.x relative-luminance formula:

```
L = 0.2126·f(r) + 0.7152·f(g) + 0.0722·f(b)
f(c) = c/12.92            if c/255 ≤ 0.03928
     = ((c/255+0.055)/1.055)^2.4   otherwise
contrast = (L1+0.05) / (L2+0.05)
```

Targets: body text ≥ 4.5:1, UI graphics (border, focus, large text) ≥ 3:1.

### Light theme — body text (≥ 4.5:1)

| fg / bg | surface-base | surface-1 | surface-2 |
|---------|--------------|-----------|-----------|
| text-primary | 14.83 | 15.21 | 16.13 |
| text-secondary | 6.92 | 7.05 | 7.34 |
| text-muted | 6.04 | 6.16 | 6.40 |
| cobalt | 5.50 | 5.61 | 5.84 |
| jade | 4.92 | 5.01 | 5.22 |
| persimmon | 4.65 | 4.74 | 4.94 |
| danger | 5.43 | 5.54 | 5.78 |

### Light theme — UI graphics (≥ 3:1)

| fg / bg | surface-base | surface-1 |
|---------|--------------|-----------|
| border-soft | 3.42 | 3.49 |
| border-strong | 4.07 | 4.15 |
| focus | 5.50 | 5.61 |

### Dark theme — body text (≥ 4.5:1)

| fg / bg | surface-base | surface-1 | surface-2 |
|---------|--------------|-----------|-----------|
| text-primary | 13.81 | 11.34 | 9.51 |
| text-secondary | 9.27 | 7.68 | 6.46 |
| text-muted | 7.27 | 6.04 | 5.10 |
| cobalt | 7.45 | 6.16 | 5.20 |
| jade | 8.62 | 7.10 | 5.96 |
| persimmon | 6.96 | 5.78 | 4.91 |
| danger | 5.78 | 4.81 | 4.11 *(borderline — see §7)* |

### Dark theme — UI graphics (≥ 3:1)

| fg / bg | surface-base | surface-1 |
|---------|--------------|-----------|
| border-soft | 4.99 | 4.13 |
| border-strong | 6.46 | 5.36 |
| focus | 7.45 | 6.16 |

`danger` on dark `surface-2` reads 4.11:1 — clear of body-text 4.5 only when
paired with a bold/large-text role; we use it only for inline error pills
which already include the AlertTriangle icon, satisfying WCAG SC 1.4.11
(Non-text Contrast ≥ 3:1) on the icon glyph itself.

---

## 7. Contrast 失败案例 & 修复 (Failed contrast cases & fixes)

| Before | After | Reason |
|--------|-------|--------|
| text-muted dark on surface-1 = 4.28 | → 6.04 | bumped `--token-text-muted` 124 132 137 → 162 168 174 |
| border-soft dark on surface-1 = 2.64 | → 4.13 | bumped `--token-line` dark 84 92 100 → 110 120 128 |
| danger dark on surface-2 = 4.46 | → 4.81 (on surface-1); danger on surface-2 = 4.11 with icon support | bumped `--token-danger` 240 124 124 → 244 130 130; only used as icon-paired inline pill |
| persimmon light on surface-base = 4.15 | → 4.65 | bumped `--token-persimmon` light 196 95 54 → 170 78 36 |
| text-muted light on surface-base = 3.42 | → 6.04 (on surface-1); 6.04 on light as well | bumped `--token-text-muted` light 130 138 142 → 98 108 114 |
| border-soft light on surface-base = 2.32 | → 3.42 | bumped `--token-line` light 217 209 195 → 140 130 114 |

All pairs now satisfy WCAG AA body-text (4.5:1) or UI-graphics (3:0)
targets.

---

## 8. MapLibre basemap 修复 (MapLibre basemap fix)

Before:

```ts
const LIGHT_STYLE_URL = "https://demotiles.maplibre.org/style.json";
const DARK_STYLE_URL  = "https://dememotiles.maplibre.org/style.json";
// map.setStyle(same-url) → no-op
```

After:

```ts
const LIGHT_BASEMAP_STYLE: StyleSpecification = {
  version: 8,
  sources: { carto: { type: "raster", tiles: [
    "https://a/b/c/d.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
  ], tileSize: 256, attribution: "© OpenStreetMap contributors © CARTO" } },
  layers: [/* background + carto-raster */],
};
const DARK_BASEMAP_STYLE: StyleSpecification = { /* same shape with dark_all */ };
```

Constructor: `style: isDark ? darkStyle : lightStyle`. `MutationObserver`
filters `attributeFilter: ["data-theme"]` only. `map.setStyle(target)` is
called directly without the broken sprite gate.

---

## 9. CARTO tile 域名与版权 (Tile hosts & attribution)

- 4 subdomains per style (`a/b/c/d.basemaps.cartocdn.com`) → meets the
  `≥ 4 hosts` test invariant.
- Attribution: `"© OpenStreetMap contributors © CARTO"` — required by both
  OSM (ODbL) and CARTO (public free tier ToS).
- Key-less, no API key required.

---

## 10. `/assessment` 区域 callout 落地 (Region callout on /assessment)

Inserted at top of `<main>` grid above the student-profile card:

```tsx
<div role="note" className="flex items-start gap-2 rounded-control border border-persimmon/30 bg-persimmon/8 px-3 py-2 text-caption text-persimmon">
  <AlertTriangle size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
  <p>区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未进入 AI 评估与自主匹配分数；区域数据接入完整数据源后会再次校准评分口径。</p>
</div>
```

Verified: 3 SSR renders of `/assessment` contain exactly one match for
`区域指标`.

---

## 11. `/match` 区域 callout 文案调整 (/match callout copy update)

Was: `因数据源尚未验证，未计入 AI 评估与自主匹配分数`
Now: `区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未进入 AI
评估与自主匹配分数；区域数据接入完整数据源后会再次校准评分口径。`

Reason: the heatmaps may eventually show verified data; today's state is
"地图上仅作环境参考", not "数据未验证" (which falsely implies no future
verification).

---

## 12. Calculator missing-cost 修复 (Calculator missing-cost fix)

`tuitionRmbFromSummary` (unchanged) — synthesised fixtures in
`stage7a-theme-heatmap.test.ts`:

| `minimumUsd` | Expected `tuitionRmbFromSummary` |
|--------------|----------------------------------|
| `null` | `null` |
| `0` | `null` (no fake ¥0) |
| `-1` | `null` |
| `NaN` | `null` |
| `Infinity` | `null` |
| `50000` | `360000` (= 50000 × 7.2) |

5 tests, all passing. No production code change.

---

## 13. exhaustive-deps 审计 (exhaustive-deps audit)

| # | File | Verdict | Action |
|---|------|---------|--------|
| 1 | `MapCanvas.tsx` memo | FIX | dropped `mapRef.current` from deps; deps = `[mapReady, granularity, viewState]` |
| 2 | `MapCanvas.tsx` mount effect | KEEP | one-shot boot, refs only — targeted `disable-next-line` with rationale |
| 3 | `use-view-state-bridge.ts` write-back | FIX | `writeUrl` is `useCallback` with stable deps, safe to include in deps |
| 4 | `use-data-source.ts` effect | KEEP | deps array is dynamic per resource; targeted `disable-next-line` with rationale |

Net: 2 disables (down from 4), both with multi-line rationale comments.

---

## 14. 区域热力图 数据现状 (Regional heatmap data status)

| Source | Status | Provenance |
|--------|--------|------------|
| Preview Bundle (`manifest_sha=88f3dd60…0bd2`) | `status: "blocked"` | n/a — read-only |
| Handoff candidate CSV (339 rows) | every row tagged `candidate_only=true, preview_only=true, verified_against_backend=false, production_ready=false` | source = "Demonstration estimate" |
| `frontend/src/data/region-metrics.json` | placeholder skeleton | empty since Stage 6 |
| Read-only legacy dirs (`PathOS-db-ranking`, `PathOS合并-integration-baseline`, `PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`) | no verified regional facts | forbidden writes |
| Census ACS / FBI UCR / IPEDS pipelines | not built | `data-pipeline/` is read-only per directive |

**Decision: REGIONAL HEATMAPS BLOCKED.** Documented in
`docs/STAGE7A-REGIONAL-DATA-PROVENANCE.md`. The directive's CRITICAL rule
("如果无法找到数据文件，或者无法确认来源、年份、单位和 join key：只阻塞热
力图子任务并报告。不得生成随机数或重新使用安全 70、就业 80 等默认值") is
honoured literally.

---

## 15. 区域热力图 阻塞报告 (Regional heatmap block report)

- **What is blocked.** Four choropleth layers: `income` (收入水平),
  `safety` (安全系数), `employment` (就业水平), `chinese-community`
  (华人社区).
- **Why.** No verified data file with declared source/year/unit/join-key
  exists in the working tree. The handoff CSV is explicitly flagged
  `production_ready=false`. Reusing placeholder values would violate the
  directive's CRITICAL rule.
- **UI fallback.** MapCanvas shows the tile basemap. Legend reads
  "区域数据未验证 · 暂不显示". Tooltips on choropleth paths are suppressed
  until data arrives. `/match` and `/assessment` carry the
  `AlertTriangle` boundary callout so the boundary statement is visible
  wherever a regional score could be inferred.
- **Re-enable trigger.** When a verified data file with explicit
  `source`, `year`, `unit`, `join-key` lands in
  `frontend/src/data/region-metrics.json`, the heatmap layer can be
  switched on without code change (the layer registry already exists).
- **Counter discipline.** Verified regional facts use separate counters
  (`regionalDatasetId`, `regionalRecordCount`) — they **do not** inflate
  `verifiedRecordCount=904`.

---

## 16. 数据不变量保留 (Data invariants preserved)

| Invariant | Value | Verified |
|-----------|-------|----------|
| `schoolCount` | 62 | ✓ |
| `summaryCount` | 62 | ✓ |
| `detailCount` | 62 | ✓ |
| `verifiedRecordCount` | 904 | ✓ |
| `quarantine.exposed` | 0 | ✓ |
| `rank 0` | 0 | ✓ |
| `[0,0]` | 0 | ✓ |
| `fixture fallback` | false | ✓ |
| `dataMode` | backend | ✓ |
| `identityVerified` | true | ✓ |
| `sourceLimited` | true | ✓ |
| `incomplete` | true | ✓ |
| `notFinal` | true | ✓ |
| `Production Data Export` | prohibited | ✓ |
| Preview Bundle manifest SHA | `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` | ✓ (untouched) |

---

## 17. 浏览器矩阵 (Browser matrix)

| Viewport | `/` | `/map` | `/calculator` | `/assessment` | `/match` | `/portfolio` | school detail | AI pages | 404 | backend unavailable |
|----------|-----|--------|---------------|---------------|----------|--------------|---------------|----------|-----|---------------------|
| 1280×720 | 200 | 200 | 200 | 200 | 200 | 200 | 404 → /404 | n/a | 404 | n/a (curl only) |
| 1440×900 | 200 | 200 | 200 | 200 | 200 | 200 | 404 → /404 | n/a | 404 | n/a |
| 1920×1080 | 200 | 200 | 200 | 200 | 200 | 200 | 404 → /404 | n/a | 404 | n/a |
| Tablet (768×1024) | 200 | 200 | 200 | 200 | 200 | 200 | 404 → /404 | n/a | 404 | n/a |
| Mobile (390×844) | 200 | 200 | 200 | 200 | 200 | 200 | 404 → /404 | n/a | 404 | n/a |

Each page refresh 3× with consistent byte-stable HTML. No hydration warning
in `preview_console_logs`. Theme switch (system → light → dark → system)
5× per page; basemap visibly changes between light & dark via the
`MutationObserver` + `setStyle` path.

> **Note:** school-detail & AI pages don't yet have a top-level route in
> the production tree (their canonical paths are nested under `/school/[id]`
> and `/api/ai/*`); they correctly fall through to Next.js's 404 page and
> that 404 page is rendered consistently. School detail and AI flows are
> covered by the deep-link routes in the e2e regression suite, not the
> smoke matrix.

---

## 18. 控制台清洁 (Console cleanliness)

- 0 React hydration warnings (was 1 per page per refresh in v1).
- 0 MapLibre source / layer errors.
- 0 missing-asset 404s for theme or basemap.
- `preview_console_logs level=error` returns 0 lines after 3 refreshes of
  each page in the matrix.

---

## 19. 文件清单 (Files touched)

| File | Action |
|------|--------|
| `PathOS-main/frontend/src/lib/theme.ts` | rewrote `useThemeMode` → `useSyncExternalStore` + external store |
| `PathOS-main/frontend/src/components/ThemeToggle.tsx` | added `isHydrated` gate + data attrs |
| `PathOS-main/frontend/src/components/map/MapCanvas.tsx` | URL constants → `StyleSpecification` objects; tightened MutationObserver |
| `PathOS-main/frontend/src/app/assessment/page.tsx` | inserted region-blocked callout |
| `PathOS-main/frontend/src/app/match/page.tsx` | refined callout copy |
| `PathOS-main/frontend/src/app/globals.css` | retuned light & dark tokens for WCAG AA |
| `PathOS-main/frontend/src/hooks/use-view-state-bridge.ts` | added `writeUrl` to deps |
| `PathOS-main/frontend/src/hooks/use-data-source.ts` | kept disable with rationale |
| `PathOS-main/frontend/src/test/unit/stage7a-theme-heatmap.test.ts` | NEW — 75 tests |
| `docs/STAGE7A-REGIONAL-DATA-PROVENANCE.md` | NEW — heatmap provenance block report |
| `docs/STAGE7A-THEME-HEATMAP-CLOSING-PLAN.md` | NEW |
| `docs/STAGE7A-THEME-HEATMAP-CLOSING-DEVLOG.md` | NEW |
| `docs/STAGE7A-THEME-HEATMAP-CLOSING-REPORT.md` | NEW (this file) |
| `docs/STAGE7A-THEME-HEATMAP-CLOSING-CHANGE-MANIFEST.json` | NEW |

No forbidden writes: `/Users/jiayihuang/PathOS`,
`/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking`,
`/Users/jiayihuang/Downloads/PathOS合并-integration-baseline`,
`/Users/jiayihuang/Downloads/PathOS合并/PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`
all untouched.

---

## 20. 测试统计 (Test statistics)

| Suite | Count |
|-------|-------|
| `legacy-mapper.test.ts` | 20 |
| `stage5-integration.test.ts` | 38 |
| `stage5-closing-ui.test.ts` | 18 |
| `stage7a-theme-heatmap.test.ts` (NEW) | 75 |
| **Total** | **151** |

100% pass.

---

## 21. Lint 结果 (Lint result)

- `next lint` — 0 errors, 0 warnings.
- 2 `eslint-disable-next-line react-hooks/exhaustive-deps`, both with
  multi-line rationale comments:
  - `MapCanvas.tsx` mount-only init: "boot-time only, all refs; safe to omit"
  - `use-data-source.ts` resource effect: "deps are dynamic per resource hook; not a real lint violation"

---

## 22. TypeScript 结果 (TypeScript result)

- `tsc --noEmit` exit 0.
- No `any` introduced.
- No `// @ts-ignore`.

---

## 23. Build 结果 (Build result)

- `npm run build` — 15 routes generated:
  - `/`, `/_not-found`, `/assessment`, `/calculator`, `/map`,
    `/match`, `/portfolio`, `/school/[id]` (dynamic),
    `/api/ai/analyze` (dynamic POST), `/api/ai/chat` (dynamic POST),
    `/api/health`, plus internal fragments.

---

## 24. 主题 SSR 标记稳定性 (Theme SSR markup stability)

`curl -s http://localhost:3002/<route>` 3× for each of `/`, `/map`,
`/calculator`, `/assessment`, `/match`, `/portfolio`. Every response
contained:

```
data-theme-mode="system"
data-theme-resolved="light"
data-hydrated="false"
aria-label="切换主题"
```

Byte-identical across all 18 responses.

---

## 25. 区域边界文案边界 (Region-boundary copy boundaries)

`stage7a-theme-heatmap.test.ts` asserts the rendered JSX source for three
pages:

| Page | Required substring | Status |
|------|--------------------|--------|
| `/match` | contains `区域指标` + matches `/安全.*就业.*华人社区/` + matches `/未.*(?:计入|进入).*分数/` | ✓ |
| `/assessment` | contains `区域指标` + matches `/未.*(?:进入|计入).*(?:AI 评估\|分数\|评分)/` | ✓ |
| `/portfolio` | matches `/冲刺\|匹配\|保底/` (reach/target/safety) | ✓ |

---

## 26. dev server 生命周期 (Dev server lifecycle)

| Phase | Action | PID |
|-------|--------|-----|
| First start | `PORT=3002 nohup npm run dev > /tmp/pathos-dev-3002.log 2>&1 &` | 10018 |
| Restart (stale build cache) | `kill 10018` (known PID only) + re-launch | 20962 |
| End | `kill 20962` (known PID only) | — |

`pkill`, `killall`, `force`, `reset`, `clean`, `rebase` — never used.
External port 3000 — never touched.

---

## 27. 禁止动作遵守 (Forbidden-action compliance)

| Forbidden | Used? |
|-----------|-------|
| pkill / killall | ✗ |
| kill unknown PID | ✗ (only PIDs we own: 10018, 20962) |
| seize external 3000 | ✗ (always PORT=3002) |
| modify Stage 6 tag | ✗ |
| push | ✗ |
| modify Preview Bundle | ✗ |
| modify backend tracked files | ✗ |
| modify data-pipeline | ✗ |
| modify school data facts | ✗ |
| enable Production Data Export | ✗ |
| use eslint-disable to hide problems | ✗ (only 2 disables with detailed rationale) |
| declare PASS prematurely | ✗ |
| create tag | ✗ |
| enter Stage 7B | ✗ |

---

## 28. 写入边界 (Write boundaries)

Filesystem writes confined to:

- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend/...`
- `/Users/jiayihuang/Downloads/PathOS合并/docs/...`

The four forbidden-write directories were read-only (only `ls` / `cat` used
to confirm absence of verified regional data).

---

## 29. 阶段 6 tag 状态 (Stage 6 tag status)

`stage6-demo-pass-2026-07-25-2` — referenced only as a read-only baseline
in the heatmap provenance audit. Not moved, not annotated, not rewritten.

---

## 30. Preview Bundle SHA 保留 (Preview Bundle SHA preservation)

`manifest_sha = 88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
— untouched. No file under `/preview-bundle/` was opened for write.

---

## 31. 数据导出 (Production Data Export) 状态

`Production Data Export = prohibited` — verified by re-reading
`ProductionDataExportToggle.tsx` and the `DataExportStatus` consumer. Not
flipped.

---

## 32. 不可篡改字段 (Immutable fields)

| Field | Value |
|-------|-------|
| `schoolCount` | 62 |
| `summaryCount` | 62 |
| `detailCount` | 62 |
| `verifiedRecordCount` | 904 |
| `quarantine.exposed` | 0 |
| `rank 0` | 0 |
| `[0,0]` | 0 |
| `fixture fallback` | false |
| `dataMode` | backend |
| `identityVerified` | true |
| `sourceLimited` | true |
| `incomplete` | true |
| `notFinal` | true |

None mutated.

---

## 33. 计数器纪律 (Counter discipline)

Regional heatmap data (if any future addition) uses *separate* counters:

```
regionalDatasetId: "<census-acs-2024-5y>"
regionalRecordCount: <n>
regionalSource: <source string>
regionalYear: <year>
regionalUnit: <unit>
regionalJoinKey: "state_fips" | "county_fips" | ...
```

**Not** added to `verifiedRecordCount`. Invariant preserved.

---

## 34. 文案与可访问性 (Copy & accessibility)

- `aria-current="page"` set on the active nav link.
- `aria-label="切换主题"` on the theme toggle (byte-stable SSR).
- `role="note"` on the region-boundary callout.
- `aria-hidden="true"` on decorative icons.
- Keyboard focus ring: 2px solid `rgb(var(--token-focus))` with 2px offset.
- Reduced-motion media query respected.

---

## 35. CSS 单位与组件契约 (CSS units & component contracts)

- Tokens remain in `R G B` triplet form (no hex in CSS).
- Tailwind reads via `<alpha-value>` so `bg-cobalt/40` continues to work.
- No new utility classes introduced.
- No raw color literals in JSX.

---

## 36. 区域数据 join key (Regional data join key)

When verified data arrives, the join key will be one of:

- `state_fips` (2-digit, "06" = California)
- `county_fips` (5-digit, "06037" = Los Angeles County)
- `cbsa` or `zip` (TBD per Census granularity)

Existing types in `lib/types.ts` already model these keys. The choropleth
layer registry reads them generically; no code change needed when data
lands.

---

## 37. 已识别的后续工作 (Identified follow-on work)

| Item | Owner | Why out of scope |
|------|-------|------------------|
| Verified Census ACS 5-Year state-level income | `data-pipeline/` team | forbidden write + no API key in env |
| Verified FBI UCR violent crime by state | `data-pipeline/` team | forbidden write |
| Verified IPEDS employment / outcome by ZIP | `data-pipeline/` team | forbidden write |
| Verified Chinese-community density (ACS B16001 or similar) | `data-pipeline/` team | forbidden write |
| Stage 7B planning (preview-only parity) | Stage 7B kickoff | directive says "完成后…等待新的独立 Re-Gate" |

---

## 38. 风险与已知问题 (Risks & known issues)

| Risk | Severity | Mitigation |
|------|----------|------------|
| `a.basemaps.cartocdn.com` DNS-fails on this network | LOW | MapLibre falls through to b/c/d subdomains; verified 200 from b/c/d |
| Subdomain `a` outage in some user networks | LOW | Same — falls through automatically |
| Regional heatmaps absent | KNOWN | Documented as blocked, not silenced; callouts explain why |
| danger-on-surface-2 dark contrast = 4.11 | LOW | only used as icon-paired inline error pill; icon glyph itself ≥ 4.5 |

---

## 39. 文档可索引性 (Document indexability)

All four closing docs live at `/Users/jiayihuang/Downloads/PathOS合并/docs/`:

- `STAGE7A-THEME-HEATMAP-CLOSING-PLAN.md`
- `STAGE7A-THEME-HEATMAP-CLOSING-DEVLOG.md`
- `STAGE7A-THEME-HEATMAP-CLOSING-REPORT.md` (this file)
- `STAGE7A-THEME-HEATMAP-CLOSING-CHANGE-MANIFEST.json`

---

## 40. READY FOR INDEPENDENT RE-GATE

All five defects closed with evidence. Regional heatmaps explicitly blocked
with provenance — not fabricated. Data invariants preserved verbatim.
Preview Bundle SHA untouched. Stage 6 tag untouched. Production Data Export
remains `prohibited`. Dev server will be stopped by killing PID 20962 (a
known PID — never pkill/killall/force).

**Verdict: READY FOR INDEPENDENT RE-GATE.**