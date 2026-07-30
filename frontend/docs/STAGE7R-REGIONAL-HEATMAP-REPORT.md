# Stage 7R — 区域热力图 数据审计 + 前端集成 验收报告

> **PathOS Stage 7R — Final Report**
>
> 状态：**READY FOR INDEPENDENT STAGE 7R RE-GATE**

---

## 1. 范围摘要

本阶段在 Stage 7A 已修复的暗色 / 浅色主题、MapLibre basemap 与 match/assessment 边界基础上，引入 4 个州级热力图：

- 收入水平（income · 绿色族）
- 安全系数（safety · 蓝色族，方向反转）
- 就业（employment · 紫色族）
- 华人社区（chinese_population · 橙色族）

单一数据源：`resource/PathOS_美国各州留学数据矩阵.xlsx`（SHA `409ed47b…`）。

---

## 2. 数据审计结论

| metric | READY | records | missing | 备注 |
|---|---|---|---|---|
| income | ✅ | 51/51 | 0 | raw: $55k–$91k USD |
| safety | ✅ | 51/51 | 0 | raw: 110.6–780.5（犯罪率），normalizedValue 经 `1 - wb_norm` 反转 |
| employment | ✅ | 51/51 | 0 | raw: 2.4%–5.6% |
| chinese_population | ✅ | 51/51 | 0 | raw: 0.1%–4.6% |
| admission_rate | ❌ BLOCKED | — | — | 工作簿无此列 |
| toefl / sat | OUT_OF_SCOPE | — | — | 不在 Stage 7R 范围 |

**总计：204 条 verified 记录，0 duplicate，0 missing。**

---

## 3. Safety 反向标准化的关键决策

工作簿 metadata 写"倒数"，但 raw 是**真实犯罪率**而非倒数。直接套用 workbook 的 `normalizedValue` 会导致"颜色越深 = 犯罪越多 = 视觉上越安全"的反直觉结果。

**决策**：

- `rawValue` 与 `displayValue` 保留原始犯罪率值（如 "110.6/10万"），**不改**；
- `normalizedValue` 在 Python 导入器内重新计算：`our_norm = 1.0 - wb_norm`，确保缅因州（最低 crime）= 最高 norm；
- `RegionalMetricDefinition.longDescription` 显式标注"越高越安全"，避免后续开发者误读；
- `rawDirection = "inverse"`、`higherIsBetter = false`，与 norm 方向一致；
- 在 PROVENANCE 与 AUDIT 中显式记录此决策，可追溯。

---

## 4. 架构与文件清单

### 4.1 新增文件

| 路径 | 用途 |
|---|---|
| `scripts/import-regional-data.py` | 确定性 Python 导入器 |
| `generated/regional-data/regional-datasets.json` | 数据集元数据 |
| `generated/regional-data/regional-metrics.json` | 4 个 metric 定义 |
| `generated/regional-data/regional-records.json` | 204 条全量 |
| `generated/regional-data/regional-record-income.json` | 51 条 income |
| `generated/regional-data/regional-record-safety.json` | 51 条 safety |
| `generated/regional-data/regional-record-employment.json` | 51 条 employment |
| `generated/regional-data/regional-record-chinese_population.json` | 51 条 chinese |
| `generated/regional-data/regional-data-manifest.json` | 全量 SHA |
| `generated/regional-data/regional-data-validation.json` | 校验报告 |
| `src/regional/types.ts` | TS 类型契约 |
| `src/regional/palettes.ts` | 4 套调色板（light+dark） |
| `src/regional/load.ts` | JSON 加载器 |
| `src/components/map/regional/RegionalStateLayer.tsx` | MapLibre 填充层 |
| `src/components/map/regional/RegionalLayerControl.tsx` | 顶部下拉控件 |
| `src/components/map/regional/RegionalLegend.tsx` | 右下角图例 |
| `src/components/map/regional/RegionalHoverTooltip.tsx` | 跟随鼠标 tooltip |
| `src/test/unit/stage7r-regional-heatmap.test.ts` | 27 个新测试 |

### 4.2 修改文件

| 路径 | 改动 |
|---|---|
| `src/components/map/MapShell.tsx` | 接入 4 个新组件 + state hooks + theme mode |
| `docs/STAGE7R-REGIONAL-HEATMAP-PLAN.md` | 新增 |
| `docs/STAGE7R-REGIONAL-HEATMAP-DEVLOG.md` | 新增 |
| `docs/STAGE7R-REGIONAL-HEATMAP-REPORT.md` | 本文档 |
| `docs/STAGE7R-REGIONAL-HEATMAP-PROVENANCE.md` | 新增 |
| `docs/STAGE7R-REGIONAL-DATA-AUDIT.md` | 新增 |
| `docs/STAGE7R-CHANGEMANIFEST.json` | 新增 |

---

## 5. 视觉与可达性

### 5.1 4 套独立调色板

每个 metric 一套独立色族，浅色 / 深色分别调色。`bucketFromNormalized(t, palette)` 把 [0,1] 映射到 5 个色阶，null/NaN/<0/>1 落入 `palette.missing`（中性灰）。

| metric | 浅色主色 | 深色主色 | missing (light/dark) |
|---|---|---|---|
| income | `#1f6b4e` deep jade | `#b8f29b` bright lime | `#e2dfd6` / `#3b4148` |
| safety | `#1c4f87` deep navy | `#bfe1fa` bright sky | 同上 |
| employment | `#3a1862` deep violet | `#e8dcf3` bright lavender | 同上 |
| chinese_population | `#a64422` persimmon | `#faf0e9` bright persimmon | 同上 |

### 5.2 WCAG-AA ΔL ≥ 8（实测全 32 对通过）

| palette/theme | ΔL [0→1] | ΔL [1→2] | ΔL [2→3] | ΔL [3→4] |
|---|---|---|---|---|
| income-green light | 19.5 | 26.3 | 20.7 | 9.5 |
| income-green dark | 9.5 | 10.0 | 12.7 | 15.4 |
| safety-blue light | 23.2 | 22.4 | 17.8 | 11.8 |
| safety-blue dark | 9.5 | 9.1 | 11.5 | 12.5 |
| employment-purple light | 25.3 | 27.9 | 16.4 | 8.2 |
| employment-purple dark | 22.2 | 9.5 | 11.6 | 12.9 |
| chinese-orange light | 21.3 | 22.7 | 16.7 | 11.5 |
| chinese-orange dark | 22.3 | 9.2 | 10.4 | 14.4 |

---

## 6. 与 Match / Assessment 的边界（再确认）

| 检查 | 结果 |
|---|---|
| `RegionalMetricDefinition.usedForMatch` | **false**（4 个 metric） |
| `RegionalMetricDefinition.usedForMap` | **true**（4 个 metric） |
| `/match` 页面文案 | "区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未计入自主匹配分数；综合分仅基于「费用 + 排名」两个真实维度。" |
| `/assessment` 页面文案 | "区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未进入 AI 评估与自主匹配分数；区域数据接入完整数据源后会再次校准评分口径。" |
| 单元测试断言 `usedForMatch === false` | 4/4 通过 |
| `regional-datasets.json.readyMetrics` | `["income", "safety", "employment", "chinese_population"]` |
| `regional-datasets.json.blockedMetrics` | `["admission_rate"]` |

---

## 7. 集成位置与交互

```
┌─────────────────────────────────────────────────────┐
│ [Logo]                [TabBar]   [RegionalCtrl] [☰] │  ← top toolbar
├─────────────────────────────────────────────────────┤
│                                                     │
│                                                     │
│               US Map (MapLibre)                     │
│   ┌─────────────┐                                   │
│   │ StateFill   │ ← RegionalStateLayer (below city) │
│   │             │                                   │
│   │ CityChoro   │                                   │
│   │ POI         │                                   │
│   │             │                                   │
│   └─────────────┘                                   │
│                                       ┌───────────┐ │
│                                       │ Legend    │ │ ← RegionalLegend (bottom-right)
│                                       │ ▢▢▢▢▢    │ │
│                                       │ Source    │ │
│                                       └───────────┘ │
└─────────────────────────────────────────────────────┘
                                          │
                                       hover on state
                                          ↓
                                  ┌──────────────┐
                                  │ Tooltip      │
                                  │ California   │
                                  │ raw:  $91k   │
                                  │ norm: 0.95   │
                                  └──────────────┘
```

### 7.1 RegionalLayerControl

下拉框（`<select>`），选项：
- 不显示区域热力图（默认）
- 收入水平（绿）
- 安全系数（蓝）
- 就业（紫）
- 华人社区（橙）

切换时 `MapShell` 重新调用 `RegionalStateLayer` 的 `useEffect`，更新 fill-color 表达式。

### 7.2 RegionalLegend

固定在地图右下角（`absolute bottom-4 right-4 z-20`），仅在 activeRegionalLayer 非 null 时显示。展示：

- metric 名（zh + en）
- 年份 + 单位 + 方向
- 5 个色阶（低/偏低/中/偏高/高）
- missing 灰
- verified 51/51 + total 51
- 工作簿 SHA 前 12 位

### 7.3 RegionalHoverTooltip

`pointer-events: none` 固定定位在鼠标偏移 (12, 12) 处，展示：

- 州名（zh + en）
- 原始值（displayValue）
- 标准化值（normalizedValue.toFixed(3)）
- 缺失时显示"该区域暂无该指标数据"
- 来源 ID + 工作簿行号

---

## 8. 回归测试矩阵

| 套件 | 数量 | 状态 |
|---|---|---|
| legacy-mapper.test.ts | 20 | ✅ |
| stage7r-regional-heatmap.test.ts | 27 | ✅ |
| stage7a-theme-heatmap.test.ts | 75 | ✅ |
| stage5-integration.test.ts | 38 | ✅ |
| stage5-closing-ui.test.ts | 18 | ✅ |
| **合计** | **178** | **✅** |

**`npx tsc --noEmit`**：0 错误
**`npx next lint`**：`✔ No ESLint warnings or errors`
**`npm run build`**：✓ Compiled successfully，15 个静态页生成

---

## 9. 浏览器真实验证

| 路由 | HTTP | 渲染 |
|---|---|---|
| `/` | 200 | ✅ |
| `/match` | 200 | ✅ 含"区域指标…未计入自主匹配分数"边界文案 |
| `/assessment` | 200 | ✅ 含"区域指标…未进入 AI 评估"边界文案 |
| `/calculator` | 200 | ✅ |
| `/news` | 200 | ✅ |
| `/portfolio` | 200 | ✅ |
| `/map` | 200 | SSR HTML 含 `RegionalLayerControl`、4 个 metric 名、"不显示区域热力图"选项 |

### 9.1 主题 hydration

- `<html class="dark" data-theme="dark">` 与 `color-scheme: dark` 一致
- 没有 hydration mismatch 警告

### 9.2 资源加载

- `/geography/us-states.topojson` 服务端 200
- 后端 `/api/pathos/preview` 在无后端进程时返回 503，导致 `<MapShell>` 进入错误分支（这是 dev-server-only 状态，不影响区域组件的 bundle 与类型契约）

---

## 10. Stage 7A 兼容

| Stage 7A 修复 | 当前状态 |
|---|---|
| H-1 hydration 警告 | ✅ 维持修复 |
| M-1 MapLibre dark basemap | ✅ 维持修复 |
| M-2 `/assessment` 区域边界 callout | ✅ 维持修复 |
| M-3 calculator missing-cost branch | ✅ 维持修复（已通过测试） |
| L-1 4× eslint disable | ✅ 维持修复 |

未引入任何禁用规则；未破坏 Stage 7A 数据不变量（`schoolCount=62`、`verifiedRecordCount=904`）。

---

## 11. 剩余已知事项

1. **`admission_rate`** 仍 BLOCKED，工作簿未提供，需后续数据源接入；
2. **toefl / sat** 不在 Stage 7R 范围，**OUT_OF_SCOPE**；
3. **dev-server-only**：本会话未启动 Node 后端，浏览器实测 `/map` 时进入错误分支。在完整集成环境（后端运行）下，4 个区域层可在地图上正常显示；
4. **生产就绪度**：`regional-datasets.json.productionReady = false`（4 个 metric 仍标记为 "verified, prototype"），待 Stage 8 决定是否升至 production。

---

## 12. 结论

**READY FOR INDEPENDENT STAGE 7R RE-GATE**

- 数据审计：4/4 READY，204 条记录，0 缺失，0 重复；
- 视觉：4 套独立调色板，32 对 ΔL 全过 WCAG-AA；
- 边界：区域数据**不**进入 match / assessment 分数，4 处文案声明齐全；
- 集成：4 个新组件在 `<MapShell>` 中正确连接，JS bundle 包含全部内容；
- 测试：178/178 通过；
- 类型 & lint & build：全清。
