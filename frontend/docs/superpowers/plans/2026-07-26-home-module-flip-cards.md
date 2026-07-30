# 首页六模块翻牌交互实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将首页六个现有功能板块改为有质感的点击翻牌交互，同时保持路由、文案口径和所有功能页不变。

**架构：** 新增一个小型 Client Component 管理每张卡片自己的翻面状态；首页 Server Component 继续持有六模块数据，只把可序列化属性与图标节点传给卡片。CSS Module 使用 3D `rotateY`、背面隐藏和 reduced-motion 静态切换，不引入新依赖。

**技术栈：** Next.js 14 App Router、React、TypeScript、CSS Modules、Vitest。

---

### 任务 1：首页翻牌契约

**文件：**
- 创建：`src/test/unit/home-module-flip-cards.test.ts`
- 创建：`src/components/home/FlipModuleCard.tsx`
- 修改：`src/app/page.tsx`
- 修改：`src/app/home.module.css`

- [ ] **步骤 1：编写失败测试**

断言首页六个模块使用 `FlipModuleCard`，组件提供按钮、`aria-pressed`、Escape 翻回、正式 Link，并且样式包含 `perspective`、`preserve-3d`、`backface-visibility`、`rotateY(180deg)` 和 reduced-motion。

- [ ] **步骤 2：确认测试因组件缺失而失败**

运行：`npx vitest run src/test/unit/home-module-flip-cards.test.ts`

- [ ] **步骤 3：实现最小翻牌组件**

每张卡片点击正面后翻到背面；背面提供正式路由入口和翻回按钮；Escape 仅关闭当前卡片，不改动任何业务状态。

- [ ] **步骤 4：接入六个现有模块**

保持原来的标题、编号、图标、说明和 href，只替换展示容器。

- [ ] **步骤 5：快速验证**

运行定向测试与 `npx next build`，随后重启当前 3017 预览服务。
