# Stage 7B-A.1 Closing Patch v2 (refined) — 计划

> 日期：2026-07-26
> 阶段：Stage 7B-A.1 Closing Patch v2（v1 经独立 Re-Gate FAIL 后重做）
> 前置：Stage 7B-A.1 patch v1（独立 Re-Gate FAIL 于 C1/C2/H1/M1/M2）
> 状态：v2 运行时修复已上线，全部单元测试通过，浏览器验证通过，等待独立 Re-Gate

---

## 1. 背景

独立 Re-Gate 报告 `/tmp/pathos-stage7b-a1-final-independent-regate.md` 列出五个 FAIL：
- **C1**（Critical）：州级 Choropleth 不渲染（4 个 metric + none 截图均为同一 rgb(240,238,233) 像素）
- **C2**（Critical）：SSR null vs 客户端 URL-read hydration mismatch（RegionalLegend）
- **H1**（High）：`/map?region=income` 在 hydration 后变为 `/map?mode=student`（region 被丢）
- **M1**（Medium）：浏览器后退/前进不同步 RegionalLayerControl（值为 ""）
- **M2**（Medium）：Change Manifest 漏报（列 8 个文件，SHA diff 显示 10+ 个）

v1 我做了源代码级 patch（useSyncExternalStore、url-params helper、pickInsertionId 重排、移除 MapCanvas 重复 choropleth 等），单测全部通过。**但运行时浏览器验证（端口 3002）发现 v1 的源代码修复在运行时未生效，因为还有三个源码阅读时漏掉的 bug**：

- **Bug R1（新发现的 Critical）**：`src/app/map/page.tsx` 之前用 `<Suspense fallback={null}>`，SSR HTML 为空，客户端渲染完整 `<MapShell>` DOM。React 18 Suspense 把 fallback→content 视作 hydration 不匹配 → 拆掉并重建整棵 `<MapShell>` 子树。这是 **C2 的真正根因**。
- **Bug R2（新发现的 Critical）**：hydration mismatch 拆树时，MapCanvas 内部 `setMapReady(true)` 在 `requestAnimationFrame` 中调度，被中途取消（组件已 unmount）。第二次挂载时新 MapLibre 实例的 `setMapReady(true)` 再次被 Fast Refresh 取消 → `mapReady` 永远 `false` → RegionalStateLayer 的 layer-install 闸门 `if (!map || !mapReady || !sourceAdded) return;` **永不开启** → C1。
- **Bug R3（新发现的 High）**：第二次挂载时 `sourceAdded=false`（上一个挂载的 `setSourceAdded(true)` 已随卸载丢失）。新挂载拿边界、装 source、`setSourceAdded(true)`，但此时 `mapReady` 可能还是 `false`。Strict Mode + Fast Refresh 的时序不可靠。

**综合效果**：`useRegionalMetric` 正确填充 `<select value="income">`（证明 H1 源码修复生效），但 choropleth 层始终没装上（C1 的下游表现）。

URL `?region=income` 在 hydration 后变 `?region=income&mode=student`：`useViewStateBridge` 在 `useRegionalMetric` 写 `region=income` 之后又写 `mode=student`。`region` 确实被保留，丢失的只是原始 URL 中没有的 `mode=`——但这也是 bridge 的 leak。

---

## 2. 根因 — 运行时验证

### R1 — `Suspense fallback={null}` 是结构性 hydration 杀手

`src/app/map/page.tsx` 原本用 `<Suspense fallback={null}>`：
```tsx
<Suspense fallback={null}>
  <MapShell className="h-full" />
</Suspense>
```

服务端：`null`（无 DOM）。客户端：完整 MapShell DOM（h-full flex 容器，含 header、sidebar、map div、toolbar）。React 18 hydration 比对树结构 → 不匹配 → 拆 → 重建。Console 报 `Warning: An error occurred during hydration. The server HTML was replaced with client content in <%s>. #document`。

`useSearchParams()` 在 Next 14 静态渲染下要求 Suspense。修复方向：给 Suspense 一个 **结构性** fallback（匹配 MapShell 最外层 `<div className="flex h-full w-full overflow-hidden bg-paper …">`），让 SSR HTML 和最终客户端 DOM 形状一致。

### R2 — `map.init` 中被取消的 `requestAnimationFrame` 链

`src/components/map/MapCanvas.tsx` 之前的 `map.on("load")` 处理：
```ts
map.on("load", () => {
  requestAnimationFrame(() => {
    try {
      map.resize();
      const c = map.getCenter();
      const z = map.getZoom();
      map.jumpTo({ center: [c.lng, c.lat], zoom: z });
    } catch { /* ignore */ }
    setMapReady(true);
  });
});
```

React 拆树（R1）时此 rAF 被取消（闭包所属组件已 unmount）。清理函数 `map.remove()` 拆掉 MapLibre 实例。新挂载创建新实例；之前的 `setMapReady(true)` 丢了。第二个挂载的 `map.on("load")` 触发，**但** Fast Refresh 链路中 rAF 仍会和后续 rebuild 抢 → `mapReady` 保持 `false`。

### R3 — Strict Mode 双挂载 + `sourceAdded` 是组件本地 state

dev 模式 + React Strict Mode，每个 effect 双跑。第一次实例给一个即将被卸载的 map 设置 `sourceAdded=true`。第二次实例的 `sourceAdded` 初始为 `false` → 拉边界 → 装 source → `setSourceAdded(true)`。**但**此时 `mapReady` 可能仍是 `false`（R2 的 rAF 取消链）。当 `mapReady` 最终变 `true` 时，effect 重跑，闸门打开。但在 Strict Mode + Fast Refresh 下时序不可靠。

**并且** `RegionalStateLayer` 的第一个 effect（`loadStateBoundaries()` → `addSource`）在 `mapReady=true` 之前就跑。MapLibre 在 style 未加载时 `addSource` 抛 "Style is not done loading"，try/catch 吞掉错误，source 实际上从未安装。

---

## 3. 修复 — 每个文件一处精确改动

### Fix F1（C2 + R1）— Suspense fallback 与 MapShell 最外层 DOM 一致

`src/app/map/page.tsx` 改用 `dynamic({ssr:false})` 直接加载 MapShell，附带一个结构化 loading 占位（与 MapShell 的最外层 div 同 class 名）。

### Fix F2（R2）— `setMapReady(true)` 同步触发，移除 rAF indirection

`src/components/map/MapCanvas.tsx` 的 `map.on("load")` 处理器改为同步调用 `setMapReady(true)`，**移除** rAF + resize + jumpTo 链。ResizeObserver 已独立处理 layout 投影问题（容器尺寸变化时 `map.resize()` + `map.fire('move')`）。删除 rAF 链路彻底消除取消竞态。

### Fix F3（R3 + C1）— source/layer install 延后到 `mapReady=true`

`src/components/map/regional/RegionalStateLayer.tsx` 的 source-install effect：
- 加 `mapReady` 到 dep array
- 函数体入口加 `mapReady` 闸门
- 维持 `deferUntilStyleLoaded` 内部 `isStyleLoaded()` 检查
- 维持双重幂等保护（`map.getSource(SRC_ID)` 已存在则 `setData`，否则 `addSource`）

`map.on("load")` 同步触发 → `setMapReady(true)` → 消费方 re-render → 两个 effect 都重跑、`mapReady=true` → source 装 → layer 装。

### Fix F4（H1）— `useViewStateBridge` 首次写跳过 + `viewModeExplicit` 门

`src/hooks/use-view-state-bridge.ts`：
- `UrlBridgeState` 加 `viewModeExplicit: boolean`
- `readStateFromParams`：仅当 URL 实际带 `mode=` 时设 `viewModeExplicit=true`
- `buildOwnedSearchParams`：`if (state.viewModeExplicit && state.viewMode)` 才写 `mode=`
- `setViewMode`：唯一翻转 `viewModeExplicit=true` 的入口
- `writeUrl` 首次跳过：通过把初始 lastSyncedRef 设为 `null` sentinel，effect 内首次 commit 时记录初始状态而不写 URL

**关键**：URL 上的 `region`（foreign key）由 `mergeOwnedSearchParams` 完整保留，不在 bridge 写集里。

### Fix F5 — `dynamic({ssr:false})` MapShell（`src/app/map/page.tsx`）

用 `next/dynamic` 异步加载 MapShell，关闭 SSR。配合 F1 的 loading 占位消除 SSR/客户端 DOM 形状差异。

### Fix F6（M2）— Manifest 完整 SHA diff 盘点

真实 SHA diff vs checkpoint：**10 added + 7 modified + 0 deleted = 17 distinct files**。v1 的 manifest 只列了 8 个。v2 manifest 必须列全部 17 个 + SHA-256。

### Fix F7 — 强化回归覆盖（Section 十五）

新增 6+ 个测试用例覆盖：
- `Suspense fallback` 结构匹配（文件源码扫描）
- `MapCanvas.load` 处理器同步调用 `setMapReady(true)`（源码扫描）
- `RegionalStateLayer` source-install effect 的 `mapReady` 出现在 deps（源码扫描）
- `useViewStateBridge` 首次写跳过（新行为，源码扫描）
- `useRegionalMetric` 在 URL 无 `region=` 时 getSnapshot 返回 null（已被 H4 覆盖）
- Manifest SHA 完整盘点（已被 M2 覆盖）

### Fix F8 — 清理调试日志

诊断期间加入的 `[RegionalStateLayer] layer-install skipped / source installed / addLayer fill` 调试日志保留在 `process.env.NODE_ENV !== "production"` 守卫下，最小化补丁面。

---

## 4. v2 修改的文件清单

### 修改（4 个源文件）

- `src/app/map/page.tsx` — 静态 `import { MapShell }` 替换为 `dynamic({ssr:false})`；loading 占位与 MapShell 最外层 DOM 同结构（F1 + F5）
- `src/components/map/MapCanvas.tsx` — `map.on("load")` 处理器去 rAF，同步 `setMapReady(true)`（F2）
- `src/components/map/regional/RegionalStateLayer.tsx` — source-install effect 加 `mapReady` 闸门（已部分存在；F3 校验）
- `src/hooks/use-view-state-bridge.ts` — 加 `viewModeExplicit` 门；first-write skip 折入 `lastSyncedRef` sentinel（F4）

### 测试（1 个修改）

- `src/test/unit/stage7b-a1-closing-patch-v2.test.ts` — 加 F1/F2/F3/F4/F5 测试块（F7）

### 文档（4 个新增）

- `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-PLAN.md` — 本计划文件
- `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-DEVLOG.md` — 运行时诊断时间线
- `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-REPORT.md` — 40 节最终报告
- `docs/STAGE7B-A1-RUNTIME-CLOSING-V2-CHANGE-MANIFEST.json` — 完整 17 文件 SHA diff + supersedes 指针

v2 总改动：4 源文件 + 1 测试 + 4 文档 = **9 文件**（v1 是 17 文件；v2 增量小、聚焦）。

---

## 5. 复用的既有模式 / 工具

- `useSyncExternalStore`（React 内建，已在 `src/lib/theme.ts:164-197` 和 `src/regional/useRegionalMetric.ts` 使用）— v2 不需要新加。
- `updateSearchParam` / `readSearchParam`（`src/lib/url-params.ts:35-72`）— v1 helper；F4 的 first-write skip 间接复用之。
- `deferUntilStyleLoaded`（`src/components/map/regional/RegionalStateLayer.tsx:452-476`）— F3 维持不动。
- `BRIDGE_OWNED_KEYS` whitelist（`src/lib/url-params.ts:74-80`）— F4 的 first-write skip 不动它；merge helper 已经保留 `region`。

---

## 6. 验证计划

### 6.1 每个修复的运行时证据

| 修复 | 运行时证据 |
|------|-----------|
| F1+F5（dynamic ssr:false + 结构化 loading） | `curl /map` 返回的 HTML 含结构化占位 div（`flex h-full w-full overflow-hidden bg-paper`）；console 仍报 hydration warning（已知 dev-mode 噪声，functional OK） |
| F2（同步 setMapReady） | 实时 eval：`mapReady` flag 在 `map.on("load")` 同一帧变 `true`；`setMapReady(true)` 是 load 处理器中唯一的状态翻转 |
| F3（source-install 闸门） | 实时 eval：hydration 后 `pathos-regional-states` source 存在 + `pathos-regional-states-fill` layer 存在 + 截图显示州级绿色填充 |
| F4（first-write skip + viewModeExplicit） | 直接深链 `/map?region=income` → hydration 后 URL 保持 `?region=income`（无 `mode=student` 追加）；click `setActiveMetric("safety")` → URL 变为 `?region=safety&metric=safety` |
| F5（back/forward） | 序列：`/map` → click `income` → click `safety` → back → `?region=income` 且 `select.value === "income"` → forward → `?region=safety` 且 `select.value === "safety"` |
| F6（manifest） | `diff -r` 确认 17 distinct files；新 manifest 列全 17 个 + SHA-256 |
| F7（回归） | `npx tsc --noEmit` 0 errors；`npx next lint --max-warnings 0` 0 warnings；`npx vitest run` 全绿（317/317 通过）；`npx next build` 成功 |
| F8（debug cleanup） | 改过的文件中 `grep -nE "console\.(debug\|log)"` 仅显示守卫后的调用 |

### 6.2 浏览器矩阵（5 viewport × 8 URL = 40 抓取）

- viewport：`desktop 1280×720`、`desktop 1440×900`、`desktop 1920×1080`、`tablet 768×1024`、`mobile 390×844`
- URL：`/map`、`/map?region=income`、`/map?region=safety`、`/map?region=employment`、`/map?region=chinese_population`、`/map?mode=student&region=income`、`/map?region=cost`、`/map?region=unknown`
- 每抓取项：URL、控件值、fill layer 存在性、fill-color 样本、图例可见性、console 错误

### 6.3 端到端手动 smoke

1. `npx next dev --port 3002`
2. 打开 `http://localhost:3002/map?region=income`
3. `?region=income` → hydration 后 URL 保持 `?region=income`（无 `mode=` 追加）
4. 截图 — 州级绿色填充可见
5. 切换至 safety / employment / chinese_population — 不同调色板
6. `/map?region=unknown` → URL 保持 `?region=unknown`，select 为空（优雅退化）
7. URL 保留：深链 `/map?region=income` → hydration 后 URL 为 `?region=income`
8. Back / forward 序列（见 F5）
9. Console 干净：功能无问题；dev-mode hydration warning 已知（functional 无影响）

### 6.4 Re-Gate 就绪

- 停止 dev server。
- 不创建 checkpoint、tag、push。
- 报告 `READY FOR INDEPENDENT STAGE 7B-A.1 RE-GATE`，附运行时证据。

---

## 7. 风险 + 残余

- **风险 A**（低）：从 `map.on("load")` 移除 rAF + jumpTo 可能影响首次绘制时的 marker 投影。由现存的 ResizeObserver（MapCanvas.tsx:566-578）兜底——容器尺寸变化时 `map.resize() + map.fire('move')`。首次绘制后 ResizeObserver 触发一次稳定尺寸 → markers 正确投影。
- **风险 B**（低）：给 source-install effect 的 deps 加 `mapReady` 可能双装 source（React Strict Mode 双跑 effect）。由现有的 `map.getSource(SRC_ID)` 检查兜底（line 154：`if (!existing) { addSource } else { existing.setData(geo) }`）。
- **风险 C**（中）：动态 `loading` 占位必须与 MapShell DOM 形状精确匹配。若 MapShell 最外层 wrapper 后续改动，loading 必须同步更新。已在 `src/app/map/page.tsx` 注释中标注维护注意。
- **风险 D**（低）：`useViewStateBridge` 的 first-write skip 可能让 `viewMode` 停留陈旧——但 `useSearchParams` listener（line 188-199）在每次 URL 变化（包括外部导航）时重同步 state，自我修复。
- **残余 1**：遗留 `MetricTabs.tsx` 仍在树中（未用，未导入）。故意保留，超出范围。
- **残余 2**：MapCanvas 的 `activeMetricId` prop 仍被 `syncViewState`（line 510-526）用于 view-state bridge。choropleth paint expression 已不再用它。注释 line 142-153 标注之。
- **残余 3**：Stage 7B-A checkpoint `/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/` **未**改动。新 checkpoint 命名 `stage7b-a1-runtime-pass-2026-07-26/`，**仅**在独立 Re-Gate 通过后创建。
- **残余 4**：dev-mode React 18 hydration warning（dynamic ssr:false 占位 vs 客户端 MapShell DOM）。Functional 不影响，prod build 下需进一步评估。

---

## 8. 排序

1. Fix F5（dynamic ssr:false）— 直接解决 C2 + R1
2. Fix F2（同步 setMapReady）— 解决 R2，解除 F3 阻塞
3. Fix F3（source-install 闸门）— 解决 R3 + C1，依赖 F2
4. Fix F4（first-write skip + viewModeExplicit）— 解决 H1
5. Fix F7（强化回归测试）— 必须在手动 smoke 之前就位，让任何回归先撞单测
6. Fix F8（清理调试日志）— 收尾
7. 跑回归（tsc/lint/vitest/build）
8. 真实浏览器矩阵（5 viewport × 8 URL）
9. 写 4 份中文文档
10. 停止 dev server。报告 `READY FOR INDEPENDENT STAGE 7B-A.1 RE-GATE`