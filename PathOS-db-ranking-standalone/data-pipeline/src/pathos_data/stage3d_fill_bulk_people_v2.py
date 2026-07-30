"""Stage 3D-Fill Bulk People v2 Top-1 program-person slot pipeline.

This module builds an independent, source-limited overlay.  The first checked-in
intake is intentionally empty: every immutable Candidate v2 school receives one
Top-1 program slot, while positive people remain absent until reviewed source
intake is explicitly authorized.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .schema_validation import SchemaValidationError, load_schema, validate_instance
from .universe_candidate_v2 import validate_source_policy_use


EXPECTED_CANDIDATE_SHA256 = "8f940aa6d336402ff9c3c76a43d2efacdf2c887dc983afeb344937db9eadb18d"
EXPECTED_STAGE3C_PROGRAM_SHA256 = "11ac883fcef31d00cd57610c17c848feca479c8d5c2b7030f7f07d69540a5491"
EXPECTED_BULK_PEOPLE_V1_SUMMARY_SHA256 = "780d45fea48e8e3f55141a9abb10e947c4c005762251ca34a389449107eef1e3"

OUTPUT_FILES = (
    "stage3d-fill-bulk-people-v2-plan.json",
    "stage3d-fill-bulk-people-v2-slot-inventory.json",
    "stage3d-fill-bulk-people-v2-people-observations.json",
    "stage3d-fill-bulk-people-v2-program-person-matches.json",
    "stage3d-fill-bulk-people-v2-source-manifest.json",
    "stage3d-fill-bulk-people-v2-cache-manifest.json",
    "stage3d-fill-bulk-people-v2-exclusions.json",
    "stage3d-fill-bulk-people-v2-gap-disclosure.json",
    "stage3d-fill-bulk-people-v2-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-people-v2-validation-result.json"
SLOT_STATUSES = {
    "identified_person",
    "source_review_not_completed",
    "no_qualifying_person_found",
}
ALLOWED_RELATIONSHIPS = {"graduated", "alumnus_unspecified", "attended_no_degree"}
ALLOWED_MATCH_TYPES = {"direct_program_match", "direct_related_program_match"}
ALLOWED_EXCLUSIONS = {
    "faculty_only",
    "donor_only",
    "honorary_degree_only",
    "unclear",
    "same_name_unresolved",
    "campus_mismatch",
    "source_insufficient",
    "program_match_insufficient",
}
RANKING_KEYS = {
    "rank",
    "ranking",
    "usnews",
    "us_news",
    "ranking_category",
    "ranking_family",
}
MAX_QUOTE_LENGTH = 280
MAX_NOTES_LENGTH = 500
DATA_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
FLAGS = {
    "source_limited": True,
    "incomplete": True,
    "not_final": True,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillBulkPeopleV2ValidationError(ValueError):
    """Raised when a Bulk People v2 input or artifact fails closed."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkPeopleV2ValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read required JSON input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _candidate_suffix(candidate_id: str) -> str:
    return _slug(candidate_id.removeprefix("candidate-v2:"))


def _expected_person_id(row: dict[str, Any]) -> str:
    return ":".join((
        "person",
        _slug(str(row.get("person_name", ""))),
        _candidate_suffix(str(row.get("candidate_id", ""))),
        _slug(str(row.get("person_identity_disambiguator_source_id", ""))),
    ))


def _resolve_cache_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else DATA_PIPELINE_ROOT / path


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _reject_ranking_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.casefold().replace("-", "_")
            if any(token in normalized for token in RANKING_KEYS):
                _fail(f"Ranking field contamination at {path}.{key}")
            _reject_ranking_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_ranking_fields(child, f"{path}[{index}]")


def _load_scope(
    candidate_path: Path,
    stage3c_programs_path: Path,
    bulk_people_v1_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    candidate_path = Path(candidate_path)
    stage3c_programs_path = Path(stage3c_programs_path)
    bulk_summary_path = Path(bulk_people_v1_dir) / "stage3d-fill-bulk-people-v1-summary.json"
    hashes = {
        "candidate_v2": _sha256(candidate_path),
        "stage3c_top_program_overlay": _sha256(stage3c_programs_path),
        "bulk_people_v1_summary": _sha256(bulk_summary_path),
    }
    expected = {
        "candidate_v2": EXPECTED_CANDIDATE_SHA256,
        "stage3c_top_program_overlay": EXPECTED_STAGE3C_PROGRAM_SHA256,
        "bulk_people_v1_summary": EXPECTED_BULK_PEOPLE_V1_SUMMARY_SHA256,
    }
    if hashes != expected:
        _fail("Bulk People v2 immutable upstream SHA-256 protection failed")

    candidate_document = _read(candidate_path)
    candidate_rows = candidate_document.get("universities", [])
    candidates = {row.get("candidate_university_id"): row for row in candidate_rows}
    if len(candidate_rows) != 62 or len(candidates) != 62 or None in candidates:
        _fail("Bulk People v2 requires the immutable 62-school Candidate v2 scope")

    programs_document = _read(stage3c_programs_path)
    program_rows = programs_document.get("universities", [])
    programs = {row.get("candidate_id"): row for row in program_rows}
    if len(program_rows) != 62 or set(programs) != set(candidates):
        _fail("Bulk People v2 Stage 3C program scope must match Candidate v2 exactly")
    for candidate_id, row in programs.items():
        top_programs = row.get("top_5_programs_for_demo")
        if not isinstance(top_programs, list) or not top_programs:
            _fail(f"Bulk People v2 requires a reviewed Top-1 demo program for {candidate_id}")
        top1 = top_programs[0]
        if not top1.get("program_name") or not top1.get("normalized_program_name"):
            _fail(f"Bulk People v2 Top-1 demo program is incomplete for {candidate_id}")
    return candidates, programs, hashes


def _source_rows(document: dict[str, Any], candidates: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_source_manifest":
        _fail("Bulk People v2 source manifest has an invalid record type")
    sources: dict[str, dict[str, Any]] = {}
    for original in document.get("sources", []):
        row = dict(original)
        _reject_ranking_fields(row, "source")
        source_id = row.get("source_id")
        source_url = row.get("source_url")
        candidate_id = row.get("candidate_id")
        if not source_id or source_id in sources or candidate_id not in candidates:
            _fail("Every Bulk People v2 source needs a unique ID and in-scope candidate")
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            _fail("Every Bulk People v2 source needs a reviewed HTTPS reference")
        if row.get("source_type") != "official_institutional":
            _fail("Bulk People v2 accepts official institutional people sources only")
        if row.get("field_domain") != "attendance_and_program_people":
            _fail("Bulk People v2 source field domain is invalid")
        if not row.get("publisher") or not row.get("accessed_date"):
            _fail("Every Bulk People v2 source needs publisher and accessed-date provenance")
        if row.get("field_level_provenance_required") is not True:
            _fail("Every Bulk People v2 source must require field-level provenance")
        quotes = row.get("verified_direct_quotes")
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH for quote in quotes
        ):
            _fail("Every reviewed Bulk People v2 source needs short direct quotes")
        validate_source_policy_use(str(row["publisher"]), "detail", has_field_provenance=True)
        sources[source_id] = row
    return sources


def _cache_rows(
    document: dict[str, Any], sources: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_cache_manifest":
        _fail("Bulk People v2 cache manifest has an invalid record type")
    if document.get("cache_is_gitignored") is not True:
        _fail("Bulk People v2 cache must be explicitly gitignored")
    entries: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    for original in document.get("entries", []):
        row = dict(original)
        _reject_ranking_fields(row, "cache")
        source_id = row.get("source_id")
        if source_id not in sources or source_id in entries:
            _fail("Every Bulk People v2 cache entry must resolve uniquely to a reviewed source")
        if row.get("source_url") != sources[source_id]["source_url"]:
            _fail("Bulk People v2 cache source URL does not match the source manifest")
        if row.get("quote_verification_method") != "local_cache_substring_check":
            _fail("manual_verbatim_check is not an allowed final Bulk People v2 state")
        if not row.get("cache_path") or not row.get("sha256") or not row.get("retrieval_or_review_notes"):
            _fail("Every Bulk People v2 cache entry needs path, SHA-256, and review notes")
        path = _resolve_cache_path(str(row["cache_path"]))
        if not path.is_file():
            _fail(f"Bulk People v2 cache file is missing for {source_id}")
        if _sha256(path) != row["sha256"]:
            _fail(f"Bulk People v2 cache SHA-256 mismatch for {source_id}")
        text = path.read_text(encoding="utf-8")
        if sources[source_id]["source_url"] not in text:
            _fail(f"Bulk People v2 cache lacks its source URL for {source_id}")
        entries[source_id] = row
        texts[source_id] = text
    if set(entries) != set(sources):
        _fail("Bulk People v2 cache manifest must cover every reviewed source")
    return entries, texts


def _validate_anchor(
    anchor: Any,
    label: str,
    source_ids: list[str],
    sources: dict[str, dict[str, Any]],
    cache_entries: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> None:
    if not isinstance(anchor, dict):
        _fail(f"identified_person requires a {label} evidence anchor")
    source_id = anchor.get("source_id")
    quote = anchor.get("quote")
    if source_id not in source_ids or source_id not in sources or source_id not in cache_entries:
        _fail(f"identified_person {label} anchor does not resolve to a reviewed source")
    if anchor.get("evidence_type") != "direct_quote":
        _fail(f"identified_person {label} evidence must be a direct quote")
    if anchor.get("quote_verification_method") != "local_cache_substring_check":
        _fail("manual_verbatim_check is not an allowed final Bulk People v2 state")
    if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH:
        _fail(f"identified_person {label} quote must be short and non-empty")
    if quote not in sources[source_id]["verified_direct_quotes"] or quote not in cache_texts[source_id]:
        _fail(f"identified_person {label} quote is absent from the reviewed allowlist or cache")


def _default_slot(
    candidate: dict[str, Any], top1: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_university_id"],
        "canonical_id": candidate["canonical_university_id"],
        "university_name": candidate["display_name"],
        "slot_index": 1,
        "program_name": top1["program_name"],
        "normalized_program_name": top1["normalized_program_name"],
        "program_source_reference": {
            "source_basis": top1["source_basis"],
            "source_id": top1.get("source_id"),
            "source_record_id": top1.get("source_record_id"),
            "evidence_anchor": deepcopy(top1.get("evidence_anchor")),
        },
        "slot_status": "source_review_not_completed",
        "person_id": None,
        "person_name": None,
        "person_identity_disambiguator_source_id": None,
        "identity_resolution_method": None,
        "identity_confirmation_notes": None,
        "relationship_type": None,
        "match_type": None,
        "program_match_basis": None,
        "match_notes": None,
        "source_ids": [],
        "source_url": None,
        "evidence_anchor": None,
        "quote_verification_method": None,
        "reviewed_scope": [],
        "reviewed_source_ids": [],
        "null_reason": "program_person_source_review_not_completed",
    }


def _apply_observations(
    document: dict[str, Any],
    slots: dict[tuple[str, str], dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    cache_entries: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_program_people_observations":
        _fail("Bulk People v2 observations have an invalid record type")
    normalized: list[dict[str, Any]] = []
    seen_slots: set[tuple[str, str]] = set()
    person_contexts: dict[str, tuple[str, str, str]] = {}
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_ranking_fields(row, "program_person_observation")
        candidate_id = row.get("candidate_id")
        program = row.get("normalized_program_name")
        key = (candidate_id, program)
        if key not in slots or key in seen_slots:
            _fail("Bulk People v2 observation must resolve uniquely to an immutable Top-1 slot")
        seen_slots.add(key)
        status = row.get("slot_status")
        if status not in SLOT_STATUSES or status == "source_review_not_completed":
            _fail("Reviewed observations may only resolve an identified or reviewed-empty slot")
        slot = slots[key]
        if status == "no_qualifying_person_found":
            reviewed_scope = row.get("reviewed_scope")
            reviewed_source_ids = row.get("reviewed_source_ids")
            if not isinstance(reviewed_scope, list) or not reviewed_scope or not isinstance(reviewed_source_ids, list) or not reviewed_source_ids:
                _fail("no_qualifying_person_found requires reviewed_scope and reviewed_source_ids")
            if any(source_id not in sources for source_id in reviewed_source_ids):
                _fail("no_qualifying_person_found reviewed sources do not resolve")
            if any(sources[source_id]["candidate_id"] != candidate_id for source_id in reviewed_source_ids):
                _fail("no_qualifying_person_found sources must resolve to the same candidate")
            slot.update({
                "slot_status": status,
                "reviewed_scope": list(reviewed_scope),
                "reviewed_source_ids": list(reviewed_source_ids),
                "null_reason": "no_qualifying_person_in_reviewed_scope",
            })
            normalized.append(row)
            continue

        source_ids = row.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids)):
            _fail("identified_person requires unique reviewed source IDs")
        if any(source_id not in sources or sources[source_id]["candidate_id"] != candidate_id for source_id in source_ids):
            _fail("identified_person sources must resolve to the same candidate")
        if any(source_id not in cache_entries for source_id in source_ids):
            _fail("identified_person requires local cache coverage for every source")
        person_name = row.get("person_name")
        disambiguator = row.get("person_identity_disambiguator_source_id")
        if not isinstance(person_name, str) or not person_name.strip() or disambiguator not in source_ids:
            _fail("identified_person requires a named, source-disambiguated identity")
        expected_person_id = _expected_person_id(row)
        if row.get("person_id") != expected_person_id or expected_person_id.count(":") < 3:
            _fail("identified_person canonical ID must include name, school, and source context")
        identity_context = (person_name, candidate_id, disambiguator)
        if expected_person_id in person_contexts and person_contexts[expected_person_id] != identity_context:
            _fail("One canonical person ID cannot merge different people or contexts")
        person_contexts[expected_person_id] = identity_context
        if len(source_ids) > 1 and (
            row.get("identity_resolution_method") != "manual_source_context_confirmation"
            or not row.get("identity_confirmation_notes")
        ):
            _fail("Same-school cross-source identity requires explicit manual context confirmation")
        if not row.get("identity_resolution_method") or not row.get("identity_confirmation_notes"):
            _fail("identified_person requires explicit identity resolution notes")
        relationship = row.get("relationship_type")
        if relationship not in ALLOWED_RELATIONSHIPS:
            _fail("identified_person relationship is not allowed")
        match_type = row.get("match_type")
        if match_type not in ALLOWED_MATCH_TYPES:
            _fail("identified_person program match type is not allowed")
        match_basis = row.get("program_match_basis")
        if match_type == "direct_program_match" and match_basis != "source_stated_exact_program":
            _fail("direct_program_match must use source-stated exact program evidence")
        if match_type == "direct_related_program_match" and match_basis != "source_stated_related_program":
            _fail("direct_related_program_match must use source-stated related-program evidence")
        match_notes = row.get("match_notes")
        if not isinstance(match_notes, str) or not match_notes or len(match_notes) > MAX_NOTES_LENGTH:
            _fail("identified_person requires short program match notes")
        forbidden_inference = ("profession", "career", "company", "fame", "occupation", "research_inference")
        if any(token in str(match_basis).casefold() for token in forbidden_inference):
            _fail("Profession, company, fame, or research inference cannot establish a program match")
        anchor = row.get("evidence_anchor")
        if not isinstance(anchor, dict):
            _fail("identified_person requires attendance and program-match evidence")
        _validate_anchor(anchor.get("attendance"), "attendance", source_ids, sources, cache_entries, cache_texts)
        _validate_anchor(anchor.get("program_match"), "program_match", source_ids, sources, cache_entries, cache_texts)
        reviewed_scope = row.get("reviewed_scope")
        reviewed_source_ids = row.get("reviewed_source_ids")
        if not isinstance(reviewed_scope, list) or not reviewed_scope or not isinstance(reviewed_source_ids, list) or not reviewed_source_ids:
            _fail("identified_person requires a disclosed reviewed scope and source list")
        if set(reviewed_source_ids) - set(source_ids):
            _fail("identified_person reviewed sources must be included in source_ids")
        primary_source = sources[source_ids[0]]
        slot.update({
            "slot_status": status,
            "person_id": row["person_id"],
            "person_name": person_name,
            "person_identity_disambiguator_source_id": disambiguator,
            "identity_resolution_method": row["identity_resolution_method"],
            "identity_confirmation_notes": row["identity_confirmation_notes"],
            "relationship_type": relationship,
            "match_type": match_type,
            "program_match_basis": match_basis,
            "match_notes": match_notes,
            "source_ids": list(source_ids),
            "source_url": primary_source["source_url"],
            "evidence_anchor": anchor,
            "quote_verification_method": "local_cache_substring_check",
            "reviewed_scope": list(reviewed_scope),
            "reviewed_source_ids": list(reviewed_source_ids),
            "null_reason": None,
        })
        normalized.append(row)
    return sorted(normalized, key=lambda row: (row["candidate_id"], row["normalized_program_name"]))


def _validate_exclusions(document: dict[str, Any], candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v2_exclusions":
        _fail("Bulk People v2 exclusions input has an invalid record type")
    records: list[dict[str, Any]] = []
    for original in document.get("records", []):
        row = deepcopy(original)
        _reject_ranking_fields(row, "exclusion")
        if row.get("candidate_id") not in candidates or row.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            _fail("Bulk People v2 exclusion is outside the allowed scope")
        if row.get("exclusion_reason") == "same_name_unresolved" and not row.get("person_name"):
            _fail("same_name_unresolved exclusions require the unresolved name")
        records.append(row)
    return sorted(records, key=lambda row: (row["candidate_id"], row.get("person_name", "")))


def build_stage3d_fill_bulk_people_v2(
    *,
    candidate_path: Path,
    stage3c_programs_path: Path,
    bulk_people_v1_dir: Path,
    source_manifest_path: Path,
    cache_manifest_path: Path,
    observations_path: Path,
    exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build all deterministic Bulk People v2 artifacts in memory."""
    candidates, programs, upstream_hashes = _load_scope(
        Path(candidate_path), Path(stage3c_programs_path), Path(bulk_people_v1_dir),
    )
    source_document = _read(Path(source_manifest_path))
    cache_document = _read(Path(cache_manifest_path))
    observation_document = _read(Path(observations_path))
    exclusions_document = _read(Path(exclusions_path))
    sources = _source_rows(source_document, candidates)
    cache_entries, cache_texts = _cache_rows(cache_document, sources)

    slot_index: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate_id in sorted(candidates):
        candidate = candidates[candidate_id]
        top1 = programs[candidate_id]["top_5_programs_for_demo"][0]
        slot = _default_slot(candidate, top1)
        slot_index[(candidate_id, top1["normalized_program_name"])] = slot
    normalized_observations = _apply_observations(
        observation_document, slot_index, candidates, sources, cache_entries, cache_texts,
    )
    exclusions = _validate_exclusions(exclusions_document, candidates)
    slots = sorted(slot_index.values(), key=lambda row: row["candidate_id"])
    schema = load_schema("stage3d-fill-bulk-people-v2-slot.json")
    for index, slot in enumerate(slots):
        try:
            validate_instance(slot, schema, f"$.slots[{index}]")
        except SchemaValidationError as error:
            _fail(f"Bulk People v2 slot schema failed: {error}")

    identified = [slot for slot in slots if slot["slot_status"] == "identified_person"]
    unreviewed = [slot for slot in slots if slot["slot_status"] == "source_review_not_completed"]
    no_qualifying = [slot for slot in slots if slot["slot_status"] == "no_qualifying_person_found"]
    input_hashes = {
        **upstream_hashes,
        "source_manifest": _sha256(Path(source_manifest_path)),
        "cache_manifest": _sha256(Path(cache_manifest_path)),
        "program_people_observations": _sha256(Path(observations_path)),
        "exclusions": _sha256(Path(exclusions_path)),
    }
    summary = _flags(
        "stage3d_fill_bulk_people_v2_summary",
        total_universities=62,
        slots_target=62,
        slots_processed=len(slots),
        identified_person_count=len(identified),
        source_review_not_completed_count=len(unreviewed),
        no_qualifying_person_found_count=len(no_qualifying),
        program_people_before_count=0,
        program_people_after_count=len(identified),
        exclusions_count=len(exclusions),
        local_cache_substring_check_count=len(identified),
        manual_verbatim_check_count=0,
        cache_verified_quote_count=sum(2 for _ in identified),
        cache_missing_count=0,
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="top1_slot_pipeline_ready_reviewed_intake_not_started",
        remaining_gaps=[
            f"{len(unreviewed)} Top-1 program-person slots remain source_review_not_completed.",
            "No real-person source intake was authorized in this pipeline implementation round.",
        ],
        not_final_reason="This is a source-limited pipeline overlay, not a final People/Narrative dataset or publication export.",
        input_sha256=input_hashes,
    )
    gaps = [{
        "candidate_id": slot["candidate_id"],
        "university_name": slot["university_name"],
        "program_name": slot["program_name"],
        "slot_status": slot["slot_status"],
        "null_reason": slot["null_reason"],
        "display_as_none": False,
    } for slot in slots if slot["slot_status"] != "identified_person"]
    return {
        "stage3d-fill-bulk-people-v2-plan.json": _flags(
            "stage3d_fill_bulk_people_v2_plan",
            objective="Process one immutable Top-1 demo-program person slot for each Candidate v2 school.",
            scope={"universities": 62, "slots_per_university": 1, "real_person_intake_this_round": False},
            allowed_slot_statuses=sorted(SLOT_STATUSES),
            upstream_mutation_allowed=False,
        ),
        "stage3d-fill-bulk-people-v2-slot-inventory.json": _flags(
            "stage3d_fill_bulk_people_v2_slot_inventory", slots=slots,
        ),
        "stage3d-fill-bulk-people-v2-people-observations.json": _flags(
            "stage3d_fill_bulk_people_v2_people_observations", observations=normalized_observations,
        ),
        "stage3d-fill-bulk-people-v2-program-person-matches.json": _flags(
            "stage3d_fill_bulk_people_v2_program_person_matches", records=identified,
        ),
        "stage3d-fill-bulk-people-v2-source-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_source_manifest_artifact",
            sources=sorted(sources.values(), key=lambda row: row["source_id"]),
        ),
        "stage3d-fill-bulk-people-v2-cache-manifest.json": _flags(
            "stage3d_fill_bulk_people_v2_cache_manifest_artifact",
            cache_is_gitignored=True,
            cache_root=cache_document.get("cache_root"),
            entries=sorted(cache_entries.values(), key=lambda row: row["source_id"]),
        ),
        "stage3d-fill-bulk-people-v2-exclusions.json": _flags(
            "stage3d_fill_bulk_people_v2_exclusions_artifact", records=exclusions,
        ),
        "stage3d-fill-bulk-people-v2-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_people_v2_gap_disclosure", gaps=gaps,
            source_review_not_completed_is_none=False,
        ),
        "stage3d-fill-bulk-people-v2-summary.json": summary,
    }


def validate_stage3d_fill_bulk_people_v2(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed by rebuilding and comparing every deterministic artifact."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Bulk People v2 artifact set is incomplete")
    expected = build_stage3d_fill_bulk_people_v2(**inputs)
    if artifacts != expected:
        _fail("Bulk People v2 artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-people-v2-summary.json"]
    status_total = sum(summary[key] for key in (
        "identified_person_count",
        "source_review_not_completed_count",
        "no_qualifying_person_found_count",
    ))
    if summary["total_universities"] != 62 or summary["slots_processed"] != 62 or status_total != 62:
        _fail("Bulk People v2 summary does not account for exactly 62 processed slots")
    if summary["manual_verbatim_check_count"] != 0:
        _fail("Bulk People v2 cannot retain manual-only quote verification")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Bulk People v2 source-policy or ranking-contamination guard failed")
    return {
        "record_type": "stage3d_fill_bulk_people_v2_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 22,
        "slots_processed": 62,
        "identified_person_count": summary["identified_person_count"],
        "source_review_not_completed_count": summary["source_review_not_completed_count"],
        "no_qualifying_person_found_count": summary["no_qualifying_person_found_count"],
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_people_v2(
    artifacts: dict[str, dict[str, Any]], output_dir: Path, validation: dict[str, Any],
) -> None:
    """Write deterministic JSON artifacts and their validation result."""
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


def render_stage3d_fill_bulk_people_v2_report(artifacts: dict[str, dict[str, Any]]) -> str:
    """Render the implementation checkpoint report without overstating coverage."""
    summary = artifacts["stage3d-fill-bulk-people-v2-summary.json"]
    return f"""# Stage 3D-Fill Bulk People v2 Pipeline Implementation Report

## Outcome

- Candidate v2 scope: **{summary['total_universities']} schools (unchanged)**
- Top-1 slots processed: **{summary['slots_processed']}/{summary['slots_target']}**
- `identified_person`: **{summary['identified_person_count']}**
- `source_review_not_completed`: **{summary['source_review_not_completed_count']}**
- `no_qualifying_person_found`: **{summary['no_qualifying_person_found_count']}**

This checkpoint establishes the reviewed-source intake pipeline only. It intentionally contains no real-person observations and does not render unreviewed slots as “none.”

## Enforcement

Positive records require reviewed attendance evidence, reviewed program-match evidence, a source-disambiguated person ID, and `local_cache_substring_check` backed by a SHA-256 verified gitignored cache. Profession, company, fame, research-area, faculty, donor, honorary-degree, unclear, fuzzy-merge, and pure-name identity paths fail closed. `no_qualifying_person_found` requires both a non-empty reviewed scope and reviewed source IDs.

## Validation and boundaries

- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**
- manual-only quote verification: **{summary['manual_verbatim_check_count']}**
- deterministic generation: **passed**

This independent overlay remains `source_limited`, `incomplete`, and `not_final`. It does not modify Candidate v2, Stage 3/3B/3C/3C2/3D or prior Stage 3D-Fill artifacts, does not modify frontend files, and does not generate a final universe, formal memberships, or frontend export.
"""
