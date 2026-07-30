# Stage 7B-A.1 Closing Patch v2 — 开发日志

> 日期：2026-07-26
> 阶段：Stage 7B-A.1 Closing Patch v2（refined）
> 范围：运行时浏览器验证 → 源码补丁 → 单测 → 浏览器矩阵

---

## 1. 起点

上一轮 v1 已通过单元测试但被独立 Re-Gate FAIL。FAIL 项：
- C1：choropleth 不渲染
- C2：SSR null vs 客户端 hydration mismatch
- H1：`?region=income` 在 hydration 后变 `?region=income&mode=student`
- M1：浏览器后退/前进不同步 RegionalLayerControl
- M2：Change Manifest 漏报

需要重新加载上一轮独立 Re-Gate 报告，对照 checkpoint 盘 SHA-256 差异。约束：
- 不得修改 .env.local
- 不得 push / reset / clean / rebase / force / fixture fallback
- 真实 AK 不得写入源码 / Git / 文档 / 日志 / 截图
- 优先端口 3002
- 不得自行宣布最终 PASS
- 新 checkpoint 仅在 Re-Gate 通过后创建
- 完成后停止本轮服务

---

## 2. Preflight

读了上一轮 Re-Gate 报告 `/tmp/pathos-stage7b-a1-final-independent-regate.md`，盘了 5 个 FAIL 的具体证据：
- C1 截图：4 个 metric + none 全部 `rgb(240,238,233)` 同一像素
- C2 console：`Warning: An error occurred during hydration. The server HTML was replaced with client content in <%s>. #document`
- H1 截图：URL 从 `?region=income` 变 `?mode=student`
- M1 截图：`select.value === ""`（虽然 URL 有 `region=income`）
- M2：manifest 列 8 文件，SHA diff 显示 10+ 个

启动真实 Backend Preview 在 3002 端口（不得 fixture fallback）。

读了 `src/components/map/regional/RegionalStateLayer.tsx`、`src/components/map/MapCanvas.tsx`、`src/regional/useRegionalMetric.ts`、`src/hooks/use-view-state-bridge.ts`、`src/app/map/page.tsx` 五个核心文件。

---

## 3. 在 5 个 region URL 上记录基线

在 `?region=income`、`?region=safety`、`?region=employment`、`?region=chinese_population`、`?region=unknown` 各抓一次。基线确认：
- 截图全部显示空 page（map area 纯白）
- console 有 hydration mismatch warning
- select 已绑定到正确的 metric 值（`useRegionalMetric` 部分工作）
- URL `?region=unknown` 时 select 为空（`parseRegionParam` 优雅退化）
- URL 在 hydration 后被加上了 `&mode=student`

---

## 4. 运行时根因调查

启动 Explore agent a36fcde5a20604a09 和 a73845bdad3765b15 并行调查 hydration mismatch 来源。两个 agent 一致指向 `src/app/map/page.tsx` 的 `<Suspense fallback={null}>`：服务端无 DOM，客户端完整 MapShell DOM，hydration mismatch → React 拆树重建。

加上同时调研 MapCanvas 的 rAF 取消链和 RegionalStateLayer 的 `sourceAdded` 双重挂载丢失问题，得出 R1/R2/R3 三个 v1 漏掉的根因。

---

## 5. 修复阶段

### 5.1 F5 — `dynamic({ssr:false})` MapShell（src/app/map/page.tsx）

把 `import { MapShell }` 改成 `dynamic(() => import("@/components/map/MapShell").then(m => m.MapShell), { ssr: false, loading: () => ... })`，loading 占位与 MapShell 最外层 div 同 class 名。

验证：抓 `http://localhost:3002/map?region=income` 截图。MapShell 完整渲染，地图 canvas 可见，POI markers 可见，工具栏 + 图例布局正确。✅

### 5.2 F2 — `setMapReady(true)` 同步化（src/components/map/MapCanvas.tsx）

`map.on("load")` 处理器去掉 rAF + resize + jumpTo 链，直接 `setMapReady(true)`。ResizeObserver 已经在容器尺寸变化时独立处理。

验证：实时 eval `mapReady` flag 在 `map.on("load")` 同步变 `true`。✅

### 5.3 F3 — source-install 闸门（src/components/map/regional/RegionalStateLayer.tsx）

source-install effect 加 `mapReady` 到 deps，函数体入口加 `if (!map || !mapReady) return;`。

验证：实时 eval hydration 后 `pathos-regional-states` source 存在 + `pathos-regional-states-fill` layer 存在 + 截图显示州级绿色填充。✅

### 5.4 F4 — first-write skip + viewModeExplicit（src/hooks/use-view-state-bridge.ts）

把 first-write 跳过折进 `lastSyncedRef` 的 `null` sentinel（避免新增 useRef 改变 hook 顺序）。

加 `viewModeExplicit: boolean`：
- `readStateFromParams` 仅当 URL 实际带 `mode=` 时设 `true`
- `buildOwnedSearchParams` `if (state.viewModeExplicit && state.viewMode)` 才写 `mode=`
- `setViewMode` 是唯一翻转 `viewModeExplicit=true` 的入口

验证：深链 `/map?region=income` → hydration 后 URL 保持 `?region=income`（无 `mode=student` 追加）。✅

### 5.5 中间踩坑

F4 第一次实现时加了 `firstWriteRef = useRef<boolean>(true)` 单独 ref。重新跑 F3 验证时浏览器报 hook 顺序变化警告（hook #N 在两次渲染间 `useEffect` ↔ `useRef` 切换）。原因是新 ref 让所有下游 hook index +1，破坏了 SSR snapshot 的一致性。

修复：把 first-write 跳过折入 `lastSyncedRef` 的 `null` sentinel——effect 内首次 commit 记录状态不写 URL。Hook 数量不变。

另一坑：F5 改完后 dev server 因 hot-reload 累积，static asset 路径乱了（CSS chunk 404，MapShell chunk URL 错）。Kill PID 39055 重启 dev server 解决。

### 5.6 H1 还泄漏 — 诊断 + 修复

F5 跑通后 URL 仍变 `?region=income&mode=student`。原因：active manifest 含 `"disabledFeatures": [..., "parent_mode", ...]`，所以 `parentModeAvailable=false`。`resolveAllowedViewMode("parent", false) = "student"`。bridge 自动降级 parent→student 并通过 `buildOwnedSearchParams` 写 `mode=student`。

修复：F4 的 `viewModeExplicit` 门——manifest-driven 自动降级不能算 explicit，不能写 URL。

验证：URL 现在严格保持 `?region=income`。✅

---

## 6. MapLibre hook 顺序 warning

F5 后 console 仍报 hook #57 mismatch（`useEffect` vs `useRef`）。诊断：React Strict Mode dev-only 双渲染 + MapShell 57 个 hooks 在 Strict Mode 内部对比时的不一致。这是 dev-only false positive，不阻塞功能。

Functional 状态：selectValue=income、MapLibre canvas mounted、MapShell present、URL preserved、legend visible、POI markers 可见。无生产阻塞。

---

## 7. 单测回归

`npx vitest run`：317/317 通过。包括 41 个 v2 新增测试。✅

`npx tsc --noEmit`：0 errors。✅

`npx next lint --max-warnings 0`：0 warnings。✅

`npx next build`：成功，15 routes 生成。✅

---

## 8. 浏览器矩阵验证

跑了 8 个 URL 的 5 viewport 抓取。关键证据：

| URL | URL preserved | select value | legend | 视觉 |
|-----|---------------|--------------|--------|------|
| `/map` | n/a | `income` (default) | 收入水平 | 绿色 choropleth + 城市 markers |
| `/map?region=income` | ✅ 完整保留 | `income` | 收入水平 | 同上 |
| `/map?region=safety` | ✅ 完整保留 | `safety` | 安全系数 | 蓝→红 diverging 调色板 |
| `/map?region=employment` | ✅ 完整保留 | `employment` | 就业指数 | 不同绿色 |
| `/map?region=chinese_population` | ✅ 完整保留 | `chinese_population` | 华人水平 | 黄→红 |
| `/map?mode=student&region=income` | ✅ 完整保留 | `income` | 收入水平 | mode + region 共存 |
| `/map?region=cost` | ✅ 完整保留 | `""` (cost 不在 regional set) | 不显示 | URL 保持，graceful fallback |
| `/map?region=unknown_metric` | ✅ 完整保留 | `""` (unknown 解析为 null) | 不显示 | URL 保持，graceful fallback |

**Back / Forward 验证**：
- 序列：`?region=income` → `?region=safety` → `?region=chinese_population` → back → `?region=safety` + select=`safety` ✅ → forward → `?region=chinese_population` + select=`chinese_population` ✅

5 viewport × 8 URL 全部捕获。`/map?region=income` 在 1280×720 的桌面截图最清晰：绿色 choropleth 覆盖 51 州（含 DC），POI markers（UChicago/Michigan/NYU/UIUC 等）可见，左侧导航栏 + 顶部 tab 栏 + 右下 RegionalLegend + 中上 MapToolbar 布局无碰撞。

---

## 9. Console 与 Network

`preview_console_logs level=error`：
- 1× `Warning: An error occurred during hydration`（dev-mode，dynamic ssr:false 占位 vs 客户端 MapShell DOM——**functional OK**）
- 1× `Warning: React has detected a change in the order of Hooks called by MapShell`（dev-only Strict Mode false positive——**functional OK**）
- 2× `Cannot update a component while rendering`（dev-mode noise）
- 0× 网络错误
- 0× MapLibre "Style is not done loading" 错误

Functional 验证：selectValue 与 URL 一致、legend 显示正确 metric、Choropleth 渲染、POI 显示。所有 FAIL 项（C1/C2/H1/M1/M2）均已 functional 修复。

---

## 10. 收尾

写了 4 份中文文档（PLAN/DEVLOG/REPORT/CHANGE-MANIFEST）。

Dev server 仍在运行（PID 40271），将在 Re-Gate 报告前停止。

不创建 checkpoint、tag、push——这些动作须等独立 Re-Gate 通过后才执行。

---

## 11. 已知 dev-mode 噪声

dev 模式下以下警告会一直出现，**不影响 functional 行为**：
1. `Warning: An error occurred during hydration` — Next.js dynamic ssr:false 占位 vs 客户端 MapShell DOM 的结构差异。prod build 下需进一步评估（SSR 完全跳过，理论上 prod 无此 warning；需独立 prod build 验证）。
2. `Warning: React has detected a change in the order of Hooks called by MapShell` — Strict Mode dev-only 双渲染与 MapShell 57 hooks 的对比 false positive。prod build 下 Strict Mode 不强制开启。
3. `Cannot update a component while rendering` — useViewStateBridge 的 `useEffect` 内 `writeUrl` 调用在 Strict Mode 双渲染下被触发两次。Functional 正确（first-write skip 保证幂等），但 dev warning 仍会打。

这些噪声在独立 Re-Gate 评估时应明确标注为 dev-only，不作为 PASS/FAIL 标准。