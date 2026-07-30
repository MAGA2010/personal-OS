# PathOS 并行开发耦合计划

## 目标

在不覆盖稳定工作区、Backend、Preview Bundle 和旧 checkpoint 的前提下，完成候选项目盘点、Canonical 选择、视觉提取、隔离整合与真实浏览器验收。

## 决策门槛

1. 数据真实性优先：`pathos-preview-v1`、62 校、904 条 verified 记录为不可退让边界。
2. 功能正确性优先：保留现有 BFF、DataSource、MapLibre、四项州级指标、URL 状态和缺失值语义。
3. 视觉择优：候选首页的编辑式构图可提取，但不复制 mock 数据、未知媒体、状态管理或全局样式。
4. 风险隔离：首次整合只在 `pathos-coupling/integration` 完成；High 风险后端、migration、数据导入只记录不执行。

## 执行顺序

- 建立 Canonical 只读快照与候选工作树/提交/ZIP 三类版本实体。
- 盘点项目、路由、模块血缘、依赖、Backend、数据和媒体。
- 建立冲突决策矩阵。
- 以稳定前端为底座，HYBRID 吸收候选首页视觉语言。
- 完成本地可授权 News 摄影与 Credits，不采用候选未知来源图片。
- 补齐整合契约测试和地图运行时耦合修正。
- 在独立安装依赖的 integration 目录运行 TypeScript、Lint、529 项测试和生产构建。
- 用真实 Preview Backend 完成六视口、主题、核心路由和对比截图验收。

## 明确不做

- 不替换 Backend，不运行 migration，不导入候选数据。
- 不整体覆盖 `src`、`public`、`package.json` 或 lockfile。
- 不把候选 `/map/rankings`、explore 原型伪装成正式功能。
- 不创建 tag、commit、push 或 pass checkpoint。
- 不启用 Production Data Export。
