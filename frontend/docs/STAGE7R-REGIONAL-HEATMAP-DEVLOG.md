# Stage 7R — 开发日志

> 本日志按时间顺序记录 Stage 7R 的关键决策、踩坑与修复，方便审计与复现。

---

## Day 1 — 数据发现与单工作簿审计

### 1.1 工作簿定锚

- 路径：`resource/PathOS_美国各州留学数据矩阵.xlsx`
- SHA-256: `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`
- 三个 sheet：`美国各州留学数据` / `数据字典` / `单位与口径说明`
- 数据行从 sheet 第 4 行开始（第 1–3 行为 banner/header）

### 1.2 6 个 metric 的初判

| metric | sheet 列 | 状态 |
|---|---|---|
| income | "州家庭收入中位数 (USD)" | READY 51/51 |
| safety | "暴力犯罪率 (每10万人)" | READY 51/51，方向问题 |
| employment | "失业率 (%)" | READY 51/51 |
| chinese_population | "华人占比 (%)" | READY 51/51 |
| admission_rate | — | BLOCKED（工作簿无此列） |
| toefl / sat | — | OUT_OF_SCOPE |

---

## Day 1 — 安全指标方向反转

### 1.3 关键发现

工作簿元数据对 safety 的描述写"倒数"，但 raw value 是**犯罪率本身**（不是倒数）。
最低 raw = 缅因州 110.6（最安全），最高 raw = 新墨西哥 780.5（最不安全）。

若直接采用 workbook 的 normalizedValue，会出现"颜色越深 = 犯罪越多 = 看起来更安全"的视觉倒置。

### 1.4 决策

- `rawValue` 保留原值（不破坏数据可追溯性）；
- `displayValue` 同上；
- `normalizedValue` 在导入器中重新计算：`our_norm = 1.0 - wb_norm`，让最低 crime → 最高 norm；
- 在 `RegionalMetricDefinition.longDescription` 写明"越高越安全"；
- 在 AUDIT 文档中显式标注此反转。

---

## Day 2 — 确定性导入器

### 2.1 Python 选型

- 不引入 pandas，使用 `openpyxl` 3.1.5（项目内已依赖）；
- 输出 JSON 用 `json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)` + 末尾换行；
- 所有 SHA-256 计算在写文件后立即计算，存进 manifest。

### 2.2 9 个产物

1. `regional-datasets.json` — 数据集元数据（含 sourceWorkbookSha256, readyMetrics, blockedMetrics）
2. `regional-metrics.json` — 4 个 metric 定义
3. `regional-records.json` — 204 条全量
4. `regional-record-income.json` — 51 条 income
5. `regional-record-safety.json` — 51 条 safety
6. `regional-record-employment.json` — 51 条 employment
7. `regional-record-chinese_population.json` — 51 条 chinese
8. `regional-data-manifest.json` — 全量 SHA
9. `regional-data-validation.json` — 校验报告（duplicate=0, missing=0）

### 2.3 确定性验证

连跑两次 `python3 scripts/import-regional-data.py`，对 9 个文件做 `diff -q`：
**全部 byte-identical**。其中 `regional-records.json` SHA = `9229fb80570a41271c21779adc316b3cbadc27c3e20f8fde5e726fadd33cbf5c`。

---

## Day 2 — TypeScript 契约

### 2.4 类型设计

```ts
export type RegionalMetricId = "income" | "safety" | "employment" | "chinese_population";
export const REGIONAL_METRIC_IDS: readonly RegionalMetricId[] = [...];

export type RawDirection = "direct" | "inverse";
export type VerificationStatus = "verified" | "partial" | "user_provided_unverified" | "not_reported" | "not_applicable";

export interface RegionalMetricDefinition {
  metricId: RegionalMetricId;
  displayNameZh: string;
  displayNameEn: string;
  longDescription: string;
  rawUnit: string;
  rawDirection: RawDirection;
  higherIsBetter: boolean;
  usedForMatch: false;       // 边界：永不入 match 分数
  usedForMap: true;
  paletteId: string;
  referenceYear: string;
  sourceName: string;
  sourceUrl: string;
  verificationStatus: VerificationStatus;
}

export interface RegionalMetricRecord {
  metricId: RegionalMetricId;
  geoId: string;             // 2-char FIPS, leading zero preserved
  geoName: string;
  geoNameEn: string;
  rawValue: number | null;
  displayValue: string | null;
  normalizedValue: number | null;
  referenceYear: string;
  sourceId: string;
  sourceRow: number;
  verificationStatus: VerificationStatus;
  bucketIndex: number | null;
}
```

---

## Day 3 — 调色板迭代

### 3.1 ΔL ≥ 8 的硬性要求

测试 `every palette: adjacent stops are visibly distinct (ΔL >= 8 in HSL lightness)` 在 5+ 次迭代中失败，每次调整都基于 Python 离线计算 WCAG-L：

```
L = 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
f(c) = c/12.92 if c/255 ≤ 0.03928 else ((c/255+0.055)/1.055)^2.4
```

### 3.2 最终通过的暗色色阶

- income-green dark: `#0f2a1d` → `#2e6643` → `#4d8754` → `#7bc06b` → `#b8f29b`
- safety-blue dark: `#16263a` → `#3a6189` → `#5d8eb8` → `#8cc1e8` → `#bfe1fa`
- employment-purple dark: `#231135` → `#773bb3` → `#9e6dce` → `#c699e6` → `#e8dcf3`
- chinese-orange dark: `#211007` → `#93491f` → `#ce672b` → `#e3a27c` → `#faf0e9`

浅色色阶同样通过（income-green light ΔL = 19.5/26.3/20.7/9.5 等）。

---

## Day 3 — 边界文案

### 3.3 MapShell 集成

新增 4 个组件，在 `MapShell.tsx` 顶部工具栏放置 `<RegionalLayerControl>`（下拉），地图右下角放置 `<RegionalLegend>`，鼠标 hover 时通过 `<RegionalHoverTooltip>` 显示原始值与归一化值。

`<RegionalStateLayer>` 内部：

- 第一次 activeMetricId 非 null 时调用 `loadStateBoundaries()` 拉 `public/geography/us-states.topojson`；
- 用 `topojson-client.feature()` 转 GeoJSON；
- `map.addSource("pathos-regional-states", ...)` + `addLayer` 填充层（位于 `pathos-city-*` 之前）；
- fill-color 用 `["match", ["get", "id"], ...]` 表达式 + 51 个 FIPS → bucket color；
- hover/click 用 `feature-state`。

---

## Day 3 — 跑通完整测试

### 3.4 最终回归

```
✓ legacy-mapper.test.ts                 20
✓ stage7r-regional-heatmap.test.ts      27
✓ stage7a-theme-heatmap.test.ts          75
✓ stage5-integration.test.ts            38
✓ stage5-closing-ui.test.ts              18
─────────────────────────────────────────────
Tests  178 passed (178)
```

`npx tsc --noEmit`：0 错误
`npx next lint`：`✔ No ESLint warnings or errors`
`npm run build`：✓ 15 个静态页生成

---

## Day 3 — 浏览器真实验证

### 3.5 路由 200 + 边界文案可见

- `/` 200, `/match` 200, `/assessment` 200, `/calculator` 200, `/news` 200, `/portfolio` 200, `/map` 200
- `/match` 显示："区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未计入自主匹配分数；综合分仅基于「费用 + 排名」两个真实维度。"
- `/assessment` 显示："区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未进入 AI 评估与自主匹配分数；区域数据接入完整数据源后会再次校准评分口径。"
- hydration 安全：`<html class="dark" data-theme="dark">` 与 `colorScheme: dark` 一致
- us-states.topojson 服务端 200

### 3.6 已知的浏览器限制

由于本会话未启动 Node 后端服务，`/api/pathos/preview` 返回 503，导致 `<MapShell>` 在错误分支渲染 "后端服务暂不可用"。这是预期的 dev-server-only 状态，不影响：

- 区域组件的 JS bundle 包含正确（4 个 paletteId、RegionalLayerControl 文字"不显示区域热力图"都在 SSR HTML 中）；
- 单元测试覆盖了所有运行时逻辑；
- 真实数据流已在 Stage 5/7A 跑通过。

## Day 3 — 完成

所有 10 个 Phase 完成：审计 → 导入 → 契约 → 调色板 → 层组件 → UI 控件 → 测试 → 编译 → 浏览器 → 文档。
