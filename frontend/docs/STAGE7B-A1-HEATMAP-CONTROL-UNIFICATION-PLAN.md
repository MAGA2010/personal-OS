# Stage 7B-A.1 — 区域热力图控制统一化 / 渲染修复 / 地图工具栏碰撞修复 — 计划

> 日期：2026-07-25
> 阶段：Stage 7B-A.1
> 前置：Stage 7B-A PASS（MapLibre path） / Baidu runtime 仍 BLOCKED
> 不动：Stage 7B-A checkpoint（不可变回滚基线）

---

## 一、问题陈述

用户在真实界面发现：

1. 区域热力图存在两个入口（顶部 5 按钮 + 区域图层下拉）；
2. 点击顶部按钮选择指标后，地图仍不显示州级颜色；
3. 地图按钮、区域图层控件、"选择州"控件拥挤或重叠。

源码与浏览器复现已确认：

| 维度 | 旧入口（删除目标） | 新入口（保留目标） |
|------|-------------------|-------------------|
| 文件 | `src/components/map/MetricTabs.tsx` | `src/components/map/regional/RegionalLayerControl.tsx` |
| 部署位置 | MapShell 顶部（lines 581-582 desktop）+ 移动端副条（lines 627-628） | MapShell 工具栏右上（lines 758-760） |
| 状态变量 | `viewState.activeMetricId`（MapViewState 字段） | `activeRegionalLayer`（MapShell 局部 useState） |
| 状态写入 | `setViewState(...)` via `handleMetricChange` | `setActiveRegionalLayer(next)` |
| 驱动层 | CityChoroplethLayer / CityDetailPanel / UniversityPoiLayer / ComparePanel | RegionalStateLayer / RegionalLegend / RegionalHoverTooltip |
| 选项 | 5 项：income / safety / employment / **cost（留学成本）** / chinese_population | 5 项：none + income / safety / employment / chinese_population |
| URL 同步 | 无 | 无 |

**根因（已复现确认）**：

- 顶部按钮点击后只更新 `viewState.activeMetricId`，不更新 `activeRegionalLayer`。
- `RegionalStateLayer` 监听的是 `activeRegionalLayer`，从未变化，仍是 `null` → 不挂 fill layer。
- `RegionalLegend` 由 `activeRegionalLayer` 守卫，仍是 `null` → 不显示。
- 因此"上方选中华人水平、下方仍为不显示、地图不着色"是必然行为。

**预期根因之一 "legacy selectedMetric 与 activeRegionalLayer 是两个独立状态" —— 已通过源码 + curl /map 渲染 HTML 双重确认。**

---

## 二、本轮目标（11 项）

1. 删除旧 5 按钮入口（顶部 + 移动端副条）
2. 保留并加强新 RegionalLayerControl（唯一区域热力图入口）
3. 单一状态源：`activeRegionalMetric`
4. Layer / Legend / Tooltip / URL 全部读取同一状态
5. 修复"选择指标后地图不着色"
6. 4 个指标（income / safety / employment / chinese_population）均可实际渲染
7. 留学成本（cost）不得作为区域指标出现
8. 地图工具栏重新布局：单组 / flex-wrap / 最小间距
9. 引入 z-index token 系统
10. 深色模式可读性保持
11. 数据不变量 / Stage 7B-A checkpoint / 百度边界全部保留

---

## 三、状态设计

### 3.1 新 hook

文件：`src/regional/useRegionalMetric.ts`

```typescript
type ActiveRegionalMetric = RegionalMetricId | null;

const URL_PARAM = "region";
const VALID_VALUES = [null, ...REGIONAL_METRIC_IDS] as const;

// Returns [value, setValue] tuple backed by URL query param `region`
// Invalid → null fallback
// Back/forward → popstate listener re-reads URL
function useRegionalMetric(): readonly [
  ActiveRegionalMetric,
  (next: ActiveRegionalMetric) => void
]
```

- URL key: `?region=chinese_population` / `?region=none`
- 默认值: `null`（无区域图层）
- 唯一所有权：所有调用方只能读取，不能写状态

### 3.2 删除的并行状态

- 旧 `viewState.activeMetricId` 仅保留作为**城市层级**指标
- 旧局部 `activeRegionalLayer` 状态被替换为 hook

### 3.3 MetricTabs 处理

`MetricTabs.tsx` 当前驱动 CityChoropleth，但 cost 不属于区域指标。处理方案：

- **删除**：`MetricTabs` 在 MapShell 的两处调用（顶部 + 移动端副条）
- **保留文件**：`MetricTabs.tsx` 保留（仍可能被侧边面板等使用），但导入从此 MapShell 路径断开
- **成本指标迁移**：城市层级指标 `viewState.activeMetricId` 保留，但 UI 入口迁入 `SidebarEmptyState` 或 `CityDetailPanel` 顶部——细节在实施中确认
- **禁止**：`cost` 不得在区域入口出现

### 3.4 单状态源消费图

```
URL ?region=...
  ↓ parseFromUrl (invalid → null)
useRegionalMetric hook  ←─── 唯一可写状态源
  ├── RegionalLayerControl (UI 触发)
  ├── RegionalStateLayer (Layer 安装 + 数据)
  ├── RegionalLegend (legend 渲染 + 0/1 守卫)
  ├── RegionalHoverTooltip (tooltip 内容)
  ├── MapToolbar (active 状态徽章)
  └── Browser back / forward (popstate)
```

---

## 四、工具栏布局

### 4.1 新 MapToolbar

位置：MapShell 内部，地图右上，absolute top-3 right-3

```
┌─────────────────────────────────────────────┐
│ RegionalLayerControl │ StateSelector │ (help)│
└─────────────────────────────────────────────┘
                       (flex-wrap / gap-2 / items-center)
```

- `flex flex-wrap items-center gap-2`
- 控件最小宽度 32px
- 不与右侧 Profile 卡片重叠（Profile z=30，Toolbar z=20）
- 不与左下 Legend 重叠（Legend 在 bottom-4 right-4，宽度 ≤ 320）

### 4.2 删除项

- 顶部 5 按钮（`<MetricTabs>` 顶部 hidden lg:block）
- 移动端副条 5 按钮（`<MetricTabs>` lg:hidden）
- Calculator / Sparkles / PanelLeft 仍保留（属于地图外导航）

### 4.3 Z-index token

文件：`src/components/map/map-zindex.ts`（新建）

```typescript
export const MAP_Z = {
  basemap:    0,
  region:     5,
  city:      10,
  marker:    15,
  hover:     18,
  control:   20,
  toolbar:   22,
  legend:    24,
  tooltip:   28,
  profile:   30,
  modal:     50,
} as const;
```

- 所有 `z-10/z-20/z-30` 改为 `z-[var(--map-z-toolbar)]` 等
- Tailwind 配置：`theme.extend.zIndex` 加入 token

---

## 五、修复"选择指标后地图不着色"

根因：`RegionalStateLayer.activeMetricId === null` → install 内部 removeLayer 后不再 add。

修复链路：

1. URL `?region=chinese_population` → hook `activeRegionalMetric = "chinese_population"`
2. MapShell `<RegionalStateLayer activeMetricId={activeRegionalMetric} ... />`
3. `RegionalStateLayer` 内部 effect 在 `activeMetricId !== null` 时调用 `installSourceAndLayers`
4. MapLibre runtime 验证（Section 八）：`map.getSource('pathos-regional-states')`、`map.getLayer('pathos-regional-states-fill')`、`map.getPaintProperty(..., 'fill-color')` 均非空

---

## 六、4 项实际显示验证

逐项验证（详见 Section 八 + Section 十七 浏览器矩阵）：

| 指标 | 期望颜色 | palette |
|------|---------|---------|
| income | 绿色 | `greens` |
| safety | 蓝（diverging） | `redblue` |
| employment | 紫色 / teal | `tealgrn` |
| chinese_population | 橙 / 橙红 | `warmred` |

**关键约束**：每次只能 1 个 layer active；切指标时旧 fill-color 被 setPaintProperty 覆盖，不出现叠加；none 状态下 fill-opacity 由 case 表达式降为 0。

---

## 七、Legend 唯一性

- visible `RegionalLayerControl` 数 = 1（data-testid="regional-layer-control"）
- visible `RegionalLegend` 数：0（metric=null）或 1（metric≠null）
- 旧 `MapLegend.tsx` 不再被任何代码 mount（保留文件但无导入）

新增断言测试：

```typescript
expect(screen.queryAllByTestId('regional-layer-control')).toHaveLength(1);
expect(screen.queryAllByTestId('regional-legend').length).toBe(activeMetric ? 1 : 0);
```

---

## 八、style.load 压力测试

复用 Stage 7B-A Final Closure 的 `deferUntilStyleLoaded`：

- 初次加载 + 立即选指标
- light → dark / dark → light
- 快速切 5 次主题
- 快速切 4 个指标
- none → metric → none
- 离开 /map 后返回
- React Strict Mode 双挂载

不得出现：
- Style is not done loading
- Source already exists
- Layer already exists
- Cannot add source / layer
- 图层消失 / 地图无颜色

---

## 九、深色模式

新统一工具栏：

- 按钮：dark 下使用 `bg-surface-1/95 text-text-primary`，与 Stage 7B-A Runtime Closing 的 .dark CSS 重映射保持一致
- 下拉：保持现有 focus-visible:ring-focus-ring
- 图标：cobalt / jade 在 dark 下保持 13.78:1 通过

实测 viewport：

- 1280×720
- 1440×900
- 1920×1080
- Tablet 768×1024
- Mobile 390×844

---

## 十、数据不变量

保持：

- schoolCount=62 / summaryCount=62 / detailCount=62 / verifiedRecordCount=904
- regionalMetricCount=4 / regionalRecordCount=204 / regionalJurisdictionCount=51 / regionalDuplicateCount=0 / regionalMissingCount=0
- Preview Bundle SHA = `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Backend HEAD = `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Backend 文件 + Bundle 文件不被修改（只读）

---

## 十一、自动测试新增

至少 27 项（Section 十六清单）。优先 Vitest + jsdom / @testing-library/react：

1. visible `regional-layer-control` count = 1
2. legacy `metric-tabs` DOM count = 0（顶部 + 移动端副条均移除）
3. cost 不作为区域选项
4. hook 状态唯一
5-9. five values: null / income / safety / employment / chinese_population
10. invalid URL → null
11. back / forward
12. refresh
13-17. active 驱动 Layer / Legend / Tooltip / Source Panel / 唯一性
18-22. layer visible / fill-opacity > 0 / correct palette / one layer / none 关闭
23. legend count (0/1)
24. toolbar collision
25. mobile control exclusivity
26. theme switching
27. style.load
28. university marker retained

---

## 十二、文档

按 directive 第十九条：

- `docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-PLAN.md`（本文件）
- `docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-DEVLOG.md`
- `docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-REPORT.md`（32 节）
- `docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-CHANGE-MANIFEST.json`

---

## 十三、Checkpoint 规则

不动：`/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/`

新 checkpoint：**等待独立 Re-Gate 通过后才创建**：

```
/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a1-heatmap-ui-pass-2026-07-25/
```

不得在 Re-Gate 前创建"pass"命名 checkpoint。

---

## 十四、阶段范围

- **不开始**：Stage 7B-B
- **不接入**：BMapGL.Map / 百度 Polygon / 改默认 Provider
- **不修改**：Backend tracked files / Preview Bundle / 原始工作簿 / 大学数据 / 区域数据 / Match 算法 / Stage 6 tag
- **不创建**：Git tag / push / 自宣布 PASS