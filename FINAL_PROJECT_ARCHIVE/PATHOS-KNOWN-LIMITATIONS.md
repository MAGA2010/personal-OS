# PathOS 已知限制

## 1. AI 不是生产级 LLM 服务

当前 AI 路由保留外部模型适配能力，但冻结版本可在没有模型密钥时使用确定性本地分析。该结果是 Demo 辅助框架，不是经过安全、质量和公平性评估的生产级 AI 顾问，也不能替代专业意见。

Stage 5 verified AI context 仍为 disabled；后期本地 Demo 内容不得被误称为已验证 AI 事实。

## 2. 公网地图仍需最终人工复核

冻结前的公网调试曾出现以下现象：

- 启用区域 Choropleth 后，大学 Marker 与州级填色图层的共存表现不稳定。
- 点击州后，所选 metric 是否始终保持（例如 safety 不跳回 income）经历过回归修复，但没有在归档阶段重新完成完整浏览器 Gate。

因此，本归档保留代码和测试现状，但不声明公网 Map 已达到生产稳定性。未来恢复开发时，应首先复核 Marker、Choropleth、state URL 和主题切换的组合场景。

## 3. 两套区域数据边界并存

Stage 5 Preview Bundle 中 Choropleth 仍为 blocked、records 为空；Stage 7 另行加入 4 项、204 条、51 个辖区的地图 Demo 数据。区域数据只用于 Map，不进入 Match。未来若统一契约，必须经过新的数据审查和 Gate。

## 4. News 摄影需要持续维护授权

当前 9 张校园摄影为本地 WebP，并有 Credits / License 记录。未来替换、裁剪或重新发布时，仍需逐张保留作者、来源页面、许可证、ShareAlike 和修改说明。

## 5. Rankings 与 Explore 未正式产品化

并行候选中存在相关视觉或概念，但没有纳入正式数据契约。当前不得用旧排名、mock 或视觉原型冒充可用产品。

## 6. 用户与商业系统缺失

项目没有生产级用户账户、身份认证、权限、隐私管理、数据删除、支付、订阅、发票或客服流程。

## 7. Preview Bundle 仍是 Demo 数据模式

Bundle 明确为 `sourceLimited=true`、`incomplete=true`、`notFinal=true`。部分政策、人物和学校字段仍 pending / deferred / not reported。

## 8. Baidu Map provider 未作为正式运行链路启用

项目保留过 Baidu provider 试验与文档，但当前正式地图链路以 MapLibre 为准。任何真实 AK 都不应进入源码、文档或归档。

## 9. 没有生产级部署

当前存在 Vercel 公网 Preview / Demo，但没有生产发布流程、正式域名承诺、监控告警、备份策略、SLA、隐私合规评估或 Production Data Export。因此不能称为生产部署。

## 10. 源码形态较多

最终保留目录中同时存在稳定前端、部署快照、历史候选和调试目录。它们没有在本次归档中删除或移动。未来开发者必须先阅读技术库存和交接文档，再选择工作副本。

## 11. 本次归档的验证范围

- 归档时重新运行了部署快照的 Vitest：21 个文件、563/563。
- 本次冻结没有重新构建、重新跑完整浏览器矩阵或修复现有问题。
- 历史报告中的 TypeScript、Lint 和 Build 结果属于对应阶段证据，不应自动等同于未来环境结果。
