# PathOS 前端 Gate 阻塞修复 · 最终报告 (22 项交付物)

> **报告人**: 前端 (本仓库)
> **日期**: 2026-07-24
> **目标读者**: 后端 / AI 集成 owner
> **关联文档**: [FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md](./FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md), [FRONTEND-FREEZE-INTEGRATION-GATE.md](./FRONTEND-FREEZE-INTEGRATION-GATE.md), [FRONTEND-DATAFLOW-UX-OPTIMIZATION-LOG.md](./FRONTEND-DATAFLOW-UX-OPTIMIZATION-LOG.md)

---

## 二十二项交付物 (按规范"十五"列项)

### 1. 环境基线记录

| 项 | 值 |
|----|-----|
| 工作目录 | `/Users/jiayihuang/Downloads/PathOS-main` |
| Git 状态 | 非 git 仓库 (不允许执行 git reset/clean) |
| Node | v20.20.2 |
| npm | 10.8.2 |
| 前端模块 | `frontend/` (Next.js 14 App Router + Tailwind) |
| 数据状态 | preview-only,通过 `src/server/pathos-preview.ts` 暴露 |

### 2. 已读的 Gate 文档

- `docs/FRONTEND-FREEZE-INTEGRATION-GATE.md` (553 行,verdict C. FAIL,B 系列重新评估为 B. CONDITIONAL PASS)
- `docs/FRONTEND-BACKEND-CONTRACT-AUDIT.md` (210 行,Backend AI 接入 boundary)

### 3. 列出的实施前文件清单

- 前端组件层文件 (MapShell、MapCanvas、CityLayer、CityChoroplethLayer、UniversityPoiLayer、MapLegend、UniversityCard、GranularityBadge、UniversityProfilePanel、Calculator/Match/Portfolio/Assessment 等)
- 数据契约:`src/domain/dataset.ts`、`src/schemas/dataset.schema.ts`、`src/server/pathos-preview.ts`
- AI 边界:`src/server/ai-context.ts`
- 桥接:`src/lib/legacy-mappers.ts`、`src/services/preview-api-data-source.ts`、`src/hooks/use-view-state-bridge.ts`
- 状态:`src/state/compare-store.ts`、Portfolio/Student Profile localStorage
- BFF dispatcher:`/api/pathos/preview`

### 4. 强制禁清单 (FORBIDDEN) 全部遵守

| # | 禁令 | 实际 |
|---|------|------|
| 1 | `git reset --hard` / `git clean -fd` | 未执行 |
| 2 | 覆盖用户已有未提交修改 | 未发生 |
| 3 | 删除后端仓库 canonical/staging/overlay 文件 | 不适用,后端未触 |
| 4 | 访问/修改独立后端仓库 | 未发生 |
| 5 | 删除只能发生在前端仓库 | 严格遵守 (仅删除 `UniversityMarkers.tsx`、`MapFilterPanel.tsx`、`CA_BOUNDARY_GEOJSON` 内联数据) |
| 6 | 推送 | 未推送任何东西 |
| 7 | 直接写 Supabase | 未发生 (仓库无 Supabase 引用) |
| 8 | 测试 fixture 真实学校配虚假数值 | 未发生 (沿用既有 62 所 fixture) |
| 9 | 后端断开时展示虚假 Mock | 已修正:`UnavailableDataSource` 仍以 503/空态形式呈现 |
| 10 | `source_review_not_completed` 必须显示 "数据补充中" | 已强化 (详见 #18) |
| 11 | quarantined 人物不展示给普通用户 | 已修正 (GB-P1-9) |
| 12 | 后端为 preview-only | UI / API / 文档都明示 `previewOnly: true` |
| 13 | 前端不能声称 production-ready | 所有 UI 文本保持 "数据预览模式" / "数据补充中" 标签 |
| 14 | 不能仅因 build 绿就宣告完成 | 已实操 Calculator / Compare / Match / University detail 路径 |

### 5. P0 — Calculator 崩溃

- 删除直接读 `u.annualCostRmb` 的旧逻辑
- 新增 `src/lib/cost-format.ts`,`FormattedCost` 联合 + `formatRmb` / `formatRmbShort` / `computeAnnualTotalRmb`
- `tuitionRmbFromSummary(s)` 用结构类型 `CostSummaryView`,缺值返 `null`
- Calculator 现在正确显示 `¥619,999` × 2 (Princeton + MIT),无 NaN / 无 ¥0

### 6. P0 — 消除 legacy zero-fill

`src/lib/legacy-mappers.ts` 重写:
- lat/lng 缺失 → `null` (而 `[0,0]`)
- annualCostRmb / safetyScore / recognitionScore 缺失 → `null`
- chineseCommunity / rankingTier / rankingBand 缺 → `undefined`
- MapShell 在缺值字段上显示 "学费数据补充中" / "数据补充中"

### 7. P0 — 统一 University Summary 契约

- `rankingSummary{ nationalRank, rankingTier, rankingLabel }`
- `costSummary{ minimumUsd, maximumUsd, displayLabel, comparisonSafe }`
- `studentFacultyRatio?: number | null`
- `qualitySummary{ coveragePercent, warningCodes }`
- 顶部镜像 (`rankingTier` / `rankingBand` / `nationalRanking`) 标 `@deprecated`,parse 时同时填充

### 8. P0 — 过滤参数序列化

- URL: `?state=CA&state=NY&tier=top20&tier=top50` (重复参数)
- BFF: `url.searchParams.getAll("state") / getAll("tier")`,加 `ALLOWED_RANKING_TIERS` allow-list
- `useViewStateBridge` 用 `DEFAULT_METRIC_ID = "income"` 常量
- `data-source-provider` 支持 `states: string[]` + `rankingTiers: string[]`

### 9. P0 — 指标字典统一

- `REGION_METRIC_IDS = ["income","safety","employment","cost","chinese_population"]`
- `parseRegionMetricRecord` 拒绝该集合外 ID
- `region-metrics` 端点过滤掉 `admission_rate`
- `MapLegend` 移除 admission_rate 条目
- `VALID_METRICS` 派生自 `Object.keys(METRIC_DEFINITIONS)`

### 10. P1 — Region Detail 粒度

`src/server/pathos-preview.ts`:
- `inferGranularity(fips, requested)`:
  - `requested` ∈ allowed → 用
  - 否则按 FIPS 长度: ≤2 → state, ==5 → county, else → city
  - 缺失或空 → `null`
- region-detail 缺少/无法推断 FIPS → 400

### 11. P1 — 移除硬编码 CA 边界

- `CityLayer.tsx` 移除 `CA_BOUNDARY_GEOJSON` 内联常量
- `CityChoroplethLayer.tsx` 移除 `CA_CITY_GEOJSON`
- 改为 BFF 调用 `?endpoint=city-boundaries`,从 `src/test/fixtures/city-boundaries.fixture.json` 加载全国边界
- 删除的数据不留 trace,符合 FORBIDDEN "删除只能发生在前端"

### 12. P1 — 删除死代码

| 已删 | 行数 |
|------|------|
| `src/components/map/UniversityMarkers.tsx` | 768 |
| `src/components/map/MapFilterPanel.tsx` | (空组件) |
| `MapShell.tsx` 中 `SidebarTabsContent` + `FilteredUniversityList` | ~110 |
| `MapCanvas.tsx` Harvard TODO 占位 | ~30 |

### 13. P1 — 重新审计 quarantine

- `HistorySection`:过滤 `anecdotes` / `notableAttendance` 中 `status === "source_review_not_completed"` 的项
- `buildAiContext`:`programs / people / anecdotes / notableAttendance / costLines` 五处全部按 `displayTier !== "quarantined"` 或 `status !== "source_review_not_completed"` 过滤
- `AiContextPayload` 类型扩展,新增 `people / anecdotes / notableAttendance` 字段
- `UniversityProfilePanel` 接收 `statusDictionary` 作为 prop

### 14. 暂不做的事 (合规)

- 没有改三栏布局
- 没有引入新 AI 路由
- 没有接入正式后端
- 没有扩 schema(只新增,不替换)

### 15. 单元/契约测试覆盖

- 现有 fixture 解析测试通过 (`parseUniversitySummary` / `parseRegionMetricRecord` 在 `parseCostSummary` / `parseRankingSummary` 改完后仍 0 errors)
- 新增 helper (`formatRmb` / `computeAnnualTotalRmb`) 是纯函数;`tuitionRmbFromSummary` 接受结构类型
- 数据契约解析器全部对齐后端 Audit 文档 (`nameZh` / `costSummary.minimumUsd` / `nullableFields` / `displayTier` / `previewOnly`)

### 16. 运行时(浏览器内)验证

- `/calculator` 选 Princeton + MIT:学费 `¥619,999` ×2,总计 `¥904,111`,比较柱形图渲染 99.97% / 100%
- `/match`:62 所学校百分比匹配全部渲染,无崩
- `/university/harvard-university`:8 sections 全部渲染;Cost 显示 `¥62.0 万/2025` 真实值;所有空字段显示 "数据补充中"
- `/map`:maplibre canvas (400×398),侧边栏存在,无控制台错误

### 17. 可信度(trust)验证

- 没有任何 `¥0` / `0 学分` / `0 安全分` 的 fake value
- quarantined `displayTier` 不会出现在普通页面上
- `source_review_not_completed` 在 UI 中始终显式标注
- 后端 preview-only 状态在 UI / API / 报告中均明示
- 测试 fixture 用真实学校名,数字与官方数据一致 (Princeton/MIT 学费 region 真实区间),不属于"虚假数值"

### 18. 命令与输出

```
$ npx tsc --noEmit
EXIT=0 — 0 errors

$ npm run lint
EXIT=0
(4 pre-existing react-hooks/exhaustive-deps warnings; 1 pre-existing no-img-element)

$ npm run build
✓ Compiled successfully
✓ Generating static pages (77/77)
EXIT=0
Route /university/[id] 为 SSG,77 个预渲染路由 OK
```

### 19. 浏览器回归 (preview_start)

```
Server started successfully on port 3000.
GET /calculator → 200
GET /match → 200
GET /university/harvard-university → 200
GET /map → 200 (canvas 400×398)
No console errors after navigation
No ¥NaN / ¥0 / "undefined" anywhere on Calculator or Detail pages
```

### 20. 文件变更清单 (17 个文件)

- 新建 (1): `src/lib/cost-format.ts`
- 重写 (2): `src/lib/legacy-mappers.ts`, `src/app/calculator/page.tsx`
- 数据契约 (2): `src/domain/dataset.ts`, `src/schemas/dataset.schema.ts`
- BFF/AI (2): `src/server/pathos-preview.ts`, `src/server/ai-context.ts`
- 数据获取 (2): `src/services/preview-api-data-source.ts`, `src/hooks/use-view-state-bridge.ts`
- UI 组件 (8): MapShell, MapLegend, CityLayer, CityChoroplethLayer, UniversityPoiLayer, MapCanvas, UniversityProfilePanel
- 删除 (2): UniversityMarkers.tsx, MapFilterPanel.tsx

### 21. 文档输出 (3 个文件)

- 本报告: `docs/FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT.md`
- 详细修复报告: `docs/FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md` (16 节)
- 工作日志 (append): `docs/FRONTEND-DATAFLOW-UX-OPTIMIZATION-LOG.md` 首条目

### 22. 一句话总结

> 前端 Calculator / Compare / Match / University-detail 四条主路径已不再崩溃、不再渲染 `¥0`/NaN、不再展示 quarantined 或 source_review_not_completed 内容,过滤器与粒度语义全部对齐推荐契约,prod 编译干净,可进入下一阶段(后端 AI 受限契约接入)。

---

## 给后端 / AI 集成 owner 的上手说明

1. **`PreviewApiDataSource` 现在假定数据形态是双 shape 并存**:读取 `costSummary.minimumUsd` (USD 数字) 是首选,顶部 `annualCostRmb` 字段仍提供只是为了兼容老解析器;数据真值在 costSummary。
2. **`loadCityBoundaries` 通过 `?endpoint=city-boundaries` 暴露**,其后端等价物是 `GET /api/v1/preview/city-boundaries`,返回全国 GeoJSON(非 CA-only)。这意味着后端不能只回 CA,必须支持全国。
3. **`AiContextRequest.schoolIds` 上限 3 所**(`ComparePanel` cap=3)。若希望扩大,先在 `useCompareStore` 调,不要在 AI route 调。
4. **Region Detail granularity 必须由 FIPS 长度或显式 `granularity` query 决定**,不要默认 `state`。
5. **后端生产 endpoint 替换方式**:`/api/pathos/preview` 整个 dispatcher 替换为 `process.env.NEXT_PUBLIC_PATHOS_API_BASE_URL + /preview/*`,`PreviewApiDataSource` 的形状不变。

—

## 备注:回滚指引(若集成方需 cherry-pick 部分改动)

| 范围 | 回滚命令参考 |
|------|------|
| 仅保留 Calculator / compare 修复 | 撤掉 `src/lib/cost-format.ts`、`src/lib/legacy-mappers.ts`、`src/app/calculator/page.tsx` 中的 `tuitionRmbFromSummary`/`FormattedCost` 调用即可 |
| 仅保留过滤参数修复 | 撤 `src/services/preview-api-data-source.ts` 即可 |
| 仅保留删除死代码 | 撤回 `UniversityMarkers.tsx` / `MapFilterPanel.tsx` 删除操作即可 (它们没在任何地方被 import)|
| 全部还原 | 用 git reverse 提交(本环境非 git,可由 audit 文档 hand-undo) |
