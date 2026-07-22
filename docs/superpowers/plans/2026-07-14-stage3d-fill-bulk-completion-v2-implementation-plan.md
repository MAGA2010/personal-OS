# Stage 3D-Fill Bulk Completion v2 实现计划

> **面向 AI 代理的工作者：** 使用测试先行逐任务实现；本仓库当前会话不使用子代理。步骤使用复选框语法跟踪。

**目标：** 在 62 所 Candidate v2 学校的固定范围内，建立独立、可离线复核的 People/Narrative Bulk v2 overlay；正向事实只接受本地 reviewed-excerpt cache 中可逐字验证的官方或可信来源。

**架构：** 生成器读取不可变 Candidate v2、Stage 3C demo-program slots、Batch 1/2 与 People Pilot 作为只读输入指纹。Bulk v2 的 version-controlled observation/manifest 只保存结构化事实、短 quote、cache 相对路径与 SHA-256；cache 正文保持在 `data-pipeline/cache/` 并由 `.gitignore` 排除。每所学校在 history/anecdote 中都有一条状态记录；未审阅并不被表述为“无”。

**技术栈：** Python 标准库、现有 `pathos_data` CLI/JSON artifact 约定、`unittest`。

---

## 文件职责

- 创建：`data-pipeline/src/pathos_data/stage3d_fill_bulk_completion_v2.py` — 独立生成、缓存 quote 校验、fail-closed validator、报告。
- 修改：`data-pipeline/src/pathos_data/__main__.py` — 增加 generate/validate Bulk v2 CLI。
- 创建：`data-pipeline/tests/test_stage3d_fill_bulk_completion_v2.py` — cache/identity/status/determinism 红绿契约。
- 创建：`data-pipeline/data/stage3d-fill-bulk-completion-v2/*.json` — reviewed source intake、observations、cache manifest、exclusions；不保存网页正文。
- 创建（gitignored）：`data-pipeline/cache/stage3d-fill-bulk-completion-v2/*.txt` — 每个 source 的最小 reviewed excerpt，带 URL marker。
- 创建：`data-pipeline/artifacts/stage3d-fill-bulk-completion-v2/*.json` — 11 个独立产物。
- 创建：`data-pipeline/reports/stage3d-fill-bulk-completion-v2-report.md` — coverage、限制和 not-final 披露。
- 修改：`docs/database-development-log.md` — 范围、证据、验证与下一步。

### 任务 1：写失败的 Bulk v2 合同测试

- [ ] 创建 `test_stage3d_fill_bulk_completion_v2.py`，导入尚不存在的 `build_stage3d_fill_bulk_completion_v2` 和 `Stage3DFillBulkCompletionV2ValidationError`。
- [ ] 覆盖：62 校 scope；cache SHA 不匹配失败；quote 不在 cache 失败；`person:name-only` 失败；不允许 attendance relationship 失败；职业推断 program match 失败；`no_qualifying_person_found` 缺 reviewed scope/IDs 失败；`source_review_not_completed` 不是 scoped none；确定性 build。
- [ ] 运行 `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_stage3d_fill_bulk_completion_v2 -v`；预期 ImportError/缺失模块的红灯。

### 任务 2：实现最小独立生成器与 validator

- [ ] 建立 `build_stage3d_fill_bulk_completion_v2(...)`：读取 Candidate v2 和 Stage 3C slots，写全 62 条 history/anecdote status 和 310 个 program-slot status。
- [ ] 只允许 `local_cache_substring_check` 的正向 anchor：解析相对 cache 路径、校验 SHA-256 与 quote substring。
- [ ] 建立 source/identity guards：source 必须是 detail/narrative domain；attendance 仅允许 `graduated`、`attended_no_degree`、`alumnus_unspecified`；person ID 必须含 name/candidate/disambiguator；program-person 必须关联同 candidate 的 attendance 并有 direct program source evidence。
- [ ] 建立 `validate_stage3d_fill_bulk_completion_v2(...)`：重建结果与 committed artifacts byte-equal，检查 input fingerprints、范围、上游不变 flags、counts、禁止 ranking fields。
- [ ] 将 CLI 命令接入 `__main__.py`：`generate-stage3d-fill-bulk-completion-v2` 与 `validate-stage3d-fill-bulk-completion-v2`。
- [ ] 运行任务 1 测试；预期绿灯。

### 任务 3：审核 intake、创建最小 cache、生成 artifacts

- [ ] 将 Batch 1/2 的 16 条已有 history/anecdote 作为新 overlay 的独立 reviewed intake：为每条 source 创建简短 cache excerpt，anchor 从源 artifact 的直接 quote 逐字复制，cache manifest 写入 URL、SHA、review notes。不得回写 Batch 1/2。
- [ ] 将 People Pilot 的 10 条 attendance 和 1 条 program-person（如果独立 source/cache 可复核）作为 Bulk v2 独立 observations；否则保留相应未审阅状态。
- [ ] 对可正常访问并可人工复核的额外官方 history/about 页面做 source-cache-first intake；若不能达到相同标准，保持 `source_review_not_completed`。
- [ ] 生成 11 个 artifacts 和 report；summary 必须披露 coverage、cache 验证、source-limited/incomplete/not-final、未生成 frontend/final universe/memberships。

### 任务 4：验证、范围审计、提交

- [ ] 运行 Bulk v2 validator、全量 Python unittest discovery、fixture/schema/migration validation、`git diff --check`、byte-identical regeneration。
- [ ] 运行 `git diff --exit-code -- frontend` 与上游 artifact path audit；运行 `git check-ignore -v` 验证 Bulk cache 不会进入 commit。
- [ ] 显式暂存 Bulk v2 code/tests/data/artifacts/report/docs/plan；不暂存 cache；运行 `git diff --cached --check`。
- [ ] 创建单一 commit：`feat(data): add stage3d fill bulk completion v2`；不打 tag、不 push、不 merge、不 rebase。

## 接受标准

- Candidate v2 62 校范围、上游 fingerprints、frontend 均不变。
- 所有正向 history/anecdote/attendance/program-person 均有 source 和 `local_cache_substring_check` evidence。
- cache SHA 与 quote substring 校验 fail-closed；正向人物 ID 不使用纯姓名 slug。
- 未审阅状态保持 `source_review_not_completed`，不伪造“无”。
- `source_policy_violations = 0`、`ranking_field_contamination = 0`、all tests/validator/schema/diff/regeneration checks 通过。
