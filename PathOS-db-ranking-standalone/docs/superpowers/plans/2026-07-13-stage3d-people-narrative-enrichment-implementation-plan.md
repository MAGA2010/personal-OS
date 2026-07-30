# Stage 3D People + Narrative Enrichment 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 Candidate v2 固定的 62 所学校生成来源可审计、不会污染 ranking fields 的人物与叙事 Stage 3D overlay。

**架构：** 新增独立的 Stage 3D structured-observation input layer、deterministic generator 与 full-artifact validator。generator 只读取 Candidate v2 与不可变的 Stage 3/3B/3C/3C2 artifacts，输出独立 Stage 3D artifacts；所有正向人物和叙事断言都通过 source manifest 的短 evidence anchor 解析。已完成审查但无合格证据时才表示为 scoped `无`；尚未审查的输入批次必须表示为 `source_review_not_completed`，不能伪装为 `无`。

**技术栈：** Python 3 标准库、现有 `pathos_data` CLI、JSON artifacts、`unittest`、Git ignore policy。

---

## 0. File Map and Non-Mutation Boundary

### Create

- `data-pipeline/src/pathos_data/stage3d_people_narrative.py` — input loading, source-policy guard, deterministic generator, report renderer, validator and writer.
- `data-pipeline/data/stage3d/source-manifest.json` — reviewed source metadata only.
- `data-pipeline/data/stage3d/person-identity-mappings.json` — source-backed person identity mappings.
- `data-pipeline/data/stage3d/program-alias-mappings.json` — explicit program-name equivalence permitted for direct related-major matches.
- `data-pipeline/data/stage3d/top-program-notable-student-observations.json` — affirmative person observations and scoped no-result research records.
- `data-pipeline/data/stage3d/notable-attendance-observations.json` — affirmative attendance observations plus exclusions.
- `data-pipeline/data/stage3d/history-observations.json` — atomic history observations.
- `data-pipeline/data/stage3d/interesting-fact-observations.json` — atomic interesting-fact observations.
- `data-pipeline/artifacts/stage3d-people-narrative-enrichment/` — the 10 artifacts defined in the specification.
- `data-pipeline/reports/stage3d-people-narrative-enrichment-report.md` — generated report.
- `data-pipeline/tests/test_stage3d_people_narrative.py` — unit and full-artifact regression tests.

### Modify

- `data-pipeline/src/pathos_data/__main__.py` — add `generate-stage3d-people-narrative` and `validate-stage3d-people-narrative` only.
- `docs/database-source-policy.md` — add Stage 3D person/narrative provenance and relationship exclusion policy.
- `docs/database-development-log.md` — record Stage 3D decision, source classes, coverage, gaps, tests and non-final boundary after implementation.

### Do not modify

- Any Candidate v2 artifact.
- `data-pipeline/artifacts/stage3-program-mvp-detail-pack/`.
- `data-pipeline/artifacts/stage3b-demo-critical-gap-fill/`.
- `data-pipeline/artifacts/stage3c-academic-geo-enrichment/`.
- `data-pipeline/artifacts/stage3c2-nearest-towns-gap-repair/`.
- `frontend/`, `frontend/package-lock.json`, final universe files, formal membership files or the Stage 3A stash.

### Cache policy

- Optional raw source cache lives only under `data-pipeline/cache/stage3d-people-narrative/`.
- Reuse existing `cache/` gitignore; verify `git check-ignore` for every cache input.
- Never stage cache files, HTML snapshots, PDF copies or full biographies.

## 1. Establish Stage 3D Contracts and Fixtures

**Files:**
- Create: the seven `data-pipeline/data/stage3d/*.json` inputs listed above.
- Create: `data-pipeline/tests/test_stage3d_people_narrative.py`.
- Modify: `docs/database-source-policy.md`.

- [ ] **Step 1: Write failing contract tests for the empty/invalid Stage 3D inputs.**

```python
def test_top_program_slot_requires_exactly_one_identified_or_scoped_none_result():
    artifacts = build_stage3d_people_narrative(**valid_inputs())
    slots = artifacts["stage3d-top-program-notable-students.json"]["records"]
    self.assertEqual(len(slots), stage3c_demo_program_slot_count())
    self.assertTrue(all(row["record_status"] in {"identified", "no_qualifying_person_found", "source_review_not_completed"} for row in slots))


def test_no_result_uses_scoped_wu_not_a_false_absence_claim():
    row = make_no_result_row()
    self.assertEqual(row["display_value"], "无")
    self.assertEqual(row["null_reason"], "qualifying_student_major_evidence_not_found_in_reviewed_sources")
    self.assertTrue(row["reviewed_source_ids"])
```

- [ ] **Step 2: Run the new tests and confirm they fail because Stage 3D builder is absent.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: `FAIL`/`ERROR` due to missing `stage3d_people_narrative` module or builder.

- [ ] **Step 3: Create minimal schema-valid input fixtures.**

Use these concrete shapes, with every affirmative claim source-backed:

```json
{
  "record_type": "stage3d_top_program_observations",
  "observations": [
    {
      "candidate_id": "candidate-v2:example",
      "normalized_program_name": "computer-science",
      "record_status": "identified",
      "canonical_person_id": "person:example",
      "person_display_name": "Example Person",
      "relationship_type": "graduated",
      "major_name": "Computer Science",
      "major_match_status": "direct_program_match",
      "source_id": "source_example_official_alumni",
      "evidence_anchor": {"source_id": "source_example_official_alumni", "evidence_type": "direct_quote", "quote": "earned a degree in computer science"}
    }
  ]
}
```

Every no-result row must include a non-empty `reviewed_scope` list naming the source types actually examined, `reviewed_source_ids`, `display_value="无"`, the exact scoped null reason and `evidence_anchor=null` with `evidence_anchor_null_reason=no_affirmative_person_claim_to_anchor`. It means only that reviewed sources contain no qualifying evidence; it must never say the person does not exist in reality. A source batch not yet reviewed must instead use `record_status=source_review_not_completed`, null display/person/source fields, `reviewed_scope=[]`, an explicit `reviewed_scope_note`, and `null_reason=stage3d_source_review_not_completed`.

- [ ] **Step 4: Add source-policy documentation before accepting observations.**

Add a Stage 3D section that states: people/history sources are `detail` domain; relationship types are not interchangeable; honorary degree/faculty/donor cannot prove attendance; major and degree require direct evidence; and no Stage 3D source can modify U.S. News ranking fields.

- [ ] **Step 5: Commit the contract and source-policy foundation.**

```bash
git add data-pipeline/data/stage3d docs/database-source-policy.md data-pipeline/tests/test_stage3d_people_narrative.py
git commit -m "feat(data): define stage 3d narrative evidence contracts"
```

## 2. Implement Source Loading, Identity Semantics and Top-Program Slot Generation

**Files:**
- Create: `data-pipeline/src/pathos_data/stage3d_people_narrative.py`.
- Modify: `data-pipeline/tests/test_stage3d_people_narrative.py`.

- [ ] **Step 1: Write failing relationship and identity tests.**

```python
def test_honorary_degree_and_faculty_cannot_fill_student_or_attendance_rows():
    artifacts = build_stage3d_people_narrative(**inputs_with_honorary_or_faculty())
    with self.assertRaises(Stage3DPeopleNarrativeValidationError):
        validate_stage3d_people_narrative(artifacts, **validation_inputs())


def test_same_name_people_need_explicit_source_backed_identity_mapping():
    artifacts = build_stage3d_people_narrative(**inputs_with_fuzzy_person_merge())
    with self.assertRaises(Stage3DPeopleNarrativeValidationError):
        validate_stage3d_people_narrative(artifacts, **validation_inputs())


def test_attended_no_degree_does_not_imply_graduated_or_a_major():
    record = attendance_record("attended_no_degree", major_name=None)
    self.assertEqual(record["attendance_status_label"], "attended_no_degree")
    self.assertIsNone(record["degree_name"])
    self.assertEqual(record["null_reason"], "major_not_stated_in_accepted_source")
```

- [ ] **Step 2: Run the new tests and confirm red state.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: validation behavior is unavailable or incorrectly accepts forbidden relationships.

- [ ] **Step 3: Implement narrow helper functions and types.**

```python
ALLOWED_STUDENT_RELATIONSHIPS = {"graduated", "attended_no_degree", "alumnus_unspecified"}
EXCLUDED_RELATIONSHIPS = {"faculty_only", "donor_only", "honorary_degree_only", "unclear"}

def _is_affirmative_student_claim(row: dict[str, Any]) -> bool:
    return row["record_status"] == "identified" and row["relationship_type"] in ALLOWED_STUDENT_RELATIONSHIPS

def _validate_person_identity(row: dict[str, Any], mappings: dict[str, dict[str, Any]]) -> None:
    mapping = mappings.get(row["canonical_person_id"])
    if mapping is None or mapping["identity_status"] != "resolved":
        _fail("affirmative person claim requires explicit source-backed identity mapping")
```

The builder must read Candidate v2 and the Stage 3C demo-program overlay, construct exactly one row per program slot, and reject an observation whose program is not an immutable Stage 3C slot. It must call `validate_source_policy_use()` for every affirmative source ingestion path. It must emit `source_review_not_completed` rather than `无` where no reviewed source scope has been supplied.

- [ ] **Step 4: Implement scoped no-result conversion.**

```python
def _no_result_slot(candidate_id: str, program: dict[str, Any], reviewed_source_ids: list[str]) -> dict[str, Any]:
    if not reviewed_source_ids:
        _fail("no-result slot requires recorded reviewed sources")
    return {
        "candidate_id": candidate_id,
        "normalized_program_name": program["normalized_program_name"],
        "record_status": "no_qualifying_person_found",
        "display_value": "无",
        "canonical_person_id": None,
        "source_id": None,
        "evidence_anchor": None,
        "reviewed_source_ids": sorted(reviewed_source_ids),
        "null_reason": "qualifying_student_major_evidence_not_found_in_reviewed_sources",
        "evidence_anchor_null_reason": "no_affirmative_person_claim_to_anchor",
    }
```

- [ ] **Step 5: Run targeted tests and confirm green state.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: relationship/identity/no-result tests pass.

- [ ] **Step 6: Commit the person-slot core.**

```bash
git add data-pipeline/src/pathos_data/stage3d_people_narrative.py data-pipeline/tests/test_stage3d_people_narrative.py
git commit -m "feat(data): add stage 3d person evidence overlay"
```

## 3. Implement Notable Attendance, History and Interesting-Fact Generation

**Files:**
- Modify: `data-pipeline/src/pathos_data/stage3d_people_narrative.py`.
- Modify: `data-pipeline/tests/test_stage3d_people_narrative.py`.
- Create: `data-pipeline/reports/stage3d-people-narrative-enrichment-report.md` (generated later by CLI).

- [ ] **Step 1: Write failing tests for attendance and narrative claims.**

```python
def test_notable_attendance_requires_direct_relationship_and_major_evidence_when_present():
    artifacts = build_stage3d_people_narrative(**inputs_with_unanchored_major())
    with self.assertRaises(Stage3DPeopleNarrativeValidationError):
        validate_stage3d_people_narrative(artifacts, **validation_inputs())


def test_history_and_interesting_facts_reject_unanchored_or_folklore_claims():
    artifacts = build_stage3d_people_narrative(**inputs_with_unanchored_fact())
    with self.assertRaises(Stage3DPeopleNarrativeValidationError):
        validate_stage3d_people_narrative(artifacts, **validation_inputs())
```

- [ ] **Step 2: Run the tests and confirm red state.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: incomplete narrative validation fails.

- [ ] **Step 3: Add atomic record builders.**

```python
def _history_fact(observation: dict[str, Any], manifest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _validate_anchor(observation, manifest, domain="history")
    return {key: observation[key] for key in HISTORY_OUTPUT_FIELDS}


def _interesting_fact(observation: dict[str, Any], manifest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _validate_anchor(observation, manifest, domain="interesting_fact")
    if observation["fact_category"] == "tradition" and not observation.get("source_characterizes_as_tradition"):
        _fail("tradition requires source characterization")
    return {key: observation[key] for key in INTERESTING_FACT_OUTPUT_FIELDS}
```

`history_summary` may be generated only from accepted fact rows, in sorted event-year/fact-ID order. It must not introduce a new claim or a new quote.

- [ ] **Step 4: Add gap/exclusion output.**

The gap disclosure must list each excluded relationship observation (`faculty`, `donor`, `honorary_degree`, `unknown`) with `exclusion_reason`, each unknown major, each no-result program slot and every school without accepted history/fact source.

- [ ] **Step 5: Run targeted tests and confirm green state.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: affirmative attendance/history/fact rows pass only with their direct anchors; bad rows fail.

- [ ] **Step 6: Commit narrative builders and tests.**

```bash
git add data-pipeline/src/pathos_data/stage3d_people_narrative.py data-pipeline/tests/test_stage3d_people_narrative.py
git commit -m "feat(data): add stage 3d narrative fact validation"
```

## 4. Add Deterministic Artifact Writer, Full Validator and CLI

**Files:**
- Modify: `data-pipeline/src/pathos_data/stage3d_people_narrative.py`.
- Modify: `data-pipeline/src/pathos_data/__main__.py`.
- Modify: `data-pipeline/tests/test_stage3d_people_narrative.py`.

- [ ] **Step 1: Write failing full-artifact tests.**

```python
def test_stage3d_is_byte_deterministic_and_preserves_all_upstream_hashes():
    first = build_stage3d_people_narrative(**valid_inputs())
    second = build_stage3d_people_narrative(**valid_inputs())
    self.assertEqual(first, second)
    self.assertEqual(first["stage3d-universities.json"]["metadata"]["input_sha256"], immutable_input_hashes())


def test_stage3d_rejects_ranking_field_contamination_and_final_output_flags():
    artifacts = build_stage3d_people_narrative(**valid_inputs())
    artifacts["stage3d-top-program-notable-students.json"]["records"][0]["usnews_rank"] = 1
    with self.assertRaises(Stage3DPeopleNarrativeValidationError):
        validate_stage3d_people_narrative(artifacts, **validation_inputs())
```

- [ ] **Step 2: Run tests and confirm red state.**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v`
Expected: missing full-artifact validator/CLI contract fails.

- [ ] **Step 3: Implement the artifact bundle and semantic validator.**

Required artifact keys:

```python
OUTPUT_FILES = (
    "stage3d-universities.json",
    "stage3d-source-manifest.json",
    "stage3d-person-identity-mappings.json",
    "stage3d-top-program-notable-students.json",
    "stage3d-notable-attendance.json",
    "stage3d-history.json",
    "stage3d-interesting-facts.json",
    "stage3d-gap-disclosure.json",
    "stage3d-summary.json",
)
```

The validator rebuilds expected artifacts, compares exact structures, checks all semantic rules in the specification, validates `source_policy_violations == 0`, validates `ranking_field_contamination == 0`, checks immutable SHA-256 inputs before/after, checks `git check-ignore` for cache paths, and rejects any output outside the independent Stage 3D directory.

- [ ] **Step 4: Add CLI commands.**

```text
generate-stage3d-people-narrative
  --candidate-v2 ...
  --stage3-dir ... --stage3b-dir ... --stage3c-dir ... --stage3c2-dir ...
  --source-manifest ... --person-mappings ... --program-alias-mappings ...
  --top-program-observations ... --attendance-observations ...
  --history-observations ... --interesting-fact-observations ...
  --output ... --report-output ...

validate-stage3d-people-narrative
  [same immutable/input flags]
  --universities ... --source-manifest-output ... --person-mappings-output ...
  --top-program-students ... --notable-attendance ... --history ... --interesting-facts ...
  --gap-disclosure ... --summary ... --report ... --result-output ...
```

Both commands must require every artifact/input path and fail closed when one is missing.

- [ ] **Step 5: Run the targeted suite and CLI fail-closed checks.**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_stage3d_people_narrative -v
PYTHONPATH=src python3 -m pathos_data generate-stage3d-people-narrative --help
PYTHONPATH=src python3 -m pathos_data validate-stage3d-people-narrative --help
```

Expected: all Stage 3D tests pass; both commands expose mandatory full-artifact arguments.

- [ ] **Step 6: Commit generator, validator and CLI.**

```bash
git add data-pipeline/src/pathos_data/stage3d_people_narrative.py data-pipeline/src/pathos_data/__main__.py data-pipeline/tests/test_stage3d_people_narrative.py
git commit -m "feat(data): generate stage 3d people narrative overlay"
```

## 5. Collect Reviewed Sources and Generate Stage 3D Artifacts

**Files:**
- Modify: `data-pipeline/data/stage3d/*.json`.
- Create: `data-pipeline/artifacts/stage3d-people-narrative-enrichment/*`.
- Create: `data-pipeline/reports/stage3d-people-narrative-enrichment-report.md`.
- Modify: `docs/database-development-log.md`.

- [ ] **Step 1: Collect only allowed source observations.**

For each school, record each source before extracting claims. For people, preserve direct wording about attendance and major; classify ambiguous relationship evidence as excluded rather than guessing. For history/facts, store a concise factual paraphrase in the narrative field and a separate short quote only in `evidence_anchor`; never copy paragraphs. For a program with no qualifying person, add scoped no-result metadata, non-empty `reviewed_scope`, and reviewed source IDs. Missing evidence never blocks a school-level Stage 3D record and never permits a guessed person, major, relationship or story.

- [ ] **Step 2: Run generation.**

```bash
PYTHONPATH=src python3 -m pathos_data generate-stage3d-people-narrative \
  --candidate-v2 data/university-universe-candidates/v2-source-limited/candidate-universities.json \
  --stage3-dir artifacts/stage3-program-mvp-detail-pack \
  --stage3b-dir artifacts/stage3b-demo-critical-gap-fill \
  --stage3c-dir artifacts/stage3c-academic-geo-enrichment \
  --stage3c2-dir artifacts/stage3c2-nearest-towns-gap-repair \
  --source-manifest data/stage3d/source-manifest.json \
  --person-mappings data/stage3d/person-identity-mappings.json \
  --program-alias-mappings data/stage3d/program-alias-mappings.json \
  --top-program-observations data/stage3d/top-program-notable-student-observations.json \
  --attendance-observations data/stage3d/notable-attendance-observations.json \
  --history-observations data/stage3d/history-observations.json \
  --interesting-fact-observations data/stage3d/interesting-fact-observations.json \
  --output artifacts/stage3d-people-narrative-enrichment \
  --report-output reports/stage3d-people-narrative-enrichment-report.md
```

Expected: generator writes only the independent Stage 3D directory/report and prints a pass message.

- [ ] **Step 3: Update development log.**

Record source classes used, relationship breakdown (`graduated`, `attended_no_degree`, `alumnus_unspecified`, strict exclusions), no-result program count and `reviewed_scope` distribution, history/fact coverage, source-confidence distribution, all gaps, policy counters, tests, cache exclusion and non-final boundary.

- [ ] **Step 4: Commit reviewed observations and generated artifacts.**

```bash
git add data-pipeline/data/stage3d data-pipeline/artifacts/stage3d-people-narrative-enrichment \
  data-pipeline/reports/stage3d-people-narrative-enrichment-report.md docs/database-development-log.md
git commit -m "feat(data): enrich stage 3d people and narratives"
```

## 6. Full Verification and Scoped Commit Review

**Files:**
- Verify all Stage 3D files only; do not add implementation work outside this list.

- [ ] **Step 1: Run formal Stage 3D validation.**

```bash
PYTHONPATH=src python3 -m pathos_data validate-stage3d-people-narrative \
  --candidate-v2 data/university-universe-candidates/v2-source-limited/candidate-universities.json \
  --stage3-dir artifacts/stage3-program-mvp-detail-pack \
  --stage3b-dir artifacts/stage3b-demo-critical-gap-fill \
  --stage3c-dir artifacts/stage3c-academic-geo-enrichment \
  --stage3c2-dir artifacts/stage3c2-nearest-towns-gap-repair \
  --source-manifest data/stage3d/source-manifest.json \
  --person-mappings data/stage3d/person-identity-mappings.json \
  --program-alias-mappings data/stage3d/program-alias-mappings.json \
  --top-program-observations data/stage3d/top-program-notable-student-observations.json \
  --attendance-observations data/stage3d/notable-attendance-observations.json \
  --history-observations data/stage3d/history-observations.json \
  --interesting-fact-observations data/stage3d/interesting-fact-observations.json \
  --universities artifacts/stage3d-people-narrative-enrichment/stage3d-universities.json \
  --source-manifest-output artifacts/stage3d-people-narrative-enrichment/stage3d-source-manifest.json \
  --person-mappings-output artifacts/stage3d-people-narrative-enrichment/stage3d-person-identity-mappings.json \
  --top-program-students artifacts/stage3d-people-narrative-enrichment/stage3d-top-program-notable-students.json \
  --notable-attendance artifacts/stage3d-people-narrative-enrichment/stage3d-notable-attendance.json \
  --history artifacts/stage3d-people-narrative-enrichment/stage3d-history.json \
  --interesting-facts artifacts/stage3d-people-narrative-enrichment/stage3d-interesting-facts.json \
  --gap-disclosure artifacts/stage3d-people-narrative-enrichment/stage3d-gap-disclosure.json \
  --summary artifacts/stage3d-people-narrative-enrichment/stage3d-summary.json \
  --report reports/stage3d-people-narrative-enrichment-report.md \
  --result-output artifacts/stage3d-people-narrative-enrichment/stage3d-validation-result.json
```

Expected: `Stage 3D people narrative validation passed`.

- [ ] **Step 2: Run full pipeline verification.**

```bash
cd data-pipeline
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json
git diff --check
```

Expected: all Python tests pass; schema/migration validation passes; no whitespace errors.

- [ ] **Step 3: Prove non-mutation and cache/frontend boundaries.**

```bash
git diff --name-only | rg '^(frontend/|data-pipeline/artifacts/stage3-program-mvp-detail-pack/|data-pipeline/artifacts/stage3b-demo-critical-gap-fill/|data-pipeline/artifacts/stage3c-academic-geo-enrichment/|data-pipeline/artifacts/stage3c2-nearest-towns-gap-repair/|data-pipeline/data/university-universe-candidates/)' && exit 1 || true
git ls-files 'data-pipeline/cache/stage3d-people-narrative/*'
git diff --cached --check
git status --short
```

Expected: no forbidden paths in the Stage 3D diff; no tracked Stage 3D cache; clean status after the final commit.

- [ ] **Step 4: Create the final local commit only after all checks pass.**

```bash
git add data-pipeline/src/pathos_data/stage3d_people_narrative.py \
  data-pipeline/src/pathos_data/__main__.py \
  data-pipeline/tests/test_stage3d_people_narrative.py \
  data-pipeline/data/stage3d \
  data-pipeline/artifacts/stage3d-people-narrative-enrichment \
  data-pipeline/reports/stage3d-people-narrative-enrichment-report.md \
  docs/database-source-policy.md docs/database-development-log.md
git commit -m "feat(data): enrich people and narrative detail pack"
```

Do not tag, push, merge, rebase, restore the Stage 3A stash, or begin Stage 4 frontend integration without a new explicit request.

## Acceptance Checklist

- [ ] Candidate scope remains exactly 62 schools.
- [ ] Every Stage 3C demo-program slot has one `identified` record, scoped `无` row, or explicit `source_review_not_completed` row.
- [ ] All affirmative people, relationship, major, degree, history and interesting-fact fields resolve to source IDs and short anchors.
- [ ] Honorary-degree-only, faculty-only, donor-only and unclear relationship records are excluded from student/alumni output.
- [ ] No major, degree or attendance claim is inferred.
- [ ] History/facts are atomic, source-backed and not fabricated.
- [ ] `source_policy_violations=0` and `ranking_field_contamination=0`.
- [ ] Deterministic generation and full-artifact validation pass.
- [ ] Full Python tests, fixture/schema/migration validation and `git diff --check` pass.
- [ ] No cache, frontend, final-universe or formal-membership output is committed.
