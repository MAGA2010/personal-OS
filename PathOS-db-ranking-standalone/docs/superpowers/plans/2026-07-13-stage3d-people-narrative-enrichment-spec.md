# Stage 3D People + Narrative Enrichment 设计规格

**状态：** 设计规格，尚未实施。
**基线：** `f01dc69d9b6182a830101c7935516b8f0be50389`；Candidate v2 固定为 62 所学校。
**输入定位：** Candidate v2、Stage 3、Stage 3B、Stage 3C 与 Stage 3C2 都是只读输入。
**输出定位：** Stage 3D 是 source-limited、not-final 的 People + Narrative overlay，不是 final database、final universe、正式 selection memberships 或 frontend export。

---

## 1. Purpose / Goal

Stage 3D 在不扩大 62 所学校范围、也不改变任何 ranking 字段的前提下，为 demo 提供可审计的人物与叙事信息：

1. 每所学校的每个 top-5 demo program 尝试给出 1 位可来源核验的杰出学生；没有合格证据时明确展示「无」。
2. 记录可核验的名人是否曾以学生身份就读该校，以及其专业、学位或未知状态。
3. 提供来源明确、短小的学校历史事实与时间线。
4. 提供来源明确、非虚构的 interesting facts。

本阶段只提升 demo 的可解释性；来源不足时展示 gap，而不是推断人物关系、专业、故事或学位。

## 2. Baseline and Immutable Inputs

- Candidate v2：62 所 source-limited candidate universities；不新增、删除或合并学校。
- Stage 3/3B：提供既有 demo programs、identity、tuition、major 与 ratio overlay；不得回写。
- Stage 3C：提供最终的 top-5 demo-program overlay；Stage 3D 仅从其中读取 program slots。
- Stage 3C2：提供 nearest-town overlay；本阶段不依赖其内容进行人物或历史断言，但把它视作不可变上游 artifact。
- 当前 pipeline 的 `source_policy_violations = 0` 与 `ranking_field_contamination = 0` 是必须保持的硬约束。
- Stage 3A stash 保留且绝不恢复。

Generator 必须在开始和结束时对所有读取的上游文件计算 SHA-256；任一 hash 变化都 fail closed。Stage 3D 不读取或写入 `frontend/`。

## 3. In Scope

1. 结构化人物 source manifest、person identity mapping 与 observations。
2. top-5 demo-program 的「杰出学生 / 无」逐 program overlay。
3. 名人就读状态、专业/学位（若有直接证据）及身份关系语义。
4. 学校历史事实、简短时间线与来源透明的 summary。
5. interesting facts 的结构化、短文本记录。
6. 独立 artifacts、report、gap disclosure、deterministic generator、validator、CLI、tests 与 development log。

## 4. Out of Scope

- U.S. News、National 或 program ranking records、类别、rank、membership reason 的新增或改写。
- 新学校、fuzzy UNITID、人物的模糊身份合并、全量人物百科或全量历史档案采集。
- final universe、正式 selection memberships、正式 frontend export、frontend 修改或地图/详情页接入。
- 以人物专业推断 tuition、以学校声誉推断人物关系、以 Wikipedia/搜索摘要/AI 记忆作为无来源结论。
- 完整网页快照、大段正文、受版权保护的 biographies；Git 只保留结构化 observations、source manifest、短 evidence anchors 与 gap disclosure。
- 恢复或提交 Stage 3A stash。

## 5. Data Sources and Source Policy

### 5.1 Source priority

| Domain | Accepted priority | Notes |
| --- | --- | --- |
| Student / alumni relationship | school official biography, alumni profile, commencement record, registrar/archive → official university library archive → authoritative biographical institution | A relationship must be directly stated. |
| Major / degree | official alumni or archive profile → official degree/commencement record → authoritative biography that directly states the school and major | Never infer from a later profession or faculty department. |
| School history | official history page → official archive/library → university publication or primary institutional record → reputable encyclopedia/reference | Every factual claim has its own anchor. |
| Interesting fact | official archive, museum, athletics/history archive, institutional publication → reputable reference | Must be a short factual observation, not marketing copy or folklore. |

Search-result snippets, forums, user-generated biographies, unsourced listicles and AI memory are discovery aids only and cannot become final evidence. Wikipedia/Wikidata may assist source discovery but are not sufficient standalone evidence for a person relationship, major, degree, or attendance claim. A reputable encyclopedia is permitted only when it directly supports the final factual claim and has `source_confidence=medium`; the report must disclose the source class.

### 5.2 Source policy boundary

- Stage 3D sources are `detail` domain only. Each generator ingestion path calls `validate_source_policy_use(source_name, "detail", has_field_provenance=True)`.
- No Stage 3D source may write or overwrite `usnews_rank`, `usnews_category`, ranking family, ranking membership, or other ranking fields.
- THE, QS, xuanxiao, CollegeData and any ranking-like secondary source cannot supply U.S. News ranking fields and are not required by this stage.
- Every affirmative person, relationship, major, degree, history fact and interesting fact requires `source_id` and a short `evidence_anchor` that resolves in the manifest.
- A no-result row is not a claim that no such person exists. It means no qualifying evidence was found in the recorded reviewed source set; it carries `reviewed_scope`, `reviewed_source_ids`, `null_reason`, and an explicit null-anchor reason.
- `source_review_not_completed` is a separate, explicit scoped gap for a slot or domain whose approved source types have not yet been reviewed in this Stage 3D input batch. It must never be rendered as 「无」; this prevents an unperformed review from becoming a false-negative claim.

### 5.3 Source manifest schema

```json
{
  "source_id": "source_unique_stable_id",
  "candidate_id": "candidate-v2:example",
  "source_type": "official_institutional | official_archive | official_alumni | official_library_archive | reputable_reference",
  "field_domain": "people | attendance | history | interesting_fact",
  "source_title": "Human-readable title",
  "source_url_or_reference": "https://...",
  "publisher": "Institution or reference publisher",
  "accessed_date": "YYYY-MM-DD",
  "source_confidence": "high | medium",
  "official_institutional": true,
  "field_level_provenance_required": true,
  "license_or_use_note": "Short reuse/copyright note",
  "limitation_note": "Short factual limitation or null"
}
```

`source_id` is unique. A source cannot be marked `official_institutional=true` unless it is controlled by the institution, its official archive, library or alumni office. The manifest does not store full snapshots.

## 6. Person Identity and Relationship Semantics

### 6.1 Canonical person mapping

Each accepted person gets a stable `canonical_person_id`. A merge is allowed only with an explicit source-backed identity mapping: matching official profile URL, archival identifier, authority identifier, or a direct source that names the same person. Name similarity alone never merges persons.

```json
{
  "candidate_id": "candidate-v2:example",
  "canonical_person_id": "person:source-backed-slug",
  "display_name": "Example Person",
  "identity_status": "resolved | unresolved",
  "identity_source_id": "source_example_bio",
  "evidence_anchor": {"source_id": "source_example_bio", "evidence_type": "direct_quote", "quote": "Example Person ..."},
  "null_reason": null
}
```

Unresolved person identities cannot populate an affirmative demo slot.

### 6.2 Relationship types

Allowed values are intentionally separate:

| `relationship_type` | Meaning | May populate student/alumni display? |
| --- | --- | --- |
| `graduated` | Direct evidence says the person graduated or earned a degree from the university. | Yes |
| `attended_no_degree` | Direct evidence says the person attended/enrolled; no degree or graduation is asserted. | Yes, labelled attended without degree |
| `alumnus_unspecified` | Source calls the person an alumnus/alumna/alum but does not directly state graduation. | Yes, labelled alumnus; do not infer degree |
| `faculty_only` | Person taught, researched or worked for the institution, without accepted student evidence. | No |
| `honorary_degree_only` | Person received an honorary degree, without accepted student evidence. | No |
| `donor_only` | Person donated to the institution, without accepted student evidence. | No |
| `unclear` | Relationship cannot be classified from the source. | No |

`honorary_degree_only`, `faculty_only`, `donor_only` and `unclear` observations may be retained only as exclusion/audit observations; they must not appear as attendance, alumnus, top-program student or celebrity-attendance records. An honorary degree is never equivalent to attendance or graduation.

### 6.3 Major and degree semantics

- `major_name`, `degree_name`, `degree_type`, `graduation_year` and `attendance_years` are each null unless their own source quote supports them.
- A person’s career field, faculty appointment, later graduate degree, school affiliation or public reputation does not establish their undergraduate major.
- `major_match_status` is `direct_program_match`, `direct_related_program_match`, `not_stated`, or `not_applicable`. A related match must use a version-controlled, explicit program-alias map and still require direct source evidence for the person’s field of study.

## 7. Top-5 Demo Program Distinguished Student Overlay

Stage 3D reads the five programs per university from the immutable Stage 3C demo overlay. It does not call all demo programs “ranked”: only existing U.S. News-backed records retain that label.

### 7.1 Record schema

```json
{
  "candidate_id": "candidate-v2:example",
  "canonical_id": "institution:example",
  "program_name": "Computer Science",
  "normalized_program_name": "computer-science",
  "program_source_basis": "usnews_program_ranking | official_school_program_page | official_major_list",
  "record_status": "identified | no_qualifying_person_found | source_review_not_completed",
  "display_value": "Example Person | 无 | null",
  "canonical_person_id": "person:example | null",
  "person_display_name": "Example Person | null",
  "relationship_type": "graduated | attended_no_degree | alumnus_unspecified | null",
  "major_name": "Computer Science | null",
  "major_match_status": "direct_program_match | direct_related_program_match | null",
  "notability_basis": "Short factual role or award | null",
  "source_id": "source_example_bio | null",
  "evidence_anchor": {"source_id": "source_example_bio", "evidence_type": "direct_quote", "quote": "..."},
  "reviewed_source_ids": ["source_example_alumni_page"],
  "null_reason": null,
  "evidence_anchor_null_reason": null
}
```

For `identified`, `source_id`, `evidence_anchor`, person identity, relationship and major-match evidence are mandatory. For `no_qualifying_person_found`, `display_value` must be exactly `无`; `canonical_person_id`, person fields and `source_id` are null; `reviewed_scope` is a non-empty ordered list of source types actually reviewed (for example, `official_alumni`, `official_archive`); `reviewed_source_ids` is non-empty; `null_reason=qualifying_student_major_evidence_not_found_in_reviewed_sources`; and `evidence_anchor_null_reason=no_affirmative_person_claim_to_anchor`. This is a scoped research gap, never a claim that no such person exists in reality. For `source_review_not_completed`, `display_value`, person fields, `source_id` and `evidence_anchor` are null; `reviewed_scope` is an empty list; `reviewed_scope_note` must state that no approved source type was reviewed in this input batch; and `null_reason=stage3d_source_review_not_completed`. It is an honest collection gap, not a 「无」 result.

One person should fill at most one program slot per university. The exception is a direct source proving a dual major or separately documented program qualifications; the record must list both source anchors and `multi_program_exception=true`.

## 8. Notable Attendance / Celebrity Records

The attendance artifact is independent from top-program slots. It answers whether a known public figure was a student, not whether the person merely worked with or supported the university.

```json
{
  "candidate_id": "candidate-v2:example",
  "canonical_person_id": "person:example",
  "person_display_name": "Example Person",
  "notability_category": "public_service | arts | science | business | sports | other",
  "relationship_type": "graduated | attended_no_degree | alumnus_unspecified",
  "attendance_status_label": "graduated | attended_no_degree | alumnus_unspecified",
  "major_name": "Economics | null",
  "degree_name": "Bachelor of Arts | null",
  "graduation_year": 2000,
  "source_id": "source_example",
  "evidence_anchor": {"source_id": "source_example", "evidence_type": "direct_quote", "quote": "..."},
  "source_confidence": "high",
  "null_reason": null
}
```

Affirmative records must use only `graduated`, `attended_no_degree` or `alumnus_unspecified`; every relationship and every major/degree value must be source-backed. If a person’s major is absent, the record says `major_name=null` and `null_reason=major_not_stated_in_accepted_source`, rather than guessing. Faculty, donor and honorary-degree records go only to exclusions/gap disclosure under their strict `_only` relationship types.

## 9. History and Interesting Facts

### 9.1 History schema

History is stored as atomic facts and a deterministic summary assembled only from accepted facts. No free-form unsourced narrative is permitted.

```json
{
  "candidate_id": "candidate-v2:example",
  "fact_id": "history:example:founding",
  "fact_type": "founding | rename | merger | milestone | campus_development",
  "event_year": 1850,
  "fact_text": "Short factual paraphrase.",
  "source_id": "source_example_history",
  "evidence_anchor": {"source_id": "source_example_history", "evidence_type": "direct_quote", "quote": "Founded in 1850"},
  "source_confidence": "high",
  "null_reason": null
}
```

Every university has a history status row: `accepted_history_facts_found` or `no_qualifying_history_source_found`. A no-result row has a non-empty `null_reason`, `reviewed_scope` and reviewed source IDs; it never fabricates a founding date or institutional story.

### 9.2 Interesting-fact schema

```json
{
  "candidate_id": "candidate-v2:example",
  "fact_id": "interesting:example:001",
  "fact_category": "tradition | architecture | archive | institutional_milestone | campus_culture | other",
  "fact_text": "Short factual paraphrase, not promotional copy.",
  "source_id": "source_example_archive",
  "evidence_anchor": {"source_id": "source_example_archive", "evidence_type": "direct_quote", "quote": "..."},
  "source_confidence": "high | medium",
  "editorial_safety_note": "No unsupported superlative or causal claim.",
  "null_reason": null
}
```

Facts must be directly supported, concise and non-sensational. Narrative and anecdote body text is always a short paraphrase; only `evidence_anchor.quote` may preserve a short verbatim quote. Long webpage passages, copied institutional histories and copied biographies are forbidden. Anecdotes marked as tradition must be explicitly characterized by their source as a tradition; unverified folklore is excluded.

## 10. Artifact Plan

Stage 3D writes only to `data-pipeline/artifacts/stage3d-people-narrative-enrichment/`:

| Artifact | Contents |
| --- | --- |
| `stage3d-universities.json` | Fixed 62-school overlay, immutable-input fingerprints and per-domain status. |
| `stage3d-source-manifest.json` | Accepted source metadata and confidence. |
| `stage3d-person-identity-mappings.json` | Explicit source-backed person identities; no fuzzy merge. |
| `stage3d-top-program-notable-students.json` | Exactly one record per Stage 3C demo-program slot; identified person or scoped 「无」. |
| `stage3d-notable-attendance.json` | Source-backed public-figure attendance/degree/major records. |
| `stage3d-history.json` | Atomic history facts and per-school status. |
| `stage3d-interesting-facts.json` | Atomic factual interesting-fact records. |
| `stage3d-gap-disclosure.json` | no-result rows, excluded relationships, source limitations and policy counters. |
| `stage3d-summary.json` | Coverage counts, relationship breakdown, source confidence and readiness. |
| `stage3d-validation-result.json` | Formal full-artifact validation result. |

Version-controlled structured inputs live under `data-pipeline/data/stage3d/`:

- `source-manifest.json`
- `person-identity-mappings.json`
- `top-program-notable-student-observations.json`
- `notable-attendance-observations.json`
- `history-observations.json`
- `interesting-fact-observations.json`
- `program-alias-mappings.json`

The report is `data-pipeline/reports/stage3d-people-narrative-enrichment-report.md`. Cache, if needed for permitted documents, belongs under gitignored `data-pipeline/cache/stage3d-people-narrative/` and must not enter the commit.

## 11. Gap Disclosure Rules

- One top-program person row exists for every Stage 3C demo program. A completed review with no qualifying person is displayed as `无`; a source-review-not-completed slot is an explicit null gap and is never silently omitted or rendered as `无`.
- A `无` row has non-empty `reviewed_scope` and `reviewed_source_ids`, is scoped to those reviewed source types, and is not an assertion that no notable student exists worldwide.
- Major, degree and attendance gaps are represented independently; an attended person with unknown major is valid only when the attendance claim has direct evidence.
- Each university gets history and interesting-fact status, even when no acceptable fact is found.
- Excluded relationship observations identify `faculty_only`, `donor_only`, `honorary_degree_only` or `unclear` and the exclusion reason, but do not surface as student/alumni content.
- Report and summary must disclose all no-result counts, source-class limitations, `source_policy_violations=0`, `ranking_field_contamination=0`, and non-final flags.

## 12. Validator Rules

The formal Stage 3D validator must fail closed if any condition is false:

1. Scope equals Candidate v2’s 62 candidate IDs; no new school appears.
2. Stage 3/3B/3C/3C2 input fingerprints are unchanged before/after generation.
3. Every top-5 demo-program slot has exactly one Stage 3D person row.
4. An affirmative top-program record has source ID, anchor, resolved person identity, allowed student relationship and direct program-major match evidence.
5. A no-result top-program record has `display_value=无`, non-empty reviewed source IDs and required scoped null reasons; it cannot masquerade as an affirmative fact. A source-review-not-completed record has null display/person/source fields plus required explicit collection-gap metadata and cannot masquerade as `无`.
6. `faculty_only`, `donor_only`, `honorary_degree_only` and `unclear` cannot appear in top-program or notable-attendance output.
7. Honorary degree cannot be rendered as attended or graduated; faculty/donor cannot be rendered as student/alumnus.
8. Major/degree/attendance fields cannot be populated without their own direct source anchor.
9. Person identity merges require explicit source-backed mappings; duplicate-name fuzzy merges fail.
10. History and interesting facts require a source ID, short anchor, allowed source confidence and no unanchored summary claim.
11. Source ID resolution, short-anchor limits, field-domain policy and source confidence are valid for every affirmative fact.
12. `source_policy_violations=0` and `ranking_field_contamination=0`.
13. Artifacts regenerate byte-identically from inputs.
14. No final universe, official selection memberships, frontend export or frontend changes exist.
15. Gitignored cache is not tracked by Git.

## 13. Test Plan

Minimum regression coverage:

1. A top-program row is emitted for every immutable Stage 3C demo-program slot.
2. A source-backed graduated person with a direct major match is accepted.
3. A missing qualifying person becomes exactly `无` with scoped gap metadata.
4. Faculty-only, donor-only and honorary-degree-only records are rejected as student/alumni evidence.
5. `attended_no_degree` remains distinct from `graduated`; degree cannot be inferred.
6. An attendance record with null major is accepted only with explicit `major_not_stated...` reason.
7. Fuzzy same-name person merge is rejected; explicit identity mapping succeeds.
8. History and interesting facts fail without source ID/short anchor or with forbidden folklore status.
9. Detail sources cannot alter U.S. News ranking fields.
10. Missing/changed upstream Stage 3/3B/3C/3C2 fingerprints fail validation.
11. Full artifact bundle fails if a required file is absent or a cache file is tracked.
12. Deterministic regeneration is byte-identical.

## 14. Determinism and Artifact Integrity

- Sort candidate IDs, program slots, sources, persons and fact IDs deterministically.
- JSON output uses stable key order, UTF-8 and trailing newline.
- `source_id`, `canonical_person_id` and `fact_id` are stable; generated ordering does not depend on network ordering or cache timestamps.
- Generator must not browse during validation. Network/source collection is an explicit observation-input step, recorded in manifests.
- Validator rebuilds expected artifacts from structured inputs and compares exact JSON objects; it additionally performs semantic checks rather than relying only on equality.

## 15. Acceptance Criteria

Stage 3D is accepted for Gate review only when:

- all 62 schools have an independent Stage 3D row; no requirement forces every people/narrative field to be populated when evidence is unavailable;
- all Stage 3C top-program slots have one affirmative result, an explicit scoped `无` gap row, or an explicit `source_review_not_completed` collection gap row;
- every affirmative person relationship/major/degree/history/fact claim has resolvable source provenance and a short anchor;
- no honorary degree, donor or faculty claim is displayed as student/alumnus;
- all history/fact statements are source-backed or explicitly absent;
- all upstream artifacts are unchanged;
- policy violations and ranking contamination are zero;
- deterministic generation, validator, complete Python tests, fixture/schema/migration validation and `git diff --check` pass;
- cache is ignored, frontend is unchanged, and no final outputs were produced.

Meeting these criteria still does not make Candidate v2, Stage 3D, or any detail pack a final university database.

## 16. Handoff to Stage 4

Stage 4 may consume only a later reviewed Stage 3D overlay and must preserve `source_limited=true`, `incomplete=true`, `not_final=true`. It may produce a controlled demo preview export after frontend collaboration is ready, but must not treat a person/no-result row as a final institutional biography claim. Stage 4 owns map/detail-page/AI-advisor integration; Stage 3D does not modify frontend.

## 17. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| A famous person is wrongly called an alumnus | Require an allowed, direct relationship type and source anchor; reject faculty-only/donor-only/honorary-degree-only evidence. |
| Major is inferred from career or graduate study | Require direct major source; otherwise null with reason. |
| 「无」 is mistaken for proof of absence | Define it as no qualifying evidence in reviewed sources and retain search/source scope. |
| Narrative becomes promotional or fabricated | Store atomic source-backed facts; deterministic summary may use only accepted facts. |
| Person name collision | Require source-backed canonical mapping; no fuzzy merge. |
| Ranking contamination | Keep all Stage 3D sources in detail domain and validate policy counters. |
| Copyright or source retention risk | Commit only manifest metadata, short quotes and structured observations; ignore caches. |
