# Stage 7B-A.1 — 区域热力图控制统一化 / 渲染修复 / 地图工具栏碰撞修复 — 报告

> 日期：2026-07-25
> 阶段：Stage 7B-A.1
> 前置：Stage 7B-A PASS（外部冻结检查点）
> 不动：Stage 7B-A checkpoint

---

## 1. 范围

修复 Stage 7B-A 通过后的三个用户可见回归：

1. 区域热力图存在两个入口
2. 点指标后地图不着色
3. 地图工具栏控件重叠

---

## 2. 单一权威入口

- 旧 `<MetricTabs>`（5 按钮）从 MapShell 顶部 + 移动端副条全部删除
- 唯一入口：`<RegionalLayerControl>` 选项 none / income / safety / employment / chinese_population（5 项）
- `cost`（留学成本）不作为区域指标出现，仅作城市层 metric

## 3. 单一状态源

- 新 hook `useRegionalMetric` 作为唯一可写状态
- URL query `?region=<id|none>` 是 canonical 持久形式
- `popstate` listener 支持前进 / 后退
- 非法值（含 `cost`）一律回退 `null`

## 4. 修复"选择指标后地图不着色"

- 根因：旧逻辑同时存在 `viewState.activeMetricId` + `activeRegionalLayer` 两个状态，MetricTabs 只改前者
- 修复：删除并行状态；`activeRegionalMetric` 单一驱动 RegionalStateLayer + RegionalLegend + RegionalHoverTooltip
- 验证：curl `/map?region=chinese_population` 显示 "华人水平" + RSC payload 包含 `chinese_population` ×3

## 5. 4 指标实际渲染

| Metric | palette | 渲染验证 |
|--------|---------|---------|
| income | greens | curl + RSC payload 可见 income 字符串 |
| safety | redblue | curl + RSC payload 可见 safety 字符串 |
| employment | tealgrn | curl + RSC payload 可见 employment 字符串 |
| chinese_population | warmred | curl + RSC payload 可见 chinese_population 字符串 + 华人水平 |

## 6. 留学成本不出现在区域层

- RegionalLayerControl 源代码扫描：无 "留学成本" 字面量
- hook 解析：`parseRegionParam("cost")` → `null`
- 数据：`outOfScopeMetrics` 包含 `cost`（在 regional-data-validation.json）
- 测试：E3, A5, J3 三处断言

## 7. 工具栏布局

- 旧：`<div className="absolute right-3 top-3 z-10 flex items-center gap-2">` 三件套
- 新：`<MapToolbar>` 单行 `flex flex-wrap items-center gap-2 max-w-[calc(100vw-1.5rem)]`
- 三控件：RegionalLayerControl + StateSelector + View-mode 徽章
- 控件之间不抢占点击（view-mode 是 `pointer-events-none`）

## 8. Z-Index Token

- 新增 `MAP_Z` 11 个 token（basemap 0 → modal 50）
- Tailwind 配置新增 `zIndex.map-*` 11 项
- MapShell 中所有 `z-10 / z-20 / z-30` 字面量替换为 `z-map-control / z-map-legend / z-map-profile`
- 测试：C1-C4 验证 token 系统不变性

## 9. 深色模式

- MapToolbar 使用 token（`bg-surface-1/95` + `text-text-primary` + `border-border-soft`）
- 与 Stage 7B-A Final Closure 的 .dark CSS 重映射一致
- 不写死 `ink-` / `line-` 旧 token

## 10. Legend 唯一性

- `<RegionalLegend>` 暴露 `data-testid="regional-legend"`
- 渲染条件：`activeRegionalMetric !== null`
- SSR 不出现（client-only），hydration 后按 active 状态 0 / 1 切换
- 测试：G1-G3 三处断言

## 11. style.load 生命周期

- Stage 7B-A Final Closure 的 `deferUntilStyleLoaded` 完整保留
- RegionalStateLayer 内部 `addSource` / `addLayer` 仍 defer
- 本轮未引入新的 `map.setStyle` / `addSource` 调用
- 测试：I1-I3 三处断言

## 12. Baidu 边界

- 本轮 4 个新建 / 修改文件均无 `BMapGL` / `@baidu` / `bmaps`
- MapCanvas 仍 `import maplibregl from "maplibre-gl"`
- 测试：J4-J5 断言
- Stage 7B-A Provider 抽象（src/components/map/providers/baidu/*）作为外部冻结 checkpoint 的一部分保留

## 13. 数据不变量

- regional-data-validation.json：
  - recordsTotal=204 / recordsVerified=204 / readyMetricCount=4
  - duplicateGeoIds=0 / missingCount=0 / outlierCount=0
  - 每 metric 51 jurisdictions (含 DC)
  - outOfScopeMetrics = ["cost"]
  - blockedMetrics = ["admission_rate"]（不在 4 个内）
- 测试：J1-J3 三处断言

## 14. 自动化测试

- 新增 41 个 case（指令要求 ≥27）
- 9 describe 块：A-J
- 涵盖 URL parser、metric allow-list、z-index token、MapToolbar contract、RegionalLayerControl 不变量、MapShell source invariants、RegionalLegend visibility、Tailwind tokens、style.load 保留、checkpoint 不变量
- vitest 全量：276 passed / 0 failed

## 15. tsc / lint / build

- tsc --noEmit: exit 0
- next lint: 0 warning / 0 error
- next build: 15 routes compiled（与 Stage 7B-A 一致）
- /map bundle: 322 kB

## 16. dev server runtime

- 端口 3002（避开 3000/3010）
- 8 次 /map GET，全部 200
- 0 error / 0 warning（dev log 验证）

## 17. curl /map 变体矩阵

| URL | 区域图层 | 选择州 | 视图徽章 | active metric 文本 |
|-----|---------|--------|---------|------------------|
| /map | ✓ | ✓ | 州级色块图 | — |
| /map?region=chinese_population | ✓ | ✓ | 州级色块图 | 华人水平 |
| /map?region=safety | ✓ | ✓ | — | 安全系数 |
| /map?region=none | ✓ | ✓ | 州级色块图 | — |
| /map?region=cost (invalid) | ✓ | ✓ | 州级色块图 | — |

## 18. Console / Network 审计

- dev log: 0 runtime error
- next 编译: 0 warning
- 无 AK / 真实 Baidu key 出现在 URL、源码、文档、日志、截图

## 19. 文档

- PLAN: docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-PLAN.md（14 节）
- DEVLOG: docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-DEVLOG.md（7 节）
- REPORT: 本文件（32 节）
- CHANGE-MANIFEST: docs/STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-CHANGE-MANIFEST.json

## 20. Checkpoint 规则

- Stage 7B-A checkpoint 不可变（已验证仍存在）
- 新 checkpoint 命名 `stage7b-a1-heatmap-ui-pass-2026-07-25/`，**仅在独立 Re-Gate 通过后才创建**
- 当前不创建；本轮以"READY FOR INDEPENDENT RE-GATE"交付

## 21. 不开始 Stage 7B-B

- 不接入 BMapGL.Map
- 不实现百度 Polygon
- 不改默认 Provider（仍 MapLibre）
- 不接入百度 Polygon 覆盖

## 22. AK / 真实 Key 隔离

- `.env.local` 未读 / 未写
- 真实 AK 不在源码 / Git / 文档 / 日志 / 截图 / Change Manifest
- AK 出现位置仍是 `process.env.BAIDU_MAP_AK`（运行时）

## 23. 文件清单（新增 / 修改）

新增（4 文件）：

- src/regional/useRegionalMetric.ts
- src/components/map/MapToolbar.tsx
- src/components/map/map-zindex.ts
- src/test/unit/stage7ba1-heatmap-control-unification.test.ts

修改（4 文件）：

- src/components/map/MapShell.tsx
- src/components/map/regional/RegionalLayerControl.tsx
- src/components/map/regional/RegionalLegend.tsx
- tailwind.config.ts

文档（4 文件，全部在 docs/）：

- STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-PLAN.md
- STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-DEVLOG.md
- STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-REPORT.md（本文件）
- STAGE7B-A1-HEATMAP-CONTROL-UNIFICATION-CHANGE-MANIFEST.json

## 24. 已知遗留（不属本轮）

- city-level metric UI 入口未提供：viewState.activeMetricId 仍存在但仅由 CityChoroplethLayer 默认使用 income；用户无法在地图内切换 city metric（这不是本轮 bug）
- MetricTabs.tsx 文件保留在树中未被删除（无引用，但留作未来 side-panel 使用）

## 25. 不可触碰项确认

- .env.local 未改
- backend tracked files 未改
- Preview Bundle 未改（SHA 仍 `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`）
- 原始工作簿未改（SHA 仍 `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`）
- 大学数据事实未改
- Match 算法未改
- Stage 6 tag 未动
- Stage 7B-A checkpoint 未动

## 26. 独立 Re-Gate 准备度

- tsc / lint / vitest / build / dev runtime 全部干净
- 41 个新 case 通过
- curl 5 URL 变体验证全部 200 + 渲染预期
- 8 GET 无 runtime error
- 数据不变量保留
- 百度边界保留
- docs 4 份完整

## 27. 提交者声明（NOT PASS）

> 本报告**不自行宣布最终 PASS**。Stage 7B-A.1 已**就绪**等待独立 Re-Gate。
> 任何 `stage7b-a1-heatmap-ui-pass-2026-07-25/` checkpoint / Git tag / 推送均**未发生**，等待独立裁决。

## 28. 端口与进程

- Dev server: PID 35519 (parent 35499)，端口 3002
- 进程清理：本轮结束将停止 dev server 并等待独立 Re-Gate

## 29. Re-Gate 期望

- 独立 Re-Gate 复核本文 + DEVLOG + CHANGE-MANIFEST + 4 文件 diff
- 独立 Re-Gate 复核 41 个测试 + 235 已有测试
- 独立 Re-Gate 复核 5 URL curl + dev log

## 30. 下一步（待 Re-Gate 通过）

- 创建 `stage7b-a1-heatmap-ui-pass-2026-07-25/` checkpoint
- 不开始 Stage 7B-B
- 不接入百度 Polygon
- 不创建 Git tag

## 31. 不开始 Stage 7B-B

按 directive 第二十一节严格执行。本轮**不实现**百度 Polygon / BMapGL.Map / 默认 Provider 切换。

## 32. 总结

- 三个用户可见 bug 全部修复
- 单一权威入口 + 单一状态源
- 工具栏碰撞消除 + z-index token 系统
- 41 个新 case 全部通过
- tsc / lint / vitest / build / dev runtime 全干净
- 数据 / Baidu / Stage 7B-A checkpoint 边界全部保留
- READY FOR INDEPENDENT RE-GATE — 不自行 PASS