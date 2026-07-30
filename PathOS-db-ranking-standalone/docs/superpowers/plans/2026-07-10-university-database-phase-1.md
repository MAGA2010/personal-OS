# PathOS 美国大学数据库第一阶段实现计划

> **面向 AI 代理的工作者：** 按测试驱动顺序实现：先写测试并验证失败，再写最小实现并验证通过。

**目标：** 建立本地可验证、PostgreSQL-compatible 的大学数据 canonical contract 与 pipeline skeleton。

**架构：** SQL migrations 定义长期关系模型；Python 标准库 pipeline 校验版本化 JSON Schema、执行 raw 至 canonical 的最小 transform，并只从已验证 canonical record 生成前端 preview/export。

**技术栈：** PostgreSQL SQL、Python 3.9 标准库、JSON Schema Draft 2020-12、Next.js TypeScript check。

---

## 文件职责

- `data-pipeline/migrations/`：有序 PostgreSQL canonical schema。
- `data-pipeline/schemas/v1/`：raw、staging、canonical 和 export JSON Schema。
- `data-pipeline/src/pathos_data/`：CLI、校验、转换、导出和 migration 静态审计。
- `data-pipeline/tests/`：fixture 驱动的端到端与 migration 约束测试。
- `docs/database-*.md`：数据合同、来源政策、字段定义与持续开发日志。

## 任务

### 任务 1：建立失败的端到端测试

- 创建：`data-pipeline/tests/test_end_to_end.py`
- 创建：`data-pipeline/tests/fixtures/test-university-raw.json`

- [ ] 验证 raw fixture 被 schema 校验，能转换为 staging 和 canonical-compatible record。
- [ ] 验证 canonical record 才能给 export adapter 使用，且输出满足 `UniversityPOI` 必填字段。
- [ ] 验证测试 fixture 被禁止写入正式 canonical 和正式前端路径。

运行：`PYTHONPATH=src python3 -m unittest discover -s tests -v`。
预期：实现前因 `pathos_data` 模块缺失而失败。

### 任务 2：实现最小闭环与 CLI

- 创建：`data-pipeline/src/pathos_data/{__init__,__main__,schema_validation,pipeline,exporter,migration_audit}.py`
- 创建：`data-pipeline/pyproject.toml`

- [ ] 实现无外部依赖的 JSON Schema 子集校验与 schema 文档审计。
- [ ] 实现 fixture 隔离、staging、normalization、canonical validation、preview export 和正式写入保护。
- [ ] 实现 `validate`、`report`、`export-frontend`、`discover-rankings`、`collect` 与 `normalize` 的 dry-run CLI 契约。

### 任务 3：定义 SQL、Schemas 与数据文档

- 创建：`data-pipeline/migrations/001_core.sql`、`002_rankings_and_programs.sql`、`003_enrichment_and_quality.sql`
- 创建：`data-pipeline/schemas/v1/*.json`
- 创建：`docs/database-data-contract.md`、`docs/database-source-policy.md`、`docs/database-field-definitions.md`

- [ ] 通过多对多 sources 表完成复杂事实 provenance。
- [ ] 使用 migration 静态测试验证顺序、外键、唯一约束与 snapshot / provenance 设计。
- [ ] 明确正式前端导出只读取 canonical validated data。

### 任务 4：验证与交付记录

- 创建：`data-pipeline/tests/test_migrations.py`
- 修改：`docs/database-development-log.md`

- [ ] 运行 Python 单元测试和 schema validation。
- [ ] 运行 `npx tsc --noEmit`，不启动端口测试。
- [ ] 在开发日志记录决策、文件、验证、风险和下一步。
