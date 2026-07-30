# Stage 3D-Fill Reviewed People + Narrative 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为固定 Candidate v2 的 62 所学校建立独立的、已审查来源驱动的 People + Narrative 填充 overlay，同时保留未审查与已审查无结果的严格语义差异。

**架构：** 新增 `stage3d_fill_people_narrative.py`，它只读取 Candidate v2、不可变 Stage 3/3B/3C/3C2/3D framework 和 version-controlled reviewed observations。生成器为每个 Stage 3C demo-program slot 输出 `identified`、scoped `无` 或 `source_review_not_completed`；history、attendance 与 anecdotes 仅从带短 anchor 的已审查 observation 生成。所有输出写入独立 Stage 3D-Fill 目录。

**技术栈：** Python 3 标准库、现有 `pathos_data` CLI、JSON artifacts、`unittest`、允许的正常公开网页人工审查；不保存网页快照。

---

## 文件计划

### 新增

- `data-pipeline/src/pathos_data/stage3d_fill_people_narrative.py`：source intake loader、deterministic builder、validator、report renderer、writer。
- `data-pipeline/data/stage3d-fill/`：source manifest、resolved person mappings、program-people observations、attendance observations、history observations、anecdote observations、reviewed no-result observations。
- `data-pipeline/artifacts/stage3d-fill-reviewed-people-narrative/`：9 个用户指定 output artifacts。
- `data-pipeline/reports/stage3d-fill-reviewed-people-narrative-report.md`：生成的范围、source、coverage 与 gap 报告。
- `data-pipeline/tests/test_stage3d_fill_people_narrative.py`：source semantics、determinism、scope 与 full-artifact regression tests。

### 修改

- `data-pipeline/src/pathos_data/__main__.py`：仅增加 Stage 3D-Fill generate/validate commands。
- `docs/database-source-policy.md`：Stage 3D-Fill reviewed-source、relationship 和 paraphrase 规则。
- `docs/database-development-log.md`：记录 source intake、coverage、gap、validation 与非最终边界。

### 绝不修改

- Candidate v2、Stage 3、3B、3C、3C2、3D framework artifacts。
- `frontend/`、正式 universe、正式 selection memberships、正式 frontend export 或 Stage 3A stash。

## 任务 1：先建立 source-intake 与测试契约

- [ ] 编写失败测试，证明：62 个 candidate IDs 和 310 个 Stage 3C program slots 固定；`无` 必须有非空 `reviewed_scope`/`reviewed_source_ids`；未审查不能输出 `无`；`faculty_only`/`donor_only`/`honorary_degree_only`/`unclear` 不能进入 student/alumni output；ranking field 出现即失败。
- [ ] 运行 `PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_people_narrative -v`，确认 builder 未实现时失败。
- [ ] 创建最小空 observation inputs；空输入必须生成 explicit source gaps，不能虚构 `无` 或人名。
- [ ] 把 source manifest schema 固定为 `source_id`、`candidate_id`、`field_domain`、`source_type`、`source_url_or_reference`、`publisher`、`accessed_date`、`source_confidence`、`field_level_provenance_required`、`limitation_note`。

## 任务 2：实现 generator 与 validator

- [ ] 实现下列 status：

```python
TOP_SLOT_STATUSES = {
    "identified",
    "no_qualifying_person_found",
    "source_review_not_completed",
}
ALLOWED_STUDENT_RELATIONSHIPS = {
    "graduated", "attended_no_degree", "alumnus_unspecified",
}
EXCLUDED_RELATIONSHIPS = {
    "faculty_only", "donor_only", "honorary_degree_only", "unclear",
}
```

- [ ] 对 affirmative people/attendance/history/anecdote 调用 `validate_source_policy_use(publisher, "detail", has_field_provenance=True)`，并要求 manifest 可解析、短 direct-quote anchor 和 source-backed resolved canonical person mapping。
- [ ] 对 `no_qualifying_person_found` 强制 `display_value="无"`、非空 reviewed scope/source IDs、scoped absence null reason；对未审查强制 null display 与 `source_review_not_completed` gap reason。
- [ ] history/anecdote 仅接受短 paraphrase（上限 280 chars）和短 quote（上限 280 chars），拒绝长段正文、无 source、无 anchor 和 ranking field contamination。
- [ ] 在 generate/validate CLI 都要求全部 upstream/input/output artifact paths；validator 通过 deterministic rebuild、immutable fingerprints、scope、policy/flags、cache/frontend boundary 验证。

## 任务 3：reviewed source intake

- [ ] 仅通过正常可访问的学校官方 biography、alumni/archive、history/archive、official publication 或直接支持事实的可信参考页收集 observations；不把搜索 snippet、AI memory、论坛或未审查转载作为 evidence。
- [ ] 对每个实际审查且无合格人物证据的 slot，写入 scoped `无` observation 并列出审查的来源类型和 source IDs；从未审查的 slot 维持 `source_review_not_completed`。
- [ ] 对任何人名、就读、major、degree、history 或 anecdote 只保存短 direct quote 与 paraphrase，不提交完整网页、长传记或 HTML cache。
- [ ] 每所学校尝试至少一个 history source；若环境或来源不足，生成明确 source gap，而不编造历史摘要。

## 任务 4：生成、验证与交付

- [ ] 运行 `generate-stage3d-fill-reviewed-people-narrative`，只写 `artifacts/stage3d-fill-reviewed-people-narrative/` 和 report。
- [ ] 运行正式 Stage 3D-Fill validator；运行全部 Python tests、fixture/schema/migration validation、`git diff --check`。
- [ ] 用 `git diff --name-only` 证明没有 frontend、Candidate v2 或 Stage 3/3B/3C/3C2/3D framework artifact 变更；用 `git ls-files` 证明 cache 未追踪。
- [ ] 显式暂存 Stage 3D-Fill 文件和文档，强制暂存 ignored report，执行本地 commit：`feat(data): fill reviewed people and narrative details`；不 tag、push、merge、rebase。

## 验收标准

- Candidate 范围为 62 所，top program slot 范围为 310，且所有 slot 都有 identified、scoped `无` 或 explicit source gap。
- 任何「无」只表示有记录的已审查来源范围没有合格证据，绝不表示现实世界绝对不存在。
- `faculty_only`、`donor_only`、`honorary_degree_only` 和 `unclear` 不出现在 student/alumni 内容。
- 每条 affirmative claim 有 source ID、短 direct quote、resolved person identity（如适用）和 short paraphrase（history/anecdote）。
- `source_policy_violations=0`、`ranking_field_contamination=0`；生成可 byte-identical 重建；不产生 final/frontend output，也不修改上游或 frontend。
