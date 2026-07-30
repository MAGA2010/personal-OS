# Stage 3B Demo Critical Gap Fill 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在不改变 Candidate v2 或 Stage 3 artifacts 的前提下，生成可审计的 Stage 3B detail overlay，优先补 student-faculty ratio、11 个 identity gap 与实际 8 个 demo-program gap。

**架构：** 新 generator 只读 Candidate v2、Stage 3 artifact 与受控的官方数据 cache；它写入独立 Stage 3B artifacts。版本控制的人工 alias mapping 只允许 candidate alias 到 `IPEDS INSTNM` 的显式 exact mapping；所有官方下载留在 gitignored cache。validator 通过 deterministic regeneration、防污染与 field-level provenance checks fail closed。

**技术栈：** Python 3.9、stdlib CSV/JSON/zipfile、现有 `validate_source_policy_use()`、官方 College Scorecard/IPEDS CSV、现有 unittest CLI。

---

## 文件职责

- 创建：`data-pipeline/src/pathos_data/stage3b_gap_fill.py` — Stage 3B deterministic generator、official cache adapters、validator。
- 修改：`data-pipeline/src/pathos_data/__main__.py` — `generate-stage3b-gap-fill` 与 `validate-stage3b-gap-fill` CLI。
- 创建：`data-pipeline/data/stage3b/identity-alias-mappings.json` — 11 个候选学校的显式人工审核 alias 到 exact IPEDS name mapping；不存 fuzzy match。
- 创建：`data-pipeline/data/stage3b/official-program-observations.json` — 仅学校官方本科 majors/programs 页面产生的 demo-program observations；无法核验的学校不填假记录。
- 创建：`data-pipeline/tests/test_stage3b_gap_fill.py` — Stage 3B 红绿与防回归测试。
- 创建：`data-pipeline/artifacts/stage3b-demo-critical-gap-fill/*.json` — 九个独立可发布 MVP artifacts。
- 创建：`data-pipeline/reports/stage3b-demo-critical-gap-fill-report.md` — 统计、来源、基线 gap 语义、剩余 blocker。
- 修改：`data-pipeline/.gitignore` — 忽略 `cache/stage3b-official/`，保留报告白名单。
- 修改：`docs/database-source-policy.md` — College Scorecard/IPEDS ratio 与 explicit alias mapping 边界。
- 修改：`docs/database-development-log.md` — Stage 3B 目标、来源、结果、风险与下一步。

## 任务 1：锁定输入不变量与 Stage 3B gap 语义

**文件：**
- 创建：`data-pipeline/tests/test_stage3b_gap_fill.py`
- 创建：`data-pipeline/src/pathos_data/stage3b_gap_fill.py`

- [ ] **步骤 1：编写失败的输入不变量测试**

```python
def test_stage3b_uses_all_candidate_rows_and_derived_program_gap_semantics(self):
    artifacts = build_stage3b_gap_fill(self.inputs())
    rows = artifacts["stage3b-mvp-universities.json"]["universities"]
    self.assertEqual(len(rows), 62)
    summary = artifacts["stage3b-summary.json"]
    self.assertEqual(summary["demo_program_gap_original_count"], 8)
    self.assertEqual(sum(row["top_5_gap_reason"] is not None for row in rows), summary["demo_program_gap_remaining_count"])
    self.assertEqual(summary["stale_top5_gap_reason_original_count"], 6)
    self.assertEqual(summary["stale_top5_gap_reason_cleared_in_overlay_count"], 6)
    self.assertTrue(all(
        not row["top_5_gap_reason"]
        for row in rows if len(row["top_5_programs_for_demo"]) == 5
    ))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3b_gap_fill.Stage3BGapFillTests.test_stage3b_uses_all_candidate_rows_and_derived_program_gap_semantics -v`

预期：FAIL，原因是 `stage3b_gap_fill` 不存在。

- [ ] **步骤 3：实现最小只读 Stage 3 input loader 与 gap normalizer**

```python
def normalized_program_gap(programs: list[dict], inherited_reason: str | None) -> str | None:
    return None if len(programs) == 5 else (
        inherited_reason or "fewer_than_five_provenance_backed_demo_programs_available"
    )
```

实现读取 Candidate v2 与 Stage 3 files；不写入或修改任何 Stage 3 path。

- [ ] **步骤 4：运行测试验证通过**

运行相同步骤 2 命令。

预期：PASS。

## 任务 2：实现官方 student-faculty ratio adapter 与 provenance contract

**文件：**
- 修改：`data-pipeline/src/pathos_data/stage3b_gap_fill.py`
- 修改：`data-pipeline/tests/test_stage3b_gap_fill.py`
- 修改：`data-pipeline/.gitignore`

- [ ] **步骤 1：编写失败的 ratio provenance 与 null fallback 测试**

```python
def test_ratio_requires_official_source_or_explicit_null_reason(self):
    artifacts = build_stage3b_gap_fill(self.inputs())
    for row in artifacts["stage3b-student-faculty.json"]["universities"]:
        if row["student_faculty_ratio"] is None:
            self.assertTrue(row["null_reason"])
        else:
            self.assertTrue(row["source_id"])
            self.assertTrue(row["source_reference"])
            self.assertTrue(row["evidence_anchor"])
            self.assertTrue(row["definition_notes"])
            if row["derived_ratio"]:
                self.assertTrue(row["derivation_formula"])
                self.assertTrue(row["derivation_variable_sources"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3b_gap_fill.Stage3BGapFillTests.test_ratio_requires_official_source_or_explicit_null_reason -v`

预期：FAIL，原因是 ratio adapter 尚未产生 Stage 3B rows。

- [ ] **步骤 3：实现 College Scorecard/IPEDS adapter**

将官方 CSV 下载到 `data-pipeline/cache/stage3b-official/`，但不暂存该目录。读取只含官方字段的 `STUFACR`（如官方文件可用）；将其记录为 `source_type=college_scorecard`、字段行短 anchor、reporting year 与定义说明。若官方输入没有该字段或该 candidate 没有安全 UNITID，输出 null reason；不得从非官方网页估算。

- [ ] **步骤 4：运行测试验证通过**

运行相同步骤 2 命令。

预期：PASS。

## 任务 3：以显式 alias mapping 填补 identity/tuition/major gaps

**文件：**
- 创建：`data-pipeline/data/stage3b/identity-alias-mappings.json`
- 修改：`data-pipeline/src/pathos_data/stage3b_gap_fill.py`
- 修改：`data-pipeline/tests/test_stage3b_gap_fill.py`

- [ ] **步骤 1：编写失败的 exact-alias-only 测试**

```python
def test_identity_gap_unitid_requires_reviewed_exact_ipeds_alias(self):
    artifacts = build_stage3b_gap_fill(self.inputs())
    records = artifacts["stage3b-identity-gap-fill.json"]["universities"]
    for row in records:
        if row["unitid"] is not None:
            self.assertEqual(row["match_method"], "reviewed_alias_exact_ipeds_instnm")
            self.assertTrue(row["mapping_id"])
            self.assertTrue(row["evidence_anchor"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3b_gap_fill.Stage3BGapFillTests.test_identity_gap_unitid_requires_reviewed_exact_ipeds_alias -v`

预期：FAIL，原因是 reviewed mappings 尚未接入。

- [ ] **步骤 3：实现 mapping reader 与 exact IPEDS resolver**

每条 mapping 必须有 candidate ID、reviewed candidate alias、exact `IPEDS INSTNM`、mapping source/review notes 与固定 mapping ID。resolver 只能用 `_normal(exact_ipeds_instnm)` 在 HD 数据中查找；缺任何字段、找不到一条或找到多条则保持 unresolved。validator 必须拒绝没有该 mapping 的新增 UNITID。对已解析 identity 用现有 Stage 3 IPEDS helper 补 university fields、tuition 与 award areas，不写 ranking field。

- [ ] **步骤 4：运行测试验证通过**

运行相同步骤 2 命令。

预期：PASS。

## 任务 4：补足实际 8 个 demo-program gap，并拒绝 graduate-only source

**文件：**
- 创建：`data-pipeline/data/stage3b/official-program-observations.json`
- 修改：`data-pipeline/src/pathos_data/stage3b_gap_fill.py`
- 修改：`data-pipeline/tests/test_stage3b_gap_fill.py`

- [ ] **步骤 1：编写失败的官方本科 source 与 graduate guard 测试**

```python
def test_program_fill_uses_only_official_undergraduate_observations(self):
    artifacts = build_stage3b_gap_fill(self.inputs())
    for row in artifacts["stage3b-program-gap-fill.json"]["universities"]:
        for program in row["added_demo_programs"]:
            self.assertEqual(program["source_type"], "official_institutional")
            self.assertEqual(program["undergraduate_status"], "undergraduate")
            self.assertTrue(program["source_id"])
            self.assertTrue(program["evidence_anchor"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3b_gap_fill.Stage3BGapFillTests.test_program_fill_uses_only_official_undergraduate_observations -v`

预期：FAIL，原因是 Stage 3B official observations 尚未被应用。

- [ ] **步骤 3：收集并导入官方本科 observations**

仅使用直接列明 undergraduate majors/programs/areas-of-study 的学校官方页面；每条 observation 包含 candidate ID、program name、source URL、短 anchor、access date、`undergraduate_status=undergraduate` 与 source ID。reject `graduate`、`MBA`、`law`、`medical`、`professional` 语境。无合格来源时不新增 program。

- [ ] **步骤 4：运行测试验证通过**

运行相同步骤 2 命令。

预期：PASS。

## 任务 5：完成 artifacts、validator、CLI、文档与提交前验证

**文件：**
- 修改：`data-pipeline/src/pathos_data/__main__.py`
- 修改：`data-pipeline/src/pathos_data/stage3b_gap_fill.py`
- 创建：`data-pipeline/artifacts/stage3b-demo-critical-gap-fill/`（九个 JSON）
- 创建：`data-pipeline/reports/stage3b-demo-critical-gap-fill-report.md`
- 修改：`data-pipeline/.gitignore`
- 修改：`docs/database-source-policy.md`
- 修改：`docs/database-development-log.md`

- [ ] **步骤 1：编写失败的 validator boundary 测试**

```python
def test_stage3b_rejects_final_outputs_and_ranking_contamination(self):
    artifacts = build_stage3b_gap_fill(self.inputs())
    artifacts["stage3b-summary.json"]["frontend_export_generated"] = True
    with self.assertRaises(Stage3BValidationError):
        validate_stage3b_gap_fill(artifacts, self.inputs())
```

- [ ] **步骤 2：运行测试验证失败**

运行：`PYTHONPATH=src python3 -m unittest tests.test_stage3b_gap_fill.Stage3BGapFillTests.test_stage3b_rejects_final_outputs_and_ranking_contamination -v`

预期：FAIL，原因是 Stage 3B validator 尚未实现。

- [ ] **步骤 3：实现 deterministic validator 与 CLI**

实现 `generate-stage3b-gap-fill` 与 `validate-stage3b-gap-fill`。validator 必须 exact-compare deterministic regeneration，验证 62 candidate IDs、student-faculty provenance/null、reviewed exact alias mapping、undergraduate-only tuition/program sources、清理 6 条 stale gap、保留 8 条 actual gap、零 source-policy/ranking-contamination 与所有 final-output flags 为 false。

- [ ] **步骤 4：生成 artifacts、报告和 development log**

报告写清楚 resolved/remaining counts、ratio definition、identity mappings、official program sources、baseline inconsistency repair、remaining blockers 与 Stage 3B 非 final 边界。将 cache 继续排除，只显式暂存 generator、tests、versioned mappings/observations、artifacts、report 和 docs。

- [ ] **步骤 5：运行完整验证并提交**

运行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m pathos_data validate-stage3b-gap-fill ...
PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json
git diff --check
git status --short
```

预期：全部 Python tests 通过、Stage 3B validator 通过、schema/migration validation 通过、diff 无空白错误、无 frontend 变更且 cache 未纳入暂存。

- [ ] **步骤 6：创建最终 commit**

```bash
git add data-pipeline/.gitignore \
  data-pipeline/data/stage3b \
  data-pipeline/artifacts/stage3b-demo-critical-gap-fill \
  data-pipeline/reports/stage3b-demo-critical-gap-fill-report.md \
  data-pipeline/src/pathos_data/stage3b_gap_fill.py \
  data-pipeline/src/pathos_data/__main__.py \
  data-pipeline/tests/test_stage3b_gap_fill.py \
  docs/database-source-policy.md docs/database-development-log.md
git commit -m "feat(data): fill demo-critical stage 3 gaps"
```

预期：仅 Stage 3B database/pipeline files 被提交；不创建 tag、不 push、不 merge、不 rebase。
