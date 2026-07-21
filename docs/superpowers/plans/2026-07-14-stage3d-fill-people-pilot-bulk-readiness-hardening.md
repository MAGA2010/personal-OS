# Stage 3D-Fill People Pilot Bulk Readiness Hardening 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框语法跟踪。

**目标：** 在不扩大 People Pilot 数据覆盖的前提下，将其 11 条正向引文升级为可离线 cache-substring 复核，并将人物 ID 从纯姓名 slug 迁移为确定性的 source-context identity。

**架构：** 保持 Candidate v2 与所有上游 overlay 只读。People Pilot 的 version-controlled manifest 仅记录 gitignored reviewed-excerpt cache 的路径、哈希和来源元数据；生成器在读取 cache 后对每条 `local_cache_substring_check` anchor 做 SHA-256 与 substring 验证。人物 ID 由规范姓名、candidate ID 和 source-backed disambiguator 组成，program-person 必须复用其对应 attendance identity。

**技术栈：** Python 标准库、现有 `pathos_data` generator/validator、JSON artifacts、`unittest`。

---

### 任务 1：建立失败的 Bulk-readiness 合同

**文件：**
- 修改：`data-pipeline/tests/test_stage3d_fill_people_pilot_notable_attendance.py`

- [ ] 增加 `test_rejects_cached_quote_not_present_in_local_cache`：复制 cache manifest，替换一个已 cache source 的 quote，调用 `build_stage3d_fill_people_pilot()`，预期抛出 `Stage3DFillPeoplePilotValidationError`。
- [ ] 增加 `test_rejects_same_name_with_missing_source_context_disambiguator`：复制 attendance observations，在同一规范姓名的另一 candidate/source context 中移除 `person_identity_disambiguator`，预期 fail closed。
- [ ] 增加 `test_rejects_same_person_id_for_different_source_contexts`：复制 observation 形成另一个 context，但保留原 canonical ID，预期拒绝自动合并。
- [ ] 增加 `test_program_person_reuses_hardened_attendance_identity`：断言 Jeff Bezos 的 program-person ID 与 attendance record 完全相同。
- [ ] 运行：`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_stage3d_fill_people_pilot_notable_attendance -v`。
- [ ] 预期：在实现前至少 cache substring 与 source-context ID 合同失败，原因是当前代码只验证 cache hash 并接受 `person:<name-slug>`。

### 任务 2：实现 cache-substring 与 source-context identity guard

**文件：**
- 修改：`data-pipeline/src/pathos_data/stage3d_fill_people_pilot_notable_attendance.py`
- 修改：`data-pipeline/data/stage3d-fill-people-pilot/reviewed-source-cache-manifest.json`
- 修改：`data-pipeline/data/stage3d-fill-people-pilot/notable-attendance-observations.json`
- 修改：`data-pipeline/data/stage3d-fill-people-pilot/program-people-observations.json`

- [ ] 定义 `canonical_person_id` 格式：`person:<normalized-name>:<candidate-id-suffix>:<source-backed-disambiguator>`；disambiguator 为 version-controlled `person_identity_disambiguator`，例如受来源支持的 degree/year 或 `source:<source-id>`。
- [ ] 要求 observation 的 `person_identity_disambiguator` 非空；若同一 normalized name 跨 candidate/source 出现，必须产生不同 context ID，否则报错，或进入 `same_name_unresolved` exclusion。
- [ ] 对 cache entry 要求 `source_url_or_reference`、`quote_verification_method`、`cache_path`、`sha256`、`retrieval_or_review_notes`；当 method 为 `local_cache_substring_check` 时，读取文本、验证 hash、验证 source URL marker 与 anchor quote substring。
- [ ] 将已验证 source 的 11 条 positive anchors 改为 `local_cache_substring_check`；保留无 cache 时的 `manual_verbatim_check` 兼容分支，以支持后续受限来源。
- [ ] summary 增加 `cache_verified_quote_count`、`cache_missing_count`，并保持 method counts 可审计。
- [ ] 运行任务 1 测试，预期全部通过。

### 任务 3：建立 gitignored reviewed excerpt cache 并重建 artifacts

**文件：**
- 创建（gitignored）：`data-pipeline/cache/stage3d-fill-people-pilot/*.txt`
- 修改：`data-pipeline/artifacts/stage3d-fill-people-pilot-notable-attendance/*`
- 修改：`data-pipeline/reports/stage3d-fill-people-pilot-bulk-readiness-hardening-report.md`

- [ ] 使用正常访问的学校 official source，将每个 source 的 source ID、URL、访问日期和已人工核对的短逐字片段写入独立 reviewed-excerpt cache；不保存完整网页快照。
- [ ] 在 cache manifest 中保存绝对/工作区稳定 cache path 和 SHA-256；确认 `git check-ignore` 命中 `data-pipeline/.gitignore` 的 `cache/`。
- [ ] 运行现有 generator 重建 People Pilot 独立 artifacts，保持 10 attendance、1 program person、309 未审查 slots，不增加人物事实。
- [ ] 报告明确写出这是 Bulk readiness hardening，不是 Bulk completion/PASS tag；列出 11/11 cache verified、0 manual fallback（若实际 cache 完成）。

### 任务 4：验证、范围审计和提交

**文件：**
- 修改：`docs/database-development-log.md`
- 可选修改：`docs/database-source-policy.md`（仅补 cache/identity rule）

- [ ] 运行 People Pilot validator、全量 Python discovery、`pathos_data validate --fixture tests/fixtures/test-university-raw.json` 与 `git diff --check`。
- [ ] 运行 `git diff --exit-code -- frontend` 及上游 artifact 路径，确认只修改 People Pilot hardening 范围。
- [ ] 运行 `git check-ignore -v data-pipeline/cache/stage3d-fill-people-pilot/<cache-file>`，确认 cache 正文不会入库。
- [ ] 显式暂存代码、tests、People Pilot inputs/artifacts、report 与 docs；使用 `git add -f` 暂存 gitignored report，但不暂存 cache。
- [ ] 运行 `git diff --cached --check`，创建 commit：`fix(data): harden people pilot quote cache and identity`；不创建 tag、不 push、不 merge、不 rebase。
