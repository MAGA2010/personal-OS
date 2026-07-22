# PathOS 美国大学数据库数据合同

## 目的与范围

本合同定义 PathOS 美国本科选校数据库的长期 canonical contract。正式数据库以 `data-pipeline/migrations/` 中按编号排序的 PostgreSQL-compatible SQL 为准；不要求本地或远程 Supabase 实例。

学校全集是动态排名并集：`National Universities` 数字排名不高于 50，和纳入范围内本科专业排名数字名次不高于 20 的去重并集。并列按数字名次纳入。早期「40 所」仅可用于 featured、deep-verified 或 launch subset。

## 强制数据流

```
raw → staging → normalization → canonical → canonical validation → frontend export adapter → frontend/src/data/universities.json
```

- `raw`：保留抓取或人工输入的最初结构与来源元数据。
- `staging`：只用于 dry-run、preview、调试、重试与报告。
- `normalization`：解析身份、名称、CIP、年份、单位与值域；不能猜测缺失值。
- `canonical`：对应 migration 定义的关系记录，是唯一可供正式导出的数据层。
- `canonical validation`：检查 schema、外键、唯一性、来源、排名范围和测试 fixture 隔离。
- `frontend export`：只读取通过验证的非测试 canonical records；不得读取 raw 或 staging，也不得从现有 `universities.json` 反向导入。

## 身份与选择范围

- `universities.internal_id` 是 PathOS 稳定标识。
- IPEDS `UNITID` 是学校去重的优先键；名称或别名只能作为解析线索。
- `selection_reason` 为 `national_top_50`、`program_top_20` 或 `both`，只作为学校级 display / summary。`university_selection_memberships` 只保存原子理由；`both` 必须展开为两条记录。
- 排名范围配置位于 `data-pipeline/config/ranking-scope.json`。它现在只定义机制，不含任何真实学校名单或排名。
- 每版真实本科 category inventory 位于 `data-pipeline/data/ranking-discovery/<edition>/category-inventory.json`，而不是 `ranking-scope.json`；该 inventory 必须保留 category lineage 以表达改名、新增、删除、拆分与合并。
- ranking pilot 的 `verified` record 需要每个 claimed direct field 的可人工复核 evidence anchor。`edition` 只有在 `edition_direct` 时才能 claimed direct；release-cycle inference 与 ambiguous year label 只能产生 partial/unresolved candidate。
- 正式/批量 ranking pilot validation 是 full artifact path：seed batches、identity mappings、source manifest、candidate observations、coverage matrix 与 validation result 必须共同校验。该路径不创建 canonical university、selection membership 或 frontend export。

## Source-limited universe candidate contract

- `data/university-universe/<edition>/candidate/` 是审计用、source-limited 的中间产物，不是 canonical university universe。它必须标记 `source_limited: true`、`incomplete: true`、`not_final: true`，并明确禁止 final universe、selection memberships 和 frontend export。
- candidate 与 membership 的每个 `supporting_ranking_records`、source ID 和 evidence-anchor reference 都必须回验为同一 corpus 的 accepted verified record。partial、unresolved、no-verified stream 或不存在的 record ID 均不得进入。
- 正式 `validate-universe-candidate` 和 `generate-universe-candidate` 必须同时接收 corpus root 及 `corpus-validation-result.json`；它们重跑 corpus validation，并比对 counts、gaps 与 readiness。缺少任一 corpus artifact 必须 fail closed。
- candidate artifact 是 deterministic generator output。正式 validator 会拒绝任何与当前 revalidated corpus 派生结果不一致的手工编辑。

## 关系模型与溯源

| 领域 | 主表 | provenance 规则 |
| --- | --- | --- |
| 学校身份 | `universities` | `university_sources` 支持多个身份、地址和别名来源 |
| 排名 | `ranking_snapshots`、`university_rankings`、`program_rankings` | snapshot 与 ranking record 均有多对多 source 关系；program ranking category 只从 `ranking_snapshots.category` 获得 |
| 专业 | `programs`、`university_programs` | 官方名称保留；CIP 映射可标记 unresolved |
| 学费与师生比 | `tuition_records`、`student_faculty_ratio_records` | 原子记录直接保存 `source_id` |
| 结构化可变事实 | `university_facts` | `university_fact_sources` 支持多来源 |
| 地理 | `nearby_places` | 直接保存源与距离方法 |
| 人物与叙事 | `distinguished_students`、`public_figures`、`university_history`、`university_anecdotes` | 各自使用多对多来源表 |
| 审计 | `data_quality_issues` | 记录 unresolved、冲突、stale 与 validation 问题 |

一个来源只可用于单个原子事实时可直接存 `source_id`；需要共同支持结论的实体必须使用对应关系表，不允许为了简化而丢失来源。

## 测试 fixture 隔离

`data-pipeline/tests/fixtures/` 下测试数据必须含 `is_test_fixture: true`。它可生成临时 canonical-compatible record 和 preview export，以验证适配器；`assert_formal_canonical` 和正式 export 必须拒绝它。fixture 绝不进入 `data/canonical/` 或 [`frontend/src/data/universities.json`](/Users/jiayihuang/PathOS/frontend/src/data/universities.json)。

## 前端兼容性

本阶段不修改 `UniversityPOI`。adapter 输出其现有必填字段，并以 `frontend-universities.json` schema 校验。缺少任何必填前端字段的真实 canonical record 必须拒绝正式导出，不能填充推测值。
