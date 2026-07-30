# PathOS 美国大学数据库第一阶段设计

## 目标与边界

建立可追溯、可更新、可恢复、可审计的美国大学数据库基础设施。本阶段不采集学校全集、不创建远程 Supabase 项目、不请求 API Key，也不改动前端类型或地图组件。

长期 canonical contract 是 PostgreSQL / Supabase 兼容 SQL migration；本地 JSON、JSONL 和 SQLite（后续任务状态或缓存时）只服务 raw、staging、调试和可恢复运行，不能成为长期唯一真相来源。

## Scope 决策

早期 MVP 文档中的「40 所深度核验」是产品规模假设。canonical universe 改为动态排名并集：U.S. News `National Universities` 数字排名不高于 50，和纳入范围内本科专业排名数字名次不高于 20 的学校并集。40 所可作为 future featured、deep-verified 或 launch subset，不能筛掉 canonical university universe。

## 数据流与安全边界

```
raw → staging → normalization → canonical → canonical validation → frontend export adapter → frontend/src/data/universities.json
```

正式前端导出只接受通过 canonical validation 的非测试 canonical records。staging 只能用于 dry-run、preview、调试和报告。端到端测试 fixture 带 `is_test_fixture: true`，只在测试临时目录生成 preview，不得写入 `data/canonical/` 或正式前端 JSON。

## Canonical 模型

- 稳定身份：`universities`、`university_sources`、`university_selection_memberships`。
- 来源：`sources` 是事实溯源根表；原子事实保存 `source_id`，综合事实通过关系表支持多来源。
- 排名：`ranking_snapshots`、`ranking_snapshot_sources`、`university_rankings`、`university_ranking_sources`、`program_rankings`、`program_ranking_sources`；每一版排名追加为 snapshot，绝不覆盖历史。
- 专业：`programs`、`university_programs`；官方专业名与 CIP 标准化映射同时保留。
- 可变事实：`tuition_records`、`student_faculty_ratio_records`、`university_facts`，均记录年份、核验时间与来源。
- 地理与内容：`nearby_places`、`distinguished_students`、`public_figures`、`university_history`、`university_anecdotes`，其中复杂实体各有多对多来源表。
- 审计：`data_quality_issues` 保存 unresolved、conflict、stale 与 validation 问题。

## Migration 原则

使用编号 SQL 文件；仅使用标准 PostgreSQL 类型、外键、唯一约束、检查约束和索引。第一阶段不引入 pgvector、PostGIS、Supabase Auth、RLS、Edge Functions 或远程依赖。当前未运行 PostgreSQL，因此静态 migration 审计验证编号顺序、主键、外键目标、约束和来源关系；真实数据库 apply test 属于后续本地 PostgreSQL CI 工作。

## 最小闭环

`tests/fixtures/test-university-raw.json` 经过 raw JSON Schema validation、staging、normalization、canonical-compatible validation 与前端 export adapter。测试断言输出包含 `UniversityPOI` 所有必填字段，并断言测试 fixture 不可进入正式 canonical 或正式前端输出路径。

## 失败处理

所有无来源、违反 cutoff、身份冲突、无法解析的 CIP 映射或缺少年份的记录要么被 validation 拒绝，要么进入 `data_quality_issues`；不得猜测或用前端 JSON 反向补齐数据。
