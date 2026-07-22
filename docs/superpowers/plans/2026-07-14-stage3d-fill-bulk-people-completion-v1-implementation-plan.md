# Stage 3D-Fill Bulk People Completion v1 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 executing-plans 与 test-driven-development 在当前受控 worktree 内执行；本会话不使用子代理。步骤使用复选框跟踪。

**目标：** 在固定 Candidate v2 62 校范围内，为每校建立至少一条 cache-verified notable attendance，复用既有 People Pilot 10 条并补充 reviewed official-source observations；不扩展 program people。

**架构：** 新建独立 People Completion v1 overlay。生成器读取 Candidate v2、People Pilot 与 Bulk v2 program-slot artifact 的只读指纹；新增 observation/source/cache manifest 只保存结构化事实、短 quote、SHA-256 和 gitignored cache reference。Validator fail-closed 检查 62 校覆盖、关系白名单、source-backed disambiguated person ID、collision handling、cache substring、ranking isolation 与 deterministic regeneration。

**技术栈：** Python 标准库、现有 `pathos_data` CLI、JSON artifacts、`unittest`。

---

### 任务 1：建立红灯契约

**文件：**
- 创建：`data-pipeline/tests/test_stage3d_fill_bulk_people_completion_v1.py`

- [ ] 写测试：62 校至少一条 attendance；program people 维持 0/310；只允许 `graduated`、`alumnus_unspecified`、`attended_no_degree`。
- [ ] 写失败测试：manual quote、cache SHA/substring 错误、纯姓名 person ID、同名跨 context 合并、faculty/donor/honorary/unclear、缺 source URL/anchor、ranking field contamination。
- [ ] 运行 `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_stage3d_fill_bulk_people_completion_v1 -v`；预期因模块不存在红灯。

### 任务 2：实现独立 generator / validator / CLI

**文件：**
- 创建：`data-pipeline/src/pathos_data/stage3d_fill_bulk_people_completion_v1.py`
- 修改：`data-pipeline/src/pathos_data/__main__.py`

- [ ] 实现 `build_stage3d_fill_bulk_people_completion_v1(...)`，合并不可变 People Pilot 10 条与新增 observations，并按 candidate/person ID 排序。
- [ ] 强制 `local_cache_substring_check`、cache path/SHA/source URL、短 quote、关系白名单和 source-backed canonical person ID。
- [ ] 对 normalized same-name 跨 context 只允许不同 deterministic ID；同一 ID 对应不同 context 必须失败。
- [ ] 复制 Bulk v2 的 310 个 program slots，不新增 identified person，并保持 `source_review_not_completed`。
- [ ] 实现 deterministic validator、report renderer、artifact writer 和 generate/validate CLI。
- [ ] 运行任务 1 测试；预期绿灯。

### 任务 3：Reviewed source intake 与 artifacts

**文件：**
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-completion-v1/source-manifest.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-completion-v1/cache-manifest.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-completion-v1/notable-attendance-observations.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-completion-v1/exclusions.json`
- 创建（gitignored）：`data-pipeline/cache/stage3d-fill-bulk-people-completion-v1/reviewed-excerpts.txt`
- 创建：`data-pipeline/artifacts/stage3d-fill-bulk-people-completion-v1/*.json`
- 创建：`data-pipeline/reports/stage3d-fill-bulk-people-completion-v1-report.md`

- [ ] 为 People Pilot 未覆盖的 52 校优先审阅学校官方 alumni/news/archive/profile 页面；只接受页面直接支持 person、institution 与 attendance relationship 的短 quote。
- [ ] degree/major 未直接出现时保持 null，并写 `major_not_stated_in_accepted_source`；不得从职业推断。
- [ ] cache 仅保存 URL marker 与短 reviewed excerpt；manifest 保存 SHA-256，cache 正文不得 commit。
- [ ] 生成独立 artifacts：plan、attendance、program people、source manifest、cache manifest、exclusions、gap disclosure、summary、validation result。

### 任务 4：验证与提交

**文件：**
- 修改：`docs/database-development-log.md`

- [ ] 运行 targeted tests、全量 Python tests、People Completion validator、fixture/schema/migration validation。
- [ ] 运行 byte-identical regeneration、`git diff --check`、frontend/upstream non-mutation 和 `git check-ignore`。
- [ ] 显式暂存本阶段文件，确认 cache 正文不在 index。
- [ ] 提交 `feat(data): complete reviewed notable attendance coverage`；不 tag、不 push、不进入 Gate。

## 接受标准

- Candidate v2 62 校范围不变；每校至少一条 reviewed notable attendance。
- 所有正向 direct quote 均为 `local_cache_substring_check`；manual count、cache missing、source policy violation、ranking contamination 均为 0。
- canonical person ID 包含 normalized name、candidate context 与 source-backed disambiguator；禁止 fuzzy merge。
- Program people 保持 0 identified / 310 `source_review_not_completed`；不生成 fake “无”。
- frontend、final universe、正式 memberships、frontend export 与所有上游 artifacts 均不变。
