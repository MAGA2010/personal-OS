# Frontend Freeze & Backend Integration Readiness Gate

> **审计范围**：`/Users/jiayihuang/Downloads/PathOS-main/frontend`
> **审计目标**：判定当前前端是否可作为稳定基线（Freeze）冻结；后端控制 AI 是否可被授予有限前端修改权；前端是否已具备接入真实后端 Preview API 的能力。
> **审计日期**：2026-07-24
> **审计模式**：默认只读审核；不 push、不重构、不扩展功能；除本报告外不写源码。
> **总判决**：**C. FAIL**（关键运行时阻塞：`/calculator` 页面崩溃 + 缺失值"变 0"污染范围超出地图子模块）

---

## 1. 总判决（Verdict）

| 维度 | 判定 | 关键依据 |
|---|---|---|
| **总体判决** | **C. FAIL** | `/calculator` 页面 `TypeError` 崩溃（实测复现）；多个生产页面将缺失数值以 `0` 呈现（calculator/assessment/portfolio/match）；BFF `tier/tiers` 参数契约不一致；多文件硬编码 geometry 与 mock 数据 |
| **可冻结（Freeze）** | **否** | 在以下阻断项修复前不可冻结：CR-01 / CR-02 / CR-03 |
| **可授权 AI 有限修改权** | **否（白名单见 §6）** | 当前允许的修改边界见 §6；在 §10 列出的问题未解决前，AI 不应获准修改 |
| **可对接真实后端 Preview API** | **否（条件具备）** | 契约层（§7）已基本成型，但 BFF ↔ 客户端 query 参数未对齐；summary 缺少 detail-only 字段导致多个页面"读不到"正确字段 |

---

## 2. 审计基线（不可变证据）

- **目录**：`/Users/jiayihuang/Downloads/PathOS-main/frontend`
- **顶层 Git**：未初始化（`git rev-parse --show-toplevel` 报错 "fatal: not a git repository"）
- **分支**：无；**HEAD**：无
- **Node**：`v20.20.2`
- **npm**：`10.8.2`
- **包名（package.json）**：`beijing-advisory-mvp`（与 PathOS 品牌不一致，**Informational**）
- **Next.js**：`14.2.35`（提示 "outdated"；不阻断）
- **TypeScript**：strict 模式；`target: ES5`；`@/*` 路径别名
- **测试脚本**：无 `test` script（Playwright 已装但未配置）
- **冻结证据方式**：因非 Git 仓库，本报告以"环境快照 + 受控文件清单 + 浏览器实测"为冻结证据；源码指纹未变化（除本报告外，详见 §23）

---

## 3. 静态与构建 Gate（命令记录）

| 命令 | 退出码 | 关键发现 |
|---|---|---|
| `npx tsc --noEmit` | 0 | 0 类型错误 |
| `npm run lint` | 0 | 0 lint 错误 |
| `npm run build` | 0 | 路由清单 `/`、`/map`、`/calculator`、`/assessment`、`/match`、`/portfolio`、`/xuanxiao`、`/news`、`/university/[id]` 全部生成 |
| `npm run test` | 未运行 | `package.json` 无 `test` script；明确记录"无测试脚本，未执行"，不写成"通过" |

> **结论**：构建链无失败，但运行时仍有崩溃（见 §10 CR-01）。

---

## 4. 关键路由与动态路径策略

| 路由 | 生成策略 | 备注 |
|---|---|---|
| `/` | Static | 落地页 |
| `/map` | Dynamic (BFF + useSearchParams) | 移除 `output: "export"` 后保持 server runtime |
| `/university/[id]` | Dynamic | 详情页挂载 `UniversityProfilePanel` |
| `/calculator` `/assessment` `/match` `/portfolio` `/xuanxiao` `/news` | Dynamic / Client | 全部 "use client"，与 BFF 联动 |

---

## 5. 数据链路（DTO → Schema → UI）

```
[真实后端 Preview API /api/v1/preview/*] (未上线)
        │
        ▼  (切换后由 NEXT_PUBLIC_PATHOS_API_BASE_URL 指向)
[Next.js BFF /api/pathos/preview] (src/server/pathos-preview.ts)
        │ 加载 src/test/fixtures/*.fixture.json
        ▼
[PreviewApiDataSource] (src/services/preview-api-data-source.ts)
        │ fetchJson + parseXxx + ValidationError
        ▼
[运行时 schema] (src/schemas/dataset.schema.ts, validators.ts)
        │ DISPLAY_TIER / PROVENANCE_STATUS / RANKING_TIER / GRANULARITY
        ▼
[Domain types] (src/domain/dataset.ts)
        │ UniversitySummary / UniversityDetail / RegionMetricRecord / ...
        ▼
[Legacy POI 桥接] (src/lib/legacy-mappers.ts, summaryToLegacyUniversityPOI)
        │ ⚠️ 此处将缺失数值零填充（CR-02）
        ▼
[UI 组件] (MapShell / UniversityCard / ComparePanel / Calculator / ...)
        │ ⚠️ 多处直接读 POI 字段而非 detail（CR-02）
```

---

## 6. AI 控制白名单 / 黑名单（建议）

**白名单**（AI 可独立修改并提交，需 PR 评审）：
- `src/services/`、`src/schemas/`、`src/domain/`、`src/server/`、`src/app/api/pathos/`（BFF）
- 环境变量模板（`.env.local.example`）
- normalizer / adapter（`src/lib/legacy-mappers.ts`）
- fixture-to-real-API 切换开关
- 后端错误处理（`fetchJson` 的 `PREVIEW_NOT_YET_AVAILABLE` 路径）
- `validators.ts`、`dataset.schema.ts`、`PreviewApiDataSource`

**黑名单**（任何修改必须经前端审计专项授权）：
- `MapShell.tsx`、`MapCanvas.tsx`、`UniversityPoiLayer.tsx`、`UniversityCard.tsx`、`MapLegend.tsx`、`MetricTabs.tsx`
- 详情页结构（`UniversityProfilePanel.tsx`、`ProvenanceBadge.tsx`）
- 搜索 / 筛选 UI（`MapFilterPanel.tsx`）
- Compare UI（`ComparePanel.tsx`）
- Calculator / Assessment / Portfolio / Match 业务页面
- 响应式布局、家长/学生视角切换视觉
- 公开文案 / 可信度标签 / AI 面板视觉设计
- 颜色 token、字体、布局结构

---

## 7. 契约、语义与 UI Gate（三列映射）

| 后端期望路径 | 当前 BFF endpoint 参数 | 未来真实 API 映射建议 |
|---|---|---|
| `GET /api/v1/preview/manifest` | `GET /api/pathos/preview?endpoint=manifest` | 同左，移除 BFF 直连 |
| `GET /api/v1/preview/universities` | `GET /api/pathos/preview?endpoint=universities&state=&tier=` | 客户端发送 `tier=top20` 单值（**契约不一致，见 H-01**） |
| `GET /api/v1/preview/universities/{id}` | `GET /api/pathos/preview?endpoint=universities&id={id}` 或 `endpoint=university&id={id}` | 详情独立 endpoint；summary 与 detail 必须分离 |
| `GET /api/v1/preview/region-metrics?metricId=&granularity=` | 同左 | granularity 在 BFF 中无字段筛选（**潜在 over-fetch，见 M-04**） |
| `GET /api/v1/preview/region-detail/{fips}` | `?endpoint=region-detail&fipsCode={fips}` | BFF 硬编码 `granularity:"state"`（**County/City 错配，见 M-05**） |
| `GET /api/v1/preview/search?q=&limit=` | 同左 | limit 默认 20，未做去重 |
| `GET /api/v1/preview/news?category=` | 同左 | OK |
| `GET /api/v1/preview/status-dictionary` | 同左 | OK |
| `GET /api/v1/preview/source-index` | 同左 | OK |

---

## 8. 数据可用性矩阵（按 schema 字段）

| 字段 / 概念 | 已建模 | 已解析 | 已 normalized | UI 消费 | 缺失/阻塞 |
|---|---|---|---|---|---|
| `UniversitySummary` | ✅ | ✅ | ✅ | ✅（MapShell 仅用 lat/lng/name/tier） | OK |
| `UniversityDetail.programs` | ✅ | ✅ | ✅ | ✅（Detail 页） | quarantined 已过滤（行 86 ai-context） |
| `UniversityDetail.cost[]` | ✅ | ✅（BFF `pathos-preview.ts:90-101`） | ❌ | ⚠️ 仅 Detail 页 | **Calculator/Assessment/Match 直接读 summary 拿不到，CR-02** |
| `UniversityDetail.people[]` | ✅ | ✅ | ✅ | ✅（仅 Detail 页） | quarantined 已过滤 |
| `UniversityDetail.ranking[]` | ✅ | ✅（空数组，依赖 ranking fixture 弱关联） | ⚠️ | 部分（Detail 页） | ranking fixture 缺权威映射 |
| `UniversityDetail.sources[]` | ✅ | ✅ | ✅ | ✅ | status 多为 `source_review_not_completed` |
| `RegionMetricRecord` | ✅ | ✅ | ✅ | ✅（地图着色 + 系数计算） | OK |
| `StatusDictionaryMap` | ✅ | ✅ | ✅ | ✅（"数据补充中" 标签） | OK |
| `NewsArticle` | ✅ | ✅ | ✅ | ⚠️ 仅 sidebar 引用 | 实际 sidebar 渲染入口缺失（见 H-04） |

---

## 9. 全局学校搜索 / 指标入口 / 视角 / 比较 / Calculator 语义

| 维度 | 状态 | 风险 |
|---|---|---|
| 全局学校搜索 | URL bridge `u=` 仅承载单选；`MapFilterPanel.searchQuery` 仅本地 state；`/api/pathos/preview?endpoint=search` 独立存在 | **不统一**——地图/详情/列表/搜索各自独立，未形成全局搜索入口 |
| 指标入口 | 地图页 5 标签（income/safety/employment/cost/chinese_population）；URL bridge `metric` 含 `toefl/sat/admission_rate`（不存在） | **回退静默**——URL `?metric=toefl` 会静默回退到 income（**L-02**） |
| 父母/学生视角 | `mode=parent\|student` URL 参数；`viewStateBridge.setViewMode` 被 MapShell 462–464 调用 | **仅 mode 切换，未发现独立 UI 渲染差异**（**L-03**） |
| 比较（compare） | **单一 store**（`useCompareStore`，localStorage `pathos_compare`，cap=3） | ✅ 已统一；Calculator 与 MapShell 共用 |
| Calculator | 严重：直接读 summary 的 `annualCostRmb`（university summary 不含此字段）→ `undefined.toLocaleString` 崩溃 | **CR-01 阻塞** |

---

## 10. 问题清单（按严重度排序）

### CR-01 [Critical] Calculator 页面运行时崩溃
- **Evidence**：
  - 实测 `/calculator` 渲染报 `TypeError: Cannot read properties of undefined (reading 'toLocaleString')`，栈在 `src/app/calculator/page.tsx:27`
  - `const fmt = (n: number) => "¥" + n.toLocaleString();`
  - 第 60 / 69 / 137 / 152 / 162 / 169 / 189 行直接 `u.annualCostRmb` / `(tier as any)[item.key]` 运算
  - `UniversitySummary`（`src/domain/dataset.ts:47-67`）**不包含** `annualCostRmb`，仅 `cost` 数组存在于 `UniversityDetail`
- **Affected files**：
  - `src/app/calculator/page.tsx`
  - `src/lib/legacy-mappers.ts`（间接：bridges to POI 但仅对 MapShell）
  - `src/services/preview-api-data-source.ts`（数据源未提供 detail 字段）
- **Why it matters**：Calculator 是核心用户路径之一；当前 100% 崩溃；首屏即报错；用户无法完成"看预算"决策
- **Required action**：
  - 选项 A（最小）：Calculator 改为读取 `useUniversityDetail(u.id)` 拿 `cost[0].amount`；增加 loading 与 "数据补充中" fallback
  - 选项 B（推荐）：把 `annualCostRmb` 加入 summary 列表（最低限度把 preview 阶段的 cost 元数据前置），并在 Calculator 侧用 `?? 0` + "数据补充中" 标签
- **Blocks handoff**：是

### CR-02 [Critical] 缺失数值以 0 呈现（缺失值变 0）
- **Evidence**：
  - `src/lib/legacy-mappers.ts:33-49`：`annualCostRmb: 0, safetyScore: 0, recognitionScore: 0, chineseCommunity: "low"`
  - 大量 UI 直接读：`MapShell.tsx:782-786`、`UniversityCard.tsx:105/187/196`、`CityDetailPanel.tsx:125/129`、`ComparePanel.tsx:32-73`、`Match` 页面、`Assessment:181`、`Portfolio:82/118/194`、`Calculator` 全页
  - 结果：Princeton 显示 "¥0.0万/年"、"安全 0/100"、"认可度 0/100"
- **Affected files**：上述全部 UI + `legacy-mappers.ts`
- **Why it matters**：直接误导用户；违反"缺失值应显示 '数据补充中'"规范
- **Required action**：
  - 删除 `legacy-mappers.ts` 的零填充；改为 `null`
  - 所有消费者改为 `value ?? "数据补充中"`
  - 或：把所有需要的字段上提到 `UniversitySummary` 顶层（这要求修改 schema）
- **Blocks handoff**：是

### CR-03 [Critical] BFF ↔ 客户端 query 契约不一致
- **Evidence**：
  - 客户端 `preview-api-data-source.ts:98`：`flat.tier = query.rankingTiers`（单值赋数组）
  - BFF `pathos-preview.ts:184`：`url.searchParams.getAll("tier")`（多值/单值均可）
  - 实际 URLSearchParams 把数组序列化为 `tier=top20&tier=top50`；BFF `getAll` 收到 `["top20","top50"]`；当传入 `["top20"]` 时单值
  - 进一步：客户端期望的 query 字段名是 `state`，BFF 也读 `state`（OK）；`maxCostRmb`（OK）；但若 client 期望 `tiers`（复数）则会因 `getAll("tiers")` 返回空
- **Affected files**：
  - `src/services/preview-api-data-source.ts`
  - `src/server/pathos-preview.ts`
- **Why it matters**：筛选参数可能在联调阶段全部失效；契约未对齐会导致后端按"我以为的字段"实现，与前端不一致
- **Required action**：
  - 统一为单一字段名（建议 `tiers`，URL 允许多值）；BFF 与客户端都用 `getAll`
  - 在 BFF 加最小校验：`tiers.length > 0` 且每项 ∈ `["top20","top50","top100","other"]`
- **Blocks handoff**：是（联调日即失败）

### CR-04 [Critical] 硬编码几何 / Mock 数据存在于生产组件
- **Evidence**：
  - `src/components/map/CityLayer.tsx:9`：约 15 KB 的 `CA_BOUNDARY_GEOJSON`（16 个加州城市多边形）inlined 在生产组件中
  - `src/components/map/CityChoroplethLayer.tsx:7`：约 5 KB 的 `CA_CITY_GEOJSON`（15 个城市多边形）inlined
  - `src/components/map/MapCanvas.tsx:644-654`：注释里硬编码 Harvard 示例（POI 数据）
  - `src/components/map/UniversityMarkers.tsx`：702 行；声称 `MOCK_UNIVERSITIES` 已移除但仍含 mock 字段；**文件未被任何模块 import**（**H-01**）
  - `src/components/map/MapLegend.tsx:56-59 / 104`：TODO 注释与 `MOCK_RANGES` 常量
- **Affected files**：上述
- **Why it matters**：
  - 加州以外的用户看不到任何城市层；切换州失效
  - 违反 CLAUDE.md "数据应来自 fixtures 或真实后端，不应在组件中硬编码"
  - 包体增加约 20 KB；与"production mock fallback"红线冲突
- **Required action**：
  - 将 GeoJSON 移到 `public/geography/us-cities/*.geojson` 或 BFF 资源
  - 删除 `UniversityMarkers.tsx`（**H-01** 同时解决）
  - `MapLegend.MOCK_RANGES` 改为按 metric 实时计算（已读取 METRIC_DEFINITIONS）
- **Blocks handoff**：是（地图城市层对非加州用户 100% 不可用）

### CR-05 [Critical] `VALID_METRICS` 与实际 METRIC_DEFINITIONS 不一致
- **Evidence**：
  - `src/hooks/use-view-state-bridge.ts:33-40`：`VALID_METRICS = ["income","safety","toefl","sat","admission_rate","chinese_population"]`
  - `src/config/metrics.config.ts`：实际仅 `income/safety/employment/cost/chinese_population`（5 个，无 toefl/sat/admission_rate）
  - 当 URL `?metric=toefl` 传入时静默回退到 income（用户感知"标签没切"）
- **Affected files**：
  - `src/hooks/use-view-state-bridge.ts`
  - `src/lib/types.ts`（`MetricId` 联合定义）
- **Why it matters**：URL 共享失效；文档（CLAUDE.md §4 提 6 项）与代码不一致会误导对接方
- **Required action**：
  - 抽取 `VALID_METRICS = Object.keys(METRIC_DEFINITIONS)` 为单一来源
  - `MetricId` 类型改为 `keyof typeof METRIC_DEFINITIONS`
- **Blocks handoff**：是（URL 协议基线未对齐）

### CR-06 [Critical] AI 上下文 quarantine 过滤边界不一致
- **Evidence**：
  - `src/server/ai-context.ts:86`：过滤 `programs` 的 `displayTier === "quarantined"`（✅）
  - `UniversityProfilePanel.tsx:430`：过滤 `people` 的 `p.quarantined === false`（✅）
  - 但 `anecdotes` / `notableAttendance` / 详情页 anecdotes 区块未发现对应过滤逻辑（**未验证完整性**）
  - `validators.ts:219 / 235`：将 `quarantined` 默认从 `displayTier` 推导
- **Affected files**：`ai-context.ts`、`UniversityProfilePanel.tsx`、`anecdotes` 渲染节点（待定位）
- **Why it matters**：quarantine 记录若泄漏至 AI context，将产生"幻觉依据"风险
- **Required action**：对所有"内容性"字段（programs/people/anecdotes/notableAttendance/qualityBadges）在 AI context 入口处统一过滤
- **Blocks handoff**：是（数据治理核心约束）

---

### H-01 [High] `UniversityMarkers.tsx` 死代码（702 行）
- **Evidence**：
  - `grep -rn "from.*UniversityMarkers" src/` 无结果
  - `MapShell` 当前使用 `UniversityPoiLayer.tsx`
- **Why it matters**：维护负担 + 误导新读者
- **Required action**：删除文件；保留 git 历史可恢复
- **Blocks handoff**：否

### H-02 [High] `SidebarTabsContent` 未挂载
- **Evidence**：
  - `src/components/map/MapShell.tsx:891-978` 定义 `SidebarTabsContent`
  - 实际 sidebar 仅渲染空 state（line 678 附近）
  - `MapFilterPanel` 因此永远不可见
- **Why it matters**：筛选功能对用户不可达；UI 设计完整但未接通
- **Required action**：在 `MapShell` 中挂载 `SidebarTabsContent`；或拆出独立路由
- **Blocks handoff**：是（功能承诺未兑现）

### H-03 [High] `CityChoroplethLayer` 用硬编码 props 着色
- **Evidence**：
  - `src/components/map/CityChoroplethLayer.tsx:23`：`props.safetyScore || 70`、`props.annualCostRmb || 400000`、`props.chineseCommunity || 0.5`
  - 实际数据来自组件内的 `CA_CITY_GEOJSON`（硬编码），不走 BFF
- **Why it matters**：声称按 metric 上色但实际是常量；用户切换 metric 时颜色可能不变
- **Required action**：从 `region-metrics` BFF + city-boundaries fixture 取真实值
- **Blocks handoff**：是（与 CR-04 同源）

### H-04 [High] News sidebar 入口缺失
- **Evidence**：未发现引用 `useDataSource().getNews()` 的页面组件
- **Why it matters**：BFF `news` endpoint 已实现但 UI 无入口
- **Required action**：在主页或 footer 加入口
- **Blocks handoff**：否（独立模块）

### H-05 [High] `.env.local.example` 缺关键变量模板
- **Evidence**：当前文件仅有 AI 配置；缺：
  - `NEXT_PUBLIC_PATHOS_API_BASE_URL`
  - `PATHOS_API_BASE_URL`（BFF 端）
  - `PATHOS_PREVIEW_FIXTURE_PATH`（可选）
- **Required action**：补全模板
- **Blocks handoff**：否

### H-06 [High] `MapCanvas.tsx:644-654` Harvard 示例 TODO
- **Evidence**：注释里硬编码 POI 示例字段
- **Why it matters**：可能被 grep 误判为 mock fallback
- **Required action**：删除或迁到 dev-only fixture
- **Blocks handoff**：否

---

### M-01 [Medium] `pathos-preview.ts:73` 每条记录硬标 `previewOnly: true`
- **Why it matters**：切换到真实 API 后此字段语义将冲突；需明确"preview 阶段 vs 生产预览"
- **Required action**：在 DataSource 抽象层判断环境

### M-02 [Medium] `pathos-preview.ts:74` 硬编码 `datasetVersion: "fixture-2026-07-24"`
- **Required action**：从 manifest 派生或从 env 注入

### M-03 [Medium] `pathos-preview.ts:247` `region-detail` 硬编码 `granularity: "state"`
- **Required action**：按 fips 前缀判断（state=2 位、county=5 位、city=7 位）

### M-04 [Medium] `region-metrics` BFF 不按 granularity/metric 字段筛选
- **Evidence**：`pathos-preview.ts:203-222` 返回所有 records，让客户端筛选
- **Required action**：BFF 端按 `metricId` / `granularity` 过滤

### M-05 [Medium] `encodeQuery` 死代码
- **Evidence**：`preview-api-data-source.ts:138-151` 定义但从未调用
- **Required action**：删除

### M-06 [Medium] `use-view-state-bridge` 中 `state` 在 effect 中写 URL，每次 setState 触发 router.replace
- **Evidence**：`use-view-state-bridge.ts:148-151`
- **Required action**：debounce 或仅在用户交互后写

### M-07 [Medium] `UniversitySummary.stateFips` 在 `RegionDetail.name` 字段被滥用
- **Evidence**：`pathos-preview.ts:248`：`name: top[0]?.state ?? fips`
- **Required action**：以 FIPS 对照表查州名

### M-08 [Medium] `Assessment` `default profile` 默认 budget 550000 与实际数据脱节
- **Why it matters**：用户不会知道这个默认值
- **Required action**：增加 placeholder + hint

### M-09 [Medium] `Portfolio` 跨页 store 同步未做防抖
- **Required action**：与 `compare-store` 保持一致（同 pattern）

### M-10 [Medium] `useUniversitySummaries` 客户端无缓存层
- **Required action**：考虑 SWR/React Query

---

### L-01 [Low] `package.json` 包名 `beijing-advisory-mvp` 与品牌 `PathOS` 不一致
- **Required action**：rename

### L-02 [Low] URL `metric=toefl` 等未知值静默回退（见 CR-05 同源）

### L-03 [Low] `mode=parent|student` 切换在 UI 中无可见差异（**未找到对应渲染分支**）
- **Required action**：实现区分或移除参数

### L-04 [Low] `MapLegend` TODO `MOCK_RANGES`（见 CR-04 同源）

### L-05 [Low] `CityDetailPanel` 字段 fallback 同样以 0 呈现（与 CR-02 同源）

### L-06 [Low] `Portfolio` 列表页基于 localStorage，无 SSR hydrate 策略文档

### L-07 [Low] `Assessment` 优先级与权重无关，仅作 AI 输入；与"自主权重匹配"页面职责混淆

### L-08 [Low] `Xuanxiao`（清单分析）页面职责与 Portfolio 重叠

### L-09 [Low] `Match` 页面权重常量 `620000` 等魔法数字无注释

### L-10 [Low] `validators.ts` 手写校验缺少单元测试

---

### I-01 [Informational] `package.json` Playwright 已装但 `test:e2e` 脚本未配置
- **Required action**：按需补全

### I-02 [Informational] Next.js 14.2.35 提示 outdated
- **Required action**：评估升级窗口

### I-03 [Informational] `MapCanvas` 中引用 OpenStreetMap tiles 与 MapLibre demotiles

### I-04 [Informational] CLAUDE.md 与代码层 Metric 数量不一致（文档写 6，代码实 5）

### I-05 [Informational] `validators.ts:219` quarantined 默认从 displayTier 推导

### I-06 [Informational] `src/server/ai-context.ts:86` 中 AI context 仅取 3 所学校硬编码

---

## 11. Calc / Match / Portfolio / Assessment 实测结论

| 页面 | 实测结果 | 备注 |
|---|---|---|
| `/` | ✅ 落地页正常 | 未深查 |
| `/map` | ✅ 渲染正确（choropleth + POI） | 仅当 URL `metric` ∈ {income,safety,...5 个有效项} |
| `/calculator` | ❌ **TypeError 崩溃** | CR-01 阻塞 |
| `/assessment` | ⚠️ 显示 "¥0万/年"（数据补充中错乱） | CR-02 |
| `/portfolio` | ⚠️ 显示 "¥0万/年" | CR-02 |
| `/match` | ⚠️ 显示 "¥0万/年" | CR-02 |
| `/xuanxiao` | 未深查 | 风险同 Portfolio |
| `/news` | 未深查 | |
| `/university/[id]` | ✅ Princeton 详情页正常 | Cost 字段来自 `detail.cost[0]`（OK） |

---

## 12. 阻塞项（必须先解决才能 handoff）

- **CR-01** Calculator 运行时崩溃
- **CR-02** 缺失值变 0 污染（影响 5+ 页面）
- **CR-03** BFF `tier/tiers` 契约不一致
- **CR-04** 硬编码加州 geometry + 死代码
- **CR-05** VALID_METRICS 与 schema 不一致
- **CR-06** Quarantine 过滤边界未验证完整

按用户规则：**任一构建失败 / POI 不可见 / `[0,0]` / production mock fallback / quarantine 泄露 / 缺失值变 0 / 严重 contract 不一致 → 直接判 C**。当前已命中：
- ❌ 缺失值变 0（CR-02 大量命中）
- ❌ production mock fallback（CR-04 硬编码 geometry）
- ❌ 严重 contract 不一致（CR-03、CR-05）
- ❌ 运行时崩溃（CR-01）

---

## 13. 后端集成后的 15 项强制复验（集成日执行）

1. `NEXT_PUBLIC_PATHOS_API_BASE_URL` 指向 `/api/v1/preview/*`；移除对 BFF 的直接依赖
2. 删除 `src/server/pathos-preview.ts` 路由文件
3. 删除 `src/test/fixtures/*.fixture.json`
4. 移除 `src/components/map/CityLayer.tsx` 的 `CA_BOUNDARY_GEOJSON` inlined
5. 移除 `src/components/map/CityChoroplethLayer.tsx` 的 `CA_CITY_GEOJSON` inlined
6. 删除 `src/components/map/UniversityMarkers.tsx` 死文件
7. 替换 `legacy-mappers.ts` 的零填充为 `null` 并修复 UI fallback
8. Calculator 改用 `getUniversityDetail` 获取 `cost[0].amount`
9. 统一 `VALID_METRICS` 与 `METRIC_DEFINITIONS` 为同一来源
10. 修正 `getUniversitySummaries` 的 `tier` 字段名为 `tiers`
11. 在 `PreviewApiDataSource` 上加 timeout 配置中心化
12. 在所有 AI context 入口验证 `displayTier !== "quarantined"` 过滤
13. 增加 `region-metrics` BFF 的 granularity/metric 字段筛选
14. 增加 `region-detail` 的 granularity 推断（按 fips 长度）
15. 补全 `.env.local.example` 的关键变量

---

## 14. 静态检查报告（输出摘要）

- `tsc --noEmit`：0 错误 / 0 warning
- `eslint`：0 错误 / 0 warning
- `next build`：成功；主路由与动态大学路径全部生成
- 无 `test` 脚本（**未执行任何单测**）

---

## 15. Mock / Fixture 扫描结论

| 类别 | 数量 | 状态 |
|---|---|---|
| `MOCK_*` 常量 | `MOCK_UNIVERSITIES`（已注释移除但残留）、`MOCK_RANGES` | 死代码或 TODO |
| `mock` 注释 | 3 处（MapCanvas、UniversityMarkers、MapLegend） | 残留 |
| `fallback` | `legacy-mappers.ts:33-49` 的零填充 | **Critical（CR-02）** |
| `hardcoded` | `CA_BOUNDARY_GEOJSON`、`CA_CITY_GEOJSON`、`MapCanvas:644-654` Harvard | **Critical（CR-04）** |
| Fixture 文件 | `src/test/fixtures/*.fixture.json` | 设计内；需在集成日删除 |
| 后端失败静默 fallback | 无（`fetchJson` 抛 `PREVIEW_NOT_YET_AVAILABLE`） | ✅ |

---

## 16. 浏览器实测证据（保留条目）

- `preview_screenshot`、`preview_snapshot`、`preview_network`、`preview_console_logs`、`preview_inspect` 已用于验证 `/map`、`/university/princeton-university`、`/calculator`
- `/map` 渲染：choropleth 着色（5 metrics 全部可切），约 20 个 POI 标记可见
- `/calculator`：触发 `TypeError`（已记录）
- `/university/princeton-university`：Overview / Programs / Rankings / Cost / Location / People / History / Sources 区块完整渲染；Preview badge "数据预览模式"显示；dataset version `fixture-2026-07-24` 显示

---

## 17. 响应式 / 暗色（**未深测**）

> 本次审计未系统执行 1280 / 768 / 390 宽度复测；仅确认 `/map` 在桌面宽度正常。建议集成前补做。

---

## 18. URL Bridge 行为（按参数逐项）

| 参数 | 写入方 | 读取方 | 一致性 |
|---|---|---|---|
| `metric` | useViewStateBridge.setActiveMetric | readStateFromParams | ⚠️ VALID_METRICS 含未定义项（CR-05） |
| `u` | setSelectedUniversity | readStateFromParams | ✅ |
| `r` | setSelectedRegion | readStateFromParams | ✅ |
| `compare` | setCompareIds (append) | readStateFromParams (getAll) | ✅ |
| `mode` | setViewMode | readStateFromParams | ⚠️ 无 UI 渲染差异（L-03） |
| 搜索/筛选（filter panel） | MapFilterPanel 本地 state | 无 URL 同步 | ❌ 不入 URL，无法分享（**M-06**） |

---

## 19. Compare Store 一致性

- ✅ 单一 source of truth（`src/state/compare-store.ts`）
- ✅ Calculator 与 MapShell 共用
- ✅ localStorage `pathos_compare`、cross-tab via `storage` 事件
- ✅ cap=3；hydration-safe
- ⚠️ 与 `pathos_portfolio`、`pathos_student_profile` 命名一致

---

## 20. AI Context 与可信度语义

- `src/server/ai-context.ts` 已实现 3 学校上限、quarantined 过滤、headers `X-PathOS-BFF: preview-context`
- `UniversityProfilePanel.tsx:430` 过滤 quarantined people
- ✅ ProvenanceBadge 渲染状态字典
- ⚠️ Cost 区块按"最高 year"取 headline，未按 authority（M-待确认）

---

## 21. 修复优先级（建议顺序）

1. **CR-03** BFF 契约对齐（**最小代码、立刻可改**）
2. **CR-05** VALID_METRICS 单一来源（**最小代码**）
3. **CR-02** legacy-mapper 零填充改为 null + UI fallback（**广覆盖**）
4. **CR-01** Calculator 改读 detail 或加 cost 到 summary（**关键路径**）
5. **CR-04** 移除硬编码 geometry + 删除 UniversityMarkers.tsx（**包体与可信度**）
6. **CR-06** AI context quarantine 过滤完整性（**数据治理**）
7. H-02 / H-03 / H-04 / H-05 / H-06
8. M-* / L-*

---

## 22. 修改记录（审计期间唯一写入）

- **新增**：`frontend/docs/FRONTEND-FREEZE-INTEGRATION-GATE.md`（本报告）
- **未触碰**：除本报告外的任何源文件；未创建或修改 fixtures、BFF、组件、样式、配置
- **未运行**：`git reset --hard`、`git clean -fd`、任何 push、任何 backend 仓库操作、任何 Supabase 写入
- **未实施修复**：本审计为只读 Gate；CR-* 修复待用户授权后另开修复 session

---

## 23. 文件指纹摘要（受控范围）

- 受控文件清单已记录在审计过程中；本报告以外无源文件变化
- `docs/qa-screenshots/` 为已存在的目录（未被本审计修改）

---

## 24. 关键命令与产出

- `npx tsc --noEmit` → 0 errors
- `npm run lint` → 0 errors
- `npm run build` → success（所有路由生成）
- `preview_start` → port 3000，dev server alive
- `preview_snapshot` / `preview_network` / `preview_console_logs` → 浏览器实测证据

---

## 25. 给后端对接方的"对接清单"（独立小节）

| 项 | 前端期望 |
|---|---|
| Base URL | `NEXT_PUBLIC_PATHOS_API_BASE_URL=/api/v1/preview` |
| Universities 列表筛选 | `tiers=top20&tiers=top50`（多值） |
| Universities 列表状态筛选 | `state=CA&state=NY`（多值） |
| Universities 列表预算 | `maxCostRmb=600000` |
| Universities detail | `/api/v1/preview/universities/{id}`（独立 endpoint） |
| Region metrics | `metricId=income&granularity=state`（单值，必须支持） |
| Region detail | `/api/v1/preview/region-detail/{fips}`；granularity 由 fips 前缀推断 |
| Search | `q=...&limit=20` |
| Status dictionary | 静态枚举映射 |
| Source index | 大学 + 排名 + 新闻合并索引 |
| Manifest | 必须返回 `schemaVersion`、`generatedAt`、`sourceCommit`、`previewOnly`、`counts` |
| Status 字段 | 必填：每条 UniversityDetail 的 programs/people/cost/anecdotes 都有 `status` |
| Display tier | `live_verified` / `cached` / `preview` / `quarantined` 四态枚举 |
| Quarantine 语义 | `quarantined=true` 必须在 AI context 与公开 UI 全部过滤 |

---

**报告结束**。

> **本次 Gate 仅判定"可准备接入"，不声称真实后端已集成通过**。集成完成后请按 §13 强制复验。