# PathOS 未来路线图

本路线图是恢复开发时的建议，不属于当前冻结版本承诺。

## Phase 0：恢复前复核

- 从冻结哈希确认 Backend、Bundle、区域工作簿和前端来源。
- 选择唯一工作副本，避免同时修改稳定前端、integration 和 Vercel staging。
- 首先关闭公网 Map 的 Marker / Choropleth / metric retention 复核项。
- 建立新的 change manifest、自动化和独立浏览器 Gate。

## Phase 1：AI Advisor

- 接入真实模型服务与可观测性。
- 为提示词、输出 schema、缺失值和来源边界建立评估集。
- 增加失败策略、成本控制、隐私保护和人工复核入口。
- 明确 AI 只做辅助解释，不做录取保证。

## Phase 2：User Profile

- 用户注册、登录、会话与权限。
- 可撤回的学生画像、偏好、预算和学校清单。
- 隐私政策、数据导出与删除机制。
- 将匿名 Demo 数据与用户私有数据严格隔离。

## Phase 3：Application Tracker

- 申请院校、截止日期、材料、任务与状态追踪。
- 顾问 / 家庭协作权限。
- 通知、审计日志和数据恢复。

## Phase 4：More Universities

- 扩大大学覆盖前先扩展来源、schema 和 validator。
- 建立增量更新与版本迁移策略。
- 保持 provenance、warning 和 missing-first 原则。
- Rankings / Explore 只有在真实数据契约完成后再产品化。

## Phase 5：商业化

- 明确免费、订阅或机构版边界。
- 接入支付前完成账户、合规、隐私和客服体系。
- 建立监控、SLA、成本模型和事故响应。
- Production Data Export 需单独审批和数据 Gate，不因商业化自动开启。
