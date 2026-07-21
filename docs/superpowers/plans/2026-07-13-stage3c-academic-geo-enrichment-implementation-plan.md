# Stage 3C Academic + Geo Enrichment 实施计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `executing-plans` 逐任务实施此计划。步骤使用复选框（`- [ ]`）语法跟踪。实施前阅读并遵守 `docs/superpowers/plans/2026-07-13-stage3c-academic-geo-enrichment-spec.md`。

**目标：** 以 Candidate v2、Stage 3 与 Stage 3B 为不可变输入，生成 source-limited、可复现的 Stage 3C Academic + Geo overlay；补强官方本科 majors、UNC demo program、undergraduate tuition differences、highest/lowest tuition、Census 四区与最近三个 place 的 Haversine 直线距离。

**架构：** 一个新 Python generator 仅消费版本控制的 Stage 3C observations/source manifest、受控的 gitignored federal geography cache，以及只读的 Candidate v2/Stage 3/Stage 3B artifacts。它在独立目录输出九个 JSON artifacts。formal validator 通过 deterministic regeneration、input hash、防排名污染、fee applicability、region/place/distance 与非 mutation checks fail closed。

**技术栈：** Python 3.9 stdlib（JSON/CSV/ZIP/hashlib/math）、现有 `validate_source_policy_use()`、现有 Stage 3 tuition guards、official institutional sources、Census Gazetteer Places、现有 `unittest` CLI。

**实施边界：** 不修改 `frontend/`、Stage 3、Stage 3B 或 Candidate v2 artifacts；不恢复 Stage 3A stash；不生成 final universe、正式 selection memberships 或 frontend export；不提交完整网页快照或 cache。

---

## 1. Files and Responsibilities

### Create

| Path | Responsibility |
| --- | --- |
| `data-pipeline/src/pathos_data/stage3c_academic_geo.py` | Deterministic Stage 3C generator, controlled input readers, Haversine helper, tuition comparator, validator, writer. |
| `data-pipeline/tests/test_stage3c_academic_geo.py` | Red/green tests for scope, source policy, official-undergraduate guard, fee calculation, region/place/distance, determinism and non-mutation. |
| `data-pipeline/data/stage3c/source-manifest.json` | Version-controlled source rows, each with domain, URL/reference, access date, publisher, license note, limitation. |
| `data-pipeline/data/stage3c/official-major-observations.json` | Reviewed short official undergraduate major/program observations, including UNC additions only when directly supported. |
| `data-pipeline/data/stage3c/official-tuition-fee-observations.json` | Reviewed official undergraduate tuition confirmation and fee observations; no inferred values. |
| `data-pipeline/data/stage3c/region-classification.json` | Complete state/DC → Census four-region controlled mapping. |
| `data-pipeline/data/stage3c/town-source-manifest.json` | Gazetteer/GeoNames source version and permitted place taxonomy policy. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-universities.json` | 62 university overlay rows, Census region, nearest places, input provenance and gap flags. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-official-major-sources.json` | Per-university official-major source status. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-official-majors.json` | Official undergraduate major entries only. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json` | Stage 3B programs plus official UNC supplement only. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-tuition-deepening.json` | Official tuition confirmation and college/program fee observations. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-highest-lowest-tuition.json` | Comparability-safe highest/lowest outputs. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-gap-disclosure.json` | Aggregate/per-school limitations. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-summary.json` | Coverage/status/policy/determinism/readiness statistics. |
| `data-pipeline/artifacts/stage3c-academic-geo-enrichment/stage3c-validation-result.json` | Validator-produced real result. |
| `data-pipeline/reports/stage3c-academic-geo-enrichment-report.md` | Human-readable source, coverage, calculation and risk report. |

### Modify

| Path | Responsibility |
| --- | --- |
| `data-pipeline/src/pathos_data/__main__.py` | Add strict `generate-stage3c-academic-geo-enrichment` and `validate-stage3c-academic-geo-enrichment` CLI contracts. |
| `data-pipeline/.gitignore` | Ignore `cache/stage3c-*` but retain explicitly requested Stage 3C report/artifacts. |
| `docs/database-source-policy.md` | Document official majors vs IPEDS fallback, official undergraduate fee applicability, Census region and place-source boundary. |
| `docs/database-development-log.md` | Record objective, sources, gaps, validation, risks, and Stage 3D handoff. |

No `frontend/` file, Stage 3 artifact, Stage 3B artifact, Candidate v2 artifact, migration, or Stage 3A stash is modified.

## 2. Input and Source-Manifest Contracts

### 2.1 Immutable upstream inputs

The generator receives explicit paths for:

```text
Candidate v2: data-pipeline/data/university-universe-candidates/v2-source-limited/candidate-universities.json
Stage 3:      data-pipeline/artifacts/stage3-program-mvp-detail-pack/
Stage 3B:     data-pipeline/artifacts/stage3b-demo-critical-gap-fill/
```

At generation start, calculate SHA-256 for every consumed Stage 3 and Stage 3B JSON file. Store sorted `path → sha256` input fingerprints in `stage3c-summary.json`. Recalculate after generation; any change fails. The validator recalculates the same fingerprints before deterministic comparison.

### 2.2 Source manifest input row

`data-pipeline/data/stage3c/source-manifest.json` must use:

```json
{
  "record_type": "stage3c_source_manifest",
  "sources": [{
    "source_id": "source_unc_undergraduate_catalog",
    "candidate_id": "candidate-v2:university-of-north-carolina-chapel-hill",
    "source_type": "official_institutional",
    "field_domain": "official_majors",
    "source_title": "Undergraduate Programs",
    "source_url_or_reference": "https://...",
    "publisher": "University of North Carolina at Chapel Hill",
    "accessed_date": "YYYY-MM-DD",
    "license_or_use_note": "Public official page; short direct quotes only.",
    "official_institutional": true,
    "field_level_provenance_required": true,
    "limitation_note": null
  }]
}
```

Validation requirements:

- `source_id` unique; all observation source IDs resolve exactly once.
- `official_institutional=true` only for university/college/catalog/bursar/program pages.
- `field_domain` limited to `official_majors`, `tuition_detail`, or `geography`.
- Census/IPEDS/GeoNames sources must never carry `official_institutional=true`.
- Source ingest calls `validate_source_policy_use(source, "detail", has_field_provenance=True)` before rows are accepted.

### 2.3 Official major observation input row

```json
{
  "candidate_id": "candidate-v2:university-of-north-carolina-chapel-hill",
  "major_name": "Example Undergraduate Major",
  "normalized_major_name": "Example Undergraduate Major",
  "degree_type": "BA",
  "college_or_school": "College of Arts and Sciences",
  "list_type": "official_undergraduate_majors",
  "source_id": "source_unc_undergraduate_catalog",
  "evidence_anchor": {
    "source_id": "source_unc_undergraduate_catalog",
    "evidence_type": "direct_quote",
    "quote": "Example Undergraduate Major, B.A."
  },
  "undergraduate_status": "undergraduate",
  "confidence": "high",
  "null_reason": null
}
```

Reject observations whose program/title/source context indicates `graduate`, `MBA`, `law`, `medical`, `professional`, certificate-only, course-only, or non-undergraduate status. An official academic observation must set no U.S. News category/rank field.

### 2.4 Official tuition/fee observation input row

```json
{
  "candidate_id": "candidate-v2:example",
  "academic_year": "2025-26",
  "tuition_deepening_status": "college_level_surcharge_found",
  "source_id": "source_example_bursar_2025_26",
  "evidence_anchor": {
    "source_id": "source_example_bursar_2025_26",
    "evidence_type": "direct_quote",
    "quote": "Undergraduate engineering differential tuition: $..."
  },
  "fee_observations": [{
    "fee_name": "Engineering differential tuition",
    "applies_to_college_or_school": "College of Engineering",
    "applies_to_program": null,
    "undergraduate_only": true,
    "fee_type": "college_surcharge",
    "amount": 0.0,
    "currency": "USD",
    "residency_scope": "all_undergraduate",
    "required_for_program": true,
    "calculation_notes": "Added only to programs assigned to the named college.",
    "source_id": "source_example_bursar_2025_26",
    "evidence_anchor": {
      "source_id": "source_example_bursar_2025_26",
      "evidence_type": "direct_quote",
      "quote": "..."
    }
  }],
  "extraction_notes": "No room/board, COA, graduate or professional tuition retained.",
  "confidence": "high",
  "null_reason": null
}
```

Permitted statuses: `university_level_only_confirmed`, `college_level_surcharge_found`, `program_level_extra_fee_found`, `mixed_base_plus_surcharge_found`, `official_page_found_no_program_difference`, `not_found`, `insufficient_data`. A successful row does not require a fee difference.

### 2.5 Region and town inputs

`region-classification.json` lists all 50 states and DC with exactly one of `Northeast`, `Midwest`, `South`, `West`, with `region_taxonomy=us_census_four_regions`. No subregion is emitted.

`town-source-manifest.json` declares:

- primary source: versioned U.S. Census Gazetteer Places;
- permitted candidate types: `city`, `town`, `municipality`, `incorporated_place`, `census_designated_place`;
- forbidden types: `county`, `campus`, `neighborhood`, unincorporated/ambiguous labels unless source explicitly classifies it as an allowed Census place or municipality;
- fallback GeoNames only with dataset version and attribution/license note; no SimpleMaps default input;
- caches are stored only under `data-pipeline/cache/stage3c-*`.

## 3. Generator Design

### 3.1 Module interface

Create `stage3c_academic_geo.py` with focused public functions:

```python
def build_stage3c_academic_geo(
    candidate_path: Path,
    stage3_dir: Path,
    stage3b_dir: Path,
    source_manifest_path: Path,
    major_observations_path: Path,
    tuition_observations_path: Path,
    region_mapping_path: Path,
    town_manifest_path: Path,
    town_cache: Path,
) -> dict[str, dict]:
    """Return all nine Stage 3C artifacts without writing upstream paths."""

def validate_stage3c_academic_geo(
    artifacts: dict[str, dict],
    *, candidate_path: Path, stage3_dir: Path, stage3b_dir: Path,
    source_manifest_path: Path, major_observations_path: Path,
    tuition_observations_path: Path, region_mapping_path: Path,
    town_manifest_path: Path, town_cache: Path,
) -> dict:
    """Fail closed on scope, provenance, fee, geography, mutation, and determinism errors."""

def write_stage3c_academic_geo(artifacts: dict[str, dict], output_dir: Path, validation: dict) -> None:
    """Write stable JSON only under the Stage 3C output directory."""
```

Use existing helpers only where their contracts match: Stage 3 `_candidate_rows`, `_normal`, `_amount`, and `validate_undergraduate_tuition_record`; do not modify their Stage 3 semantics.

### 3.2 Overlay construction order

1. Read 62 Candidate v2 IDs; read and hash all Stage 3/3B input files.
2. Load source manifest, controlled region map, town manifest, official major observations and tuition observations.
3. Copy Stage 3B university rows into Stage 3C memory; never mutate source dictionaries.
4. Create official-major source status for each candidate. Official list missing is a valid disclosed status; preserve IPEDS fallback only as `only_ipeds_award_areas_available`.
5. Copy Stage 3B top-five programs. For UNC, append only deduplicated official undergraduate observations until five; preserve gap reason if still below five.
6. Copy validated Stage 3B university-level tuition as base. Apply only confirmed required, undergraduate, comparable tuition fee observations.
7. Derive highest/lowest outputs by the rules in Section 4; do not derive an amount from absent data.
8. Derive Census four-region value from state mapping.
9. Read permitted town coordinates from cache, filter by allowed `place_type`, calculate/sort Haversine distances, then keep up to three.
10. Generate gap disclosure, summary, and real validator result. Recheck upstream hashes before write.

### 3.3 Flags

Every Stage 3C artifact metadata/summary must retain:

```json
{
  "source_limited": true,
  "incomplete": true,
  "not_final": true,
  "final_universe_generated": false,
  "official_selection_memberships_generated": false,
  "frontend_export_generated": false
}
```

## 4. Tuition and Highest/Lowest Algorithm

1. Build per-demo-program display candidates from Stage 3B top-five programs plus a valid Stage 3B university-level undergraduate tuition record.
2. Align `academic_year`, `residency_scope`, currency, and required applicability before comparison. For public institutions, preserve both residency rows; use declared `out_of_state_total` only when the calculation notes say so.
3. Add a college surcharge only when the program names/college mapping and official source explicitly establish the undergraduate college applicability.
4. Add a program fee only when the official source explicitly makes it a required undergraduate program-level fee.
5. Exclude `lab_or_course_fee` from highest/lowest unless `required_for_program=true` and the evidence quote says it applies to the entire undergraduate program; otherwise retain it as contextual, non-comparable detail only.
6. If at least two aligned total values differ, select deterministic maximum/minimum by amount then normalized program name. Set `program_level_only` or `college_level_or_program_level` as appropriate.
7. If all valid demo programs use the same university-level total, set both results to the deterministic first normalized program name and `university_level_same_for_all`; notes state no published comparable program difference.
8. If no valid base or incomparable inputs exist, set both null and use `not_published` or `insufficient_comparable_data` with non-empty reason.
9. Reject source metadata/text containing graduate/MBA/law/medical/professional tuition, COA, room and board, books, transportation, or personal-expense language in the used tuition component.

## 5. Region and Nearest-Place Algorithm

### 5.1 Region

- `region = region_map[state]` using only the complete controlled Census four-region file.
- `region_taxonomy = us_census_four_regions` on every row.
- Any unrecognized state fails validation. No subregion field is created.

### 5.2 Nearest places

```python
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    # Convert degrees to radians; use the standard Haversine formula.
```

For each validated campus coordinate:

1. select only permitted place candidates from Census Gazetteer primary cache;
2. reject counties, campuses, neighborhoods and unclassified labels;
3. calculate unrounded distance using campus and town coordinates;
4. sort `(distance_km_raw, normalized_town_name, state)`; deduplicate `(town_name, state)`;
5. retain up to three; then round km/miles to two decimals;
6. write exact `distance_method=haversine_straight_line`, `school_latitude`, `school_longitude`, town coordinates, source ID and `calculation_notes="Haversine straight-line distance; not driving distance."`;
7. when a retained place matches the campus city according to controlled normalized matching, add `campus_city_included=true` to notes; otherwise false; and
8. if campus coordinate/source is absent, return `nearest_towns=[]` with disclosed `campus_coordinate_unavailable_for_nearest_towns`.

Driving-distance APIs are not called or represented anywhere.

## 6. Validator Design

`validate_stage3c_academic_geo()` must perform, in this order:

1. verify all required artifact names and their metadata flags;
2. verify Candidate v2 set equality and exactly 62 rows in every per-university output;
3. verify source manifest uniqueness/resolution and source-policy guard usage for all detail ingestion paths;
4. verify upstream Stage 3/3B fingerprints are the current values and re-run after deterministic build;
5. verify official-major status semantics, anchor source IDs, allowed list types, undergraduate-only guard and IPEDS fallback naming;
6. verify demo program ranking isolation, UNC official supplement rule, 5-or-gap semantics, and no graduate program;
7. verify tuition observation forbidden-term guard, undergraduate/required applicability, academic year, amount/currency/residency, and calculation source trace;
8. verify highest/lowest selected values/bases/null rules using recomputation;
9. verify Census four-region mapping exactly, no subregion, and region source anchor;
10. verify eligible `place_type`, no county/unqualified locality, unique sorted towns, correct Haversine distance/miles, school/town coordinates and straight-line notes;
11. reject any output path that resembles final universe, official membership or frontend export;
12. compare supplied artifacts with a fresh deterministic build byte-for-byte; and
13. return/write `result=passed` only after all checks.

## 7. CLI Contract

Add exact CLI paths in `data-pipeline/src/pathos_data/__main__.py`.

### Generate

```bash
PYTHONPATH=src python3 -m pathos_data generate-stage3c-academic-geo-enrichment \
  --candidate-v2 data/university-universe-candidates/v2-source-limited/candidate-universities.json \
  --stage3-dir artifacts/stage3-program-mvp-detail-pack \
  --stage3b-dir artifacts/stage3b-demo-critical-gap-fill \
  --source-manifest data/stage3c/source-manifest.json \
  --major-observations data/stage3c/official-major-observations.json \
  --tuition-observations data/stage3c/official-tuition-fee-observations.json \
  --region-mapping data/stage3c/region-classification.json \
  --town-manifest data/stage3c/town-source-manifest.json \
  --town-cache cache/stage3c-geography \
  --output artifacts/stage3c-academic-geo-enrichment
```

### Validate formal artifact bundle

```bash
PYTHONPATH=src python3 -m pathos_data validate-stage3c-academic-geo-enrichment \
  --candidate-v2 data/university-universe-candidates/v2-source-limited/candidate-universities.json \
  --stage3-dir artifacts/stage3-program-mvp-detail-pack \
  --stage3b-dir artifacts/stage3b-demo-critical-gap-fill \
  --source-manifest data/stage3c/source-manifest.json \
  --major-observations data/stage3c/official-major-observations.json \
  --tuition-observations data/stage3c/official-tuition-fee-observations.json \
  --region-mapping data/stage3c/region-classification.json \
  --town-manifest data/stage3c/town-source-manifest.json \
  --town-cache cache/stage3c-geography \
  --universities artifacts/stage3c-academic-geo-enrichment/stage3c-universities.json \
  --official-major-sources artifacts/stage3c-academic-geo-enrichment/stage3c-official-major-sources.json \
  --official-majors artifacts/stage3c-academic-geo-enrichment/stage3c-official-majors.json \
  --demo-programs-overlay artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json \
  --tuition-deepening artifacts/stage3c-academic-geo-enrichment/stage3c-tuition-deepening.json \
  --highest-lowest-tuition artifacts/stage3c-academic-geo-enrichment/stage3c-highest-lowest-tuition.json \
  --gap-disclosure artifacts/stage3c-academic-geo-enrichment/stage3c-gap-disclosure.json \
  --summary artifacts/stage3c-academic-geo-enrichment/stage3c-summary.json \
  --result-output artifacts/stage3c-academic-geo-enrichment/stage3c-validation-result.json
```

All arguments are mandatory. The CLI fails closed rather than accepting a shortened validation path.

## 8. Task Sequence (TDD)

### Task 1: Lock immutable scope and output boundaries

**Files:** create `data-pipeline/tests/test_stage3c_academic_geo.py`; create `data-pipeline/src/pathos_data/stage3c_academic_geo.py`.

- [ ] Write a failing test that imports `build_stage3c_academic_geo`, captures pre-build SHA-256 for Stage 3/3B, and asserts exactly 62 output IDs plus unchanged input hashes.
- [ ] Run: `PYTHONPATH=src python3 -m unittest tests.test_stage3c_academic_geo.Stage3CAcademicGeoTests.test_scope_and_upstream_artifacts_are_immutable -v`; expect an import/function failure.
- [ ] Implement only input readers, hash helper, flags, and 62-ID scope check.
- [ ] Re-run the same test; expect PASS.

### Task 2: Add controlled inputs and manifest validation

**Files:** create all four `data-pipeline/data/stage3c/*.json` input files; modify Stage 3C module/tests.

- [ ] Write a failing test for duplicate source ID, non-resolving anchor, non-official major source, and non-Census region value.
- [ ] Run it and confirm each malformed fixture fails for the expected contract error.
- [ ] Add strict JSON readers/validators and controlled full state/DC region map.
- [ ] Re-run expected valid/invalid tests; expect PASS.

### Task 3: Build official-major and UNC demo-program overlay

**Files:** modify Stage 3C module/tests; populate reviewed official-major observations and source manifest rows.

- [ ] Write failing tests that official major entries remain undergraduate-only, IPEDS fallback cannot be labelled official, and UNC only resolves after two direct official undergraduate observations.
- [ ] Run the focused test; expect failure before overlay logic exists.
- [ ] Implement source-status derivation, official-major extraction and overlay append/dedupe logic with `usnews_category/usnews_rank=None` for detail observations.
- [ ] Review each UNC source manually before adding it; if two qualifying sources are unavailable, leave the gap and update its status instead of adding entries.
- [ ] Re-run focused tests; expect PASS.

### Task 4: Build tuition deepening and safe highest/lowest calculations

**Files:** modify Stage 3C module/tests; populate official tuition observation/manifest rows.

- [ ] Write failing tests for uniform university-level result, valid required college/program surcharge result, excluded course fee, graduate/COA rejection, and insufficient comparison null output.
- [ ] Run focused tests; expect expected failures before calculation logic.
- [ ] Implement tuition status derivation and component calculator using only Stage 3B validated undergraduate base tuition plus aligned official required fee observations.
- [ ] Re-run focused tests; expect PASS.

### Task 5: Build Census region and nearest-place overlay

**Files:** modify Stage 3C module/tests; populate town source manifest; use gitignored geography cache.

- [ ] Write failing tests for Census four-region-only mapping, county rejection, deterministic Haversine ordering, campus-city flag, and coordinate-gap disclosure.
- [ ] Run focused tests; expect failure before geography helpers.
- [ ] Download/read an approved Census Gazetteer cache to `cache/stage3c-geography/`; do not stage it. Implement place filter, Haversine formula and sorted top-three output.
- [ ] Re-run focused tests; expect PASS.

### Task 6: Add writer, full validator, CLI, artifacts and report

**Files:** modify `__main__.py`, `.gitignore`, policy/log docs; create all nine artifacts and report; modify tests.

- [ ] Write failing tests that formal validation omits an artifact, accepts an altered result, has a frontend path, or does not call source policy guard.
- [ ] Run focused tests; expect failure before full validator/CLI.
- [ ] Implement stable JSON writer, complete validator, both strict CLIs, report/summary generation, cache ignore and source-policy/document updates.
- [ ] Generate artifacts only under `artifacts/stage3c-academic-geo-enrichment/`.
- [ ] Run focused tests; expect PASS.

### Task 7: Verify, audit scope, and commit

**Files:** all approved Stage 3C paths only.

- [ ] Run full Python tests:

```bash
cd data-pipeline
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

- [ ] Run Stage 3C formal validation using the complete command in Section 7.
- [ ] Re-run existing Stage 3B validator, Stage 3 validator, Candidate v2 validator/corpus validation/ranking discovery validation, fixture/schema/migration validation, and `git diff --check`.
- [ ] Verify no `frontend/`, cache, Stage 3, Stage 3B or Candidate v2 input path appears in `git diff --name-only`.
- [ ] Explicitly stage only reviewed Stage 3C source/data/artifact/report/module/test/doc files; do not use `git add .`.
- [ ] Inspect `git diff --cached --stat`, `git diff --cached`, and `git diff --cached --check` before commit.
- [ ] Commit once with `feat(data): deepen official program and tuition data` only after all validation passes and `git status --short` is clean afterward.

## 9. Cache and Ignored-File Strategy

- Add `.gitignore` entries for `data-pipeline/cache/stage3c-geography/` and any direct downloaded source cache under `data-pipeline/cache/stage3c-*`.
- Cache input names, versions, checksum (when available), source URL and access date belong in source/town manifests and report, not in staged binary files.
- Assert with `git check-ignore -v` that all cache files are ignored before staging.
- If a cache cannot be legally or reliably reused, do not generate town observations from it; disclose the gap instead.
- Do not add full HTML/PDF snapshots, downloaded table dumps, or browser profiles to the repository.

## 10. Acceptance Criteria

Implementation is complete only when all criteria below are evidenced by formal output:

1. Stage 3C output scope is exactly Candidate v2’s 62 IDs.
2. Stage 3 and Stage 3B input hashes are unchanged before/after generation.
3. All nine Stage 3C artifacts exist and formal validation is real/passed.
4. Official major rows are undergraduate-only; IPEDS fallback status is honest and lack of official major page does not block the stage.
5. UNC either reaches five with two official undergraduate program observations or keeps a precise gap reason.
6. Tuition rows use only official undergraduate scope; differentiated fee discovery is optional, while `university_level_only_confirmed`, `insufficient_data`, and `not_found` are accepted honest outcomes.
7. Highest/lowest results are derived only from comparable required components or use uniform/insufficient/not-published basis correctly.
8. All 62 regions use exactly Census `Northeast`, `Midwest`, `South`, or `West`; no subregion is present.
9. Nearest places are cities/towns/municipalities/incorporated places/CDPs only, never counties; every distance is `haversine_straight_line` with campus/town coordinates and notes, or a disclosed gap.
10. `source_policy_violations = 0`, `ranking_field_contamination = 0`, and all final-output flags remain false.
11. All Python tests, full Stage 3C validation, inherited validations and `git diff --check` pass.
12. No frontend change, cache file, final universe, official membership, frontend export, or Stage 3A stash restoration occurs; final git status is clean.

## 11. Commit Message

After the acceptance criteria pass, create exactly one Stage 3C implementation commit:

```text
feat(data): deepen official program and tuition data
```

Do not tag, push, merge, or rebase unless a later explicit user request authorizes it.
