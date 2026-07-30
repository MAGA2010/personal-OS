"""Reviewed-source intake Batch B for Stage 3D-Fill Bulk People v2."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .schema_validation import SchemaValidationError, load_schema, validate_instance
from .stage3d_fill_bulk_people_v2 import (
    ALLOWED_MATCH_TYPES,
    ALLOWED_RELATIONSHIPS,
    FLAGS,
    MAX_NOTES_LENGTH,
    MAX_QUOTE_LENGTH,
    SLOT_STATUSES,
    _expected_person_id,
    _reject_ranking_fields,
    _resolve_cache_path,
)
from .universe_candidate_v2 import validate_source_policy_use


EXPECTED_INPUT_SHA256 = {
    "candidate_v2": "8f940aa6d336402ff9c3c76a43d2efacdf2c887dc983afeb344937db9eadb18d",
    "pipeline_v2_slot_inventory": "ed80718f55a7aade6971fbd21574c1251e86f09f3938e31540cf68b762de0c1b",
    "pipeline_v2_summary": "bb37a1b8b74aa98b62edf8fab52fd68bd82aa5fed51c1fe7c3f8b721fc0e1b79",
    "bulk_people_v1_attendance": "291cee5474876bf9230e45c7205c921aa14800ebee04bd54246cf05d46787b21",
    "bulk_people_v1_source_manifest": "c774a7a07df6010369e02ef157e7b3ceed0fceac882ce4ab54a87288680a786d",
    "bulk_people_v1_cache_manifest": "9386d74dbfdd1b5254e301e2059863da54698e1cff841ba7a40d23fd75255447",
    "batch_a_attendance": "2171eefc72ee6cf2ccf755678d85925505417e3eec87e938cd01c5358e6c40c1",
    "batch_a_slots": "ed167081cc653a833c742eec17988ccf20a45b2b26e570e252fb8f55ae3ed97c",
    "batch_a_summary": "e9b24febac392ed5ab74beb0309f211d8cfa7d41e82ce7ffcf15b722cc862a57",
}

OUTPUT_FILES = (
    "stage3d-fill-bulk-people-v2-batch-b-plan.json",
    "stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json",
    "stage3d-fill-bulk-people-v2-batch-b-program-people.json",
    "stage3d-fill-bulk-people-v2-batch-b-exclusions.json",
    "stage3d-fill-bulk-people-v2-batch-b-source-manifest.json",
    "stage3d-fill-bulk-people-v2-batch-b-cache-manifest.json",
    "stage3d-fill-bulk-people-v2-batch-b-gap-disclosure.json",
    "stage3d-fill-bulk-people-v2-batch-b-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-people-v2-batch-b-validation-result.json"
ALLOWED_EXCLUSIONS = {
    "faculty_only",
    "donor_only",
    "honorary_degree_only",
    "visitor_only",
    "speaker_only",
    "unclear",
    "same_name_unresolved",
    "campus_mismatch",
    "source_insufficient",
    "program_match_insufficient",
    "profession_inference_rejected",
}


class Stage3DFillBulkPeopleV2BatchBValidationError(ValueError):
    """Raised when Batch B violates a scope, evidence, or integrity rule."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkPeopleV2BatchBValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read Batch B input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _input_paths(
    candidate_path: Path,
    pipeline_v2_dir: Path,
    bulk_people_v1_dir: Path,
    batch_a_dir: Path,
) -> dict[str, Path]:
    return {
        "candidate_v2": Path(candidate_path),
        "pipeline_v2_slot_inventory": Path(pipeline_v2_dir) / "stage3d-fill-bulk-people-v2-slot-inventory.json",
        "pipeline_v2_summary": Path(pipeline_v2_dir) / "stage3d-fill-bulk-people-v2-summary.json",
        "bulk_people_v1_attendance": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-notable-attendance.json",
        "bulk_people_v1_source_manifest": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-source-manifest.json",
        "bulk_people_v1_cache_manifest": Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-cache-manifest.json",
        "batch_a_attendance": Path(batch_a_dir) / "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json",
        "batch_a_slots": Path(batch_a_dir) / "stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json",
        "batch_a_summary": Path(batch_a_dir) / "stage3d-fill-bulk-people-v2-batch-a-summary.json",
    }


def _candidate_scope(candidate_path: Path) -> dict[str, dict[str, Any]]:
    rows = _read(candidate_path).get("universities", [])
    candidates = {row.get("candidate_university_id"): row for row in rows}
    if len(rows) != 62 or len(candidates) != 62 or None in candidates:
        _fail("Batch B requires the immutable 62-school Candidate v2 scope")
    return candidates


def _school_scope(
    manifest_path: Path, candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    document = _read(manifest_path)
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_batch_b_school_manifest":
        _fail("Batch B school manifest has an invalid record type")
    rows = document.get("schools", [])
    ids = {row.get("candidate_id") for row in rows}
    if len(rows) != 20 or len(ids) != 20 or None in ids:
        _fail("Batch B school manifest must contain exactly 20 distinct schools")
    if not ids <= set(candidates):
        _fail("Batch B school manifest contains a school outside Candidate v2")
    if "candidate-v2:virginia-tech" in ids:
        _fail("Virginia Tech is outside Candidate v2 and cannot enter Batch B")
    if "candidate-v2:texas-a-and-m-university" not in ids:
        _fail("Texas A&M University must replace Virginia Tech in Batch B")
    for row in rows:
        candidate = candidates[row["candidate_id"]]
        expected = (candidate["canonical_university_id"], candidate["display_name"])
        actual = (row.get("canonical_id"), row.get("university_display_name"))
        if actual != expected:
            _fail("Batch B manifest identity must exactly match Candidate v2")
    return sorted(deepcopy(rows), key=lambda row: row["candidate_id"]), ids


def _source_url(source: dict[str, Any]) -> str | None:
    return source.get("source_url") or source.get("source_url_or_reference")


def _load_source_rows(document: dict[str, Any], expected_record_types: set[str]) -> dict[str, dict[str, Any]]:
    if document.get("record_type") not in expected_record_types:
        _fail("Batch B source manifest has an invalid record type")
    result: dict[str, dict[str, Any]] = {}
    for row in document.get("sources", []):
        source_id = row.get("source_id")
        if not source_id or source_id in result:
            _fail("Batch B source IDs must be present and unique")
        result[source_id] = deepcopy(row)
    return result


def _load_cache_rows(document: dict[str, Any], expected_record_types: set[str]) -> dict[str, dict[str, Any]]:
    if document.get("record_type") not in expected_record_types or document.get("cache_is_gitignored") is not True:
        _fail("Batch B cache manifest must declare a gitignored reviewed cache")
    result: dict[str, dict[str, Any]] = {}
    for row in document.get("entries", []):
        source_id = row.get("source_id")
        if not source_id or source_id in result:
            _fail("Batch B cache source IDs must be present and unique")
        result[source_id] = deepcopy(row)
    return result


def _validate_source_cache(
    source: dict[str, Any], cache: dict[str, Any], candidate_ids: set[str],
) -> str:
    _reject_ranking_fields(source, "batch_b_source")
    source_id = source.get("source_id")
    source_url = _source_url(source)
    quotes = source.get("verified_direct_quotes")
    if source.get("candidate_id") not in candidate_ids:
        _fail("Batch B source resolves outside the approved 20-school scope")
    if source.get("source_type") != "official_institutional":
        _fail("Batch B positive facts require official institutional sources")
    if not source_url or not source.get("publisher") or not isinstance(quotes, list) or not quotes:
        _fail("Batch B reviewed source metadata is incomplete")
    if any(not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH for quote in quotes):
        _fail("Batch B direct quotes must be short and non-empty")
    validate_source_policy_use(str(source["publisher"]), "detail", has_field_provenance=True)
    if cache.get("source_id") != source_id or cache.get("quote_verification_method") != "local_cache_substring_check":
        _fail("Batch B source cache cannot use manual-only verification")
    cache_url = cache.get("source_url") or cache.get("source_url_or_reference")
    if cache_url != source_url:
        _fail("Batch B cache URL must match the reviewed source")
    cache_path = _resolve_cache_path(str(cache.get("cache_path", "")))
    if not cache_path.is_file() or _sha256(cache_path) != cache.get("sha256"):
        _fail("Batch B source cache is missing or fails SHA-256 verification")
    text = cache_path.read_text(encoding="utf-8")
    if source_url not in text or any(quote not in text for quote in quotes):
        _fail("Batch B source URL or reviewed quote is absent from the local cache")
    return text


def _validate_attendance(
    rows: list[dict[str, Any]],
    candidate_ids: set[str],
    sources: dict[str, dict[str, Any]],
    caches: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    selected = [deepcopy(row) for row in rows if row.get("candidate_id") in candidate_ids]
    if len(selected) != 20 or {row["candidate_id"] for row in selected} != candidate_ids:
        _fail("Batch B requires exactly one reviewed attendance record per approved school")
    normalized: list[dict[str, Any]] = []
    for row in selected:
        _reject_ranking_fields(row, "batch_b_attendance")
        source_id = row.get("source_id")
        source = sources.get(source_id)
        cache = caches.get(source_id)
        if not source or not cache or source.get("candidate_id") != row.get("candidate_id"):
            _fail("Batch B attendance source/cache does not resolve to the same school")
        anchor = row.get("evidence_anchor", {})
        quote = anchor.get("quote")
        if row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail("Batch B positive attendance uses a forbidden relationship")
        if (
            row.get("quote_verification_method") != "local_cache_substring_check"
            or anchor.get("quote_verification_method") != "local_cache_substring_check"
            or anchor.get("evidence_type") != "direct_quote"
            or anchor.get("source_id") != source_id
        ):
            _fail("Batch B attendance must use local_cache_substring_check")
        if quote not in source.get("verified_direct_quotes", []) or quote not in cache_texts[source_id]:
            _fail("Batch B attendance quote is absent from the source allowlist or cache")
        identity = {
            **row,
            "person_name": row.get("person_name"),
            "person_id": row.get("canonical_person_id"),
            "person_identity_disambiguator_source_id": source_id,
        }
        if row.get("canonical_person_id") != _expected_person_id(identity):
            _fail("Batch B attendance person ID is not school/source disambiguated")
        normalized.append({
            **row,
            "source_url": _source_url(source),
            "publisher": source["publisher"],
            "quote_verification_method": "local_cache_substring_check",
        })
    return sorted(normalized, key=lambda row: row["candidate_id"])


def _validate_anchor(
    anchor: Any,
    label: str,
    source_ids: list[str],
    sources: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> None:
    if not isinstance(anchor, dict):
        _fail(f"Batch B identified person requires {label} evidence")
    source_id = anchor.get("source_id")
    quote = anchor.get("quote")
    if source_id not in source_ids or source_id not in sources:
        _fail(f"Batch B {label} source is unresolved")
    if anchor.get("evidence_type") != "direct_quote" or anchor.get("quote_verification_method") != "local_cache_substring_check":
        _fail(f"Batch B {label} evidence must use local_cache_substring_check")
    if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH:
        _fail(f"Batch B {label} evidence requires a short direct quote")
    if quote not in sources[source_id].get("verified_direct_quotes", []) or quote not in cache_texts[source_id]:
        _fail(f"Batch B {label} quote is absent from the reviewed source or cache")


def _apply_program_observations(
    document: dict[str, Any],
    slots: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_batch_b_program_people_observations":
        _fail("Batch B program observations have an invalid record type")
    slot_map = {(row["candidate_id"], row["normalized_program_name"]): row for row in slots}
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_ranking_fields(row, "batch_b_program_observation")
        key = (row.get("candidate_id"), row.get("normalized_program_name"))
        if key not in slot_map or key in seen:
            _fail("Batch B observation must resolve uniquely to an approved Top-1 slot")
        seen.add(key)
        slot = slot_map[key]
        status = row.get("slot_status")
        if status not in SLOT_STATUSES or status == "source_review_not_completed":
            _fail("Batch B positive input has an unsupported slot status")
        if status == "no_qualifying_person_found":
            if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
                _fail("no_qualifying_person_found requires reviewed_scope and reviewed_source_ids")
            slot.update({
                "slot_status": status,
                "reviewed_scope": list(row["reviewed_scope"]),
                "reviewed_source_ids": list(row["reviewed_source_ids"]),
                "null_reason": "no_qualifying_person_in_reviewed_scope",
            })
            observations.append(row)
            continue
        source_ids = row.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or any(source_id not in sources for source_id in source_ids):
            _fail("Batch B identified person requires resolved reviewed sources")
        if row.get("relationship_type") not in ALLOWED_RELATIONSHIPS:
            _fail("Batch B identified person uses a forbidden attendance relationship")
        if row.get("person_identity_disambiguator_source_id") not in source_ids:
            _fail("Batch B identity requires a source-backed disambiguator")
        if row.get("person_id") != _expected_person_id(row):
            _fail("Batch B canonical person ID cannot be name-only")
        if not row.get("identity_resolution_method") or not row.get("identity_confirmation_notes"):
            _fail("Batch B identified person requires explicit identity resolution")
        match_type = row.get("match_type")
        match_basis = row.get("program_match_basis")
        if match_type not in ALLOWED_MATCH_TYPES:
            _fail("Batch B program match type is not allowed")
        expected_basis = {
            "direct_program_match": "source_stated_exact_program",
            "direct_related_program_match": "source_stated_related_program",
        }[match_type]
        if match_basis != expected_basis or not row.get("match_notes"):
            _fail("Batch B program match must be explicitly source-stated and documented")
        forbidden = ("profession", "career", "company", "fame", "research_inference")
        if any(token in str(match_basis).casefold() for token in forbidden):
            _fail("Batch B cannot infer a program from profession, company, fame, or research")
        for notes_field in ("identity_confirmation_notes", "match_notes"):
            if len(str(row.get(notes_field, ""))) > MAX_NOTES_LENGTH:
                _fail("Batch B identity or match notes exceed the length limit")
        anchors = row.get("evidence_anchor")
        if not isinstance(anchors, dict):
            _fail("Batch B identified person requires attendance and program anchors")
        _validate_anchor(anchors.get("attendance"), "attendance", source_ids, sources, cache_texts)
        _validate_anchor(anchors.get("program_match"), "program_match", source_ids, sources, cache_texts)
        if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
            _fail("Batch B identified person requires reviewed scope disclosure")
        if set(row["reviewed_source_ids"]) - set(source_ids):
            _fail("Batch B reviewed source IDs must resolve to the identified person")
        first_source = sources[source_ids[0]]
        slot.update({
            "slot_status": "identified_person",
            "person_id": row["person_id"],
            "person_name": row["person_name"],
            "person_identity_disambiguator_source_id": row["person_identity_disambiguator_source_id"],
            "identity_resolution_method": row["identity_resolution_method"],
            "identity_confirmation_notes": row["identity_confirmation_notes"],
            "relationship_type": row["relationship_type"],
            "match_type": match_type,
            "program_match_basis": match_basis,
            "match_notes": row["match_notes"],
            "source_ids": list(source_ids),
            "source_url": _source_url(first_source),
            "evidence_anchor": anchors,
            "quote_verification_method": "local_cache_substring_check",
            "reviewed_scope": list(row["reviewed_scope"]),
            "reviewed_source_ids": list(row["reviewed_source_ids"]),
            "null_reason": None,
        })
        observations.append(row)
    return sorted(observations, key=lambda row: (row["candidate_id"], row["normalized_program_name"]))


def _validate_exclusions(document: dict[str, Any], candidate_ids: set[str]) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_batch_b_exclusions":
        _fail("Batch B exclusions have an invalid record type")
    rows: list[dict[str, Any]] = []
    for original in document.get("records", []):
        row = deepcopy(original)
        _reject_ranking_fields(row, "batch_b_exclusion")
        if row.get("candidate_id") not in candidate_ids or row.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            _fail("Batch B exclusion is outside scope or uses an unsupported reason")
        if not row.get("source_id") or not row.get("evidence_anchor"):
            _fail("Batch B exclusions require provenance")
        rows.append(row)
    return sorted(rows, key=lambda row: (row["candidate_id"], str(row.get("person_name"))))


def _cumulative_counts(
    batch_a_dir: Path,
    batch_b_attendance: list[dict[str, Any]],
    batch_b_slots: list[dict[str, Any]],
) -> dict[str, int]:
    batch_a_attendance = _read(Path(batch_a_dir) / "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json").get("records", [])
    batch_a_slots = _read(Path(batch_a_dir) / "stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json").get("slots", [])
    attendance_ids = {row["candidate_id"] for row in [*batch_a_attendance, *batch_b_attendance]}
    precedence = {"source_review_not_completed": 0, "no_qualifying_person_found": 1, "identified_person": 2}
    slot_status: dict[str, str] = {}
    for row in [*batch_a_slots, *batch_b_slots]:
        candidate_id = row["candidate_id"]
        status = row["slot_status"]
        if candidate_id not in slot_status or precedence[status] > precedence[slot_status[candidate_id]]:
            slot_status[candidate_id] = status
    counts = Counter(slot_status.values())
    return {
        "cumulative_batch_a_b_university_occurrences": len(batch_a_attendance) + len(batch_b_attendance),
        "cumulative_batch_a_b_universities_processed": len(attendance_ids),
        "cumulative_batch_a_b_notable_attendance_identified": len(attendance_ids),
        "cumulative_batch_a_b_program_slots_processed": len(slot_status),
        "cumulative_batch_a_b_program_people_identified": counts["identified_person"],
        "cumulative_batch_a_b_program_people_source_review_not_completed": counts["source_review_not_completed"],
        "cumulative_batch_a_b_program_people_no_qualifying_person_found": counts["no_qualifying_person_found"],
    }


def build_stage3d_fill_bulk_people_v2_batch_b(
    *,
    candidate_path: Path,
    pipeline_v2_dir: Path,
    bulk_people_v1_dir: Path,
    batch_a_dir: Path,
    school_manifest_path: Path,
    source_manifest_path: Path,
    cache_manifest_path: Path,
    observations_path: Path,
    exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build deterministic Batch B artifacts from immutable and reviewed inputs."""
    paths = _input_paths(candidate_path, pipeline_v2_dir, bulk_people_v1_dir, batch_a_dir)
    upstream_hashes = {name: _sha256(path) for name, path in paths.items()}
    if upstream_hashes != EXPECTED_INPUT_SHA256:
        _fail("Batch B immutable upstream SHA-256 protection failed")
    pipeline_summary = _read(paths["pipeline_v2_summary"])
    if pipeline_summary.get("slots_processed") != 62 or pipeline_summary.get("identified_person_count") != 0:
        _fail("Batch B requires the immutable 62-slot zero-positive pipeline baseline")
    candidates = _candidate_scope(Path(candidate_path))
    schools, candidate_ids = _school_scope(Path(school_manifest_path), candidates)
    all_slots = _read(paths["pipeline_v2_slot_inventory"]).get("slots", [])
    slots = [deepcopy(row) for row in all_slots if row.get("candidate_id") in candidate_ids]
    if len(slots) != 20 or {row["candidate_id"] for row in slots} != candidate_ids:
        _fail("Batch B requires exactly one immutable Top-1 slot per approved school")
    if any(row.get("slot_status") != "source_review_not_completed" for row in slots):
        _fail("Batch B must begin from unreviewed Top-1 slots")

    bulk_sources_all = _load_source_rows(
        _read(paths["bulk_people_v1_source_manifest"]),
        {"stage3d_fill_bulk_people_v1_source_manifest_artifact"},
    )
    bulk_caches_all = _load_cache_rows(
        _read(paths["bulk_people_v1_cache_manifest"]),
        {"stage3d_fill_bulk_people_v1_cache_manifest_artifact"},
    )
    attendance_all = _read(paths["bulk_people_v1_attendance"]).get("records", [])
    attendance_source_ids = {
        row["source_id"] for row in attendance_all if row.get("candidate_id") in candidate_ids
    }
    sources = {source_id: bulk_sources_all[source_id] for source_id in attendance_source_ids}
    caches = {source_id: bulk_caches_all[source_id] for source_id in attendance_source_ids}
    program_sources = _load_source_rows(
        _read(Path(source_manifest_path)),
        {"stage3d_fill_bulk_people_v2_batch_b_source_manifest"},
    )
    program_caches = _load_cache_rows(
        _read(Path(cache_manifest_path)),
        {"stage3d_fill_bulk_people_v2_batch_b_cache_manifest"},
    )
    if set(program_sources) != set(program_caches) or set(sources) & set(program_sources):
        _fail("Batch B program source/cache coverage is incomplete or collides with attendance sources")
    sources.update(program_sources)
    caches.update(program_caches)
    cache_texts = {
        source_id: _validate_source_cache(source, caches[source_id], candidate_ids)
        for source_id, source in sources.items()
    }
    attendance = _validate_attendance(
        attendance_all, candidate_ids, sources, caches, cache_texts,
    )
    observations = _apply_program_observations(
        _read(Path(observations_path)), slots, sources, cache_texts,
    )
    exclusions = _validate_exclusions(_read(Path(exclusions_path)), candidate_ids)
    slots = sorted(slots, key=lambda row: row["candidate_id"])
    schema = load_schema("stage3d-fill-bulk-people-v2-slot.json")
    for index, slot in enumerate(slots):
        try:
            validate_instance(slot, schema, f"$.slots[{index}]")
        except SchemaValidationError as error:
            _fail(f"Batch B slot schema failed: {error}")
    identified = [row for row in slots if row["slot_status"] == "identified_person"]
    unreviewed = [row for row in slots if row["slot_status"] == "source_review_not_completed"]
    no_qualifying = [row for row in slots if row["slot_status"] == "no_qualifying_person_found"]
    exclusions_by_identity = {
        (row.get("candidate_id"), row.get("person_name"), row.get("source_id")) for row in exclusions
    }
    positive_ids: dict[str, str] = {}
    for row in [*attendance, *identified]:
        person_id = row.get("canonical_person_id") or row.get("person_id")
        person_name = row.get("person_name")
        if person_id in positive_ids and positive_ids[person_id] != person_name:
            _fail("One Batch B canonical person ID cannot represent different names")
        positive_ids[person_id] = person_name
    same_name_contexts: dict[str, set[tuple[str, str]]] = {}
    for row in [*attendance, *identified]:
        name = str(row.get("person_name", "")).casefold()
        context = (row["candidate_id"], (row.get("source_id") or row.get("source_ids", [None])[0]))
        same_name_contexts.setdefault(name, set()).add(context)
    for name, contexts in same_name_contexts.items():
        if len(contexts) > 1:
            for candidate_id, source_id in contexts:
                if not any(
                    (row.get("canonical_person_id") or row.get("person_id"))
                    and candidate_id in (row.get("canonical_person_id") or row.get("person_id"))
                    and source_id.replace("_", "-") in (row.get("canonical_person_id") or row.get("person_id"))
                    for row in [*attendance, *identified]
                    if str(row.get("person_name", "")).casefold() == name
                ):
                    if (candidate_id, name, source_id) not in exclusions_by_identity:
                        _fail("Ambiguous same-name Batch B identities require disambiguation or exclusion")

    cumulative = _cumulative_counts(Path(batch_a_dir), attendance, slots)
    relationship_counts = dict(sorted(Counter(row["attendance_relationship"] for row in attendance).items()))
    match_counts = dict(sorted(Counter(row["match_type"] for row in identified).items()))
    source_rows = [
        {
            **sources[source_id],
            "source_url": _source_url(sources[source_id]),
            "cache_path": caches[source_id]["cache_path"],
            "sha256": caches[source_id]["sha256"],
            "verified_quotes": list(sources[source_id]["verified_direct_quotes"]),
            "retrieval_or_review_notes": (
                sources[source_id].get("retrieval_or_review_notes")
                or caches[source_id].get("retrieval_or_review_notes")
            ),
            "quote_verification_method": "local_cache_substring_check",
        }
        for source_id in sorted(sources)
    ]
    cache_rows = [
        {
            **caches[source_id],
            "source_url": _source_url(sources[source_id]),
        }
        for source_id in sorted(caches)
    ]
    input_sha256 = {
        **upstream_hashes,
        "school_manifest": _sha256(Path(school_manifest_path)),
        "program_source_manifest": _sha256(Path(source_manifest_path)),
        "program_cache_manifest": _sha256(Path(cache_manifest_path)),
        "program_people_observations": _sha256(Path(observations_path)),
        "exclusions": _sha256(Path(exclusions_path)),
    }
    summary = _flags(
        "stage3d_fill_bulk_people_v2_batch_b_summary",
        total_batch_b_universities=20,
        notable_attendance_identified_count=len(attendance),
        notable_attendance_source_review_not_completed_count=0,
        notable_attendance_unresolved_count=0,
        program_slots_processed_count=len(slots),
        program_people_identified_count=len(identified),
        program_people_source_review_not_completed_count=len(unreviewed),
        program_people_no_qualifying_person_found_count=len(no_qualifying),
        exclusions_count=len(exclusions),
        relationship_type_counts=relationship_counts,
        match_type_counts=match_counts,
        local_cache_substring_check_count=len(attendance) + len(identified),
        manual_verbatim_check_count=0,
        cache_verified_quote_count=len(attendance) + len(identified),
        cache_missing_count=0,
        source_policy_violations=0,
        ranking_field_contamination=0,
        readiness_status="batch_b_reviewed_intake_validated_program_coverage_partial",
        remaining_gaps=[
            f"{len(unreviewed)} of 20 Batch B Top-1 program-person slots remain source_review_not_completed.",
            "No unreviewed slot is rendered as no_qualifying_person_found.",
        ],
        not_final_reason="Batch B is a source-limited reviewed overlay and not a final People/Narrative dataset.",
        deterministic_generation=True,
        input_sha256=input_sha256,
        **cumulative,
    )
    gaps = [
        {
            "candidate_id": row["candidate_id"],
            "university_name": row["university_name"],
            "program_name": row["program_name"],
            "slot_status": row["slot_status"],
            "null_reason": row["null_reason"],
            "display_as_none": False,
        }
        for row in slots if row["slot_status"] != "identified_person"
    ]
    return {
        "stage3d-fill-bulk-people-v2-batch-b-plan.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_plan",
            objective="Process reviewed attendance and Top-1 program-person slots for exactly 20 corrected Candidate v2 schools.",
            target_schools=schools,
            virginia_tech_excluded=True,
            texas_a_and_m_replacement=True,
            upstream_mutation_allowed=False,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_notable_attendance", records=attendance,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-program-people.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_program_people", slots=slots, observations=observations,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-exclusions.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_exclusions", records=exclusions,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-source-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_source_manifest", sources=source_rows,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-cache-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_cache_manifest", cache_is_gitignored=True, entries=cache_rows,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_people_v2_batch_b_gap_disclosure",
            gaps=gaps,
            source_review_not_completed_is_none=False,
        ),
        "stage3d-fill-bulk-people-v2-batch-b-summary.json": summary,
    }


def validate_stage3d_fill_bulk_people_v2_batch_b(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed by deterministic rebuild and explicit Batch B checks."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Batch B artifact set is incomplete")
    expected = build_stage3d_fill_bulk_people_v2_batch_b(**inputs)
    if artifacts != expected:
        _fail("Batch B artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-people-v2-batch-b-summary.json"]
    if summary["total_batch_b_universities"] != 20 or summary["notable_attendance_identified_count"] != 20:
        _fail("Batch B school or attendance coverage is incomplete")
    if sum(summary[key] for key in (
        "program_people_identified_count",
        "program_people_source_review_not_completed_count",
        "program_people_no_qualifying_person_found_count",
    )) != 20:
        _fail("Batch B program statuses do not account for all 20 slots")
    if summary["manual_verbatim_check_count"] != 0 or summary["cache_missing_count"] != 0:
        _fail("Batch B quote/cache verification is incomplete")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Batch B source policy or ranking contamination guard failed")
    batch_a_ids = {
        row["candidate_id"]
        for row in _read(Path(inputs["batch_a_dir"]) / "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json").get("records", [])
    }
    batch_b_ids = {
        row["candidate_id"]
        for row in artifacts["stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json"]["records"]
    }
    if summary["cumulative_batch_a_b_universities_processed"] != len(batch_a_ids | batch_b_ids):
        _fail("Batch A+B unique coverage must reflect the Michigan overlap")
    return {
        "record_type": "stage3d_fill_bulk_people_v2_batch_b_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 25,
        "batch_b_universities": 20,
        "notable_attendance_identified_count": summary["notable_attendance_identified_count"],
        "program_slots_processed_count": summary["program_slots_processed_count"],
        "program_people_identified_count": summary["program_people_identified_count"],
        "program_people_source_review_not_completed_count": summary["program_people_source_review_not_completed_count"],
        "program_people_no_qualifying_person_found_count": summary["program_people_no_qualifying_person_found_count"],
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_people_v2_batch_b(
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


def render_stage3d_fill_bulk_people_v2_batch_b_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-bulk-people-v2-batch-b-summary.json"]
    return f"""# Stage 3D-Fill Bulk People v2 Batch B Report

## Corrected scope

- Batch B schools processed: **{summary['total_batch_b_universities']}/20**
- Virginia Tech: **excluded (not in Candidate v2)**
- Texas A&M University: **included as the approved replacement**
- all Batch B schools are in Candidate v2: **yes**

## Batch B coverage

- notable attendance identified: **{summary['notable_attendance_identified_count']}/20**
- Top-1 program slots processed: **{summary['program_slots_processed_count']}/20**
- program people identified: **{summary['program_people_identified_count']}**
- program slots `source_review_not_completed`: **{summary['program_people_source_review_not_completed_count']}**
- program slots `no_qualifying_person_found`: **{summary['program_people_no_qualifying_person_found_count']}**
- exclusions: **{summary['exclusions_count']}**

Every positive record uses an official institutional source, a short direct quote, a SHA-256 verified gitignored cache, and `local_cache_substring_check`. No occupation, employer, fame, achievement, or research-area inference was used for a program match. Unreviewed program slots remain `source_review_not_completed` and are not displayed as “none.”

## Cumulative Batch A + B

- batch occurrences: **{summary['cumulative_batch_a_b_university_occurrences']}**
- unique universities processed: **{summary['cumulative_batch_a_b_universities_processed']}**
- unique notable-attendance coverage: **{summary['cumulative_batch_a_b_notable_attendance_identified']}**
- unique Top-1 program slots processed: **{summary['cumulative_batch_a_b_program_slots_processed']}**
- program people identified: **{summary['cumulative_batch_a_b_program_people_identified']}**
- program slots `source_review_not_completed`: **{summary['cumulative_batch_a_b_program_people_source_review_not_completed']}**
- program slots `no_qualifying_person_found`: **{summary['cumulative_batch_a_b_program_people_no_qualifying_person_found']}**

University of Michigan—Ann Arbor appears in both batches. Cumulative unique counts are derived from artifact unions with slot-status precedence; they are not hard-coded or reported as 30 distinct schools.

## Validation and boundaries

- local-cache verified positive records: **{summary['cache_verified_quote_count']}**
- manual-only verification: **{summary['manual_verbatim_check_count']}**
- missing cache: **{summary['cache_missing_count']}**
- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**

This independent Batch B overlay remains `source_limited`, `incomplete`, and `not_final`. It does not modify Candidate v2, Stage 3/3B/3C/3C2/3D, previous batches, or frontend, and it does not generate a final universe, formal memberships, or frontend export.
"""
