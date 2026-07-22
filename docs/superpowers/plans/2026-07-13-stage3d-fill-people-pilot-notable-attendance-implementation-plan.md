# Stage 3D-Fill People Pilot — Notable Alumni / Attendees Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an independent, deterministic, source-limited People Pilot containing 8–12 reviewed notable-attendance records and only directly supported program-person records for the fixed 62-school Candidate v2 scope.

**Architecture:** The pilot reads Candidate v2, immutable Stage 3C demo-program slots, Stage 3D-Fill seed, and immutable Batch 1/2 artifacts only to establish scope and fingerprints. Version-controlled observations retain reviewed short quotes and structured assertions. An optional gitignored local cache is referenced by a committed manifest but never committed. The generator derives only People Pilot artifacts, rejects ranking fields, and never writes an upstream artifact.

**Tech Stack:** Python 3.9 standard library, existing `pathos_data` deterministic artifact conventions, `unittest`, JSON, local Git.

## Global Constraints

- Do not modify frontend, Candidate v2, Stage 3/3B/3C/3C2/3D, Stage 3D-Fill seed, or Batch 1/2 artifacts.
- Keep Candidate v2 scope fixed at 62 universities; do not restore the Stage 3A stash.
- Do not create a final universe, official selection memberships, frontend export, or complete/PASS tag.
- Positive attendance/program-person assertions require a source manifest entry, short verbatim direct quote, quote-verification method, and resolved deterministic `canonical_person_id`.
- Only `graduated`, `attended_no_degree`, and `alumnus_unspecified` may enter attendance content. Faculty, donor, honorary degree, unclear, same-name ambiguity, and campus mismatch go only to exclusions.
- A missing major remains null with a scoped null reason. Do not infer it from occupation or fame.
- Source-policy violations and ranking-field contamination must both be zero. Cache remains gitignored and is never staged.

---

### Task 1: Define red contracts for the isolated People Pilot

**Files:**
- Create: `data-pipeline/tests/test_stage3d_fill_people_pilot_notable_attendance.py`
- Create: `docs/superpowers/plans/2026-07-13-stage3d-fill-people-pilot-notable-attendance-implementation-plan.md`

**Interfaces:**
- Consumes: Candidate v2, Stage 3C slots, Stage 3D-Fill seed, Batch 1/2 roots, and People Pilot input documents.
- Produces: a failing contract for `build_stage3d_fill_people_pilot(**inputs)` and `Stage3DFillPeoplePilotValidationError`.

- [ ] **Step 1: Write the failing test**

```python
def test_builds_fixed_scope_with_reviewed_attendance_and_unreviewed_program_slots(self):
    artifacts = build_stage3d_fill_people_pilot(**self.inputs())
    summary = artifacts["stage3d-fill-people-pilot-summary.json"]
    self.assertEqual(summary["total_universities"], 62)
    self.assertGreaterEqual(summary["notable_attendance_resolved_count"], 8)
    self.assertEqual(summary["program_people_source_review_not_completed_count"] + summary["program_people_identified_count"], 310)

def test_rejects_honorary_relationship_or_quote_outside_allowlist(self):
    observations[0]["attendance_relationship"] = "honorary_degree_only"
    with self.assertRaises(Stage3DFillPeoplePilotValidationError):
        build_stage3d_fill_people_pilot(**inputs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_people_pilot_notable_attendance -v`

Expected: FAIL because the People Pilot module and input bundle do not yet exist.

### Task 2: Implement deterministic source intake, generator, validator, and CLI

**Files:**
- Create: `data-pipeline/src/pathos_data/stage3d_fill_people_pilot_notable_attendance.py`
- Modify: `data-pipeline/src/pathos_data/__main__.py`

**Interfaces:**
- Defines `build_stage3d_fill_people_pilot(...)`, `validate_stage3d_fill_people_pilot(...)`, `render_stage3d_fill_people_pilot_report(...)`, and `write_stage3d_fill_people_pilot(...)`.
- Registers `generate-stage3d-fill-people-pilot-notable-attendance` and `validate-stage3d-fill-people-pilot-notable-attendance`.

- [ ] **Step 1: Implement source/cache and quote validation**

```python
def _anchor(value, manifest, domain):
    if value["evidence_type"] != "direct_quote":
        _fail("People Pilot affirmative fact requires a direct quote")
    if value["quote"] not in manifest[value["source_id"]]["verified_direct_quotes"]:
        _fail("People Pilot quote must match the reviewed allowlist")
    if value["quote_verification_method"] not in {"manual_verbatim_check", "local_cache_substring_check"}:
        _fail("People Pilot needs a quoted verification method")
```

- [ ] **Step 2: Implement attendance/program-person/exclusion derivation**

```python
if attendance_relationship not in {"graduated", "attended_no_degree", "alumnus_unspecified"}:
    _fail("Excluded relationship cannot enter notable attendance")
if canonical_people.get(canonical_person_id, person_name) != person_name:
    _fail("Canonical person ID cannot refer to two different people")
if relationship_to_program == "direct_related_program_match" and not match_notes:
    _fail("Related program match requires explicit evidence notes")
```

- [ ] **Step 3: Preserve all 310 explicit program slots and non-final flags**

```python
record = reviewed_by_slot.get(slot_key) or {
    **slot, "record_status": "source_review_not_completed", "display_value": None,
    "null_reason": "stage3d_fill_people_pilot_program_source_review_not_completed",
}
```

- [ ] **Step 4: Run targeted tests to verify green**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_people_pilot_notable_attendance -v`

Expected: PASS with quote-allowlist, relationship, canonical-person and program-slot regressions enforced.

### Task 3: Add a small reviewed source-intake bundle

**Files:**
- Create: `data-pipeline/data/stage3d-fill-people-pilot/source-manifest.json`
- Create: `data-pipeline/data/stage3d-fill-people-pilot/reviewed-source-cache-manifest.json`
- Create: `data-pipeline/data/stage3d-fill-people-pilot/notable-attendance-observations.json`
- Create: `data-pipeline/data/stage3d-fill-people-pilot/program-people-observations.json`
- Create: `data-pipeline/data/stage3d-fill-people-pilot/exclusions.json`

**Interfaces:**
- Sources contain candidate ID, domain, source reference, publisher, confidence, reviewed short-quote allowlist, and verification metadata.
- Attendance observations contain relationship, person ID, direct anchor, and a scoped null reason when a major is unknown.

- [ ] **Step 1: Collect 8–12 normal-access reviewed official sources**

For each source, preserve only a short verbatim quote supporting the institution and allowed attendance relationship. Use `manual_verbatim_check` without a local cache; otherwise put a SHA-256, cache path, and retrieval/review notes in the committed cache manifest while keeping the cache itself gitignored.

- [ ] **Step 2: Add only reviewed exclusions**

```json
{"candidate_id":"candidate-v2:...","person_name":"...","observed_relationship":"honorary_degree_only","exclusion_reason":"honorary_degree_is_not_attendance","source_id":"...","evidence_anchor":{"evidence_type":"direct_quote","source_id":"...","quote":"...","quote_verification_method":"manual_verbatim_check"},"notes":"Excluded from student/alumni output."}
```

- [ ] **Step 3: Re-run targeted tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3d_fill_people_pilot_notable_attendance -v`

Expected: PASS with 8–12 reviewed attendance records and no fabricated `无`.

### Task 4: Generate artifacts, validate, document, and commit

**Files:**
- Create: `data-pipeline/artifacts/stage3d-fill-people-pilot-notable-attendance/` (eight required JSON artifacts)
- Create: `data-pipeline/reports/stage3d-fill-people-pilot-notable-attendance-report.md`
- Modify: `docs/database-source-policy.md`
- Modify: `docs/database-development-log.md`

- [ ] **Step 1: Generate isolated artifacts and report**

Run: `PYTHONPATH=src python3 -m pathos_data generate-stage3d-fill-people-pilot-notable-attendance ...`

Expected: only People Pilot artifact root and report are written.

- [ ] **Step 2: Run formal deterministic validation**

Run: `PYTHONPATH=src python3 -m pathos_data validate-stage3d-fill-people-pilot-notable-attendance ...`

Expected: `result=passed`, 62 universities, 0 policy/contamination counters, and `ready_for_claude_gate_review=true`.

- [ ] **Step 3: Run full verification**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -q`, `PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json`, and `git diff --check`.

Expected: zero exit codes.

- [ ] **Step 4: Stage exact paths and commit**

Run: `git add` only the new People Pilot module, CLI change, source inputs, artifacts, test, documentation, and plan; use `git add -f` only for the ignored report. Check `git diff --cached --check`, then commit `feat(data): add reviewed notable attendance pilot`.

Expected: local commit only; no tag, push, merge, rebase, cache, frontend, final universe, memberships, or frontend export.

## Acceptance Checklist

- [ ] 8–12 notable attendance records have allowed relationships and source-backed canonical person IDs.
- [ ] Any program-person record has a direct program/degree relationship; all remaining 310 slots stay `source_review_not_completed`.
- [ ] Direct quotes are short, allowlisted, and verification-method-backed.
- [ ] Cache manifest is committed but cache content is gitignored and absent from staged files.
- [ ] Candidate scope is 62; non-final flags remain false; ranking contamination/policy violations are zero.
- [ ] Targeted tests, full tests, formal validator, schema/migration validation, and `git diff --check` pass.
