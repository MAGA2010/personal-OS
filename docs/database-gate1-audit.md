# PathOS 数据库 Gate 1 独立审计记录

## 审计信息

- 审计日期：2026-07-10
- 审计范围：Phase 1 PostgreSQL-compatible migrations、JSON Schema、Python pipeline skeleton、fixture 隔离、前端 export compatibility、项目文档与离线验证。
- 实际运行测试：Python unit tests、fixture pipeline validation、JSON Schema validation、migration static validation、frontend TypeScript validation、`git diff --check`。
- 独立审计结论：**B. CONDITIONAL PASS**。
- Critical：无。

本文件忠实记录独立 Agent 的结论；仅 M4 与 M5 在 Gate 1 收口中修复，其余项目不因记录在此而视为已解决。

## High

- H1：canonical SQL 与 Python JSON pipeline 尚未绑定。
- H2：frontend export 当前仍为 `frontend_fields` 直通。
- H3：tuition / ratio 的 provenance 仍为单一 source。

H1–H3 不阻塞 ranking discovery：第二阶段只需发现、版本化和核验 ranking universe，不写入真实 PostgreSQL、不会生成真实前端 projection，也不采集 tuition / ratio。它们分别延后到 PostgreSQL runtime binding / CI、Phase 6 frontend export、Phase 4 tuition 与 ratio 采集。

## Medium

- M1：tuition / ratio 缺少合理去重约束。延后到 Phase 4 的收费与师生比口径实现。
- M2：`residency_basis` 是自由文本。延后到 Phase 4，在国际生 / out-of-state 定价口径锁定时枚举化。
- M3：`null_reason` 未标准化。延后到跨实体缺失数据政策与质量审计阶段。
- M4：program ranking category 存在重复真相来源。**本 Gate 1 修复。**
- M5：`both` membership 语义错误。**本 Gate 1 修复。**
- M6：`university_facts` 的 NULL uniqueness / conflict policy 尚未锁定。延后到 PostgreSQL runtime binding 与冲突处理策略阶段。

## Low

独立审计摘要未提供单独编号的 Low 项；其余低优先级问题按非阻断的文档、测试覆盖和运行维护事项记录，不宣称已解决。

## Gate 1 修复理由

M4 会使本科专业排名 category 的过滤、审计和导出在同一记录上出现可独立漂移的两个值；M5 会把一个派生 display summary 错写为 canonical 纳入事实。两者都直接影响第二阶段 ranking universe 的可审计性，必须在 discovery 前修复。

## 延后项与准入

本 Gate 1 不扩展 tuition provenance、PostgreSQL runtime binding、真实 frontend projection 或 U.S. News discovery。ranking discovery 的准入条件是：004 migration 存在、M4/M5 回归测试通过、原有测试无回归、没有真实学校数据或网络采集，并保持 `UniversityPOI` 与地图组件不变。
