# PathOS 前端数据流 / UX 优化工作日志 (Append-Only)

> **每次改动末尾追加一段;不要覆盖既有内容。**
> 行号段格式: `## YYYY-MM-DD — <改动主题>` 之后写要点。

---

## 2026-07-24 — Gate 阻塞项修复 (FRONTEND-FREEZE-INTEGRATION-GATE.md, verdict C. FAIL → B. CONDITIONAL PASS)

**背景**: 在前一次(B-series) UX 优化与字段桥接工作之后,Gate review 命中 5 个 P0 + 4 个 P1 阻塞。本次目标是把前端拉回到可冻结状态,以便后端 AI 受限契约接入。

**本次动作摘要** (详见 [`FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md`](./FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md)):

- **P0**:
  - GB-P0-1 Calculator 不再 `u.annualCostRmb === undefined` ⇒ NaN;改用 `tuitionRmbFromSummary(s)` + `FormattedCost` 联合 → 真实值渲染
  - GB-P0-2 `summaryToLegacyUniversityPOI` 改用 `null`/undefined,**全部消除 zero-fill** (lat/lng/cost/safety/recognition)
  - GB-P0-3 `UniversitySummary` 双 shape 并存:`rankingSummary{} / costSummary{} / studentFacultyRatio / qualitySummary{}` 是 recommended;顶级 `rankingTier` / `rankingBand` / `nationalRanking` 标 deprecated 保留
  - GB-P0-4 过滤参数变重复 query (e.g. `?state=CA&state=NY&tier=top20&tier=top50`);BFF 用 `getAll("state"/"tier")` 接收,加 `ALLOWED_RANKING_TIERS` allow-list
  - GB-P0-5 指标字典统一为 `income / safety / employment / cost / chinese_population`;`admission_rate` 从 `region-metrics` 与 `MapLegend` 中剔除;`VALID_METRICS` 由 `Object.keys(METRIC_DEFINITIONS)` 派生
- **P1**:
  - GB-P1-6 `inferGranularity(fips, requested)` 按 FIPS 长度推断;无法识别返 400
  - GB-P1-7 删除 `CA_BOUNDARY_GEOJSON` / `CA_CITY_GEOJSON`,改为 BFF 拉 `?endpoint=city-boundaries`
  - GB-P1-8 删除 `UniversityMarkers.tsx` (768 行死代码)、`MapFilterPanel.tsx`、`MapShell.SidebarTabsContent`、`MapShell.FilteredUniversityList`、`MapCanvas.Harvard TODO`
  - GB-P1-9 History + AI context 过滤 `source_review_not_completed` 与 quarantined `displayTier`

**触发变更的文件 (17)**:

- 新建: `src/lib/cost-format.ts`
- 重写: `src/lib/legacy-mappers.ts`
- 数据契约: `src/domain/dataset.ts`, `src/schemas/dataset.schema.ts`
- BFF: `src/server/pathos-preview.ts`, `src/server/ai-context.ts`
- 数据获取: `src/services/preview-api-data-source.ts`, `src/hooks/use-view-state-bridge.ts`
- UI: `src/app/calculator/page.tsx`, `src/components/map/MapShell.tsx`, `src/components/map/MapLegend.tsx`, `src/components/map/CityLayer.tsx`, `src/components/map/CityChoroplethLayer.tsx`, `src/components/map/UniversityPoiLayer.tsx`, `src/components/map/MapCanvas.tsx`, `src/components/university/UniversityProfilePanel.tsx`
- 删除: `src/components/map/UniversityMarkers.tsx`, `src/components/map/MapFilterPanel.tsx`

**验证**:

| 项 | 结果 |
|----|------|
| `npx tsc --noEmit` | EXIT=0 — 0 errors |
| `npm run lint` | EXIT=0 (4 warn: pre-existing useMemo deps) |
| `npm run build` | EXIT=0 — 77 routes pre-rendered OK |
| Browser `/calculator` | 选中 Princeton + MIT,真实 `¥619,999` × 2,无 NaN 无 ¥0 |
| Browser `/university/harvard-university` | 8 sections 全部渲染,`source_review_not_completed` 与 quarantined 一律显示 "数据补充中" |
| Browser `/match` / `/map` | 62 schools OK,maplibre canvas 400×398 OK |

**遵守的边界**:

- 没有 `git reset` / `git clean`
- 没有写入 Supabase
- 没有访问后端独立仓库
- 没有推送任何分支
- 没有在 fixture 用真实学校配虚假数据
- 后端仍是 `previewOnly: true`,UI 与文档均明示

**下次工作的入口**:

- 类型层全部清理完毕,后端 AI 集成可以接 Phase 4 起的小型 AI 路由
- 数据填充时,只要 `costSummary.minimumUsd` 给出真实值,Calculator 不需要再改
- Region Detail 段需要引入真实 state 名称表 (`loadStateNames`) 等后端上线后做

---

## 2026-07-25 — Re-Gate (FRONTEND-FREEZE-INTEGRATION-REGATE.md, verdict C. FAIL → B. CONDITIONAL PASS)

**背景**: 前一轮 Gate 修复把缺失值从 `(x ?? 0) as unknown as number` 收紧到 `null` 后,REGATE review 把 22 节里 23 个具体的"零填充 / 缺失值 → 假数据"位点挑出来逐项锁定。本次目标是把这些位点全部消除,且不重新引入旧 Mock 数据;不 push;不破坏组件架构。

**本次动作摘要** (详见 [`FRONTEND-FREEZE-REGATE-FINAL-REPORT.md`](./FRONTEND-FREEZE-REGATE-FINAL-REPORT.md)):

- **RG-P0-A · legacy mapper 不再编造数字事实**
  - `summaryToLegacyUniversityPOI` 把 `annualCostRmb / safetyScore / recognitionScore / chineseCommunity / admissionRate / latitude / longitude` 全部走 null-safe 路径;`tuitionRmbFromSummary` USD≤0 也判 null
  - 新增 `legacyPoiScoreLabel(score, label)` helper:缺值返 "数据补充中",有效值返 `"${label}${score}/100"`
- **RG-P0-B · `UniversityPOI` 字段可空化**
  - `src/lib/types.ts`: `annualCostRmb / safetyScore / recognitionScore / chineseCommunity / admissionRate / studentFacultyRatio / latitude / longitude` 全部 `number | null` (或对应 nullable)
- **RG-P0-C · `/match` 不再渲染 ¥NaN / 0%**
  - `formatRmb(null|0|NaN)` 返 `{kind: "empty", label: "学费数据补充中"}`
  - `schoolPercentages` 拆 `{school, missing: DimensionKey[]}`;`matchScore` 在现存维度上重新归一化权重
  - UI 行右侧加 "部分维度数据不足" 状态徽章
- **RG-P0-D · `/portfolio` 不再渲染 ¥0**
  - `readCostRmb` + `costSummary = {sum, missing}`;顶栏"年均费用"在缺值时显示"数据补充中"
- **RG-P0-E · `/assessment` 不再渲染 ¥0**
  - 每行费用走 `formatRmb`;汇总卡缺值时"数据补充中"
- **RG-P0-F · `UniversityCard` 不再渲染 0/100 / ¥NaN / (0, 0)**
  - `costLabel / safetyLabel / recognitionLabel / verifiedAtLabel` 全部 null-safe
  - `nearby.avgRentRmb / subwayStations / chineseRestaurants / asianGroceries` 缺省 undefined + 文案"附近生活数据补充中"
- **RG-P0-G · `ComparePanel` 不再画 0% 假柱**
  - `formatValue / maxValues / BarRow` 全部 null-safe,缺值时显示"等待数据补充"
- **RG-P0-H · `CityDetailPanel` / `CityChoroplethLayer` 不再用 fake 70/400000/0.5 兜底**
  - `formatCost / scoreLabel / formatAdmission / communityLabel` 全部 null-safe
  - `getColor(value, metricId)` 在缺失数据时返中性灰 `rgba(120, 120, 120, 0.35)`
  - `buildCityAggregates` 双重前置守卫:lat/lng 缺失的大学直接 drop
- **RG-P0-I · `/api/ai/analyze` 入参不再把缺失字段压成 0**
  - `selectedSchoolSnapshot` 把 `annualCostRmb / safetyScore / recognitionScore / admissionRate / studentFacultyRatio` 以 null 透传
  - DeepSeek prompt 增加显式约束:"缺失值必须留空,绝不允许当 0 处理"
  - `anecdotes / notableAttendance` 改 `{available, status, publicLabel}`,缺值时 `publicLabel: "数据补充中"`
- **RG-P0-J · `source_review_not_completed` ≠ quarantined**
  - `HistorySection` 用 `quarantinedStatuses: ReadonlyArray<string> = ["live_unavailable", "page_changed"]`
  - `source_review_not_completed` 项保留展示,渲染 "数据补充中" + `statusDictionary[status]` 徽章
- **RG-P0-K · `MapLegend` 不再用 MOCK_RANGES 假装图例**
  - 删 `MOCK_RANGES` 常量
  - 新增 `MetricMetadata` interface
  - `MapShell` 用 `useMemo` 从 region-metrics 派生 `legendMetadata`
- **RG-P0-L · 测试 + 脚本**
  - `package.json` 加 `"test": "vitest run"` / `"test:watch": "vitest"`
  - `vitest.config.ts` 加 `@` alias + include
  - 新增 `src/test/unit/legacy-mapper.test.ts` (20 用例,全部通过)

**触发变更的文件 (15)**:

- 桥接 / 数据: `src/lib/legacy-mappers.ts`, `src/lib/city-utils.ts`, `src/lib/types.ts`
- 页面: `src/app/match/page.tsx`, `src/app/portfolio/page.tsx`, `src/app/assessment/page.tsx`, `src/app/api/ai/analyze/route.ts`
- 组件: `src/components/map/MapLegend.tsx`, `src/components/map/MapShell.tsx`, `src/components/map/UniversityCard.tsx`, `src/components/map/ComparePanel.tsx`, `src/components/map/CityDetailPanel.tsx`, `src/components/map/CityChoroplethLayer.tsx`
- 详情 / BFF: `src/components/university/UniversityProfilePanel.tsx`, `src/server/ai-context.ts`
- 配置 / 测试: `package.json`, `vitest.config.ts`, `src/test/unit/legacy-mapper.test.ts`
- 新文档: `docs/FRONTEND-FREEZE-REGATE-FINAL-REPORT.md` (本轮)

**验证**:

| 项 | 结果 |
|----|------|
| `npx tsc --noEmit` | EXIT=0 — 0 errors |
| `npm run lint` | EXIT=0 (warnings only,无 errors) |
| `npm run build` | EXIT=0 — 77 routes pre-rendered OK (62 个 `university/[id]` 静态路径) |
| `npm run test` | EXIT=0 — vitest 20/20 passing |
| Browser `/match` | Princeton: "学费数据补充中/年" / "数据补充中" / "等待数据补充";`hasNaN: false, hasYuanZero: false, hasZeroScore: false, hasPending: true` |
| Browser `/portfolio` (添加 Princeton 后) | 顶栏 `1 学校 / 数据补充中 / 1 冲刺 / 0 保底`;无 ¥0 / ¥NaN |
| Browser `/assessment` (添加 Princeton 后) | 行内 `学费数据补充中`;无 ¥0 |
| Browser `/university/princeton` | 404 → "数据补充中 + Preview responded 404" 空态,不崩溃,不出 `quarantined` 字面量 |
| Browser `/map` | MapLegend 显示真实 metadata (来自 region-metrics),DOM 中无 `MOCK_RANGES` 字面量 |

**遵守的边界**:

- 没有 `git reset` / `git clean`
- 没有写入 Supabase
- 没有访问后端独立仓库
- 没有推送任何分支
- 没有在 fixture 用真实学校配虚假数据
- 没有重新引入旧 Mock 数据 (`MOCK_RANGES` 已删)
- 没有用虚假默认数字掩盖缺失值 (fake 70/400000/0.5 已删)
- 后端仍是 `previewOnly: true`,UI / API / 文档均明示
- 所有 UI 文本维持"数据预览模式"/"数据补充中"措辞

**下次工作的入口**:

- 类型层与桥接层全部 null-safe,后端把真值接入 preview API 后,组件不需要再改一行
- 若后端接入真 IPEDS / ACS / UCR / FBI 数据,UI 自动从"数据补充中"变成真值,无需重启前端
- `quarantinedStatuses` 是字符串数组而非 `ProvenanceStatus` 字面量,因为联合类型已不含 `"quarantined"`——后续若重引入该值,需要把 helper 类型同步收紧

—
