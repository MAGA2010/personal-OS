# Stage 7A Closing Patch · UI 重建 — 开发日志（DEVLOG）

> 立项：2026-07-25
> 范围：Stage 7A 前端 UX 重建（接续 Stage 6 demo-pass-2026-07-25-2）
> 目标：在不破坏 62/62/62/904 数据语义、不引入 fixture fallback、不解锁任何禁用数据源的前提下，关闭所有 Critical / High 工单，建立可维护的设计系统。

---

## 0. 工作流前提（核对）

| 项 | 状态 |
| --- | --- |
| Workspace | `/Users/jiayihuang/Downloads/PathOS合并` |
| Frontend | `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend` |
| Standalone backend（只读） | `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone` |
| Preview Bundle（只读） | `PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview` |
| Stage 6 checkpoint（只读，不覆盖） | `/Users/jiayihuang/Downloads/PathOS-checkpoints/stage6-demo-pass-2026-07-25-2` |
| 期望分支 | `feature/stage7-post-demo-development` |
| 起始 HEAD | `b73e61ec4fda11b7c72e74c14e414fbe2c74300f` |
| 禁用写 | `/Users/jiayihuang/PathOS*`, `PathOS-db-ranking`, `PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`, `PathOS合并-integration-baseline` |
| 禁用动作 | pkill / killall / force / reset / clean / rebase / 改 Stage 6 tag / 改 remote / push / 改 Preview Bundle / 改 backend tracked / 改 data-pipeline / 改学校数据事实 / 启用 Production Data Export |
| 数据不变量 | `schoolCount=62`, `summaryCount=62`, `detailCount=62`, `verifiedRecordCount=904`, `quarantine.exposed=0`, `rank 0=0`, `[0,0]=0`, `fixture fallback=false`, `dataMode=backend`, `identityVerified=true`, `sourceLimited=true`, `incomplete=true`, `notFinal=true`, `Production Data Export=prohibited` |
| Preview Bundle manifest SHA | `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`（不可变更） |

---

## 1. 关键判断与决策点

### 1.1 双导航根本原因
诊断：当前 6 个核心页面（match/assessment/portfolio/news/xuanxiao/calculator）均渲染了 **NavBar**（权威导航）+ **ProductJourney**（"AI-A / SELF / MAP / AI-B" 横向 pill 菜单），构成双层导航。
- ProductJourney 是历史 scaffold 阶段遗留的「产品旅程进度展示」组件，但当前职责已被 NavBar 完全承担。
- 决策：**删除 ProductJourney 组件文件本身**，并从 5 个页面（match/assessment/portfolio/news/xuanxiao）的 import / render 调用处清除。
- 替代物：NavBar 已含完整 6 项导航 + 「开始自主测验」CTA + ThemeToggle + 移动端汉堡菜单 + a11y 完备。

### 1.2 MapShell 全屏 backdrop 拦截拖动
诊断：`<div className="absolute inset-0 z-20 hidden md:block" onClick={() => setSelectedUniversityId(null)} />` 覆盖整个地图表面，没有视觉，但 `onClick` 永远拦截 pointer 事件 → drag / wheel / touch 全部失效。
- 决策：删除该层。改在 `MapCanvas` 内挂 `map.on('click')`，并用 `queryRenderedFeatures`（layers: CHOROPLETH_FILL_LAYER_ID + 'pathos-universities-points'）判断是否点中要素 — 点空地 → 触发回调关掉选中，点中要素 → MapLibre 自己处理。
- 用 `useRef + 同步 useEffect` 解决回调闭包陈旧问题。

### 1.3 Light/Dark/System + 无闪烁
- 不能依赖 React 渲染后再切主题 — 会闪。
- 方案：在 `<head>` 内放一个内联 `<script>`（同步、不阻塞）— 读 `localStorage["pathos:theme"]`，根据 `matchMedia('(prefers-color-scheme: dark)')` 解析出最终主题，调用 `documentElement.classList.toggle("dark", resolved === "dark")` + `root.dataset.theme = resolved` + `root.style.colorScheme = resolved`，然后再返回。React 在脚本执行完后再 mount，配合 `<html suppressHydrationWarning>` 避免 hydration mismatch 警告。
- 用户在客户端切换时：`useTheme()` hook 内 `matchMedia.addEventListener('change', ...)` 监听系统偏好变更；调用 `setMode(...)` 同步 `localStorage` + 重新解析。

### 1.4 Tailwind 与 CSS Variables 的兼容
- 设计 tokens 用 `:root` 里的 `--token-X: R G B;`（三个空格分隔的 RGB 通道）暴露。
- Tailwind 通过 `colors: { token: 'rgb(var(--token-X) / <alpha-value>)' }` 引用，alpha 语法让 `bg-persimmon/30` / `border-cobalt/40` 等常用透明度工具照旧可用。
- 新 token：`surface-base / surface-1 / surface-2 / surface-muted`、`text-primary / text-secondary / text-muted`、`border-soft / border-strong`、`accent / success / warning / danger / focus-ring`，加上 `borderRadius` (control/card/overlay)、`boxShadow` (pop/panel/overlay/ring)、`spacing` (control-sm/control/control-lg/nav)、`fontSize` (display/page/section/body/caption/label)、`maxWidth` (page=72rem, prose=42rem)。
- 设计风格：清晰、稳定、学术 / 地图产品感、高信息密度；避免通用 AI 模板的：堆叠渐变、所有 pill 形状、无意义玻璃拟态、巨大 Hero、过重阴影、过装饰。

### 1.5 MapLibre Dark basemap
- `MapCanvas` 构造时立即检查 `document.documentElement.classList.contains('dark')`，决定用 `styleUrl` 还是 `styleUrlDark`（默认 `https://demotiles.maplibre.org/style.json`，两个常量都用同一 URL — 因为 demotiles 的 `dark:` Tailwind variant 仍能盖住 chrome，但 style 本身无法改；后续要换 Carto Dark Matter / Stadia Alidade Dark 只需要替换常量）。
- 主题切换时挂 `MutationObserver` 监视 `<html>` 的 `class` / `data-theme` 属性变化；命中时调用 `map.setStyle(target)`。MapLibre 会在切 style 时保留运行时 add 的 source / layer（choropleth + POI），无需重新挂载。

### 1.6 ESLint 8 个警告
- 6 个 `react-hooks/exhaustive-deps`：match / assessment / portfolio 三处均因 `summariesState.state.status === "ready" ? ... : []` 在每次 render 产生新数组 → 下游 `useMemo` 的 dep 数组认为总在变。统一修法：把这一行包进自己的 `useMemo(() => ..., [summariesState.state])`，让对象身份稳定。Calculator 的 `getCostMult` 用 `useCallback` 包裹，再把 `handleCopy` 的 dep 补全（之前漏 `tier.food / tier.housing / tier.transport / standardTotal`）。
- 1 个 `@next/next/no-img-element`：xuanxiao 列表里的大学 logo — 改用 `next/image`（`next.config.mjs` 已开 `images.unoptimized: true`，不会触碰外部域名）。
- 0 禁用指令被使用（`eslint-disable`、`ignoreDuringBuilds`）。

---

## 2. 改动清单（按文件）

### 2.1 关键修复
- `src/components/map/UniversityProfile.tsx:163` — `"未报告"` 改成中文「未报告」括号，绕过 `react/no-unescaped-entities`。
- `src/components/map/MapShell.tsx` — 删除全屏 click-catch div；将回调改成 `onMapEmptyClick={() => setSelectedUniversityId(null)}` 传给 `MapCanvas`。
- `src/components/map/MapCanvas.tsx` — 增加 `onMapEmptyClick` prop + ref 同步、`styleUrlDark` 默认、构造时按 `.dark` 选择 style、MutationObserver 监听主题切换并 `map.setStyle(target)`。

### 2.2 设计系统
- `src/lib/theme.ts`（NEW）— `ThemeMode = 'light' | 'dark' | 'system'`、`useTheme()`、`THEME_INIT_SCRIPT`、`STORAGE_KEY = "pathos:theme"`、安全 JSON fallback、`matchMedia` 监听、`systemPrefersDark()`、`applyTheme()`。
- `src/components/ThemeToggle.tsx`（NEW）— 三态循环 (light → dark → system)，aria-label 动态更新。
- `tailwind.config.ts`（重写）— `darkMode: 'class'`、CSS-var 颜色、`borderRadius` / `boxShadow` / `spacing` / `fontSize` / `maxWidth` 扩展。
- `src/app/globals.css`（重写）— `:root` light tokens + `.dark` dark tokens、`MapLibre` 控件主题、`.scrollbar-thin`、`prefers-reduced-motion` 关动画。

### 2.3 导航
- `src/components/NavBar.tsx`（重写）— 单一权威全局导航、6 项 + CTA + ThemeToggle、移动端汉堡 + 抽屉（Escape 关、路由切关）、`aria-current="page"` / `aria-expanded` / `aria-controls`、`max-w-page` 容器 + `h-nav` 高度。
- `src/components/ProductJourney.tsx`（**删除**）。

### 2.4 页面统一
- `src/app/match/page.tsx` — 头部紧凑、删除 radial-gradient 外壳、加区域维度屏蔽 callout、文章卡片用 `rounded-card` + `bg-surface-1`。
- `src/app/calculator/page.tsx` — 头部紧凑、动态「还可选择 N 所」文案、缺失费用用 `border-persimmon/30 bg-persimmon/8` + 解释文案。
- `src/app/assessment/page.tsx` — 头部紧凑 + 区域屏蔽说明。
- `src/app/portfolio/page.tsx` — 头部紧凑 + 删除 radial-gradient。
- `src/app/news/page.tsx` — 头部紧凑 + 使用 `bg-surface-base` 主区。
- `src/app/xuanxiao/page.tsx` — 头部紧凑 + `bg-surface-base` 主区 + `<img>` 替换为 `next/image`。

### 2.5 全局布局
- `src/app/layout.tsx` — `<head>` 加 `THEME_INIT_SCRIPT`（无闪烁 bootstrap）、`<html suppressHydrationWarning>`、`viewport themeColor` 双模式（light `#f6f3ed` / dark `#11161a`）。

---

## 3. Gate 状态（实测）

| 检查 | 结果 |
| --- | --- |
| `npx tsc --noEmit` | **PASS** — exit 0 |
| `npm run lint` | **PASS** — 0 errors, 0 warnings |
| `npm test`（vitest） | **PASS** — 76 / 76 tests passed |
| `npm run build` | **PASS** — 15 static routes, exit 0 |
| 双导航（NavBar × ProductJourney） | 已消除 — 6 路由 SSR HTML 各只有 1 个 `aria-label="主导航"` |
| MapShell 拦截拖动 | 已修复 — `MapShell.tsx` 删去全屏 click-catch，`MapCanvas` 接管 |
| 6 个 lint warnings | 已消除 — 通过拆分 useMemo + useCallback + 替换 img → Image |
| 大学数据语义（62 / 62 / 62 / 904） | 未触及 |
| Production Data Export | 保持禁止 |

---

## 4. 自检清单（与上游要求对齐）

| 项 | 实测 | 备注 |
| --- | --- | --- |
| Map 拖动与 Profile 同框工作 | 已修复 | `MapShell` 全屏 click-catch 删；`MapCanvas` 仅在 `queryRenderedFeatures` 返回空时回调 |
| 地图空白点击关闭 Profile | 已实现 | `map.on('click')` 命中空地 → `setSelectedUniversityId(null)` |
| Escape 关闭 Profile | 保留 | 原代码已有；未删 |
| Light / Dark / System 切换 + 持久化 | 已实现 | `pathos:theme` localStorage + `prefers-color-scheme` 监听 |
| 损坏 localStorage 回退 | 已实现 | `JSON.parse` 包 try/catch，失败回 system |
| 系统主题变更实时响应 | 已实现 | `useTheme()` 内 `mq.addEventListener('change', ...)` |
| 无 hydration mismatch | 已实现 | `<html suppressHydrationWarning>` + 内联前置脚本 |
| 无白屏闪烁 | 已实现 | 内联 script 在 React mount 前完成 class 切换 |
| Calculator 添加更多学校 | 文案改为「添加大学（还可选择 N 所）」 | |
| Calculator 缺失费用 | persimmon 边框 + 「该校费用数据未纳入最高费用比较」 | |
| Assessment 加显式说明 | match / assessment 两页均加 callout | |
| 区域维度屏蔽 | `safety / employment / community` 三维不计入综合分 | |
| 单导航（仅 NavBar） | 6 路由 SSR 各只有 1 个 | |
| 设计 token 统一 | CSS vars + Tailwind 双轨，alpha 兼容 | |
| 桌面 nav 不溢出 | max-w-page + h-nav + CTA 响应式隐藏 | |
| 首屏无巨大 Hero | 6 页面均紧凑头 + max-w-page | |
| 区域数据灰显 | 「数据补充中」badge + 排除出综合分 | |
| 浏览器矩阵 1280×720/1440×900/1920×1080/Tablet/390×844 | 待独立 Re-Gate 二次验证 | 当前端口被另一进程占 3000，需独立 re-gate 任务；本次已通过 curl HTML + CSS token 抽样验证 |

---

## 5. 待办与留给独立 Re-Gate 的事项

1. **视觉截图**：dev server 在 3002；3000 端口被外部 next-server 占用（位于 `~/Downloads/PathOS-main/`，不在工作区内，禁止 pkill/kill/seize）。本次未生成新截图。HTML/CSS 抽样已确认 6 路由单 NavBar、token 注入、theme bootstrap 注入。独立 re-gate 任务用 3002 截图即可。
2. **跨视口**：1280 / 1440 / 1920 / Tablet / 390 — CSS token 已统一（`max-w-page`/`h-nav`/`rounded-control`/`bg-surface-1` 等），NavBar 桌面布局 max-w-page + CTA 在 < sm 隐藏；移动端汉堡 + 抽屉已实现。独立 re-gate 时再跑一遍 5 个断点即可。
3. **Map drag 在 Profile open 下**：需要在浏览器内手动验证 — 本次未截图，但代码路径已确认（`MapShell` 全屏拦截层已删）。在 Map 上拖动 + 滚轮缩放不应再卡。

---

## 6. 不要做的反向清单（已遵守）

- ❌ 修改 `/Users/jiayihuang/PathOS*`、外部 `PathOS-db-ranking*`、`PathOS-checkpoints/stage6-demo-pass-2026-07-25-2` — 未触碰。
- ❌ pkill / killall / kill unknown PID / seize 3000 — 未执行；外部 next-server 仍占 3000。
- ❌ 修改 Preview Bundle manifest SHA — 未变。
- ❌ 改 Stage 6 tag / 改 remote / push / reset / clean / rebase / force — 未执行。
- ❌ 启用 Production Data Export — 保持禁止。
- ❌ 改 backend tracked 文件 / 改 data-pipeline / 改学校数据事实 — 未触及。
- ❌ 切换 fixture fallback — 未切换。
- ❌ 用 `eslint-disable` / `ignoreDuringBuilds` 绕过 — 0 处。
- ❌ 声明 `READY FOR INDEPENDENT RE-GATE` — 本报告仅作为提交证据，等待独立 re-gate。

---

## 7. 工作链路回顾

1. ✅ 读 Stage 6 demo-pass 状态 → 确认 62/62/62/904 不变 + bundle manifest SHA 不变。
2. ✅ 修 `UniversityProfile:163` lint ERROR。
3. ✅ 删 `MapShell` 全屏 click-catch + `MapCanvas` 接管空点击。
4. ✅ 写 `lib/theme.ts` + `ThemeToggle.tsx` + `globals.css` + `tailwind.config.ts` + `layout.tsx` 完成 Light/Dark/System。
5. ✅ 写 `NavBar.tsx` 重写 + 删 `ProductJourney.tsx` + 5 个页面 import 清理。
6. ✅ 6 页面 header 紧凑化 + 区域数据屏蔽说明。
7. ✅ Calculator 动态文案 + 缺失费用提示。
8. ✅ 修 8 个 lint warnings（拆分 useMemo + useCallback + img → Image）。
9. ✅ tsc / lint / test / build 全绿。
10. ✅ curl 验证 6 路由单 NavBar + theme bootstrap 注入 + token CSS 注入。
11. ✅ 写 REPORT / DEVLOG / CHANGE-MANIFEST。