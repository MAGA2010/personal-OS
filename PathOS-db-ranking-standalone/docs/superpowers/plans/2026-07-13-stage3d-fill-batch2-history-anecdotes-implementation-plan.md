# Stage 3D-Fill Batch 2：Reviewed History + Anecdotes Expansion 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在不回写 Batch 1 或任何上游 artifact 的条件下，为固定 62 所 Candidate v2 学校增加 8–12 条经审阅的 history 与 anecdote 事实，并给出本批及累计覆盖。

**架构：** 新增独立 Batch 2 input contract、deterministic generator、validator、CLI 与 artifact root。生成器只读取 Candidate v2、Stage 3C demo slots、Stage 3D-Fill seed、已提交 Batch 1 artifacts 和版本化 Batch 2 observations；positive anchors 必须逐字匹配 Batch 2 manifest 的 reviewed short-quote allowlist。Batch 2 summary 同时保存本批数量和从 Batch 1 artifact 计算的累计数量。

**技术栈：** Python 3 标准库、现有 `pathos_data` CLI、JSON artifacts、`unittest`、Git。

---

## 文件变更

- 创建：`data-pipeline/src/pathos_data/stage3d_fill_batch2_history_anecdotes.py` — Batch 2 generator、validator、report renderer、writer。
- 修改：`data-pipeline/src/pathos_data/__main__.py` — Batch 2 generate/validate CLI。
- 创建：`data-pipeline/data/stage3d-fill-batch2/{source-manifest,history-observations,anecdote-observations,attendance-observations,program-people-observations,exclusions}.json` — reviewed-source intake inputs。
- 创建：`data-pipeline/artifacts/stage3d-fill-batch2-history-anecdotes/*` — nine required deterministic outputs。
- 创建：`data-pipeline/reports/stage3d-fill-batch2-history-anecdotes-report.md` — forced-added formal report。
- 创建：`data-pipeline/tests/test_stage3d_fill_batch2_history_anecdotes.py` — Batch 2 contracts and regressions。
- 修改：`docs/database-source-policy.md`、`docs/database-development-log.md` — provenance and staged coverage documentation。

## 任务 1：定义 Batch 2 红灯 contracts

- [ ] **步骤 1：创建失败测试**

```python
def test_batch2_builds_fixed_scope_and_cumulative_coverage():
    artifacts = build_stage3d_fill_batch2(**inputs())
    assert len(artifacts["stage3d-fill-batch2-history.json"]["universities"]) == 62
    assert artifacts["stage3d-fill-batch2-summary.json"]["cumulative_history_resolved_count_after_batch2"] == 16
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_batch2_history_anecdotes -v`

预期：FAIL，因为 Batch 2 module 尚不存在。

- [ ] **步骤 3：添加 quote guard regression**

```python
def test_batch2_rejects_direct_quote_not_in_reviewed_allowlist():
    # Replace an observation anchor with a paraphrase and assert validation error.
```

- [ ] **步骤 4：重新运行红灯测试**

预期：FAIL，且失败原因是尚缺少 Batch 2 implementation。

## 任务 2：实现独立 generator / validator / CLI

- [ ] **步骤 1：创建 Batch 2 module**

实现 `build_stage3d_fill_batch2(...)`、`validate_stage3d_fill_batch2(...)`、`render_stage3d_fill_batch2_report(...)`、`write_stage3d_fill_batch2(...)`。要求：

```python
summary = {
    "total_universities": 62,
    "batch2_history_resolved_count": len(history),
    "batch2_anecdotes_resolved_count": len(anecdotes),
    "cumulative_history_resolved_count_after_batch2": batch1_history_count + len(history),
    "cumulative_anecdotes_resolved_count_after_batch2": batch1_anecdote_count + len(anecdotes),
    "ready_for_claude_gate_review": True,
}
```

Fingerprint Candidate v2, Stage 3C, Stage 3D-Fill seed and all Batch 1 artifacts before/after build. Reject ranking fields, missing short quotes, missing `quote_verification_method`, excluded relationships, fuzzy person records, fake `无`, output drift and nonzero policy counters.

- [ ] **步骤 2：添加 CLI commands**

创建 `generate-stage3d-fill-batch2-history-anecdotes` 与 `validate-stage3d-fill-batch2-history-anecdotes`，要求全部输入 artifact 参数；validator fail closed 并输出 validation result。

- [ ] **步骤 3：运行 contract tests 验证绿灯**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_batch2_history_anecdotes -v`

预期：所有 Batch 2 tests PASS。

## 任务 3：审阅官方来源并生成 structured observations

- [ ] **步骤 1：只使用正常可访问的学校官方 history/about/archive 页面**

为 8–12 所尚未由 Batch 1 覆盖的学校收集一条 history 和一条 anecdote。每个 manifest item 记录 publisher、URL、detail domain、reviewed short quote allowlist、accessed date 和 limitation；不保存网页快照或长原文。

- [ ] **步骤 2：写入短 paraphrases 与 verified anchors**

每个 positive observation 使用 `manual_verbatim_check`，anchor quote 必须完全匹配 manifest allowlist。attendance 与 program people 留空，生成器将其对应 slots 标为 `source_review_not_completed`。

- [ ] **步骤 3：生成与正式验证 artifacts**

运行：

```bash
PYTHONPATH=src python3 -m pathos_data generate-stage3d-fill-batch2-history-anecdotes ...
PYTHONPATH=src python3 -m pathos_data validate-stage3d-fill-batch2-history-anecdotes ...
```

预期：nine required artifacts 与 report 出现；本批 8–12/62 history/anecdote、累计 16–20/62；所有 310 program slots仍是 `source_review_not_completed`。

## 任务 4：全量验证、scope guard 与提交

- [ ] **步骤 1：运行验证**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json
git diff --check
```

预期：Python tests 通过；schema/migration validation 输出 `Schema and migration validation passed`；diff check 无输出。

- [ ] **步骤 2：执行 non-mutation checks**

确认 staged names 不包含 `frontend/`、Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage3D-Fill seed，且 cache 仍被 `.gitignore` 忽略。

- [ ] **步骤 3：显式暂存并提交**

```bash
git add data-pipeline/src/pathos_data/__main__.py \
  data-pipeline/src/pathos_data/stage3d_fill_batch2_history_anecdotes.py \
  data-pipeline/data/stage3d-fill-batch2 \
  data-pipeline/artifacts/stage3d-fill-batch2-history-anecdotes \
  data-pipeline/tests/test_stage3d_fill_batch2_history_anecdotes.py \
  docs/database-source-policy.md docs/database-development-log.md \
  docs/superpowers/plans/2026-07-13-stage3d-fill-batch2-history-anecdotes-implementation-plan.md
git add -f data-pipeline/reports/stage3d-fill-batch2-history-anecdotes-report.md
git diff --cached --check
git commit -m "feat(data): add reviewed history and anecdotes batch 2"
```

不要 tag、push、merge 或 rebase。提交后确认 clean status 与 Stage 3A stash 保留。
