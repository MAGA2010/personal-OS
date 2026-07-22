# Stage 3D-Fill Batch 1 — Reviewed History + Anecdotes 实现计划

> **面向 AI 代理的工作者：** 在当前 `feature/database-ranking-discovery` checkout 内联执行；不得创建或切换分支、恢复 stash、改动 frontend 或上游 artifacts。每一步遵循 TDD 的 red → green → full validation 顺序。

**目标：** 用独立的 Batch 1 overlay 为固定 62 所 Candidate v2 学校收集经审查的短历史/趣闻事实，并保留无法正常复核的学校或人物槽位为 explicit source gaps。

**架构：** 新增 Batch 1 source-intake JSON、`stage3d_fill_batch1_history_anecdotes.py` generator/validator、generate/validate CLI 与独立 artifact directory。它只读取 Candidate v2、Stage 3C demo slots 与 Stage 3D-Fill seed 的 immutable fingerprints；每条正向断言必须有 source manifest、逐字短 quote、`quote_verification_method` 和短 paraphrase。没有 source 的学校仍生成 status row，绝不生成「无」。

**技术栈：** Python 3 标准库、现有 `pathos_data` CLI、JSON、`unittest`、正常可访问的学校官方/可信公开来源。禁止网页快照、浏览器绕过、爬虫规避与 driving API。

---

## 文件变更

### 新增

- `data-pipeline/src/pathos_data/stage3d_fill_batch1_history_anecdotes.py`：Batch 1 source loader、deterministic builder、validator、writer、report renderer。
- `data-pipeline/data/stage3d-fill-batch1/`：source manifest、history/anecdote/attendance/program-person observations 与 exclusions。
- `data-pipeline/artifacts/stage3d-fill-batch1-history-anecdotes/`：用户列出的 9 个 Batch 1 artifacts。
- `data-pipeline/tests/test_stage3d_fill_batch1_history_anecdotes.py`：red/green contracts、quote verification、scope and provenance guards。
- `data-pipeline/reports/stage3d-fill-batch1-history-anecdotes-report.md`：generated, forced-stage report。

### 修改

- `data-pipeline/src/pathos_data/__main__.py`：仅增加 Batch 1 generate/validate CLI commands。
- `docs/database-source-policy.md`：明确 Batch 1 的 history/anecdote/attendance 与 verbatim-quote policy。
- `docs/database-development-log.md`：记录 intake 覆盖、gaps、验证与 not-final boundary。

### 明确不修改

- `frontend/`。
- Candidate v2、Stage 3、3B、3C、3C2、3D framework 与 Stage 3D-Fill seed artifacts。
- final universe、正式 selection memberships、frontend export、Stage 3A stash。

## 任务 1：建立失败测试与 Batch 1 contract

1. 新建 `test_stage3d_fill_batch1_history_anecdotes.py`，断言 builder 缺失时 import/red；随后断言输出含固定 62 所 university status rows、310 个 program-person source gaps、只允许 student relationship allowlist、正向事实须有 source ID/reference/short anchor/method。
2. 增加 quote regression：将 review manifest 的允许原句替换为 paraphrase 后，builder 必须抛 `Stage3DFillBatch1ValidationError`。
3. 运行：
   ```bash
   PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_batch1_history_anecdotes -v
   ```
   预期：失败原因是 Batch 1 module 未实现，不是测试 import/path 拼写错误。

## 任务 2：实现最小独立 generator/validator/CLI

1. 建立 Batch 1 input record types：`stage3d_fill_batch1_source_manifest`、`..._history_observations`、`..._anecdote_observations`、`..._attendance_observations`、`..._program_people_observations`。
2. 让每条 history/anecdote university status row 为 `reviewed_fact_found` 或 `source_review_not_completed`；positive fact 只能由 `verified_direct_quotes` allowlist 匹配的 `direct_quote` 产生。
3. 对 attendance 仅允许 `graduated`、`attended_no_degree`、`alumnus_unspecified`；未知 major 必须 `null` + `major_not_stated_in_accepted_source`。program-person batch records 默认为 310 个 `source_review_not_completed`。
4. 加入 Candidate/Stage3C/Stage3D-Fill seed SHA-256 fingerprints；验证器 deterministic rebuild、flags、ranking isolation、quote/paraphrase length、no fuzzy person ID、source policy 和 no-final-output flags。
5. 新增 `generate-stage3d-fill-batch1-history-anecdotes` / `validate-stage3d-fill-batch1-history-anecdotes` CLI。

## 任务 3：reviewed source intake

1. 仅在正常访问条件下读取学校 official history/about/archive/alumni 页面或直接支持事实的可信来源。
2. 每个 source manifest entry 保存 source URL、publisher、field domain、confidence、`verified_direct_quotes`；每条 observation 只保存短 paraphrase、短 quote 与 `manual_verbatim_check`（没有 local cache 时）。
3. 对可复核的学校填 history/anecdote；对没有合格 source 的学校保留 `source_review_not_completed`。不创建 scoped 「无」，除非确有 completed reviewed scope（Batch 1 计划默认不这样做）。
4. Attendance 只有来源直接写明 relationship 时才纳入；没有 direct major 时留 null。program people 仅在 source 同时直证 person、eligible relationship 和 program/major 时才填入。

## 任务 4：生成、验证、交付

1. Generate Batch 1 artifacts/report，run formal validator。
2. Run targeted tests, full Python suite, fixture/schema/migration validation and `git diff --check`.
3. Check diff excludes frontend/upstream/cache; explicitly stage Batch 1 paths plus ignored report; review cached stat/check.
4. Commit without tag/push/merge/rebase:
   ```bash
   git commit -m "feat(data): add reviewed history and anecdotes batch"
   ```

## 验收清单

- 62 school scope fixed; 62 history and 62 anecdote status rows always present.
- Positive facts are short sourced paraphrases with verbatim anchor and verification method; no long source text committed.
- 310 program slots are identified only with high-quality direct evidence, otherwise source gaps; unreviewed is never 「无」。
- No attendance record carries excluded relationship or fuzzy identity; unknown major remains null with scoped reason.
- `source_policy_violations=0`, `ranking_field_contamination=0`; generated artifacts are deterministic and do not mutate the seed/upstream/frontend/final outputs.
