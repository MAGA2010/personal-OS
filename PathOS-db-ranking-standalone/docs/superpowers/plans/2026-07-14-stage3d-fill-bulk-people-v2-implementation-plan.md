# Stage 3D-Fill Bulk People Completion v2 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 在当前受控 worktree 内逐任务实现；本会话不使用子代理。步骤使用复选框（`- [ ]`）跟踪。

**目标：** 建立独立 Top-1 program-person slot pipeline，为 Candidate v2 的 62 所学校生成 62 个状态明确的 slots；本轮不采集真实人物，所有 slots 初始保持 `source_review_not_completed`。

**架构：** Generator 从只读 Candidate v2 与 Stage 3C top-5 program overlay 逐校选择 index 0，并完整复制其 program provenance。可选 reviewed observation 写入路径在未来支持 `identified_person` 和 `no_qualifying_person_found`，但本轮输入为空。Validator 通过 schema、upstream SHA、identity、relationship、program match、source cache 与 deterministic rebuild 执行 fail-closed 校验。

**技术栈：** Python 标准库、现有 `pathos_data` CLI、versioned JSON Schema、JSON artifacts、pytest/unittest。

---

## 文件职责

- 创建 `data-pipeline/schemas/v1/stage3d-fill-bulk-people-v2-slot.json`：单个 slot 的版本化 schema。
- 创建 `data-pipeline/src/pathos_data/stage3d_fill_bulk_people_v2.py`：输入校验、62-slot generator、validator、writer、report renderer。
- 修改 `data-pipeline/src/pathos_data/__main__.py`：独立 generate/validate CLI。
- 创建 `data-pipeline/tests/test_stage3d_fill_bulk_people_v2.py`：TDD contracts 和 fail-closed regression tests。
- 创建 `data-pipeline/data/stage3d-fill-bulk-people-v2/`：空 reviewed intake、source/cache manifest 与 exclusions。
- 创建 `data-pipeline/artifacts/stage3d-fill-bulk-people-v2/`：独立 deterministic artifacts。
- 创建 `data-pipeline/reports/stage3d-fill-bulk-people-v2-pipeline-report.md`：pipeline implementation report。
- 修改 `docs/database-development-log.md`：目标、schema、validator、测试、风险与下一步。

### 任务 1：Schema 与红灯测试

**文件：**
- 创建：`data-pipeline/schemas/v1/stage3d-fill-bulk-people-v2-slot.json`
- 创建：`data-pipeline/tests/test_stage3d_fill_bulk_people_v2.py`

- [ ] **步骤 1：定义 slot schema**

Schema 必须要求 `candidate_id`、`canonical_id`、`university_name`、`program_name`、`program_source_reference`、`slot_status`、`person_id`、`person_name`、`relationship_type`、`match_type`、`source_ids`、`evidence_anchor`、`quote_verification_method`、`reviewed_scope` 和 `null_reason`；状态 enum 只能是三种批准值。

- [ ] **步骤 2：编写失败测试**

测试调用尚不存在的：

```python
from pathos_data.stage3d_fill_bulk_people_v2 import (
    Stage3DFillBulkPeopleV2ValidationError,
    build_stage3d_fill_bulk_people_v2,
)
```

覆盖：62 slots、状态 enum、top-1 provenance、identified required fields、program match、relationship exclusion、no-qualifying gate、cache substring/SHA、ranking contamination、upstream SHA、same-name identity 和 deterministic generation。

- [ ] **步骤 3：运行红灯**

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=data-pipeline/src \
python3 -m pytest data-pipeline/tests/test_stage3d_fill_bulk_people_v2.py -q -p no:cacheprovider
```

预期：因 `stage3d_fill_bulk_people_v2` 模块不存在而失败。

### 任务 2：最小 generator 与 fail-closed validator

**文件：**
- 创建：`data-pipeline/src/pathos_data/stage3d_fill_bulk_people_v2.py`
- 测试：`data-pipeline/tests/test_stage3d_fill_bulk_people_v2.py`

- [ ] **步骤 1：实现 immutable scope loader**

固定输入 SHA：

```python
EXPECTED_CANDIDATE_SHA256 = "8f940aa6d336402ff9c3c76a43d2efacdf2c887dc983afeb344937db9eadb18d"
EXPECTED_STAGE3C_PROGRAM_SHA256 = "11ac883fcef31d00cd57610c17c848feca479c8d5c2b7030f7f07d69540a5491"
```

拒绝非 62 校 scope、缺 top-1 program 或 upstream SHA drift。

- [ ] **步骤 2：实现 62-slot 默认生成**

每校从 `top_5_programs_for_demo[0]` 复制 program name、normalized name、source basis、source ID、source record ID、evidence anchor，并生成：

```python
{
    "slot_status": "source_review_not_completed",
    "person_id": None,
    "source_ids": [],
    "reviewed_scope": [],
    "null_reason": "program_person_source_review_not_completed",
}
```

- [ ] **步骤 3：实现 future identified path**

临时测试 observation 必须同时提供 `attendance` 和 `program_match` 两个 direct-quote anchors、允许 relationship、source-stated match basis、source-disambiguated person ID 与 local cache source entries。`direct_related_program_match` 还必须提供显式 related-program mapping 和 match notes。

- [ ] **步骤 4：实现 no-qualifying gate 与 exclusions**

`no_qualifying_person_found` 只接受 non-empty reviewed scope/source IDs；同名未确认、faculty、donor、honorary 和 unclear 只能进入 exclusions。

- [ ] **步骤 5：实现 schema 和 deterministic validation**

使用 `validate_instance(slot, load_schema("stage3d-fill-bulk-people-v2-slot.json"))`，然后 rebuild 并比较所有 artifacts。Summary 强制三种状态计数之和等于 62、manual quote 为 0、policy/ranking contamination 为 0。

- [ ] **步骤 6：运行测试至绿灯**

运行任务 1 的命令，预期全部通过。

### 任务 3：CLI、空 intake 与独立 artifacts

**文件：**
- 修改：`data-pipeline/src/pathos_data/__main__.py`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-v2/program-people-observations.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-v2/source-manifest.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-v2/cache-manifest.json`
- 创建：`data-pipeline/data/stage3d-fill-bulk-people-v2/exclusions.json`
- 创建：`data-pipeline/artifacts/stage3d-fill-bulk-people-v2/*.json`
- 创建：`data-pipeline/reports/stage3d-fill-bulk-people-v2-pipeline-report.md`

- [ ] **步骤 1：接入 generate/validate CLI**

新增：

```text
generate-stage3d-fill-bulk-people-v2
validate-stage3d-fill-bulk-people-v2
```

- [ ] **步骤 2：建立空 reviewed intake**

Observation、source、cache、exclusion 列表均为空；不得生成真实人物或 `no_qualifying_person_found`。

- [ ] **步骤 3：生成 artifacts**

输出 plan、slot inventory、people observations、program-person matches、source/cache manifest、exclusions、gap disclosure、summary、validation result。预期 summary：62 processed、0 identified、62 source-review-not-completed、0 no-qualifying。

- [ ] **步骤 4：生成 Markdown report**

明确本轮只是 pipeline/empty overlay，program people coverage 为 0，不能显示为「无」，下一步才进入 reviewed intake。

### 任务 4：文档与完整验证

**文件：**
- 修改：`docs/database-development-log.md`

- [ ] **步骤 1：更新 development log**

记录目标、schema、validator、0-positive 语义、测试结果、风险与下一步。

- [ ] **步骤 2：运行全部验证**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=data-pipeline/src \
python3 -m pytest data-pipeline/tests -q -p no:cacheprovider

PYTHONPATH=data-pipeline/src python3 -m pathos_data validate-stage3d-fill-bulk-people-v2 ...

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=data-pipeline/src \
python3 -m pathos_data validate --fixture data-pipeline/tests/fixtures/test-university-raw.json

git diff --check
git status --short
```

- [ ] **步骤 3：验证 byte-identical 和 non-mutation**

生成两次并比较 artifacts/report SHA-256；检查 frontend、Candidate v2、Stage 3/3B/3C/3C2/3D 和 Stage 3D-Fill v1 路径无 diff；确认没有 final universe、memberships 或 export。

- [ ] **步骤 4：停止且不提交**

保留本阶段变更为 unstaged/未提交状态，报告新增文件、测试数量、validator、artifact 数量、git diff 与上游 non-mutation，等待用户授权后再进入 reviewed intake。

## 接受标准

- 62 所学校恰好生成 62 个 top-1 slots；状态计数为 0 identified、62 source-review-not-completed、0 no-qualifying。
- 每个 slot 的 program provenance 与 Stage 3C top-1 record 完全一致。
- Positive 写入路径在临时 fixtures 中通过 attendance + program match + identity + cache 校验，所有禁止路径被回归测试拒绝。
- `source_policy_violations=0`、`ranking_field_contamination=0`、`manual_verbatim_check_count=0`。
- 独立 artifacts/report 可 byte-identical 重生成；cache 正文不进入仓库。
- frontend 和所有上游 artifacts 无修改；不生成 final universe、memberships 或 frontend export。
- 不创建 commit。
