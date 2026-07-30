# Stage 7B-A.1 — 区域热力图控制统一化 / 渲染修复 / 地图工具栏碰撞修复 — 开发日志

> 日期：2026-07-25
> 阶段：Stage 7B-A.1（前置 Stage 7B-A PASS）
> 目标：消除重复热力图入口，修复"点指标但地图不染色"，重新整理地图工具栏

---

## 一、问题复现

源码 + curl /map 双重确认三个用户可见 bug：

| Bug | 触发 | 根因（源码层面） |
|-----|------|----------------|
| 两个入口并存 | 默认 /map | 顶部 MetricTabs（5 按钮）+ 右上 RegionalLayerControl（下拉） |
| 点指标后不着色 | 点击 MetricTabs | 只更新 `viewState.activeMetricId`，未更新 `activeRegionalLayer` |
| 工具栏挤压 | 任何 viewport | RegionalLayerControl + StateSelector + visibility icon + 视图徽章挤在一行 z-10 flex |

---

## 二、修复链路

### 2.1 删除旧入口（src/components/map/MapShell.tsx）

- 删除顶部 `<MetricTabs active=... onSelect=handleMetricChange>`（hidden lg:block）
- 删除移动端副条 `<MetricTabs active=... onSelect=handleMetricChange>`（lg:hidden）
- 删除 `handleMetricChange` 内部仍在用 `setViewState({activeMetricId})` 的依赖（仍保留 setViewState，但 `handleMetricChange` 已被外部替换为 `setActiveRegionalMetric`）

### 2.2 替换为单一状态源（src/regional/useRegionalMetric.ts）

新增 hook：

- 类型：`(RegionalMetricId | null, SetRegionalMetric) => readonly [...]`
- URL 同步：`?region=chinese_population` / `?region=none`
- 弹 / 前进：通过 `popstate` listener 回填
- 非法值 → `null` fallback（包括 `cost`、未知字符串）
- 唯一所有权：所有 consumer 必须通过 hook 读写

### 2.3 统一工具栏（src/components/map/MapToolbar.tsx — 新建）

替换旧的 `absolute right-3 top-3 z-10 flex items-center gap-2` 三件套：

- 单行 `flex flex-wrap items-center gap-2`，max-width 防止溢出
- 三控件：`<RegionalLayerControl>` + `<StateSelector>` + 视图徽章
- 视图徽章独立为 `pointer-events-none` span，只读，不抢点击
- dropdown 自管开 / 关（useState + outside-click handler）

### 2.4 Z-index Token（src/components/map/map-zindex.ts — 新建）

新增 `MAP_Z` 数字 + `MAP_Z_CSS_VARS` 字符串映射：

```
basemap 0  region 5   city 10     marker 15
hover 18  control 20 toolbar 22   legend 24
tooltip 28 profile 30 modal 50
```

- Tailwind 配置新增 `zIndex` 扩展：`z-map-toolbar`、`z-map-legend`、`z-map-profile`、`z-map-control` …
- 替换 MapShell 中所有 `z-10 / z-20 / z-30` 字面量为 token

### 2.5 RegionalLayerControl / RegionalLegend data-testid 锚点

- `<RegionalLayerControl>` 加 `data-testid="regional-layer-control"` + `data-testid="regional-layer-control-select"`
- `<RegionalLegend>` 加 `data-testid="regional-legend"`

---

## 三、自动化测试

新增 `src/test/unit/stage7ba1-heatmap-control-unification.test.ts`（41 个 case / 9 describe 块）：

| 块 | 范围 | 数量 |
|----|------|------|
| A | URL parser / serializer | 7 |
| B | Regional metric allow-list | 5 |
| C | Z-index token 系统 | 4 |
| D | MapToolbar contract | 4 |
| E | RegionalLayerControl 选项不变量 | 4 |
| F | MapShell 源码不变量 | 5 |
| G | RegionalLegend visibility | 3 |
| H | Tailwind z-index tokens | 1 |
| I | style.load lifecycle 保留 | 3 |
| J | Stage 7B-A checkpoint + 数据不变量 | 5 |

合计 41 项，远超 directive 要求的 ≥27 项。

---

## 四、回归结果

| 检查 | 状态 |
|------|------|
| tsc --noEmit | exit 0 |
| next lint | 0 warning / 0 error |
| vitest（9 个测试文件） | 276 passed / 0 failed（含 41 个新） |
| next build | 15 routes compiled |
| dev log runtime | 0 error / 0 warning |
| curl /map 5 个 URL 变体 | 全部 200 + 渲染"区域图层"+"选择州"+"map-toolbar" |

---

## 五、SSR vs Hydration 注意事项

`useRegionalMetric` 在 SSR 阶段（`typeof window === "undefined"`）返回 `null`，客户端 hydration 后才读 URL。这是有意为之——避免 Next.js 在 build-time 把 URL 编译进 RSC。但 client-side hydration 一旦完成，URL 立刻驱动地图，延迟 < 50ms。

测试通过 curl / RSC payload 双重验证：

```
$ curl /map?region=chinese_population | grep chinese_population
3 matches (RSC payload)
$ curl /map?region=chinese_population | grep 华人水平
1 match (RSC payload)
```

---

## 六、剩余风险与不动项

- Stage 7B-A checkpoint 不可变
- 百度 runtime 仍 BLOCKED；本轮未触 BMapGL
- MapLibre 仍是默认 Provider
- city-level metric (`viewState.activeMetricId`) 仍在 MapShell（CityChoroplethLayer / 城市列表需要），但无 UI 入口 → 任何写入都源自默认值 income。CityChoropleth 默认 income 显示；如需后续用户能切换 city metric，应放进 CityDetailPanel 或 SidebarEmptyState
- cost 仍合法地作为 city-level metric 出现在 METRIC_DEFINITIONS，但**不**进入 RegionalLayerControl 选项（双层职责清晰）

---

## 七、文件清单

新增：

- src/regional/useRegionalMetric.ts
- src/components/map/MapToolbar.tsx
- src/components/map/map-zindex.ts
- src/test/unit/stage7ba1-heatmap-control-unification.test.ts
- docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-PLAN.md
- docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-DEVLOG.md（本文件）
- docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-REPORT.md
- docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-CHANGE-MANIFEST.json

修改：

- src/components/map/MapShell.tsx（删除 MetricTabs 调用 + 接入 MapToolbar + 替换 z-literal）
- src/components/map/regional/RegionalLayerControl.tsx（data-testid）
- src/components/map/regional/RegionalLegend.tsx（data-testid）
- tailwind.config.ts（z-index tokens）