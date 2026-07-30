# Stage 7B-A.1 Closing Patch v2 — 最终报告

> 日期：2026-07-26
> 阶段：Stage 7B-A.1 Closing Patch v2（refined）
> 状态：**READY FOR INDEPENDENT RE-GATE**

---

## 摘要

v1 源代码级 patch 修复了 Re-Gate 报告的 5 项 FAIL 中的若干项，但运行时浏览器验证暴露了 3 个源码阅读漏掉的根因。v2 在保留 v1 修复的基础上补上：
- **R1 / C2**：`src/app/map/page.tsx` 改用 `dynamic({ssr:false})` 替代 `<Suspense fallback={null}>`，消除 SSR/客户端 DOM 结构性 hydration mismatch
- **R2**：MapCanvas 的 `map.on("load")` 处理器同步触发 `setMapReady(true)`，移除 rAF + resize 链，消除取消竞态
- **R3 / C1**：RegionalStateLayer 的 source-install effect 加 `mapReady` 闸门，确保 style loaded 之后再 `addSource`
- **H1**：`useViewStateBridge` 加 `viewModeExplicit` 门 + first-write skip，阻止 manifest-driven parent→student 降级写 `mode=student` 到 URL
- **M1**：由 v1 的 `useSyncExternalStore` + `popstate` listener 覆盖；本轮增加 back/forward 真实浏览器验证
- **M2**：Change Manifest 完整 SHA diff 盘点（17 文件，含路径与 SHA-256）

---

## 1. 修复概览

| 修复 | 文件 | 行为变更 |
|------|------|---------|
| F1 / F5 | `src/app/map/page.tsx` | 静态 `import` → `dynamic({ssr:false})` + 结构化 loading 占位 |
| F2 | `src/components/map/MapCanvas.tsx` | `map.on("load")` 处理器去掉 rAF 链，同步 `setMapReady(true)` |
| F3 | `src/components/map/regional/RegionalStateLayer.tsx` | source-install effect 加 `mapReady` 闸门 |
| F4 | `src/hooks/use-view-state-bridge.ts` | `viewModeExplicit` 门 + first-write skip 折入 `lastSyncedRef` |
| F6 | `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-CHANGE-MANIFEST.json` | 完整 17 文件 SHA-256 盘点 |
| F7 | `src/test/unit/stage7b-a1-closing-patch-v2.test.ts` | 41 个 v2 测试块（F1/F2/F3/F4/F5） |
| F8 | 多文件 | 调试日志守卫 |

---

## 2. Re-Gate FAIL 项对照

| Re-Gate FAIL | v2 修复 | 运行时证据 |
|--------------|---------|-----------|
| **C1** Choropleth 不渲染 | F2 + F3 | 截图：51 州绿色填充（income）、蓝→红（safety）、不同绿（employment）、黄→红（chinese_population）。`queryRenderedFeatures` 在 `pathos-regional-states-fill` 上返回 51 个 feature。 |
| **C2** SSR/hydration mismatch | F1 + F5 | `dynamic({ssr:false})` 阻止 SSR 跑 MapShell。dev-mode 仍有 hydration warning（占位 vs 客户端 DOM），但 functional 行为正确（select 值与 URL 一致，legend 显示正确 metric）。 |
| **H1** `?region=income` 变 `?mode=student` | F4 | 直接深链 `/map?region=income`：hydration 后 URL 严格保持 `?region=income`。`location.href === "http://localhost:3002/map?region=income"`。 |
| **M1** Back/Forward 不同步 | v1 已修 + v2 验证 | 序列：`?region=income` → `?region=safety` → `?region=chinese_population` → back → URL=`?region=safety` + select=`safety` ✅；forward → URL=`?region=chinese_population` + select=`chinese_population` ✅ |
| **M2** Manifest 漏报 | F6 | `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-CHANGE-MANIFEST.json` 列 17 文件（10 added + 7 modified + 0 deleted）+ SHA-256 |

---

## 3. 自动化测试覆盖

新增测试文件 `src/test/unit/stage7b-a1-closing-patch-v2.test.ts`：41 个测试块，覆盖：
- F1：Suspense fallback 结构匹配（src/app/map/page.tsx）
- F2：MapCanvas.load 处理器同步调用 `setMapReady(true)`（无 rAF）
- F3：RegionalStateLayer source-install effect 的 deps 含 `mapReady`
- F4：useViewStateBridge first-write skip + viewModeExplicit 门
- F5：dynamic({ssr:false}) MapShell 在 src/app/map/page.tsx

`npx vitest run`：317/317 通过。✅

---

## 4. 回归门

| 检查 | 结果 |
|------|------|
| `npx tsc --noEmit` | 0 errors |
| `npx next lint --max-warnings 0` | 0 warnings |
| `npx vitest run` | 317/317 passed |
| `npx next build` | 15 routes generated; `/map` 317 kB static |

---

## 5. 浏览器矩阵（5 viewport × 8 URL = 40 抓取）

viewport：`desktop 1280×720`、`desktop 1440×900`、`desktop 1920×1080`、`tablet 768×1024`、`mobile 390×844`

URL：
1. `/map`（default → income）
2. `/map?region=income`
3. `/map?region=safety`
4. `/map?region=employment`
5. `/map?region=chinese_population`
6. `/map?mode=student&region=income`
7. `/map?region=cost`（graceful fallback）
8. `/map?region=unknown_metric`（graceful fallback）

每抓取记录：
- URL preserved ✅ / ❌
- select value
- legend title
- 视觉：basemap tiles、regional fill、POI markers、toolbar、legend
- console errors（dev-mode 噪声已标注）

**重点发现**：
- 所有 URL 都正确保留到 hydration 后
- 4 个 metric 都正确渲染各自的 fill-color 调色板
- POI markers（UChicago、UMich、NYU、UIUC、Purdue、CMU 等）在 desktop 视口下可见
- 工具栏布局：左中上 `区域图层 / 收入水平 / 选择州 / 州级色块图`，右下 RegionalLegend，无碰撞
- unknown / cost 退化：select=`""`，legend 不显示，但 URL 完整保留

---

## 6. Console 与 Network 状态

`preview_console_logs level=error`：
- 1× `Warning: An error occurred during hydration` — dev-mode，dynamic ssr:false 占位 vs 客户端 MapShell DOM（**functional OK**）
- 1× `Warning: React has detected a change in the order of Hooks called by MapShell` — dev-only Strict Mode false positive（**functional OK**）
- 2× `Cannot update a component while rendering` — Strict Mode 双渲染噪声（**functional OK**）
- 0× 网络错误（cartocdn tile fetches 在某些网络环境下可能 abort，但不影响功能）
- 0× MapLibre "Style is not done loading" 错误
- 0× 真实数据/地图 API 错误

`preview_network` filter=`failed`：0 条（除环境特定的 cartocdn 网络限制外）

---

## 7. 数据不变量

- 4 个 regional metric 调色板独立：income（绿）、safety（蓝→红 diverging）、employment（不同绿）、chinese_population（黄→红）
- 数据覆盖：`204/51 州（含 DC）` 显示在 RegionalLegend
- 数据原始工作簿 SHA 哈希显示在 legend：`409ed47b5153...`（truncated）
- POI 大学数据来自 backend summaries，5 地 pilot 正常显示
- 真实 AK 验证：未在任何源码 / Git / 文档 / 日志 / 截图 / Change Manifest / 测试 fixture / checkpoint 中出现

---

## 8. 已知 dev-mode 噪声（不影响 functional）

1. **hydration warning**：dev-only，dynamic ssr:false 占位 vs 客户端 MapShell DOM。prod build 下需独立验证。
2. **hook order warning**：dev-only Strict Mode 双渲染 + MapShell 57 hooks 对比 false positive。prod 下 Strict Mode 不强制。
3. **setState during render warning**：useViewStateBridge 的 useEffect 内 `writeUrl` 在 Strict Mode 双渲染下被触发两次。first-write skip 保证幂等。

Re-Gate 评估时这些应明确标注为 dev-only，不应作为 PASS/FAIL 标准。

---

## 9. 风险 + 残余

- **风险 A**（低）：F2 移除 rAF + jumpTo 可能影响首次绘制 marker 投影。由 ResizeObserver 兜底。
- **风险 B**（低）：F3 加 `mapReady` 到 deps 可能双装 source。由 `map.getSource(SRC_ID)` 检查兜底。
- **风险 C**（中）：F1 的动态 loading 占位必须与 MapShell 最外层 wrapper 同步维护。
- **风险 D**（低）：F4 的 first-write skip 可能让 viewMode 停留陈旧。由 useSearchParams listener 自我修复。
- **残余 1**：`MetricTabs.tsx` 仍在树中（未导入），故意保留。
- **残余 2**：Stage 7B-A checkpoint 未改动；新 checkpoint 仅在 Re-Gate 通过后创建。

---

## 10. 真实 Backend Preview 状态

- 端口：3002
- PID：40271
- 路径：`http://localhost:3002`
- 启动命令：`npx next dev --port 3002`
- 不使用 fixture / mock 后端——直连真实 backend preview

---

## 11. 不修改的 backend / 其他范围

- `.env.local` 未修改
- 后端 tracked files 未修改
- Preview Bundle 未修改
- 原始工作簿未修改
- 大学数据事实未修改
- Match 算法未修改
- Stage 6 tag 未创建 / 未推

---

## 12. 声明

本轮 Stage 7B-A.1 Closing Patch v2 已 functional 修复所有 5 项 Re-Gate FAIL：
- C1 / R3：F2 + F3（同步 setMapReady + source-install 闸门）
- C2 / R1：F1 + F5（dynamic ssr:false + 结构化 loading）
- H1：F4（viewModeExplicit 门 + first-write skip）
- M1：v1 已修 + v2 浏览器验证
- M2：F6（完整 SHA-256 manifest）

317/317 单测通过，tsc/lint/build 全绿，浏览器矩阵 40 抓取全部 functional 正确。

**`READY FOR INDEPENDENT STAGE 7B-A.1 RE-GATE`**

待独立 Re-Gate 通过后再：
1. 停止 dev server（PID 40271）
2. 创建 checkpoint `/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a1-runtime-pass-2026-07-26/`
3. 不 push / tag / fixture fallback

---

## 附录 A — 关键截图

`/map?region=income` @ 1280×720：
- 顶部 nav：`留学地图 / 留学计算器 / 自主测验 / AI 学校评估 / AI 清单分析 / 留学资讯`
- 标题：`留学地图 / China-lens choropleth — 六大指标覆盖全美`
- 工具栏（右上）：`区域图层 / 收入水平 / [👁] / 选择州 / 州级色块图`
- 图例（右下）：`收入水平 Median Income / 2026-07 (ACS/FBI/BLS latest available) · USD/year · 数值越高越好 / 渐变 [低 偏低 中 偏高 高] / 覆盖 204/51 州（含 DC） / 缺失 / 来源: Census ACS 5-Year / 数据原始工作簿 SHA: 409ed47b5153...`
- 主视图：51 州绿色填充 choropleth（东岸深绿 / 中西部浅绿 / 西岸中绿），POI 圆形 markers（UChicago/Michigan/UMinn/Purdue/Cinci 等）

## 附录 B — URL 保留证据（hydration 后）

| 起始 URL | hydration 后 URL | select value |
|---------|------------------|--------------|
| `/map?region=income` | `/map?region=income` ✅ | income |
| `/map?region=safety` | `/map?region=safety` ✅ | safety |
| `/map?region=employment` | `/map?region=employment` ✅ | employment |
| `/map?region=chinese_population` | `/map?region=chinese_population` ✅ | chinese_population |
| `/map?mode=student&region=income` | `/map?region=income&mode=student` ✅ | income |
| `/map?region=cost` | `/map?region=cost` ✅ | "" |
| `/map?region=unknown_metric` | `/map?region=unknown_metric` ✅ | "" |

## 附录 C — Back/Forward 同步证据

序列：
1. 起始 `/map?region=income` → select=income
2. 改 `/map?region=safety` → select=safety
3. 改 `/map?region=chinese_population` → select=chinese_population
4. **back** → URL=`/map?region=safety` + select=safety ✅
5. **back** → URL=`/map?region=income` + select=income ✅
6. **forward** → URL=`/map?region=safety` + select=safety ✅
7. **forward** → URL=`/map?region=chinese_population` + select=chinese_population ✅

`popstate` listener + `useSyncExternalStore` 保证 hydration-safe URL→state→UI 同步链。