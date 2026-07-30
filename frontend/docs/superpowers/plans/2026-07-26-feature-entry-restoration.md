# PathOS 功能入场动画恢复实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在不修改现有功能逻辑的前提下，恢复首页环境层及 Map、Match、Assessment、Portfolio 四套旧版入场体验。

**架构：** 新增 `/entry/*` 独立路由承载纯视觉入场组件，CTA 进入现有正式功能 URL；首页只调整相关链接并新增非交互环境层。旧版视觉代码按当前授权、可信文案和响应式约束适配，不把旧 mock、重复 `/explore` 路由或未知媒体带入运行路径。

**技术栈：** Next.js 14 App Router、React 18、TypeScript、CSS Modules、Tailwind CSS、Vitest、Next Image。

---

## 文件结构

- 创建 `src/components/entry/EntryChrome.tsx`：四套入口共用的品牌返回、角标和状态框架。
- 创建 `src/components/entry/EntryChrome.module.css`：共用全屏框架、焦点、移动端和 reduced-motion。
- 创建 `src/components/entry/MapEntry.tsx` 与 `MapEntry.module.css`：地球观测入场。
- 创建 `src/components/entry/MatchEntry.tsx` 与 `MatchEntry.module.css`：数据波形入场。
- 创建 `src/components/entry/AssessmentEntry.tsx` 与 `AssessmentEntry.module.css`：已授权校园摄影序列入场。
- 创建 `src/components/entry/PortfolioEntry.tsx` 与 `PortfolioEntry.module.css`：CSS/SVG AI 环境入场。
- 创建 `src/app/entry/{map,match,assessment,portfolio}/page.tsx`：四个静态入场路由和 metadata。
- 修改 `src/app/page.tsx`：四个首页入口改为 `/entry/*`，增加首页地球环境层。
- 修改 `src/app/home.module.css`：环境层和 reduced-motion 样式。
- 新增 `public/entry/pathos-earth-from-orbit.jpg`：已核验 NASA 公共领域图片。
- 创建 `public/entry/ATTRIBUTIONS.md`：地球图片来源、许可、Photo ID 和本地 Hash。
- 创建 `src/test/unit/feature-entry-restoration.test.ts`：结构、路由、素材、动效与非回归测试。

### 任务 1：先建立失败的入口契约测试

**文件：**
- 创建：`src/test/unit/feature-entry-restoration.test.ts`

- [ ] **步骤 1：编写失败的路由与首页链接测试**

测试读取四个 `src/app/entry/*/page.tsx`，断言每页导入对应组件；读取 `src/app/page.tsx`，断言 `/entry/map`、`/entry/match`、`/entry/assessment`、`/entry/portfolio` 存在，`/calculator` 和 `/news` 仍直接进入。

- [ ] **步骤 2：编写失败的安全边界测试**

断言入口源码不包含 `/explore`、`universities.json`、`PATHOS_DATA_MODE=fixture`、远程图片 URL；正式 `src/app/map/page.tsx` 仍只返回 `MapPageShell`。

- [ ] **步骤 3：编写失败的动效与可访问性测试**

断言所有入口有唯一 `h1`、返回首页、正式 CTA、`prefers-reduced-motion: reduce`，CSS 动画声明不改变 `width`、`height`、`top`、`left`，装饰环境层包含 `pointer-events: none`。

- [ ] **步骤 4：运行测试验证失败**

运行：`npx vitest run src/test/unit/feature-entry-restoration.test.ts`

预期：FAIL，原因是入口路由和组件尚不存在。

### 任务 2：恢复 Map 和 Match 入场

**文件：**
- 创建：`src/components/entry/EntryChrome.tsx`
- 创建：`src/components/entry/EntryChrome.module.css`
- 创建：`src/components/entry/MapEntry.tsx`
- 创建：`src/components/entry/MapEntry.module.css`
- 创建：`src/components/entry/MatchEntry.tsx`
- 创建：`src/components/entry/MatchEntry.module.css`
- 创建：`src/app/entry/map/page.tsx`
- 创建：`src/app/entry/match/page.tsx`
- 创建：`public/entry/pathos-earth-from-orbit.jpg`
- 创建：`public/entry/ATTRIBUTIONS.md`

- [ ] **步骤 1：实现共用入口框架**

提供 `EntryChrome` 的 `sectionLabel`、`children` 和 `footer` 插槽；共用返回首页链接、四角线和状态信息，不渲染站点第二套导航。

- [ ] **步骤 2：实现 Map 星球入场**

使用本地 NASA 地球图片、遮罩、噪点和任务控制台排版；可信边界显示“4 项州级区域指标”和“51 个州级辖区”；CTA 为 `/map`。

- [ ] **步骤 3：实现 Match 波形入场**

使用静态 SVG 曲线和 CSS 位移/描边动画恢复旧波形场；标题与 CTA 恢复旧版层级，CTA 为 `/match`。

- [ ] **步骤 4：运行入口测试**

运行：`npx vitest run src/test/unit/feature-entry-restoration.test.ts`

预期：Map 与 Match 相关断言通过，Assessment 与 Portfolio 仍失败。

### 任务 3：恢复 Assessment 与 Portfolio 入场

**文件：**
- 创建：`src/components/entry/AssessmentEntry.tsx`
- 创建：`src/components/entry/AssessmentEntry.module.css`
- 创建：`src/components/entry/PortfolioEntry.tsx`
- 创建：`src/components/entry/PortfolioEntry.module.css`
- 创建：`src/app/entry/assessment/page.tsx`
- 创建：`src/app/entry/portfolio/page.tsx`

- [ ] **步骤 1：实现 Assessment 摄影序列**

使用 `/news/campus/harvard-yard.webp`、`/news/campus/mit-great-dome.webp`、`/news/campus/stanford-main-quad.webp`；每 6 秒切换，允许手动选择，CTA 为 `/assessment`，不显示未经验证的数据指标。

- [ ] **步骤 2：实现 reduced-motion 行为**

通过 `matchMedia("(prefers-reduced-motion: reduce)")` 阻止自动轮播；CSS 停止缩放、光晕漂移和状态点脉冲，首张图片保持可见。

- [ ] **步骤 3：实现 Portfolio AI 环境**

使用内联语义中立 SVG/CSS 构成抽象 AI 结构、扫描线和眼部焦点；不使用旧机器人 PNG；CTA 为 `/portfolio`。

- [ ] **步骤 4：运行入口测试**

运行：`npx vitest run src/test/unit/feature-entry-restoration.test.ts`

预期：四套入口组件和路由测试全部通过。

### 任务 4：首页恢复环境层并接线入口

**文件：**
- 修改：`src/app/page.tsx`
- 修改：`src/app/home.module.css`

- [ ] **步骤 1：让失败测试锁定首页入口映射**

确认测试要求主 Hero 的地图 CTA 指向 `/entry/map`、匹配 CTA 指向 `/entry/match`，四张相关模块卡片指向对应 `/entry/*`，Calculator 和 News 不改。

- [ ] **步骤 2：修改首页入口映射**

只改变 `href`，不改变标题、可信统计、模块说明或下方布局。

- [ ] **步骤 3：加入首页地球环境层**

在 Hero 内加入 `aria-hidden` 的本地地球层，位于网格和正文之后，使用遮罩让标题保持清晰，且 `pointer-events: none`。

- [ ] **步骤 4：加入首页 reduced-motion**

停止地球漂移和波形呼吸，保持静态可见。

- [ ] **步骤 5：运行入口与整合测试**

运行：`npx vitest run src/test/unit/feature-entry-restoration.test.ts src/test/unit/pathos-coupling-integration.test.ts`

预期：全部通过。

### 任务 5：完整自动化回归

**文件：**
- 不新增产品文件。

- [ ] **步骤 1：运行 TypeScript**

运行：`npx tsc --noEmit`

预期：0 errors。

- [ ] **步骤 2：运行 ESLint**

运行：`npx next lint --max-warnings 0`

预期：0 warnings。

- [ ] **步骤 3：运行全部 Vitest**

运行：`npx vitest run`

预期：现有测试加新增入口测试全部通过，无 skip/only。

- [ ] **步骤 4：运行生产构建**

运行：`npx next build`

预期：构建成功；新增四个静态 `/entry/*` 路由；大学详情仍保持动态路由。

### 任务 6：真实浏览器验收与运行交接

**文件：**
- 创建：`docs/FEATURE-ENTRY-RESTORATION-REPORT.md`

- [ ] **步骤 1：安全重启本任务前端**

只停止当前整合预览所拥有的进程，选择安全空闲端口，以 backend mode + standalone Preview Bundle 启动构建后的 Next.js。

- [ ] **步骤 2：检查桌面与移动端**

检查首页、四个 `/entry/*`、四个正式功能页，视口至少为 `1440×900`、`768×1024`、`390×844`、`320×568`。

- [ ] **步骤 3：检查 reduced-motion**

模拟 `prefers-reduced-motion: reduce`，确认循环动效停止、图片和 CTA 静态可见。

- [ ] **步骤 4：检查功能非回归**

确认 Map 可拖动与 Marker 可点、Match 权重可操作、Assessment 可提交、Portfolio 可管理、News 摄影入口不变；Console 无新增应用错误。

- [ ] **步骤 5：记录证据**

报告列出路由、截图、视口、动画状态、正式功能可达性、Backend/Bundle 未修改情况和服务状态。
