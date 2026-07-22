# Stage 3D-Fill Bulk People Completion v2 设计规格

## 1. Purpose

Stage 3D-Fill Bulk People Completion v2 验证 program-person 写入链路，但不以正向人物数量为完成条件。本阶段固定处理 Candidate v2 的 62 所学校，并为每校现有 demo-program 列表中的第一个项目生成一个 program-person slot。

完成口径是 `slots_processed = 62 / 62`。每个 slot 必须明确标记为 `identified_person`、`source_review_not_completed` 或 `no_qualifying_person_found`，不得把未完成来源审查解释为现实中没有合格人物。

本阶段是独立、`source_limited`、`incomplete`、`not_final` 的数据 overlay，不是 final People/Narrative dataset。

## 2. Immutable Scope and Inputs

只读输入为：

- Candidate v2 的 62 校身份范围；
- Stage 3C Academic + Geo overlay 中每校按既有顺序排列的 `top_5_programs_for_demo`；
- Stage 3D-Fill Bulk People v1 的 62 校 notable-attendance records、source manifest 和 cache manifest；
- 已通过 hardening 的 People Pilot program-person/source/cache records，可在 top-1 program 精确匹配时复用；
- 新增且经过 reviewed intake 的 program-person observations、source manifest、cache manifest 和 exclusions。

每校只选择 `top_5_programs_for_demo[0]`。不得重新排序 demo programs，不得新增 program，不得改变 program 名称、normalized name、source basis、rank 或其他 program provenance。

## 3. Slot Contract

每个 slot 至少包含：

- `candidate_id`
- `canonical_id`
- `university_display_name`
- `slot_index = 1`
- `program_name`
- `normalized_program_name`
- `program_source_basis`
- `program_source_id`
- `program_source_record_id`，如上游提供
- `program_provenance_anchor`
- `record_status`
- `person_name`
- `canonical_person_id`
- `attendance_relationship`
- `program_match_type`
- `source_id`
- `source_url`
- `evidence_anchor`
- `quote_verification_method`
- `reviewed_scope`
- `reviewed_source_ids`
- `null_reason`

`program_provenance_anchor` 只证明 slot 对应的 demo program；它不能证明人物与专业的关系。人物专业关系必须由独立的 reviewed program-person evidence 支持。

## 4. Status Semantics

### 4.1 `identified_person`

只有以下条件全部满足时才能写入：

1. 人物与学校的 attendance relationship 有直接证据；
2. 人物与 slot program 存在 `direct_program_match` 或 `direct_related_program_match`；
3. 人物具有 source-disambiguated `canonical_person_id`；
4. program-person source 能解析到 manifest；
5. positive direct quote 通过 `local_cache_substring_check`；
6. program match 没有使用职业、公司、成就、学校名气或一般 alumni 身份进行推断。

### 4.2 `source_review_not_completed`

来源范围尚未完成审查、没有 cache-verified program relationship，或现有 attendance person 与 top-1 program 不匹配时使用。该状态必须：

- person、relationship、program match 和 positive evidence 字段保持 null；
- `null_reason = program_person_source_review_not_completed`；
- 不渲染为「无」或 `no_qualifying_person_found`。

### 4.3 `no_qualifying_person_found`

只有同时满足以下条件才允许使用：

- `reviewed_scope` 为非空列表，并明确列出已审查的官方来源类型或页面范围；
- `reviewed_source_ids` 为非空列表，且全部解析到 manifest；
- 审查记录说明为什么没有观察项满足 attendance + program match 的双重证据标准。

该状态只表示在披露的 reviewed scope 中没有合格证据，不表示现实中不存在合格人物。

## 5. Attendance and Identity Rules

正向 attendance relationship 只允许：

- `graduated`
- `alumnus_unspecified`
- `attended_no_degree`

`faculty_only`、`donor_only`、`honorary_degree_only`、`unclear` 和同名未消歧人物只能进入 exclusions，不能进入 positive slot。

人物 ID 使用已加固的 deterministic 方案：normalized person name + candidate context + source-backed disambiguator。禁止 `person:<name-slug>` 形式的纯姓名 ID，禁止 fuzzy merge。同一 normalized name 出现在不同学校或来源 context 时必须生成不同 ID；无法用来源消歧时写入 `same_name_unresolved` exclusion。

## 6. Program Match Rules

允许：

- `direct_program_match`：reviewed source 明确陈述的人物 major/degree/program 与 slot normalized program 相同；
- `direct_related_program_match`：reviewed source 明确陈述的 degree/program 与 slot 存在预先披露、可审计的直接关联，并在 observation 中保存 match notes。此类型不能依赖职业或成就。

禁止：

- 从职业、公司、头衔或知名度反推专业；
- 从人物是 alumni 推断其专业；
- 仅凭 program 名称的模糊相似度自动匹配；
- 用 graduate-only、honorary、faculty 或 donor 关系代替学生关系；
- 修改上游 demo-program 名称以制造匹配。

## 7. Evidence and Source Cache

每个 positive program-person fact 必须有：

- manifest-resolved `source_id` 和 HTTPS `source_url`；
- `evidence_type = direct_quote`；
- 短 `evidence_anchor.quote`；
- `quote_verification_method = local_cache_substring_check`；
- cache path、SHA-256 和 retrieval/review notes。

Validator 必须检查 cache 文件存在、SHA-256 匹配、source URL 存在于 cache、quote 是 cache text 的 substring。`manual_verbatim_check` 不允许成为本阶段最终状态。cache 正文保持 gitignored，只提交结构化 manifest、短 evidence anchors 和 SHA-256。

来源优先学校官方 alumni/profile/archive/program 页面。People/Narrative detail source 不得写入或覆盖 U.S. News ranking fields；Stage 3C 的 program provenance 只读保留。

## 8. Artifact Plan

独立输出目录：

`data-pipeline/artifacts/stage3d-fill-bulk-people-completion-v2/`

至少包含：

1. `stage3d-fill-bulk-people-v2-plan.json`
2. `stage3d-fill-bulk-people-v2-slots.json`
3. `stage3d-fill-bulk-people-v2-identified-people.json`
4. `stage3d-fill-bulk-people-v2-exclusions.json`
5. `stage3d-fill-bulk-people-v2-source-manifest.json`
6. `stage3d-fill-bulk-people-v2-cache-manifest.json`
7. `stage3d-fill-bulk-people-v2-gap-disclosure.json`
8. `stage3d-fill-bulk-people-v2-summary.json`
9. `stage3d-fill-bulk-people-v2-validation-result.json`

报告：

`data-pipeline/reports/stage3d-fill-bulk-people-completion-v2-report.md`

新增 inputs、generator、validator、CLI 和 tests 必须与 v1 artifacts 分离。

## 9. Summary Metrics

Summary 必须分别输出：

- `total_universities = 62`
- `slots_target = 62`
- `slots_processed = 62`
- `identified_person_count`
- `source_review_not_completed_count`
- `no_qualifying_person_found_count`
- `direct_program_match_count`
- `direct_related_program_match_count`
- `local_cache_substring_check_count`
- `manual_verbatim_check_count = 0`
- `cache_verified_quote_count`
- `cache_missing_count = 0`
- `exclusions_count`
- `source_policy_violations = 0`
- `ranking_field_contamination = 0`
- `program_people_before_count = 0`
- `program_people_after_count = identified_person_count`
- `source_limited = true`
- `incomplete = true`
- `not_final = true`

## 10. Validator Rules

Validator 必须 fail closed，并检查：

1. Candidate v2 范围恰好为 62 所且没有新增学校；
2. 每校恰好一个 top-1 slot，合计 62；
3. slot program 与 Stage 3C `top_5_programs_for_demo[0]` 的名称、normalized name 和 provenance 完全一致；
4. 每个 slot 只有三种允许状态之一；
5. `identified_person` 满足 attendance、program match、identity、source 和 cache 全部规则；
6. `source_review_not_completed` 没有 positive person/evidence，也没有被显示为「无」；
7. `no_qualifying_person_found` 有非空 reviewed scope/source IDs；
8. 关系白名单生效，faculty/donor/honorary/unclear 不进入 positive records；
9. canonical person ID 不是纯姓名 ID，同名 context 不会自动合并；
10. program match 不包含 profession/company/fame inference 标记；
11. 每条 positive quote 通过 cache substring 和 SHA 校验；
12. manual-only quote verification 为 0；
13. source-policy guard 被实际调用，violations 为 0；
14. ranking contamination 为 0；
15. artifacts 可 deterministic、byte-identical 重生成；
16. Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage 3D-Fill v1 与 frontend 均未修改；
17. final universe、正式 memberships 和 frontend export 均未生成。

## 11. Test Strategy

TDD tests 必须先验证红灯，再实现：

- 62 校恰好生成 62 个 top-1 slots；
- top-1 program provenance 被逐字段保留；
- 已有 cache-verified direct/related match 可生成 `identified_person`；
- attendance 缺失、program evidence 缺失或职业推断会被拒绝；
- faculty/donor/honorary/unclear 会被拒绝或进入 exclusions；
- pure-name person ID 和 same-name context merge 会失败；
- cache missing、SHA mismatch、quote missing 和 manual-only verification 会失败；
- `source_review_not_completed` 不得带 positive evidence 或显示为「无」；
- `no_qualifying_person_found` 缺 reviewed scope/source IDs 会失败；
- deterministic regeneration、upstream SHA、frontend non-mutation 和 final-output flags；
- source policy 与 ranking contamination guards。

## 12. Non-Mutation and Acceptance Criteria

本阶段通过需同时满足：

- `slots_processed = 62 / 62`；
- 三种状态计数之和为 62；
- 所有 positive records 通过 attendance + program match + identity + local cache 校验；
- 未审查 slot 保持 `source_review_not_completed`；
- 不以 identified count 作为阶段通过门槛；
- program people coverage 从 0 更新为实际 `identified_person_count`，不得夸大；
- source-policy violations 与 ranking contamination 均为 0；
- 全部 Python tests、独立 validator、schema/migration validation、byte-identical regeneration 和 `git diff --check` 通过；
- cache 正文不进入 commit；
- frontend 和上游 artifacts 无修改；
- 不生成 final universe、正式 memberships 或 frontend export；
- 完成后停止并等待 Gate review。
