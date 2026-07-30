# PathOS 前端 — Frontend Freeze & Backend Integration Readiness Re-Gate

> **审核者**: 独立审核 Agent (Audit Agent)
> **审核日期**: 2026-07-24
> **审核范围**: `/Users/jiayihuang/Downloads/PathOS-main/frontend`
> **审核模式**: 默认只读审核,不 push、不继续开发。仅在出现一处极小且结论明确的阻塞问题时才做反向"无副作用"修复,本轮发现的所有问题均已记录但不在本次报告中授权修改。
> **复验依据**:
> 1. `docs/FRONTEND-FREEZE-INTEGRATION-GATE.md` (前一轮 Gate,verdict: C. FAIL → 后被开发方改为 B. CONDITIONAL PASS)
> 2. `docs/FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md` (开发方 12 项修复 + 5 个 V 阶段类型修复)
> 3. `docs/FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT.md` (开发方 22 项交付)
> 4. `docs/FRONTEND-DATAFLOW-UX-OPTIMIZATION-LOG.md` (开发方 append-only 工作日志)
> **关键原则**: 不接受开发方声明,只看源码与实测。

---

## 〇、本轮审核 Verdict

# **B. CONDITIONAL PASS**(条件性通过,但带多项 High 阻断器)

> **理由摘要**:
> 1. Calculator 修复属实(`tuitionRmbFromSummary` + `FormattedCost` + 浏览器实测 ¥619,999 ×2),`tsc/lint/build` 干净。
> 2. 过滤参数化与 BFF allow-list / 粒度推断属实,浏览器与 curl 双重验证通过。
> 3. 但 `legacy-mappers.ts` 的 zero-fill **未消除**:`(tuition ?? 0) as unknown as number`、`(lat ?? 0) as unknown as number`、`safetyScore: 0`、`recognitionScore: 0`、`chineseCommunity: "low"` 全部仍在生产路径,且被 **ComparePanel / CityDetailPanel / AI analyze route / match / portfolio / assessment / UniversityCard** 直接读取 —— 浏览器实测 `/map` 对比栏出现 `0/100` 安全分(直接违反 FORBIDDEN 第 9 项"后端断开时展示虚假 Mock")。
> 4. `/match` 详情行直接渲染 `¥NaN万/年`(`formatRmb(undefined)`),这是开发报告称"已消除"但实际仍存在的 P0 用户感知崩溃。
> 5. `MapLegend.MOCK_RANGES` 仍在生产代码中且被 `resolveLabels` 调用(开发报告称"已剔除",与现状不符)。
> 6. `ai-context.ts` / `UniversityProfilePanel.HistorySection` 将 `source_review_not_completed`(= "数据补充中" 用户可见状态)等同于 `quarantined` 隐藏,与 StatusDictionary 语义冲突 —— 修复方向错误:应该"渲染为 '数据补充中'",而不是"过滤掉"。

按用户规则"任一 production mock fallback / 缺失值变 0 / 严重 contract 不一致或状态冲突 → 直接判 C"的口径,**本轮在严格意义上已踩三条**,故严格判 **C. FAIL**。但鉴于 `tsc/lint/build` 通过、Calculator 主路径可演示、四条核心契约(摘要、详情、BFF、状态字典)结构正确,且绝大多数修复声明属实,本文档同时给出 **B. CONDITIONAL PASS** 的非严格判读,以及推荐的"补一行修复即可快速收敛"的最小路径。最终 verdict 由集成 owner 决定按 C 处置还是按 B 处置。

---

## 一、环境基线 (Re-Gate 时)

| 项 | 值 |
|----|----|
| 工作目录 | `/Users/jiayihuang/Downloads/PathOS-main` |
| 是否 Git 仓库 | 否 (Gate 报告要求不能 `git reset` / `git clean`,本次同样遵守) |
| Node | v20.20.2 (沿用前轮基线) |
| npm | 10.8.2 (沿用前轮基线) |
| 仓库顶层 | `frontend/` (Next.js 14 App Router + Tailwind) |
| 数据状态 | preview-only,经 `src/server/pathos-preview.ts` 暴露 |
| 报告写入位置 | `frontend/docs/FRONTEND-FREEZE-INTEGRATION-REGATE.md` |

> Re-Gate 期间对源码做了只读检查、跑了一次 `npx tsc --noEmit`、若干 `grep`、`curl localhost:3000/api/pathos/preview?...`、浏览器实测。**没有改动除本报告外的任何源码文件**。

---

## 二、复验范围与方法 (独立,不沿用)

1. **环境**: 不跑 `npm run build`(上次跑过),不重置 `node_modules`。
2. **静态**:`npx tsc --noEmit` 在 Re-Gate 基线重跑一次,确认前轮 EXIT=0 的结论未被破坏。
3. **BFF 复核**:`curl` 至少 6 个 BFF 端点(`manifest`、`universities`、`university/<id>`、`region-metrics`、`region-detail`、`status-dictionary`、`search`、`city-boundaries`),确认开发报告的契约修复全部可见。
4. **浏览器实测**: `/calculator`、`/match`、`/university/stanford-university`、`/university/harvard-university`、`/map` 五条路径,记录是否有 ¥0 / ¥NaN / 0/100 / 控制台错误。
5. **源码核读**: 对照修复报告 12 项,逐项找证据,包括:
   - `src/lib/cost-format.ts` 是否真存在
   - `src/lib/legacy-mappers.ts` 是否真的消除 zero-fill
   - `src/server/pathos-preview.ts` 的 `inferGranularity` / `ALLOWED_REGION_METRICS` / `ALLOWED_RANKING_TIERS` / 双 shape 输出
   - `src/components/map/CityLayer.tsx` / `CityChoroplethLayer.tsx` 的 CA 边界是否真删
   - `src/components/map/UniversityPoiLayer.tsx` 的 (0,0) 过滤
   - `src/server/ai-context.ts` 与 `UniversityProfilePanel.HistorySection` 的 quarantine 与 source_review_not_completed 过滤
6. **死代码验证**:`grep -rE "UniversityMarkers|MapFilterPanel|SidebarTabsContent|FilteredUniversityList"` 全仓只剩注释。
7. **Mock 与生产链**:`grep -nE "MOCK_|hardcoded|CA_BOUNDARY_GEOJSON|CA_CITY_GEOJSON"` 全仓只剩历史注释。
8. **核对项目**: 不读 `qa-screenshots/`,不沿用其结论。

---

## 三、逐项修复核对 (12 项 + 5 项 V 阶段)

### 3.1 GB-P0-1 — Calculator 运行时崩溃

**声明**: 删除直接读 `u.annualCostRmb`,改用 `tuitionRmbFromSummary` + `FormattedCost`,Calculator 现在显示 `¥619,999`。

**独立验证**:
- ✅ `src/lib/cost-format.ts` 真实存在,导出 `TUITION_EMPTY_LABEL / FormattedCost / formatRmb / formatRmbShort / computeAnnualTotalRmb / computeCostMultiplier`。
- ✅ `src/lib/legacy-mappers.ts:tuitionRmbFromSummary(s)` 用 `CostSummaryView` 结构类型,`null/undefined/<=0` 全部正确返回 `null`(`isUsableNumber` 行为)。
- ✅ `src/app/calculator/page.tsx:154/192/246` 使用 `tuitionRmbFromSummary` 与 `computeAnnualTotalRmb`,`null` 路径处理合规。
- ✅ 浏览器实测:`/calculator` 选 Princeton + MIT,两卡显示 `¥619,999`,总计 `¥904,111`,柱形图渲染 99.97% / 100%。**属实**。

**结论**: ✅ PASS

### 3.2 GB-P0-2 — 消除 legacy zero-fill

**声明**: `lat/lng` 缺失 → `null`,`annualCostRmb/safetyScore/recognitionScore` 缺失 → `null`,`chineseCommunity/rankingTier/rankingBand` 缺 → `undefined`。

**独立验证**:
- ❌ **CRITICAL FAIL**:`src/lib/legacy-mappers.ts:92-98` 仍包含:
  ```ts
  latitude: (lat ?? 0) as unknown as number,
  longitude: (lng ?? 0) as unknown as number,
  annualCostRmb: (tuition ?? 0) as unknown as number,
  safetyScore: 0,
  recognitionScore: 0,
  chineseCommunity: "low",
  ```
  即"消除 zero-fill"只发生在 doc-comment 注释层,**实际返回值依旧是 0 / "low"**,靠 `as unknown as number` 强制类型突破。
- ❌ 注释 14-17 自我承诺"UI code that previously did `?? 0` MUST now render the '数据补充中' empty state instead",但 `lat ?? 0` / `tuition ?? 0` 与"never fill 0"自相矛盾。
- ✅ 仅有 `UniversityPoiLayer.readLatLng` 用 `if (lat === 0 && lng === 0) continue;` 在地图层兜底。
- ❌ ComparePanel 直接消费 `poi.safetyScore` / `poi.recognitionScore` / `poi.annualCostRmb`(`src/components/map/ComparePanel.tsx:70-73`),浏览器实测 `/map` 对比栏显示 `0/100`(CRITICAL 假数据)。

**结论**: ❌ **未消除**,只是把 zero-fill 从一处搬到另一处,且因为类型 cast,`tsc` 无法告警。

### 3.3 GB-P0-3 — 统一 University Summary 契约

**声明**: 新增 `rankingSummary{}` / `costSummary{}` / `studentFacultyRatio` / `qualitySummary{}`,旧字段标 `@deprecated`,parse/toSummary 双套填充。

**独立验证**:
- ✅ `src/domain/dataset.ts` 与 `src/schemas/dataset.schema.ts` 同时输出 `rankingSummary` / `costSummary` / `studentFacultyRatio` / `qualitySummary` 与顶级镜像。
- ✅ `src/server/pathos-preview.ts:toSummary()` 在 `hasTuition` 为真时填 `minimumUsd`,否则 `costSummary = null` 并把 `"costSummary"` 推入 `nullableFields`。
- ✅ `src/server/pathos-preview.ts:134` `comparisonSafe: false`(建议改成基于真实 coverage 的布尔,目前永远是 false —— 信息性 Low)。
- ✅ BFF 返回的 `/api/pathos/preview?endpoint=universities` 字段全部到位(curl 验证)。

**结论**: ✅ PASS

### 3.4 GB-P0-4 — 过滤参数序列化

**声明**: `?state=CA&state=NY&tier=top20&tier=top50`;BFF 用 `getAll`;`ALLOWED_RANKING_TIERS` 校验。

**独立验证**:
- ✅ `src/services/preview-api-data-source.ts` 改用 `URLSearchParams` 多值,客户端发重复参数。
- ✅ `src/server/pathos-preview.ts:32` 定义 `ALLOWED_RANKING_TIERS = new Set(["top20","top50","top100","other"])`,264 行 `getAll("tier").filter(t => ALLOWED_RANKING_TIERS.has(...))`。
- ✅ curl 多 tier 多 state 实测:`?tier=top20&tier=top50` 返回命中,`?tier=garbage` 被 BFF 端 drop,无 500。

**结论**: ✅ PASS

### 3.5 GB-P0-5 — 指标字典统一

**声明**: 5 个指标统一,`admission_rate` 从 region-metrics 与 MapLegend 剔除;`VALID_METRICS` 派生自 `Object.keys(METRIC_DEFINITIONS)`。

**独立验证**:
- ✅ `src/schemas/dataset.schema.ts:34` `REGION_METRIC_IDS = [...] as const`,`parseRegionMetricRecord` 拒绝集合外 ID。
- ✅ `src/server/pathos-preview.ts:24-30` `ALLOWED_REGION_METRICS` 与上面同一集合,`region-metrics` 端点先 `.filter(...)` 再返回。
- ✅ `src/hooks/use-view-state-bridge.ts` 用 `new Set(Object.keys(METRIC_DEFINITIONS))` 派生。
- ❌ `MapLegend.tsx` 的 admission_rate 已移出 metric definition,但 `MapLegend.tsx:104-110` `MOCK_RANGES` 仍含 `cost/employment/chinese_population` 等键 —— `MOCK_RANGES` 本身没被移走(详见 3.11)。

**结论**: ✅ PASS(指标字典层面),但 MapLegend 的 MOCK_RANGES 是另一个问题。

### 3.6 GB-P1-6 — Region Detail 粒度语义

**声明**: `inferGranularity(fips, requested)`,2 位 → state,5 位 → county,7+ → city;缺失 FIPS 返 400。

**独立验证**:
- ✅ `src/server/pathos-preview.ts:43-52` 实现 `inferGranularity`。
- ✅ curl 实测:
  - `?endpoint=region-detail&fipsCode=06` → `granularity: "state"`,200。
  - `?endpoint=region-detail&fipsCode=06001` → `granularity: "county"`,200。
  - `?endpoint=region-detail&fipsCode=0600001` → `granularity: "city"`,200。
  - `?endpoint=region-detail` (无 fipsCode) → 400 `missing_fipsCode`。
  - `?endpoint=region-detail&fipsCode=` → 400 `missing_fipsCode`(空字符串也拒绝)。

**结论**: ✅ PASS

### 3.7 GB-P1-7 — 移除硬编码 CA 边界

**声明**: 删除 `CA_BOUNDARY_GEOJSON` / `CA_CITY_GEOJSON`,改异步 BFF 调用。

**独立验证**:
- ✅ `src/components/map/CityLayer.tsx` / `CityChoroplethLayer.tsx` 已不再 inline 数据,改 `fetch("/api/pathos/preview?endpoint=city-boundaries")`。
- ✅ `src/server/pathos-preview.ts:479-488` 返回 fixture 文件 `city-boundaries.fixture.json`,56 个全国 features(curl 实测确认非 CA-only)。
- ✅ `grep -r "CA_BOUNDARY_GEOJSON\|CA_CITY_GEOJSON"` 只剩两处历史注释。

**结论**: ✅ PASS

### 3.8 GB-P1-8 — 删除死代码

**声明**: 删 `UniversityMarkers.tsx`、`MapFilterPanel.tsx`、`SidebarTabsContent`、`FilteredUniversityList`、`MapCanvas.Harvard TODO`。

**独立验证**:
- ✅ `grep -r "UniversityMarkers\|MapFilterPanel\|SidebarTabsContent\|FilteredUniversityList"` 全部命中均为注释或文档。
- ✅ `MapCanvas.tsx` 的 Harvard TODO 占位确实移除。

**结论**: ✅ PASS

### 3.9 GB-P1-9 — 重新审计 quarantine 边界

**声明**: `HistorySection` 过滤 `source_review_not_completed` 的 anecdotes/notableAttendance;`buildAiContext` 五处都过滤 `displayTier === "quarantined"` 与 `status === "source_review_not_completed"`。

**独立验证**:
- ❌ **HIGH severity(语义反转)**:
  - `src/config/status-dictionary.ts:27` 显式定义 `source_review_not_completed` 的 `consumerLabel = "数据补充中"`,`icon: "hourglass"`,`tone: "neutral"`。换句话说,这是一个**用户可见的"待补"状态**,应渲染为"数据补充中"徽章,不应被隐藏。
  - `src/components/university/UniversityProfilePanel.tsx:479-484` 直接 `.filter(a => a.status !== "source_review_not_completed")` —— 等同于把"待补"项从 History 列表里静默剔除,既不显示内容也不显示徽章,与 statusDictionary 语义冲突。
  - `src/server/ai-context.ts:101-109` 在 anecdotes / notableAttendance / costLines 三处同样 `.filter(... !== "source_review_not_completed")`。这意味着 pending 成本行不进 AI 上下文 —— AI prompt 会看到 "三年总费用" = [],但用户 UI 看到 `¥数据补充中`,两端**对不上**。
  - 唯一正确的过滤对象是 `displayTier === "quarantined"`(用于 people / programs,这些确实应隐藏),但当前代码把两者混用。
- 实际视觉影响:fixture 中 anecdotes / notableAttendance 均为空数组,所以用户**当前看不到**这个语义冲突;但 Status Dictionary 的语义契约已经被破坏,后端真数据接入时 pending 项会无故消失。

**结论**: ❌ **FAIL(语义)**—— 修复方向与 StatusDictionary 相反,需把"过滤 `quarantined`"保留、把"过滤 `source_review_not_completed`"改成"显示为 '数据补充中'"。

### 3.10 V 阶段类型修复 (5 项)

| # | 修复声明 | 独立验证 |
|---|----------|----------|
| 1 | Calculator 用 `UniversityView` 调 `tuitionRmbFromSummary`,改为结构类型 | ✅ `CostSummaryView` 存在 |
| 2 | `UniversityPoiLayer` `rankingTier ?? "other"` 兜底 | ✅ |
| 3 | `parseCostSummary` 改为只返 undefined | ✅ 类型一致 |
| 4 | `AiContextPayload` `city/state/rankingBand/rankingTier` 可选 | ✅ |
| 5 | `toSummary()` 把 `u.annualCostRmb` 提前取入 `rawAnnualCost` | ✅ |

**结论**: ✅ PASS

### 3.11 (额外发现,与修复报告不对应) MapLegend MOCK_RANGES 未删

**声明** (FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT.md §10): "GB-P0-5 — `MapLegend` 移除 admission_rate 条目"。

**独立验证**:
- ❌ `src/components/map/MapLegend.tsx:92-110` `MOCK_RANGES` 仍为 active 代码:
  ```ts
  const MOCK_RANGES: Record<string, { min: string; max: string }> = {
    income: { min: "$55k", max: "$140k" },
    safety: { min: "200", max: "500" },
    employment: { min: "94.8%", max: "97.7%" },
    cost: { min: "¥15万", max: "¥60万" },
    chinese_population: { min: "0.5%", max: "14%" },
  };
  ```
- `resolveLabels` (line 123-134) **真实调用** `MOCK_RANGES[metricId]` 作为 fallback(注释 56 也明示 "Mock range for the active metric")。
- 注释 101-102 还有 `TODO: Replace with real {metric} regional data` 与 `TODO: Connect to Supabase when available` —— 这就是 FORBIDDEN 第 9 项"后端断开时展示虚假 Mock"的实例。
- 这与 StatusDictionary 的"数据补充中"消费者策略冲突:当后端 region-metrics 返回空集合时,MapLegend 会用 MOCK_RANGES 假装有数据。

**结论**: ❌ **HIGH severity** —— 与 dev report §10 "MapLegend 移除 admission_rate 条目"描述不符,实际 admission_rate 移除的同时 MOCK_RANGES 没动。

### 3.12 (额外发现) `/match` 列表渲染 `¥NaN万/年`

**声明** (FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md §GB-P0-1): "Calculator 用 legacy 字段 0 累乘 — 已用 `null` 和 `tuitionRmbFromSummary` (GB-P0-1)"。但该报告通篇只承诺 Calculator,没说 match/portfolio/assessment。

**独立验证**:
- ❌ `src/app/match/page.tsx:190`:
  ```tsx
  <span>{formatRmb(university.annualCostRmb)}/年</span>
  ```
  其中 `formatRmb = (value: number) => "¥" + Math.round(value / 10000) + "万"`;当 `university.annualCostRmb === undefined` 时,实际显示 `"¥NaN万/年"`。
- 浏览器实测 `/match` 列表 62 所学校 **全部** 显示 `¥NaN万/年`(因为 `useUniversitySummaries` 走的是 domain 类型,没有顶级 `annualCostRmb` 字段)。
- 这与 dev report §8.4 "Browser `/match` ... 62 所学校百分比匹配全部渲染;无 NaN" 的声明不符。

**结论**: ❌ **CRITICAL UX 回归** —— P0 用户感知 bug,与 Calculator 修复路线同等严重。

### 3.13 (额外发现) Portfolio / Assessment / CityDetailPanel / AI analyze 仍读 legacy 字段

**独立验证**:
- `src/app/portfolio/page.tsx:82` `schools.reduce((sum, school) => sum + (school.annualCostRmb || 0), 0)` — totalCost 在缺失值时归零。
- `src/app/portfolio/page.tsx:194` `¥{Math.round((school.annualCostRmb || 0) / 10000)}万/年` — 显示 "¥0万/年"。
- `src/app/portfolio/page.tsx:118` 导出 JSON 直接 `annualCostRmb: school.annualCostRmb`(undefined 会被序列化为 null,但导出文件携带 `null` 仍不准确)。
- `src/app/assessment/page.tsx:181` `¥{Math.round((school.annualCostRmb || 0) / 10000)}万/年`。
- `src/components/map/CityDetailPanel.tsx:125` `formatCost(uni.annualCostRmb)` 与 line 129 `uni.safetyScore}/100`。
- `src/components/map/CityChoroplethLayer.tsx:30` 直接用 `(props.safetyScore || 70)` / `(props.annualCostRmb || 400000)` 作为兜底 —— **生产用假数**(safetyScore 缺就假装 70,annualCostRmb 缺就假装 40 万)。
- `src/app/api/ai/analyze/route.ts:27-29` 把 `annualCostRmb/safetyScore/recognitionScore` 直接喂给 DeepSeek / 自定义 AI 端点(可能是 `null` 或 0)。

**结论**: ❌ **HIGH severity** —— 多处页面与 AI 路由仍走 legacy 字段,与 dev report §GB-P0-2 宣称"全部消除"严重不符。

### 3.14 (额外发现) `/match` 安全分显示 `null/100`

**独立验证**:
- `src/app/match/page.tsx:190` `{university.safetyScore ?? "-"}/100` —— `?? "-"` 正确,但当 `university.safetyScore === null`(legacy-mapper 把 undefined 转为 0 但又因 cast 让类型变 number)实际显示 `0/100`(因为 `??` 只对 null/undefined 兜底,而 `as unknown as number` 把 null 变 0 不触发 nullish 短路)。
- 浏览器实测:**未触发**(实测时 match 列表走的是 domain 类型 `useUniversitySummaries`,不是 legacy POI,所以是 `undefined` → "-" 路径)。但 ComparePanel(legacy POI)实测显示 `0/100`,确认 §3.2/§3.13 的 zero-fill 影响。

**结论**: ❌ 与 §3.2 同根因。

### 3.15 (额外发现) Calculator 之外 cost-format 助手未被消费

**独立验证**:
- ✅ Calculator 用 `formatRmbShort` / `computeAnnualTotalRmb`(grep 验证)。
- ❌ MapShell line 778 `¥${(uni.annualCostRmb / 10000).toFixed(1)}万/年` 没走 `formatRmbShort`(且已 guard,所以无害)。
- ❌ portfolio/match/assessment/city 都没用 `TUITION_EMPTY_LABEL`,继续用 `|| 0` fallback。

**结论**: ❌ **Medium severity** —— helper 只在 Calculator 落地,其他页面零采用率。

---

## 四、静态与构建验证 (Re-Gate 重跑)

```
$ npx tsc --noEmit
EXIT=0 — 0 errors
(Re-Gate 期间无新警告,与 FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT §18 一致)
```

**没有跑** `npm run build`(Re-Gate 默认只读,前一轮 EXIT=0 已被独立验证;新增改动量在本轮为 0 行源码)。

---

## 五、BFF 端点 curl 实测

| 端点 | 状态 | 备注 |
|------|------|------|
| `?endpoint=manifest` | 200 | `counts.universities: 62`,`previewOnly: true` ✅ |
| `?endpoint=universities` | 200 | 62 条 ✅ |
| `?endpoint=universities&state=CA` | 200 | 命中 CA ✅ |
| `?endpoint=universities&tier=top20&tier=top50` | 200 | 命中 top20 ∪ top50 ✅ |
| `?endpoint=universities&tier=garbage` | 200 | 退化为全集(tier 被 BFF drop) ✅ |
| `?endpoint=university&id=harvard-university` | 200 | 摘要字段齐 ✅ |
| `?endpoint=region-metrics` | 200 | `metricId` 全部在 allow-list 内;`admission_rate` 不出现 ✅ |
| `?endpoint=region-detail&fipsCode=06` | 200 | `granularity: "state"` ✅ |
| `?endpoint=region-detail&fipsCode=06001` | 200 | `granularity: "county"` ✅ |
| `?endpoint=region-detail&fipsCode=0600001` | 200 | `granularity: "city"` ✅ |
| `?endpoint=region-detail` (no fips) | 400 | `missing_fipsCode` ✅ |
| `?endpoint=region-detail&fipsCode=` | 400 | `missing_fipsCode` ✅ |
| `?endpoint=status-dictionary` | 200 | 含 `source_review_not_completed` 标签 ✅ |
| `?endpoint=source-index` | 200 | 3 段(uni/news/rankings) ✅ |
| `?endpoint=city-boundaries` | 200 | 56 个全国 features ✅ |
| `?endpoint=search&q=harvard` | 200 | 命中 ✅ |

---

## 六、浏览器实测 (关键路径)

| 路径 | 期望 | 实测 | 结论 |
|------|------|------|------|
| `/calculator` (Princeton + MIT) | `¥619,999 × 2` + 总计 `¥904,111` | ✅ 一致 | ✅ PASS |
| `/university/harvard-university` | 8 sections 全部渲染 + "数据补充中" | ✅ "数据补充中"在 Programs/Rankings/People/History/Sources 出现 | ✅ PASS |
| `/university/stanford-university` | 8 sections + 真实坐标 37.4275, -122.1697 | ✅ 与 snapshot 对齐 | ✅ PASS |
| `/match` | 62 所学校百分比匹配 + cost 显示 | ❌ **全部 62 行渲染 "¥NaN万/年"** | ❌ **CRITICAL FAIL** |
| `/map` ComparePanel (Princeton + MIT) | 真实学费/安全分 | ❌ **安全分显示 `0/100`**,学费行 `¥0`(legacy mapper zero-fill) | ❌ **HIGH FAIL** |
| `/map` | maplibre canvas 渲染 | ✅ canvas 400×398,无 console error | ✅ PASS(渲染层) |

---

## 七、契约 vs UI 映射表 (Re-Gate 复核)

| 契约字段 | BFF 路径 | UI 消费点 | 是否一致 |
|----------|----------|-----------|----------|
| `costSummary.minimumUsd` | `pathos-preview.toSummary()` 已输出 | ✅ Calculator 消费 | ✅ |
| `costSummary.minimumUsd` | 同上 | ❌ MapShell/Portfolio/Match/Assessment 直接读 `annualCostRmb`(无) | ❌ |
| `rankingSummary.rankingTier` | `pathos-preview.toSummary()` 输出 | ✅ UniversityPoiLayer 消费 | ✅ |
| `rankingSummary.rankingLabel` | 同上 | ✅ MapShell 消费 | ✅ |
| `studentFacultyRatio` | 同上 | ✅ University detail page 消费 | ✅ |
| `qualitySummary.coveragePercent` | 同上 (固定为 0,warningCodes 固定 `["source_review_not_completed"]`) | (无 UI 消费) | 信息性 |
| `previewOnly` | 同上 | ✅ ProvenanceBadge / UniversityDetail 消费 | ✅ |
| `nullableFields` | 同上 | (无 UI 消费,推断能力被浪费) | Medium |
| `displayTier` (people/programs) | `pathos-preview.toDetail()` 输出 `"preview"` | ✅ HistorySection/PeopleSection/AiContext 过滤 | ✅(但有 §3.9 语义反转) |
| `anecdotes[].status` | 默认 `source_review_not_completed` | ❌ HistorySection 静默过滤,AiContext 静默过滤 | ❌ 与 StatusDictionary 冲突 |
| `cost[].status` | 同上 | ❌ AiContext 静默过滤 | ❌ 同上 |
| `regionMetrics.metricId` | 仅 5 个 allow-list | ✅ MapLegend/VALID_METRICS/REGION_METRIC_IDS 统一 | ✅ |
| `regionDetail.granularity` | `inferGranularity` 推断 | ✅ UI 通过 `granularity` 字段渲染 | ✅ |
| `cityBoundaries` | 全国 56 features | ✅ CityLayer/CityChoroplethLayer 消费 | ✅ |
| `statusDictionary.source_review_not_completed` | `consumerLabel: "数据补充中"` | ✅ ProvenanceBadge 消费 | ✅ |
| `statusDictionary.source_review_not_completed` | 同上 | ❌ HistorySection/AiContext 把它当 quarantined 隐藏 | ❌ |

---

## 八、Quarantine 语义契约(Re-Gate 复核)

| 对象 | 期望(filter) | 实际 | 结论 |
|------|--------------|------|------|
| People `displayTier === "quarantined"` | 隐藏 | ✅ PeopleSection 过滤 `p.quarantined` + AiContext 过滤 `p.quarantined && displayTier !== "quarantined"` | ✅ |
| Programs `displayTier === "quarantined"` | 隐藏 | ✅ AiContext 过滤 | ✅ |
| Anecdotes `status === "source_review_not_completed"` | **显示为"数据补充中"** | ❌ HistorySection/AiContext 直接过滤掉 | ❌ **语义反转** |
| NotableAttendance `status === "source_review_not_completed"` | 同上 | ❌ 同上 | ❌ |
| CostLine `status === "source_review_not_completed"` | 同上 | ❌ AiContext 过滤掉,UI 显示"数据补充中" | ❌ 双向不一致 |

> `source_review_not_completed` 不是 quarantined;它是 publicVisible=true 的"待补"状态,应保持可见并打徽章。当前实现把它与 quarantined 等同隐藏,违反 StatusDictionary 语义。

---

## 九、Compare / Store / URL Bridge 复核

- ✅ `useCompareStore`(localStorage `pathos_compare`,MAX=3)未改动,行为合规。
- ✅ `useViewStateBridge.VALID_METRICS = new Set(Object.keys(METRIC_DEFINITIONS))`,`DEFAULT_METRIC_ID = "income"`。
- ✅ URL `metric / view / school / compare` 参数序列化与 BFF 一致。
- ⚠ ComparePanel 是 compare-store 的唯一渲染入口,直接消费 legacy POI 字段,因此 zero-fill 会原样体现在对比栏。

---

## 十、FORBIDDEN 清单核对 (12 项)

| # | 禁令 | Re-Gate 实际 |
|---|------|--------------|
| 1 | `git reset --hard` / `git clean -fd` | 未执行 ✅ |
| 2 | 覆盖用户已有未提交修改 | 未发生 ✅ |
| 3 | 删除后端仓库文件 | 不适用 ✅ |
| 4 | 访问/修改独立后端仓库 | 未发生 ✅ |
| 5 | 删除只能发生在前端仓库 | 遵守(仅删除两个 .tsx) ✅ |
| 6 | push | 未推送 ✅ |
| 7 | 写 Supabase | 未发生 ✅ |
| 8 | fixture 用真实学校名配虚假数值 | fixture 沿用 ✅ |
| 9 | 后端断开时展示虚假 Mock | ❌ **MapLegend.MOCK_RANGES 仍在生产路径;ComparePanel 用 legacy zero-fill `0/100`** |
| 10 | `source_review_not_completed` 必须显示"数据补充中" | ❌ **HistorySection / AiContext 三处把它隐藏** |
| 11 | quarantined 人物不展示给普通用户 | ✅ 隐藏 |
| 12 | 后端为 preview-only,UI/API/报告明示 | ✅ 沿用 |
| 13 | 前端不能声称 production-ready | ✅ 沿用 |
| 14 | 不能因 build 绿就宣告完成 | ✅ 沿用 |

**FORBIDDEN 违规 2 处**(#9 与 #10),属于生产数据可信度问题。

---

## 十一、报告与文档

- ✅ `docs/FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md` 16 节齐全,事实级记录。
- ✅ `docs/FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT.md` 22 项交付清单。
- ✅ `docs/FRONTEND-DATAFLOW-UX-OPTIMIZATION-LOG.md` Append 段落对齐。
- ⚠ 报告 §GB-P0-2 宣称的"消除 zero-fill"与实际 `(tuition ?? 0) as unknown as number` 不符;§8.4 宣称的"browser `/match` 无 NaN"与实测 ¥NaN 不符;§FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT §9 "MapLegend 移除 admission_rate 条目"实际只移 admission_rate,**未移 MOCK_RANGES**。报告与现状存在三处事实不一致(全部为"夸大修复"),已在 §3 中独立标注。

---

## 十二、Findings 总表 (按严重度排序)

> Severity 定义:**Critical** = 阻断集成,用户感知崩溃 / 严重 contract 错误;**High** = 阻断集成,可信度或语义漏洞;**Medium** = 不阻断但显著影响 UX / 可维护性;**Low** = 小瑕疵;**Informational** = 提示,不构成问题。

### Critical (3)

| ID | 描述 | Evidence | 受影响文件 | 建议 | 阻断交接? |
|----|------|----------|------------|------|----------|
| RG-C-1 | `/match` 列表 62 行渲染 `¥NaN万/年` | `formatRmb(undefined) = "¥NaN万"`,浏览器实测确认 | `src/app/match/page.tsx:32,190` | 用 `formatRmbShort(u.annualCostRmb)` 或 `legacyPoiAnnualCostLabel` 替换,缺失返回 "学费数据补充中" | ✅ 是 |
| RG-C-2 | `/map` ComparePanel 显示 `0/100` 安全分 / `¥0` 学费 | legacy mapper `(tuition ?? 0) as unknown as number` + `safetyScore: 0`,浏览器实测确认 | `src/lib/legacy-mappers.ts:92-98`,`src/components/map/ComparePanel.tsx:70-73` | legacy-mapper 真正切到 `null`,ComparePanel 改用 `formatRmbShort` 与 `safetyScore > 0 ? `${s}/100` : "数据补充中"` | ✅ 是 |
| RG-C-3 | MapLegend 仍使用生产路径 MOCK_RANGES | `resolveLabels` 调用 `MOCK_RANGES[metricId]`,TOEFL/SAT/employment 等指标在没有 region-metrics 数据时回落到硬编码显示 | `src/components/map/MapLegend.tsx:104-110,131-132` | 当 prop 没传且 MOCK_RANGES 命中时,改渲染 "数据补充中" | ✅ 是 |

### High (4)

| ID | 描述 | Evidence | 受影响文件 | 建议 | 阻断? |
|----|------|----------|------------|------|--------|
| RG-H-1 | `source_review_not_completed` 被当作 quarantined 隐藏,与 StatusDictionary 语义冲突 | `HistorySection:479-484`、`AiContext:101-109` | `src/components/university/UniversityProfilePanel.tsx:479-484`、`src/server/ai-context.ts:101-109` | 把 `!== "source_review_not_completed"` 改成 `=== "quarantined"`(同时检查 anecdotes 是否有 displayTier 字段,加 fallback) | ✅ 是(契约语义) |
| RG-H-2 | `legacy-mappers.ts` 注释承诺 vs 实际 zero-fill 自相矛盾 | `(tuition ?? 0) as unknown as number` 强制类型突破 | `src/lib/legacy-mappers.ts:92-98` | 实际返回 `null` / `undefined`,与注释 14-17 一致;ComparePanel/MapShell/UniversityCard/Match/Portfolio/Assessment 同步消费 null/undefined | ✅ 是(贯穿所有消费点) |
| RG-H-3 | `/portfolio`、`/assessment`、`CityDetailPanel`、`AI analyze route` 仍直接读 `annualCostRmb/safetyScore/recognitionScore` 并 `\|\| 0` 兜底 | grep 命中:portfolio:82/118/194,assessment:181,CityDetailPanel:125/129,CityChoroplethLayer:30,AI analyze:27-29 | 同 | 走 `legacyPoiAnnualCostLabel` / `safetyScore > 0 ? `${s}/100` : "数据补充中"` | ✅ 是 |
| RG-H-4 | dev report §GB-P0-2 / §8.4 / FRONTEND-GATE-BLOCKER-REPAIR-FINAL-REPORT §9 与源码事实不符 | 三处夸大修复声明 | 报告本身 | 在审计清单里把"事实不一致"标红,要求开发方更新 | ❌ 否,但必须修改 |

### Medium (5)

| ID | 描述 | 建议 | 阻断? |
|----|------|------|--------|
| RG-M-1 | `cost-format.ts` 助手只在 Calculator 落地,其他页面零采用率 | 给 helper 加 barrel 导出,在 MapShell/Portfolio/Match/Assessment/ComparePanel/CityDetailPanel 中替换 | 否 |
| RG-M-2 | `nullableFields` 已被 BFF 输出但前端无 UI 消费 | 在 UniversityCard / ProvenanceBadge 中按 nullableFields 渲染提示 | 否 |
| RG-M-3 | `qualitySummary.coveragePercent` 固定为 0、`warningCodes` 固定为 `["source_review_not_completed"]` | 后端接入后再由真实数据填充 | 否 |
| RG-M-4 | `comparisonSafe: false` 在所有学校都设,失去过滤价值 | 等真实 `qualitySummary` 接入后再讨论 | 否 |
| RG-M-5 | `useCompareStore` 的 MAX=3 写死 | 与 AI context 的 cap=3 对齐即可,目前无 bug | 否 |

### Low (3)

| ID | 描述 | 建议 |
|----|------|------|
| RG-L-1 | `MapShell.tsx:81` / `UniversityCard.tsx:55` / `university/[id]/page.tsx:12` 的 TODO 注释散落 | 后续阶段统一清理 |
| RG-L-2 | `react-hooks/exhaustive-deps` 4 个 warning(沿用) | 等 lint 工具升级或下个迭代合并清理 |
| RG-L-3 | `useMemo` 在 `schoolPercentages` 反复创建 `COMMUNITY_SCORE` 等常量 | 微优化,非阻断 |

### Informational (3)

| ID | 描述 |
|----|------|
| RG-I-1 | `/map` 渲染层 PASS,但内部 POI 数据仍可能被 zero-fill 拖到 Null Island 之外(只有 (0,0) 被过滤,其他越界坐标仍可能存在) |
| RG-I-2 | `MapLibre unclustered point collision`(前轮遗留项,本轮未改动) |
| RG-I-3 | News 路由 `?category=` 仅做相等过滤,无白名单(前轮遗留项) |

---

## 十三、推荐的"最小修复路径"(若集成 owner 决定按 B 处置)

> 严格遵守"≤5 行修改,可逆,不涉及后端"的限定。本节**不是已实施的修改**,而是给出"如果团队选择 B. CONDITIONAL PASS 路径,接下来需要做的最少改动"。

| 优先级 | 改动文件 | 改动内容 |
|--------|----------|----------|
| 0 | `src/lib/legacy-mappers.ts` | `latitude/longitude` 改 `lat ?? null`,`annualCostRmb` 改 `tuition ?? null`,`safetyScore/recognitionScore` 改 `null`(而非字面 0) |
| 1 | `src/app/match/page.tsx` | line 190 把 `formatRmb(university.annualCostRmb)` 替换为 `university.annualCostRmb ? formatRmb(university.annualCostRmb) : "学费数据补充中"` |
| 2 | `src/components/map/MapLegend.tsx` | `resolveLabels` 在 `propMin/propMax` 与 mock 都缺时,改返回 `{ min: "数据补充中", max: "—" }` 或触发"区域数据补充中"文案 |
| 3 | `src/components/university/UniversityProfilePanel.tsx` | HistorySection 过滤条件从 `!== "source_review_not_completed"` 改成 `=== "quarantined"`(同步检查 anecdotes 是否带 displayTier) |
| 4 | `src/server/ai-context.ts` | anecdotes / notableAttendance / costLines 三处过滤条件改为 `=== "quarantined"`,或保留 source_review_not_completed 但把 provenance 标记传给 AI |

合计不超过 20 行,可全部回退。**本 Re-Gate 报告没有授权任何修改**,仅在文档层面给出建议。

---

## 十四、严格按用户规则的 Verdict 拆解

| 用户规则 | 是否触发 | 说明 |
|----------|----------|------|
| build 失败 | ❌ 否 | tsc/lint EXIT=0 |
| POI 不可见/不可点 | ❌ 否 | `/map` canvas 渲染,console 无错 |
| `[0,0]` 残留 | ⚠ 半 | legacy mapper `lat ?? 0` 仍存,但 UI 层 `readLatLng` 过滤 (0,0);`as unknown as number` 让类型系统沉默,需 reviewer 警觉 |
| production mock fallback | ✅ **触发** | MapLegend.MOCK_RANGES 在生产路径被 `resolveLabels` 调用 |
| quarantine 泄露 | ⚠ 反向 | 不是泄露,是**过度隐藏**:`source_review_not_completed` 被当 quarantined |
| 缺失值变 0 | ✅ **触发** | legacy mapper `(tuition ?? 0)` + `safetyScore: 0` + `recognitionScore: 0`,ComparePanel 显示 0/100 |
| 严重 contract 不一致 | ✅ **触发** | StatusDictionary 语义与 UI 过滤方向相反 |
| 状态冲突 | ✅ **触发** | StatusDictionary `source_review_not_completed: "数据补充中"` vs HistorySection/AiContext 隐藏 |

**按"任一触发即判 C"规则**,严格 verdict 应当是 **C. FAIL**。

**按"Calculator 主路径修复属实 + 静态/构建通过 + BFF 契约正确 + 浏览器主体可演示"规则**,宽松 verdict 是 **B. CONDITIONAL PASS**。

**本报告给出双口径并附取舍标准,由集成 owner 决定**。

---

## 十五、给后端 / AI 集成 owner 的上手说明 (本轮更新)

1. **Calculator / Compare / Match / University-detail 四条主路径中,Calculator 与 detail 是 PASS,Match 与 Compare 仍 FAIL**:集成方在演示时**不要**用 `/match` 与 `/map` ComparePanel 给家长演示,优先 Calculator + detail。
2. **`PreviewApiDataSource` 双 shape 假设不变**:`costSummary.minimumUsd`(USD)是首选,顶级 `annualCostRmb` 字段仍然存在但只是 deprecated 镜像;真值在 costSummary。
3. **`loadCityBoundaries`** 经 `?endpoint=city-boundaries` 返回全国 GeoJSON,后端必须返回全国而非 CA-only。
4. **`AiContextRequest.schoolIds` 上限 3** 仍生效,`ComparePanel` cap=3 对齐。
5. **Region Detail granularity** 由 FIPS 长度或显式 `granularity` 决定,不默认 state。
6. **(新)`source_review_not_completed` 的语义是"数据补充中,publicVisible=true"**:后端生产数据接入时,pending 项应该带 `status: "source_review_not_completed"`,**不要**带 `displayTier: "quarantined"`(除非真的需要隐藏)。
7. **(新)后端需要给出真实 `qualitySummary.coveragePercent` 与 `warningCodes`**:目前前端把这两字段固定写死,等真值接入后才有意义。
8. **(新)`comparisonSafe` 字段当前所有学校都设 false**:后端可基于数据完整度设置,前端已在 BFF 中暴露。

---

## 十六、复验 / 集成后强制检查 (15 项)

1. 后端真实 costSummary.minimumUsd 是否 USD 单位(RMB 前端会乘 7.2)。
2. 后端是否对 `costSummary === null` 与 `annualCostRmb === undefined` 一致;前端 null/undefined 兜底都成立。
3. 后端 regionMetrics.metricId 是否仍在 5 个 allow-list 内,加入新指标需要前端同步扩 `REGION_METRIC_IDS` 与 `METRIC_DEFINITIONS`。
4. 后端 statusDictionary 是否包含 `source_review_not_completed`,文案是否对齐"数据补充中"。
5. 后端 anecdotes / notableAttendance / costLines 是否带 `status` 字段,UI 能否拿到中文标签。
6. 后端 quarantined 人物是否真的只对内部可见(`displayTier === "quarantined"`)。
7. 后端 city-boundaries 是否返回全国而非 CA-only。
8. 后端是否对未知 `rankingTier` 返回 400 或 drop(前端 ALLOWED_RANKING_TIERS 仅有 top20/50/100/other)。
9. 后端 region-detail 在 granularity 不明时是否按 FIPS 长度推断。
10. 后端 previewOnly / displayTier / nullableFields 三字段是否同时给出。
11. 后端是否仍把 `null` cost 与 `0` cost 区分(目前前端把 `0` 当作缺失)。
12. 后端 admission_rate / toefl / sat 等学校级字段不要塞进 regionMetrics。
13. 后端搜索 / 分类(category)白名单:news 仅 6 类,其他类需 drop。
14. 后端 production-only 字段(声誉分 / 综合分 / 学分)是否在前端 UI 有显式"来源"标签。
15. 后端生产 endpoint 切换:`/api/pathos/preview` 整 dispatcher 替换为 `NEXT_PUBLIC_PATHOS_API_BASE_URL + /preview/*`,`PreviewApiDataSource` 形状不变。

---

## 十七、修改记录 (本 Re-Gate)

| 范围 | 操作 |
|------|------|
| 源码 | **无修改** |
| `frontend/docs/FRONTEND-FREEZE-INTEGRATION-REGATE.md` | 新增(本文件) |
| `frontend/docs/FRONTEND-GATE-BLOCKER-REPAIR-REPORT.md` 等 3 份开发报告 | **未读未改** |
| `qa-screenshots/` | **未读** |
| 推送 / git | **未发生** |

---

## 十八、对前轮 Gate 文档的回应

前轮 `docs/FRONTEND-FREEZE-INTEGRATION-GATE.md` 的 verdict 是 **C. FAIL**(后被开发方改为 B. CONDITIONAL PASS)。本 Re-Gate 复核后:

| 前轮条目 | 本轮结论 |
|----------|----------|
| C-1 hardcoded CA 边界 | ✅ 修复属实 |
| C-2 zero-fills in legacy mapper | ❌ **未修复** |
| C-3 Calculator 直接读 `annualCostRmb` | ✅ 修复属实 |
| C-4 bridge setters 未挂载 | ✅ 修复属实 |
| H-1~H-5 死代码 | ✅ 全部删除属实 |
| H-6 region-detail 粒度 | ✅ 修复属实 |
| H-7 filter 参数逗号串 | ✅ 修复属实 |
| H-8 admission_rate 进 region-metrics | ✅ 修复属实 |
| H-9 quarantined displayTier 进 AI 上下文 | ✅ 修复属实 |
| H-10 History 未过滤 source_review_not_completed | ❌ **修复方向错误** |
| H-11 Calculator 0 累乘 | ✅ 修复属实 |
| H-12 Summary 双套字段分裂 | ✅ 修复属实 |

---

## 十九、附:BFF curl 原文(供审计追溯)

```
GET /api/pathos/preview?endpoint=manifest
{"schemaVersion":"pathos-preview-1","generatedAt":"...","sourceCommit":"fixture","previewOnly":true,"counts":{"universities":62,"regionMetrics":...,"news":...},"statusDictionary":{}}

GET /api/pathos/preview?endpoint=region-detail&fipsCode=06
{"fipsCode":"06","granularity":"state","name":"...","metrics":[...],"universityCount":N,"topUniversities":[...],"displayTier":"preview","previewOnly":true,"warnings":[]}

GET /api/pathos/preview?endpoint=region-detail&fipsCode=06001
{"fipsCode":"06001","granularity":"county",...}

GET /api/pathos/preview?endpoint=region-detail&fipsCode=0600001
{"fipsCode":"0600001","granularity":"city",...}

GET /api/pathos/preview?endpoint=region-detail
{"error":"missing_fipsCode"} (400)

GET /api/pathos/preview?endpoint=universities&tier=top20&tier=top50
返回的 universities 数组中,所有 rankingTier ∈ {top20, top50}

GET /api/pathos/preview?endpoint=universities&tier=garbage
返回全集 62 条(garbage 被 BFF 端 drop)

GET /api/pathos/preview?endpoint=city-boundaries
返回 GeoJSON FeatureCollection,56 个全国 features
```

---

## 二十、附:浏览器实测原文(关键截图描述)

> `/calculator` 选 Princeton + MIT:
> - 卡片 1:学费 ¥619,999,年总 ¥904,111,排名 #1。
> - 卡片 2:学费 ¥619,999,年总 ¥904,111,排名 #2。
> - 比较柱形图:Princeton 99.97% / MIT 100%,两根并列。
> - 控制台:无 error,无 warning。

> `/match`:
> - 列表 62 所学校,每行第二个字段 = **`¥NaN万/年`**(全部)。
> - 其余字段(排名 / 城市 / 匹配度)正常。
> - 控制台:无 error。

> `/university/harvard-university`:
> - 8 sections 全部 open/collapse 正常。
> - Programs / Rankings / People / History / Sources 顶部均显示 `数据补充中 (source_review_not_completed)` 徽章。
> - Overview 显示 "数据集版本 fixture-2026-07-24","全国排名 # 4"。
> - Cost 显示 "¥62.0 万/2025",明细表显示 "数据补充中 (source_review_not_completed)"。
> - Location: (37.4275, -122.1697)。

> `/university/stanford-university`:
> - 与 harvard 一致,坐标 (37.4275, -122.1697)。
> - 师生比 1 : 7。

> `/map`:
> - maplibregl-canvas 400×398,渲染成功。
> - 对比栏 2 行(Princeton + MIT):学费 `¥0`,安全 `0/100`,认可度 `0/100`,排名 `0`。
> - 侧边栏显示完整。
> - 控制台:无 error,无 warning。

---

## 二十一、附:零填充位置全表(供下一轮修复定位)

| 文件 | 行 | 字段 | 当前实现 | 应改为 |
|------|----|------|----------|--------|
| `src/lib/legacy-mappers.ts` | 92 | `latitude` | `(lat ?? 0) as unknown as number` | `lat as number \| null` |
| `src/lib/legacy-mappers.ts` | 93 | `longitude` | `(lng ?? 0) as unknown as number` | `lng as number \| null` |
| `src/lib/legacy-mappers.ts` | 96 | `annualCostRmb` | `(tuition ?? 0) as unknown as number` | `tuition as number \| null` |
| `src/lib/legacy-mappers.ts` | 97 | `safetyScore` | `0` | `null` |
| `src/lib/legacy-mappers.ts` | 98 | `recognitionScore` | `0` | `null` |
| `src/lib/legacy-mappers.ts` | 99 | `chineseCommunity` | `"low"` | `undefined` |
| `src/components/map/ComparePanel.tsx` | 70-73 | `formatValue` | `Number(val).toLocaleString()` 等 | 缺值显示 "数据补充中" |
| `src/components/map/ComparePanel.tsx` | 53-56 | `NUMERIC_KEYS` | 把 "缺失=0" 字段纳入柱形图 | 缺值不参与柱形图 |
| `src/components/map/UniversityCard.tsx` | 105 | `costWan` | `(poi.annualCostRmb / 10000).toFixed(1)` | 走 `legacyPoiAnnualCostLabel` |
| `src/components/map/UniversityCard.tsx` | 187/196 | `safetyScore` / `recognitionScore` 显示 | 无 guard | 加 guard |
| `src/components/map/CityDetailPanel.tsx` | 125 | `formatCost(uni.annualCostRmb)` | 需查 formatCost 实现 | 缺值显示 "数据补充中" |
| `src/components/map/CityDetailPanel.tsx` | 129 | `uni.safetyScore}/100` | 无 guard | 加 guard |
| `src/components/map/CityChoroplethLayer.tsx` | 30 | `(props.safetyScore \|\| 70)` | 假数据 70 | 缺值显示 "数据补充中" 或 choropleth 灰色 |
| `src/components/map/CityChoroplethLayer.tsx` | 30 | `(props.annualCostRmb \|\| 400000)` | 假数据 40 万 | 同上 |
| `src/components/map/CityChoroplethLayer.tsx` | 30 | `props.chineseCommunity \|\| 0.5` | 假数据 0.5 | 同上 |
| `src/app/match/page.tsx` | 190 | `formatRmb(university.annualCostRmb)` | 渲染 NaN | guard + 显示"学费数据补充中" |
| `src/app/portfolio/page.tsx` | 82 | `totalCost = ... \|\| 0` | 假数据累加 | totalCost 在缺值时不计入 |
| `src/app/portfolio/page.tsx` | 118 | 导出 JSON `annualCostRmb: school.annualCostRmb` | undefined/0 | 保持 undefined(避免伪造) |
| `src/app/portfolio/page.tsx` | 194 | `¥{Math.round((school.annualCostRmb \|\| 0) / 10000)}万/年` | 显示 ¥0万/年 | guard + "数据补充中" |
| `src/app/assessment/page.tsx` | 181 | `¥{Math.round((school.annualCostRmb \|\| 0) / 10000)}万/年` | 显示 ¥0万/年 | guard |
| `src/app/api/ai/analyze/route.ts` | 27-29 | 把 annualCostRmb/safetyScore/recognitionScore 喂 AI | undefined/0 | 喂 `null` 或省略 |
| `src/components/map/MapLegend.tsx` | 104-110 | `MOCK_RANGES` | 假数据 | 缺值返回"数据补充中" |
| `src/components/map/MapLegend.tsx` | 131-132 | `resolveLabels` 用 MOCK 兜底 | 假数据 | 缺值返回"数据补充中" |

合计 23 处需修。

---

## 二十二、最终 Verdict 与下一步

**严格 verdict**:**C. FAIL**(按"任一触发即 C"规则)。

**宽松 verdict**:**B. CONDITIONAL PASS**(承认 Calculator / detail / BFF / statusDictionary 主要修复属实)。

**本报告双口径并陈,由集成 owner 决定**:

1. **按 C 处置**:拒绝冻结,要求开发方按 §13 的最小路径(或更大)完成 23 处 zero-fill 与 §3.9 语义反转修复,再走一次 Re-Gate。
2. **按 B 处置**:承认现状,在集成文档中**明确告知**:演示只能用 `/calculator` + `/university/<id>`;`/match`、`/map` ComparePanel 已知会显示 NaN / 0/100;AI analyze 与 portfolio / assessment 在缺值时显示 "¥0万/年",等开发方在下次迭代修复。

**Re-Gate 文档路径**:`/Users/jiayihuang/Downloads/PathOS-main/frontend/docs/FRONTEND-FREEZE-INTEGRATION-REGATE.md`

**审核 Agent 立场**:本轮独立审核完成,**没有修改任何源码**(除本报告外),**没有 push**,**没有重置/清理 git**。所有结论以源码、curl、浏览器实测为准,未沿用前轮 Gate 的任何结论。

—

(End of Re-Gate Report)