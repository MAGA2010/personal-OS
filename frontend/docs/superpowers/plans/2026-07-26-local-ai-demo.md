# 本地 AI Demo 输出实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让 AI 学校评估与 AI 清单分析按钮在 Preview 中立即展示本地示例内容，不依赖当前关闭的 AI context。

**架构：** 保留两个页面的输入和清单功能，只把点击处理改为本地常量结果；结果明确标注为 Demo，不输出学校分数、录取结论或新的数据事实。显眼的英文区块标签同步改成中文。

**技术栈：** React、TypeScript、Vitest、Next.js。

---

### 任务 1：本地 Demo 行为

**文件：**
- 创建：`src/test/unit/local-ai-demo.test.ts`
- 修改：`src/app/assessment/page.tsx`
- 修改：`src/app/portfolio/page.tsx`

- [ ] 编写失败测试，要求两个按钮使用本地 Demo、无 `/api/ai/analyze` 请求、无伪造数值。
- [ ] 运行测试并确认因网络调用仍存在而失败。
- [ ] 将两个处理函数替换为立即设置本地结果，按钮在空输入时也可展示示例。
- [ ] 将相关英文区块标签替换为中文，并标注“非真实 AI 结论”。
- [ ] 运行定向测试和生产构建，重启 3017 预览。
