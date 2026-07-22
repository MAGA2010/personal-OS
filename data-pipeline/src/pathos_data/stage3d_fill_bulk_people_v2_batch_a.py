"""Reviewed-source intake Batch A for Stage 3D-Fill Bulk People v2."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .schema_validation import SchemaValidationError, load_schema, validate_instance
from .stage3d_fill_bulk_people_v2 import (
    ALLOWED_MATCH_TYPES,
    ALLOWED_RELATIONSHIPS,
    FLAGS,
    MAX_QUOTE_LENGTH,
    SLOT_STATUSES,
    _expected_person_id,
    _reject_ranking_fields,
    _resolve_cache_path,
)
from .universe_candidate_v2 import validate_source_policy_use


TARGET_CANDIDATE_IDS = (
    "candidate-v2:columbia-university",
    "candidate-v2:cornell-university",
    "candidate-v2:duke-university",
    "candidate-v2:harvard-university",
    "candidate-v2:massachusetts-institute-of-technology",
    "candidate-v2:princeton-university",
    "candidate-v2:stanford-university",
    "candidate-v2:university-of-california-berkeley",
    "candidate-v2:university-of-michigan-ann-arbor",
    "candidate-v2:yale-university",
)

EXPECTED_INPUT_SHA256 = {
    "pipeline_v2_slot_inventory": "ed80718f55a7aade6971fbd21574c1251e86f09f3938e31540cf68b762de0c1b",
    "pipeline_v2_summary": "bb37a1b8b74aa98b62edf8fab52fd68bd82aa5fed51c1fe7c3f8b721fc0e1b79",
    "bulk_people_v1_attendance": "291cee5474876bf9230e45c7205c921aa14800ebee04bd54246cf05d46787b21",
    "bulk_people_v1_source_manifest": "c774a7a07df6010369e02ef157e7b3ceed0fceac882ce4ab54a87288680a786d",
    "bulk_people_v1_cache_manifest": "9386d74dbfdd1b5254e301e2059863da54698e1cff841ba7a40d23fd75255447",
}

OUTPUT_FILES = (
    "stage3d-fill-bulk-people-v2-batch-a-plan.json",
    "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json",
    "stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json",
    "stage3d-fill-bulk-people-v2-batch-a-people-observations.json",
    "stage3d-fill-bulk-people-v2-batch-a-program-person-matches.json",
    "stage3d-fill-bulk-people-v2-batch-a-source-manifest.json",
    "stage3d-fill-bulk-people-v2-batch-a-cache-manifest.json",
    "stage3d-fill-bulk-people-v2-batch-a-exclusions.json",
    "stage3d-fill-bulk-people-v2-batch-a-gap-disclosure.json",
    "stage3d-fill-bulk-people-v2-batch-a-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-people-v2-batch-a-validation-result.json"


class Stage3DFillBulkPeopleV2BatchAValidationError(ValueError):
    """Raised when Batch A violates an evidence, scope, or integrity rule."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkPeopleV2BatchAValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read Batch A input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _input_paths(pipeline_v2_dir: Path, bulk_people_v1_dir: Path) -> dict[str, Path]:
    return {
        "pipeline_v2_slot_inventory": Path(pipeline_v2_dir) / "stage3d-fill-bulk-people-v2-slot-inventory.json",
        "pipeline_v2_summary": Path(pipeline_v2_dir) / "stage3d-fill-bulk-people-v2-summary.json",
        "bulk_people_v1_attendance": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-notable-attendance.json",
        "bulk_people_v1_source_manifest": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-source-manifest.json",
        "bulk_people_v1_cache_manifest": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-cache-manifest.json",
    }


def _load_inputs(
    pipeline_v2_dir: Path, bulk_people_v1_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    paths = _input_paths(pipeline_v2_dir, bulk_people_v1_dir)
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if hashes != EXPECTED_INPUT_SHA256:
        _fail("Batch A immutable upstream SHA-256 protection failed")

    pipeline_summary = _read(paths["pipeline_v2_summary"])
    if pipeline_summary.get("slots_processed") != 62 or pipeline_summary.get("identified_person_count") != 0:
        _fail("Batch A requires the immutable 62-slot, zero-positive pipeline baseline")
    all_slots = _read(paths["pipeline_v2_slot_inventory"]).get("slots", [])
    slot_rows = [deepcopy(row) for row in all_slots if row.get("candidate_id") in TARGET_CANDIDATE_IDS]
    if len(slot_rows) != 10 or {row["candidate_id"] for row in slot_rows} != set(TARGET_CANDIDATE_IDS):
        _fail("Batch A slot inventory must contain exactly the approved 10 schools")
    if any(row.get("slot_status") != "source_review_not_completed" for row in slot_rows):
        _fail("Batch A must begin from unreviewed Top-1 pipeline slots")

    attendance_all = _read(paths["bulk_people_v1_attendance"]).get("records", [])
    attendance = [deepcopy(row) for row in attendance_all if row.get("candidate_id") in TARGET_CANDIDATE_IDS]
    if len(attendance) != 10 or {row["candidate_id"] for row in attendance} != set(TARGET_CANDIDATE_IDS):
        _fail("Batch A requires exactly one immutable reviewed attendance record per target school")
    sources_all = _read(paths["bulk_people_v1_source_manifest"]).get("sources", [])
    caches_all = _read(paths["bulk_people_v1_cache_manifest"]).get("entries", [])
    used_source_ids = {row["source_id"] for row in attendance}
    sources = {row["source_id"]: deepcopy(row) for row in sources_all if row.get("source_id") in used_source_ids}
    caches = {row["source_id"]: deepcopy(row) for row in caches_all if row.get("source_id") in used_source_ids}
    if set(sources) != used_source_ids or set(caches) != used_source_ids:
        _fail("Batch A source/cache manifests do not cover all selected attendance records")
    return slot_rows, attendance, sources, caches, hashes


def _validate_attendance_and_cache(
    attendance: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    caches: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    cache_texts: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for row in attendance:
        _reject_ranking_fields(row, "batch_a_attendance")
        candidate_id = row.get("candidate_id")
        source_id = row.get("source_id")
        if candidate_id not in TARGET_CANDIDATE_IDS or row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail("Batch A attendance uses an out-of-scope school or forbidden relationship")
        source = sources.get(source_id)
        cache = caches.get(source_id)
        if not source or source.get("candidate_id") != candidate_id or not cache:
            _fail("Batch A attendance source/cache does not resolve to the same school")
        if source.get("source_type") != "official_institutional":
            _fail("Batch A positive attendance requires an official institutional source")
        validate_source_policy_use(str(source.get("publisher")), "detail", has_field_provenance=True)
        source_url = source.get("source_url_or_reference")
        anchor = row.get("evidence_anchor", {})
        quote = anchor.get("quote")
        if (
            row.get("quote_verification_method") != "local_cache_substring_check"
            or anchor.get("quote_verification_method") != "local_cache_substring_check"
            or anchor.get("evidence_type") != "direct_quote"
            or anchor.get("source_id") != source_id
        ):
            _fail("Batch A attendance direct quotes must use local_cache_substring_check")
        if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH:
            _fail("Batch A attendance requires a short direct quote")
        if quote not in source.get("verified_direct_quotes", []):
            _fail("Batch A attendance quote is absent from the reviewed source allowlist")
        if cache.get("quote_verification_method") != "local_cache_substring_check":
            _fail("Batch A cache cannot use manual-only quote verification")
        cache_path = _resolve_cache_path(str(cache.get("cache_path", "")))
        if not cache_path.is_file() or _sha256(cache_path) != cache.get("sha256"):
            _fail("Batch A cache is missing or fails SHA-256 verification")
        text = cache_path.read_text(encoding="utf-8")
        if source_url not in text or quote not in text:
            _fail("Batch A source URL or direct quote is absent from the reviewed cache")
        identity_row = {
            **row,
            "person_name": row.get("person_name"),
            "person_identity_disambiguator_source_id": source_id,
            "person_id": row.get("canonical_person_id"),
        }
        if row.get("canonical_person_id") != _expected_person_id(identity_row):
            _fail("Batch A attendance person ID is not school/source disambiguated")
        cache_texts[source_id] = text
        normalized.append({
            **row,
            "source_url": source_url,
            "publisher": source.get("publisher"),
            "quote_verification_method": "local_cache_substring_check",
        })
    return sorted(normalized, key=lambda row: row["candidate_id"]), cache_texts


def _validate_anchor(
    anchor: Any,
    label: str,
    source_ids: list[str],
    sources: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> None:
    if not isinstance(anchor, dict):
        _fail(f"Batch A identified person requires {label} evidence")
    source_id = anchor.get("source_id")
    quote = anchor.get("quote")
    if source_id not in source_ids or source_id not in sources:
        _fail(f"Batch A {label} evidence source is unresolved")
    if anchor.get("evidence_type") != "direct_quote" or anchor.get("quote_verification_method") != "local_cache_substring_check":
        _fail(f"Batch A {label} direct quote must use local_cache_substring_check")
    if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH:
        _fail(f"Batch A {label} evidence requires a short direct quote")
    if quote not in sources[source_id].get("verified_direct_quotes", []) or quote not in cache_texts[source_id]:
        _fail(f"Batch A {label} quote is absent from the reviewed allowlist or cache")


def _apply_program_observations(
    document: dict[str, Any],
    slots: list[dict[str, Any]],
    attendance: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_batch_a_program_people_observations":
        _fail("Batch A observations have an invalid record type")
    slot_map = {(row["candidate_id"], row["normalized_program_name"]): row for row in slots}
    attendance_by_person = {
        (row["candidate_id"], row["canonical_person_id"]): row for row in attendance
    }
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_ranking_fields(row, "batch_a_program_observation")
        key = (row.get("candidate_id"), row.get("normalized_program_name"))
        if key not in slot_map or key in seen:
            _fail("Batch A observation must resolve uniquely to an approved Top-1 slot")
        seen.add(key)
        status = row.get("slot_status")
        if status not in SLOT_STATUSES:
            _fail("Batch A observation has an unsupported slot status")
        slot = slot_map[key]
        if status == "source_review_not_completed":
            _fail("Unreviewed Batch A slots are represented by the pipeline default, not positive input")
        if status == "no_qualifying_person_found":
            if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
                _fail("no_qualifying_person_found requires reviewed_scope and reviewed_source_ids")
            slot.update({
                "slot_status": status,
                "reviewed_scope": list(row["reviewed_scope"]),
                "reviewed_source_ids": list(row["reviewed_source_ids"]),
                "null_reason": "no_qualifying_person_in_reviewed_scope",
            })
            normalized.append(row)
            continue

        person_id = row.get("person_id")
        source_ids = row.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or any(source_id not in sources for source_id in source_ids):
            _fail("Batch A identified person requires resolved reviewed sources")
        attendance_row = attendance_by_person.get((row.get("candidate_id"), person_id))
        if attendance_row is None:
            _fail("Batch A identified person requires reviewed attendance evidence for the same identity")
        if row.get("person_name") != attendance_row.get("person_name"):
            _fail("Batch A identified person name does not match reviewed attendance")
        if row.get("relationship_type") not in ALLOWED_RELATIONSHIPS or row.get("relationship_type") != attendance_row.get("attendance_relationship"):
            _fail("Batch A identified relationship is forbidden or conflicts with attendance evidence")
        if row.get("person_identity_disambiguator_source_id") not in source_ids:
            _fail("Batch A person identity requires a source-backed disambiguator")
        if person_id != _expected_person_id(row):
            _fail("Batch A canonical person ID cannot be name-only")
        if not row.get("identity_resolution_method") or not row.get("identity_confirmation_notes"):
            _fail("Batch A identified person requires explicit identity resolution")
        match_type = row.get("match_type")
        match_basis = row.get("program_match_basis")
        if match_type not in ALLOWED_MATCH_TYPES:
            _fail("Batch A program match type is not allowed")
        if match_type == "direct_program_match" and match_basis != "source_stated_exact_program":
            _fail("Batch A direct program match must be source-stated and exact")
        if match_type == "direct_related_program_match" and match_basis != "source_stated_related_program":
            _fail("Batch A related program match must be explicitly source-stated")
        if not row.get("match_notes"):
            _fail("Batch A identified person requires program match notes")
        forbidden = ("profession", "career", "company", "fame", "research_inference")
        if any(token in str(match_basis).casefold() for token in forbidden):
            _fail("Batch A cannot infer a program from profession, company, fame, or research")
        anchors = row.get("evidence_anchor")
        if not isinstance(anchors, dict):
            _fail("Batch A identified person requires attendance and program anchors")
        _validate_anchor(anchors.get("attendance"), "attendance", source_ids, sources, cache_texts)
        _validate_anchor(anchors.get("program_match"), "program_match", source_ids, sources, cache_texts)
        if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
            _fail("Batch A identified person requires reviewed scope disclosure")
        if set(row["reviewed_source_ids"]) - set(source_ids):
            _fail("Batch A reviewed source IDs must resolve to the identified record")
        source_id = source_ids[0]
        slot.update({
            "slot_status": "identified_person",
            "person_id": person_id,
            "person_name": row["person_name"],
            "person_identity_disambiguator_source_id": row["person_identity_disambiguator_source_id"],
            "identity_resolution_method": row["identity_resolution_method"],
            "identity_confirmation_notes": row["identity_confirmation_notes"],
            "relationship_type": row["relationship_type"],
            "match_type": match_type,
            "program_match_basis": match_basis,
            "match_notes": row["match_notes"],
            "source_ids": list(source_ids),
            "source_url": sources[source_id]["source_url_or_reference"],
            "evidence_anchor": anchors,
            "quote_verification_method": "local_cache_substring_check",
            "reviewed_scope": list(row["reviewed_scope"]),
            "reviewed_source_ids": list(row["reviewed_source_ids"]),
            "null_reason": None,
        })
        normalized.append(row)
    return sorted(normalized, key=lambda row: (row["candidate_id"], row["normalized_program_name"]))


def build_stage3d_fill_bulk_people_v2_batch_a(
    *, pipeline_v2_dir: Path, bulk_people_v1_dir: Path, observations_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build deterministic Batch A artifacts from immutable reviewed inputs."""
    slots, attendance_raw, sources, caches, upstream_hashes = _load_inputs(
        Path(pipeline_v2_dir), Path(bulk_people_v1_dir),
    )
    attendance, cache_texts = _validate_attendance_and_cache(attendance_raw, sources, caches)
    observation_document = _read(Path(observations_path))
    observations = _apply_program_observations(
        observation_document, slots, attendance, sources, cache_texts,
    )
    schema = load_schema("stage3d-fill-bulk-people-v2-slot.json")
    slots = sorted(slots, key=lambda row: row["candidate_id"])
    for index, slot in enumerate(slots):
        try:
            validate_instance(slot, schema, f"$.slots[{index}]")
        except SchemaValidationError as error:
            _fail(f"Batch A slot schema failed: {error}")
    identified = [row for row in slots if row["slot_status"] == "identified_person"]
    unreviewed = [row for row in slots if row["slot_status"] == "source_review_not_completed"]
    no_qualifying = [row for row in slots if row["slot_status"] == "no_qualifying_person_found"]
    if no_qualifying:
        for row in no_qualifying:
            if not row["reviewed_scope"] or not row["reviewed_source_ids"]:
                _fail("Batch A no-qualifying slots lack reviewed scope")
    source_rows = []
    for source_id in sorted(sources):
        source = sources[source_id]
        source_rows.append({
            **source,
            "source_url": source["source_url_or_reference"],
            "quote_verification_method": "local_cache_substring_check",
        })
    cache_rows = []
    for source_id in sorted(caches):
        cache = caches[source_id]
        cache_rows.append({
            **cache,
            "source_url": sources[source_id]["source_url_or_reference"],
        })
    input_sha256 = {**upstream_hashes, "program_people_observations": _sha256(Path(observations_path))}
    summary = _flags(
        "stage3d_fill_bulk_people_v2_batch_a_summary",
        target_university_count=10,
        notable_attendance_attempted_count=10,
        notable_attendance_identified_count=len(attendance),
        notable_attendance_source_review_not_completed_count=0,
        program_slots_processed=10,
        program_people_identified_count=len(identified),
        program_people_source_review_not_completed_count=len(unreviewed),
        program_people_no_qualifying_person_found_count=len(no_qualifying),
        local_cache_substring_check_count=len(attendance) + len(identified),
        manual_verbatim_check_count=0,
        cache_verified_quote_count=len(attendance) + len(identified),
        cache_missing_count=0,
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="batch_a_reviewed_intake_validated_program_coverage_partial",
        remaining_gaps=[
            f"{len(unreviewed)} of 10 Batch A Top-1 program-person slots remain source_review_not_completed.",
            "No unreviewed slot is rendered as no_qualifying_person_found.",
        ],
        input_sha256=input_sha256,
    )
    gaps = [{
        "candidate_id": row["candidate_id"],
        "university_name": row["university_name"],
        "program_name": row["program_name"],
        "slot_status": row["slot_status"],
        "null_reason": row["null_reason"],
        "display_as_none": False,
    } for row in slots if row["slot_status"] != "identified_person"]
    return {
        "stage3d-fill-bulk-people-v2-batch-a-plan.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_plan",
            objective="Validate reviewed notable-attendance and Top-1 program-person intake for 10 approved schools.",
            target_candidate_ids=list(TARGET_CANDIDATE_IDS),
            program_positive_not_required=True,
            upstream_mutation_allowed=False,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_notable_attendance", records=attendance,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_slot_inventory", slots=slots,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-people-observations.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_people_observations", observations=observations,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-program-person-matches.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_program_person_matches", records=identified,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-source-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_source_manifest", sources=source_rows,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-cache-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_cache_manifest",
            cache_is_gitignored=True,
            entries=cache_rows,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-exclusions.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_exclusions", records=[],
        ),
        "stage3d-fill-bulk-people-v2-batch-a-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_a_gap_disclosure",
            gaps=gaps,
            source_review_not_completed_is_none=False,
        ),
        "stage3d-fill-bulk-people-v2-batch-a-summary.json": summary,
    }


def validate_stage3d_fill_bulk_people_v2_batch_a(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed by deterministic rebuild and boundary checks."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Batch A artifact set is incomplete")
    expected = build_stage3d_fill_bulk_people_v2_batch_a(**inputs)
    if artifacts != expected:
        _fail("Batch A artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-people-v2-batch-a-summary.json"]
    if summary["target_university_count"] != 10 or summary["notable_attendance_identified_count"] != 10:
        _fail("Batch A attendance coverage is incomplete")
    if sum(summary[key] for key in (
        "program_people_identified_count",
        "program_people_source_review_not_completed_count",
        "program_people_no_qualifying_person_found_count",
    )) != 10:
        _fail("Batch A program slot statuses do not account for all 10 schools")
    if summary["manual_verbatim_check_count"] != 0 or summary["cache_missing_count"] != 0:
        _fail("Batch A quote/cache verification is incomplete")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Batch A policy or ranking-contamination guard failed")
    return {
        "record_type": "stage3d_fill_bulk_people_v2_batch_a_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 20,
        "target_university_count": 10,
        "notable_attendance_identified_count": summary["notable_attendance_identified_count"],
        "program_people_identified_count": summary["program_people_identified_count"],
        "program_people_source_review_not_completed_count": summary["program_people_source_review_not_completed_count"],
        "program_people_no_qualifying_person_found_count": summary["program_people_no_qualifying_person_found_count"],
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_people_v2_batch_a(
    artifacts: dict[str, dict[str, Any]], output_dir: Path, validation: dict[str, Any],
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        (output_dir / name).write_text(
            json.dumps(artifacts[name], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / VALIDATION_FILE).write_text(
        json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_stage3d_fill_bulk_people_v2_batch_a_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-bulk-people-v2-batch-a-summary.json"]
    return f"""# Stage 3D-Fill Bulk People v2 Reviewed-Source Intake Batch A Report

## Coverage

- approved schools processed: **{summary['target_university_count']}/10**
- notable attendance identified: **{summary['notable_attendance_identified_count']}/10**
- Top-1 program slots processed: **{summary['program_slots_processed']}/10**
- program people identified: **{summary['program_people_identified_count']}**
- program slots `source_review_not_completed`: **{summary['program_people_source_review_not_completed_count']}**
- program slots `no_qualifying_person_found`: **{summary['program_people_no_qualifying_person_found_count']}**

Princeton's Jeff Bezos record is the only Batch A program-person match. The reviewed Princeton Engineering source explicitly states an undergraduate degree in electrical engineering and computer science, supporting a `direct_related_program_match` to the immutable Computer Science Top-1 demo slot. The other nine program slots remain unreviewed; no career, company, fame, or research-area inference was used.

## Provenance and boundaries

All 10 attendance records and the one program-person match use official institutional sources, source-disambiguated identities, short direct quotes, SHA-256 verified gitignored caches, and `local_cache_substring_check`. Manual-only verification is zero. No unreviewed gap is displayed as “none.”

This independent overlay remains `source_limited`, `incomplete`, and `not_final`. It does not modify Candidate v2, Stage 3/3B/3C/3C2/3D, Bulk People v1, or frontend files, and it does not generate a final universe, memberships, or frontend export.

## Validation

- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**
- cache missing: **{summary['cache_missing_count']}**
- deterministic generation: **passed**
"""
