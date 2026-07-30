# Stage 7A Closing Patch — UI 重建实施计划

> 立项：2026-07-25
> 上游：Stage 6 demo-pass-2026-07-25-2（仅读）
> 目标：消灭当前 Gate 全部 Critical / High；建立统一、稳定、可维护的 PathOS 前端设计系统；为 Stage 7B 做最终前置。

---

## 1. 当前 Gate 真实状态

实测确认（dev port 3002，bundle 已就绪）：

| 项目 | 状态 |
| --- | --- |
| `npx tsc --noEmit` | PASS（0 error） |
| `npm run lint` | 2 ERROR + 6 warnings |
| `npm run build` | 上轮 FAIL — react/no-unescaped-entities @ UniversityProfile:163 |
| POI 缩写 / Hover / 数据语义 | 已通过 |
| Calculator / Assessment 公式 / Resizable / BottomSheet | 已通过 |
| Dark Mode | **未实现**（无 darkMode，无 CSS vars） |
| 截图两套重复菜单 | **存在** — NavBar 是权威；ProductJourney 在 5 个页面叠了第二套 |
| Map backdrop 阻塞拖动 | **存在** — MapShell:729-733 `<div className="absolute inset-0 z-20 hidden md:block" onClick=…>` 拦了所有指针事件 |
| 顶部 NavBar 桌面溢出 | **存在** — 1280px 下 6 项 + CTA + Logo 已挤；右侧开始压缩 Logo |
| 首屏无效色块 + 巨大 Hero | **存在** — match 页头部 h-22 + radial-gradient + ProductJourney + sticky aside |

## 2. 总体目标

1. 全站只保留 NavBar 一套权威全局导航。
2. ProductJourney 改为「页面内部步骤进度」组件（如果真代表连续工作流）或彻底删除（如果只是冗余菜单）。
3. 设计 Tokens 落到 CSS variables + Tailwind theme extension；新增 Light/Dark/System。
4. 修复 MapShell 全屏 backdrop，不再拦截拖动 / 滚轮 / 触摸。
5. 修复 UniversityProfile 字符转义。
6. 修复 Calculator 动态文案「还可选择 N 所」+ 缺失费用说明。
7. 修复 Assessment 加显式「区域维度已屏蔽」提示。
8. 关闭全部 6 条 ESLint warnings（拆分 all 引用、补 useMemo、xuanxiao img → Image）。
9. 重写首屏节奏：紧凑 Page Header、统一容器、避免巨大 Hero。
10. 真浏览器跨视口验收：1280×720 / 1440×900 / 1920×1080 / Tablet / 390×844。

## 3. 不做事项（边界）

- 不动 Preview Bundle 任何文件（manifest sha `88f3dd6081df…` 保持）。
- 不动 backend tracked files、data-pipeline。
- 不动学校数据事实（62/62/62/904、quarantine.exposed=0、rank 0=0、[0,0]=0、sourceLimited=true、incomplete=true、notFinal=true）。
- 不动 .env.local、不切 fixture、不开 Production Data Export。
- 不动 Stage 6 tag、不 reset、不 push、不 force。
- 不写 eslint-disable / ignoreDuringBuilds。
- 不删失败测试。

## 4. 实施顺序

| 顺序 | 项 | 涉及文件 |
| --- | --- | --- |
| P1 | Critical — UniversityProfile 字符转义 | `components/map/UniversityProfile.tsx` |
| P1 | High — 移除 MapShell 全屏 backdrop，加 click-empty 行为 | `components/map/MapShell.tsx` + `MapCanvas.tsx` |
| P2 | NavBar 设计系统重构（高度 / Logo / 折叠 / 桌面溢出） | `components/NavBar.tsx`、`tailwind.config.ts`、`app/globals.css` |
| P2 | ProductJourney 改名为 StepProgress，仅在真工作流页面用 | 新 `components/StepProgress.tsx`、替换 5 处 import |
| P2 | Hero / Page Header 重写（紧凑、统一容器） | `app/match/page.tsx`、`app/assessment/page.tsx`、`app/portfolio/page.tsx`、`app/news/page.tsx`、`app/xuanxiao/page.tsx` |
| P3 | Tailwind darkMode + CSS variables | `tailwind.config.ts`、`globals.css`、新增 `lib/theme.ts`、`components/ThemeToggle.tsx` |
| P3 | 全站 dark: 复审 | 所有顶层组件 |
| P3 | MapLibre 暗色底图（不依赖 API key） | `components/map/MapCanvas.tsx` |
| P4 | Calculator 动态文案 + 缺失费用说明 | `app/calculator/page.tsx`、`components/calculator/SchoolPicker.tsx` |
| P4 | Assessment 显式 region-blocked 说明 | `app/match/page.tsx`、`app/assessment/page.tsx` |
| P5 | Lint 6 warnings 全关 | match / assessment / portfolio / calculator / xuanxiao |
| P6 | tsc / lint / test / build 全绿 | CI |
| P7 | 真实浏览器跨视口 + Console / Network 验收 | 文档化截图 |
| P8 | 写中文 REPORT / DEVLOG / CHANGEMANIFEST | docs/ |

## 5. 风险与对策

- 风险：MapLibre dark style 自定义 source/layer 切换时丢失。
  对策：style 切换前先记录已添加的 source/layer，切换后再重新添加。
- 风险：CSS variables + Tailwind 同时启用 darkMode 出现 hydration mismatch。
  对策：根组件读 localStorage 之前显示 neutral，避免首屏闪烁；用 `suppressHydrationWarning`。
- 风险：移除 MapShell backdrop 后无法 click-empty 关闭 profile。
  对策：把 click-empty 逻辑移到 MapCanvas 的 map.on('click') 中，区分是否点中 POI。

## 6. 完成判定（自检）

- `npm run build` exit 0
- `npm run lint` 0 error / 0 warning
- `npx tsc --noEmit` 0 error
- 全部测试通过
- 1280×720 截图中 NavBar 不溢出、Logo 不裁切
- /match 截图中只剩 NavBar 一套菜单
- 地图 Profile 打开后拖动 / 滚轮 / 触摸 都生效
- Dark Mode 切换并刷新后保持；System 跟随系统
- 62/62/62/904 / quarantine 0 / fixture false / sourceLimited true 全部不变