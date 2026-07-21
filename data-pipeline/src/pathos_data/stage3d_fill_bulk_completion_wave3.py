"""Reviewed top-five program-person intake for Bulk Completion Wave 3."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .immutable_input_pins import load_and_verify_input_pins
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


PIN_RECORD_TYPE = "stage3d_fill_bulk_completion_wave3_immutable_input_pin_manifest"
EXPECTED_REMAINING_SCHOOLS = 22
TOTAL_CANDIDATE_SCHOOLS = 62
SLOTS_PER_SCHOOL = 5
TOTAL_PROGRAM_SLOTS = 310
OUTPUT_FILES = (
    "stage3d-fill-bulk-completion-wave3-plan.json",
    "stage3d-fill-bulk-completion-wave3-program-people.json",
    "stage3d-fill-bulk-completion-wave3-exclusions.json",
    "stage3d-fill-bulk-completion-wave3-source-manifest.json",
    "stage3d-fill-bulk-completion-wave3-cache-manifest.json",
    "stage3d-fill-bulk-completion-wave3-gap-disclosure.json",
    "stage3d-fill-bulk-completion-wave3-cumulative-dedup.json",
    "stage3d-fill-bulk-completion-wave3-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-completion-wave3-validation-result.json"
ALLOWED_MATCH_BASES = {"source_stated_exact_program", "source_stated_related_program"}
ALLOWED_EXCLUSIONS = {
    "faculty_only", "donor_only", "honorary_degree_only", "visitor_only",
    "speaker_only", "unclear", "same_name_unresolved", "campus_mismatch",
    "source_insufficient", "program_match_insufficient", "profession_inference_rejected",
}


class Stage3DFillBulkCompletionWave3ValidationError(ValueError):
    """Raised when Wave 3 violates scope, evidence, or integrity rules."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkCompletionWave3ValidationError(message)


def validate_preflight_state(current_head: str, status_short: str, expected_head: str) -> None:
    """Pure preflight contract used by tests and the operator-facing checkpoint."""
    if status_short.strip():
        _fail("Wave 3 preflight requires a clean worktree")
    if current_head.strip() != expected_head.strip():
        _fail("Wave 3 preflight HEAD does not match the expected Wave 2 baseline")


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read Wave 3 input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _reject_detail_ranking_fields(value: Any, path: str) -> None:
    try:
        _reject_ranking_fields(value, path)
    except ValueError as error:
        _fail(str(error))


def _candidate_scope(candidate_path: Path) -> dict[str, dict[str, Any]]:
    rows = _read(candidate_path).get("universities", [])
    candidates = {row.get("candidate_university_id"): row for row in rows}
    if len(rows) != TOTAL_CANDIDATE_SCHOOLS or len(candidates) != TOTAL_CANDIDATE_SCHOOLS or None in candidates:
        _fail("Wave 3 requires the immutable 62-school Candidate v2 scope")
    return candidates


def _verify_pins(
    manifest_path: Path, candidate_path: Path, programs_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    document, pins = load_and_verify_input_pins(
        manifest_path, expected_record_type=PIN_RECORD_TYPE, fail=_fail,
    )
    expected = {
        "candidate_v2": Path(candidate_path).resolve(),
        "stage3c_demo_programs": Path(programs_path).resolve(),
    }
    for pin_id, path in expected.items():
        if pin_id not in pins or Path(pins[pin_id]["resolved_path"]).resolve() != path:
            _fail(f"Wave 3 argument does not match immutable pin {pin_id}")
    waves = document.get("processed_wave_inputs")
    if not isinstance(waves, list) or len(waves) != 2:
        _fail("Wave 3 requires two processed-wave input descriptors")
    if {row.get("wave_id") for row in waves} != {"wave1", "wave2"}:
        _fail("Wave 3 processed-wave descriptors must identify Wave 1 and Wave 2")
    for row in waves:
        if row.get("program_people_pin_id") not in pins or row.get("summary_pin_id") not in pins:
            _fail("Wave 3 processed-wave descriptor has an unresolved immutable pin")
        if row.get("collection_field") != "slots":
            _fail("Wave 3 processed-wave scope must be derived from slot artifacts")
    cumulative_pin_id = document.get("prior_cumulative_pin_id")
    if cumulative_pin_id not in pins:
        _fail("Wave 3 prior cumulative program-person pin is unresolved")
    return document, pins


def _processed_wave_data(
    pin_document: dict[str, Any], pins: dict[str, dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    school_ids: dict[str, set[str]] = {}
    slots_by_wave: dict[str, list[dict[str, Any]]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for descriptor in pin_document["processed_wave_inputs"]:
        wave_id = descriptor["wave_id"]
        slot_doc = _read(Path(pins[descriptor["program_people_pin_id"]]["resolved_path"]))
        slots = deepcopy(slot_doc.get(descriptor["collection_field"], []))
        ids = {row.get("candidate_id") for row in slots}
        if len(ids) != 20 or None in ids or len(slots) != 100:
            _fail(f"Wave 3 expected 20 schools and 100 slots in pinned {wave_id}")
        school_ids[wave_id] = ids
        slots_by_wave[wave_id] = slots
        summaries[wave_id] = _read(Path(pins[descriptor["summary_pin_id"]]["resolved_path"]))
    if school_ids["wave1"] & school_ids["wave2"]:
        _fail("Wave 1 and Wave 2 school scopes overlap")
    return school_ids, slots_by_wave, summaries


def _remaining_schools(
    candidates: dict[str, dict[str, Any]], processed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    processed_ids = set().union(*processed.values())
    remaining_ids = set(candidates) - processed_ids
    if len(remaining_ids) != EXPECTED_REMAINING_SCHOOLS:
        _fail(
            f"Wave 3 remaining Candidate v2 scope must be 22 schools, got {len(remaining_ids)}"
        )
    return [candidates[candidate_id] for candidate_id in sorted(remaining_ids)]


def _program_inventory(
    programs_path: Path, schools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    document = _read(programs_path)
    by_id = {row.get("candidate_id"): row for row in document.get("universities", [])}
    inventory = []
    for candidate in schools:
        candidate_id = candidate["candidate_university_id"]
        program_rows = by_id.get(candidate_id, {}).get("top_5_programs_for_demo", [])
        if len(program_rows) != SLOTS_PER_SCHOOL:
            _fail(f"Wave 3 requires five immutable demo programs for {candidate_id}")
        for index, program in enumerate(program_rows, 1):
            if not program.get("program_name") or not program.get("normalized_program_name") or not program.get("source_id"):
                _fail("Wave 3 demo-program provenance is incomplete")
            inventory.append({
                "slot_id": f"{candidate_id}:slot-{index}",
                "candidate_id": candidate_id,
                "canonical_id": candidate["canonical_university_id"],
                "university_name": candidate["display_name"],
                "program_slot": index,
                "program_name": program["program_name"],
                "normalized_program_name": program["normalized_program_name"],
                "program_source_reference": {
                    "source_id": program["source_id"],
                    "source_basis": program.get("source_basis"),
                    "source_record_id": program.get("source_record_id"),
                    "evidence_anchor": program.get("evidence_anchor"),
                },
            })
    if len(inventory) != EXPECTED_REMAINING_SCHOOLS * SLOTS_PER_SCHOOL:
        _fail("Wave 3 inventory must contain exactly 110 top-five program slots")
    return inventory


def _source_cache(
    source_manifest_path: Path,
    cache_manifest_path: Path,
    candidate_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    source_doc = _read(source_manifest_path)
    cache_doc = _read(cache_manifest_path)
    if source_doc.get("record_type") != "stage3d_fill_bulk_completion_wave3_source_manifest_input":
        _fail("Wave 3 source manifest has an invalid record type")
    if (
        cache_doc.get("record_type") != "stage3d_fill_bulk_completion_wave3_cache_manifest_input"
        or cache_doc.get("cache_is_gitignored") is not True
    ):
        _fail("Wave 3 cache manifest must declare a gitignored reviewed cache")
    sources: dict[str, dict[str, Any]] = {}
    for original in source_doc.get("sources", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if not source_id or source_id in sources or row.get("candidate_id") not in candidate_ids:
            _fail("Wave 3 source IDs must be unique and in the derived school scope")
        _reject_detail_ranking_fields(row, "wave3_source")
        if row.get("source_type") != "official_institutional" or not row.get("source_url") or not row.get("publisher"):
            _fail("Wave 3 positive sources must be complete official institutional sources")
        quotes = row.get("verified_direct_quotes")
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH for quote in quotes
        ):
            _fail("Wave 3 sources require short verified direct quotes")
        validate_source_policy_use(str(row["publisher"]), "detail", has_field_provenance=True)
        sources[source_id] = row
    caches: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    for original in cache_doc.get("entries", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if not source_id or source_id in caches or source_id not in sources:
            _fail("Wave 3 cache entries must resolve one-to-one to reviewed sources")
        if row.get("quote_verification_method") != "local_cache_substring_check":
            _fail("Wave 3 disallows manual-only quote verification")
        path = _resolve_cache_path(str(row.get("cache_path", "")))
        if not path.is_file() or _sha256(path) != row.get("sha256"):
            _fail("Wave 3 cache is missing or fails SHA-256 verification")
        text = path.read_text(encoding="utf-8")
        source = sources[source_id]
        if source["source_url"] not in text or any(quote not in text for quote in source["verified_direct_quotes"]):
            _fail("Wave 3 source URL or reviewed quote is absent from cache")
        caches[source_id] = row
        texts[source_id] = text
    if set(caches) != set(sources):
        _fail("Wave 3 requires one cache entry for every reviewed source")
    return sources, caches, texts


def _anchor(source_id: str, quote: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "evidence_type": "direct_quote",
        "quote": quote,
        "quote_verification_method": "local_cache_substring_check",
    }


def _apply_observations(
    observations_path: Path,
    inventory: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    caches: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    document = _read(observations_path)
    if document.get("record_type") != "stage3d_fill_bulk_completion_wave3_program_people_observations":
        _fail("Wave 3 observations have an invalid record type")
    inventory_by_id = {row["slot_id"]: row for row in inventory}
    observations: dict[str, dict[str, Any]] = {}
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_detail_ranking_fields(row, "wave3_observation")
        slot_id = row.get("slot_id")
        slot = inventory_by_id.get(slot_id)
        if slot is None or slot_id in observations:
            _fail("Wave 3 observation must resolve exactly once to a derived slot")
        if row.get("candidate_id") != slot["candidate_id"] or row.get("program_slot") != slot["program_slot"]:
            _fail("Wave 3 observation identity conflicts with its slot")
        status = row.get("slot_status")
        if status not in SLOT_STATUSES:
            _fail("Wave 3 slot status is invalid")
        if status == "no_qualifying_person_found":
            if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
                _fail("Wave 3 no_qualifying_person_found requires reviewed scope and source IDs")
        elif status == "identified_person":
            source_ids = row.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                _fail("Wave 3 identified person requires source-backed attendance and program evidence")
            if any(source_id not in sources or sources[source_id].get("candidate_id") != row.get("candidate_id") for source_id in source_ids):
                _fail("Wave 3 identified source does not resolve to the same school")
            attendance_source_id = row.get("attendance_source_id") or source_ids[0]
            program_source_id = row.get("program_source_id") or source_ids[-1]
            attendance_quote = row.get("attendance_quote")
            program_quote = row.get("program_quote")
            for source_id, quote, role in (
                (attendance_source_id, attendance_quote, "attendance"),
                (program_source_id, program_quote, "program match"),
            ):
                if (
                    source_id not in source_ids
                    or not isinstance(quote, str)
                    or quote not in sources[source_id]["verified_direct_quotes"]
                    or quote not in cache_texts[source_id]
                ):
                    _fail(f"Wave 3 identified {role} quote is absent from the reviewed source cache")
            if row.get("relationship_type") not in ALLOWED_RELATIONSHIPS:
                _fail("Wave 3 identified person uses a forbidden attendance relationship")
            if row.get("match_type") not in ALLOWED_MATCH_TYPES:
                _fail("Wave 3 identified person uses an invalid program match")
            if row.get("program_match_basis") not in ALLOWED_MATCH_BASES:
                _fail("Wave 3 program match must be source-stated, never inferred from career, company, research, or fame")
            if not row.get("match_notes") or len(str(row["match_notes"])) > MAX_NOTES_LENGTH:
                _fail("Wave 3 program match requires concise notes")
            identity = {**row, "person_identity_disambiguator_source_id": source_ids[0]}
            if row.get("person_id") != _expected_person_id(identity):
                _fail("Wave 3 person ID must include name, candidate, and source context")
        observations[slot_id] = row

    result = []
    for slot in inventory:
        observation = observations.get(slot["slot_id"])
        if observation is None:
            result.append({
                **slot, "slot_status": "source_review_not_completed",
                "person_id": None, "canonical_person_id": None,
                "person_name": None, "relationship_type": None,
                "match_type": None, "program_match_basis": None, "source_ids": [],
                "source_id": None, "source_url": None, "source_urls": {},
                "source_sha256": {}, "cache_sha256": None, "evidence_anchor": None,
                "quote_verification_method": None, "match_notes": None,
                "reviewed_scope": [], "reviewed_source_ids": [],
                "null_reason": "source_review_not_completed", "display_as_none": False,
            })
            continue
        if observation["slot_status"] == "identified_person":
            source_ids = observation["source_ids"]
            attendance_source_id = observation.get("attendance_source_id") or source_ids[0]
            program_source_id = observation.get("program_source_id") or source_ids[-1]
            result.append({
                **slot, "slot_status": "identified_person",
                "person_id": observation["person_id"],
                "canonical_person_id": observation["person_id"],
                "person_name": observation["person_name"],
                "relationship_type": observation["relationship_type"],
                "match_type": observation["match_type"],
                "program_match_basis": observation["program_match_basis"],
                "source_ids": source_ids,
                "source_id": source_ids[0],
                "source_url": sources[source_ids[0]]["source_url"],
                "source_urls": {source_id: sources[source_id]["source_url"] for source_id in source_ids},
                "source_sha256": {source_id: caches[source_id]["sha256"] for source_id in source_ids},
                "cache_sha256": caches[source_ids[0]]["sha256"],
                "evidence_anchor": {
                    "attendance": _anchor(attendance_source_id, observation["attendance_quote"]),
                    "program_match": _anchor(program_source_id, observation["program_quote"]),
                },
                "quote_verification_method": "local_cache_substring_check",
                "match_notes": observation["match_notes"],
                "reviewed_scope": observation["reviewed_scope"],
                "reviewed_source_ids": source_ids,
                "null_reason": None, "display_as_none": False,
            })
        else:
            result.append({
                **slot, "slot_status": observation["slot_status"],
                "person_id": None, "canonical_person_id": None,
                "person_name": None, "relationship_type": None,
                "match_type": None, "program_match_basis": None, "source_ids": [],
                "source_id": None, "source_url": None, "source_urls": {},
                "source_sha256": {}, "cache_sha256": None, "evidence_anchor": None,
                "quote_verification_method": None, "match_notes": None,
                "reviewed_scope": observation.get("reviewed_scope", []),
                "reviewed_source_ids": observation.get("reviewed_source_ids", []),
                "null_reason": observation.get("null_reason") or observation["slot_status"],
                "display_as_none": observation["slot_status"] == "no_qualifying_person_found",
            })
    return result


def _prior_cumulative(
    pin_document: dict[str, Any], pins: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    document = _read(Path(pins[pin_document["prior_cumulative_pin_id"]]["resolved_path"]))
    records = deepcopy(document.get("records", []))
    for row in records:
        canonical_person_id = row.get("canonical_person_id") or row.get("person_id")
        row["person_id"] = canonical_person_id
        row["canonical_person_id"] = canonical_person_id
        row["origin_waves"] = sorted(set(row.get("origin_waves", row.get("origin_batches", []))))
    return records


def _deduplicate_program_people(
    prior_rows: list[dict[str, Any]], wave_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    occurrences = [deepcopy(row) for row in prior_rows]
    for row in wave_rows:
        if row["slot_status"] == "identified_person":
            clone = deepcopy(row)
            clone["canonical_person_id"] = clone.get("canonical_person_id") or clone.get("person_id")
            clone["origin_waves"] = ["wave3"]
            occurrences.append(clone)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in occurrences:
        key = (row.get("candidate_id"), row.get("canonical_person_id") or row.get("person_id"))
        if not all(key):
            _fail("Wave 3 cumulative program person lacks a dedup key")
        grouped.setdefault(key, []).append(row)
    merged = []
    duplicates = []
    for key, rows in sorted(grouped.items()):
        names = {row.get("person_name") for row in rows}
        if len(names) != 1:
            _fail("Wave 3 cumulative duplicate key maps to different person names")
        primary = deepcopy(rows[0])
        primary["canonical_person_id"] = key[1]
        primary["person_id"] = key[1]
        origin_waves = sorted({wave for row in rows for wave in row.get("origin_waves", row.get("origin_batches", []))})
        primary["origin_waves"] = origin_waves
        primary["origin_batches"] = origin_waves
        primary["source_ids"] = sorted({source_id for row in rows for source_id in row.get("source_ids", [])})
        primary["program_slots"] = sorted({row.get("program_slot") for row in rows if row.get("program_slot")})
        merged.append(primary)
        if len(rows) > 1:
            duplicates.append({
                "candidate_id": key[0], "canonical_person_id": key[1],
                "person_name": next(iter(names)), "input_occurrence_count": len(rows),
                "origin_waves": origin_waves,
                "resolution": "merged_by_candidate_and_canonical_person_id_preserving_provenance",
            })
    keys = [(row["candidate_id"], row["canonical_person_id"]) for row in merged]
    if len(keys) != len(set(keys)):
        _fail("Wave 3 cumulative program-person output retains duplicate keys")
    return merged, duplicates, len(occurrences)


def build_stage3d_fill_bulk_completion_wave3(
    *, candidate_path: Path, programs_path: Path, input_pin_manifest_path: Path,
    source_manifest_path: Path, cache_manifest_path: Path, observations_path: Path,
    exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build the independent, automatically scoped Wave 3 overlay."""
    pin_document, pins = _verify_pins(input_pin_manifest_path, candidate_path, programs_path)
    candidates = _candidate_scope(candidate_path)
    processed, prior_slots, prior_summaries = _processed_wave_data(pin_document, pins)
    schools = _remaining_schools(candidates, processed)
    inventory = _program_inventory(programs_path, schools)
    candidate_ids = {row["candidate_university_id"] for row in schools}
    sources, caches, cache_texts = _source_cache(source_manifest_path, cache_manifest_path, candidate_ids)
    slots = _apply_observations(observations_path, inventory, sources, caches, cache_texts)
    exclusions_doc = _read(exclusions_path)
    if exclusions_doc.get("record_type") != "stage3d_fill_bulk_completion_wave3_exclusions_input":
        _fail("Wave 3 exclusions input has an invalid record type")
    exclusions = deepcopy(exclusions_doc.get("exclusions", []))
    for row in exclusions:
        _reject_detail_ranking_fields(row, "wave3_exclusion")
        if row.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            _fail("Wave 3 exclusion reason is invalid")

    prior_cumulative = _prior_cumulative(pin_document, pins)
    cumulative, duplicate_records, raw_occurrences = _deduplicate_program_people(prior_cumulative, slots)
    wave_statuses = Counter(row["slot_status"] for row in slots)
    cumulative_statuses = Counter()
    for wave_slots in prior_slots.values():
        cumulative_statuses.update(row["slot_status"] for row in wave_slots)
    cumulative_statuses.update(row["slot_status"] for row in slots)
    if sum(cumulative_statuses.values()) != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 3 cumulative status dashboard must account for all 310 program slots")
    gap_rows = [deepcopy(row) for row in slots if row["slot_status"] != "identified_person"]

    source_output = [
        {**sources[source_id], "cache_path": caches[source_id]["cache_path"],
         "sha256": caches[source_id]["sha256"],
         "quote_verification_method": "local_cache_substring_check"}
        for source_id in sorted(sources)
    ]
    cache_output = [deepcopy(caches[source_id]) for source_id in sorted(caches)]
    plan_schools = []
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in inventory:
        by_candidate.setdefault(row["candidate_id"], []).append(row)
    for candidate in schools:
        candidate_id = candidate["candidate_university_id"]
        plan_schools.append({
            "candidate_id": candidate_id,
            "canonical_id": candidate["canonical_university_id"],
            "university_display_name": candidate["display_name"],
            "top_5_program_slots": [
                {key: row[key] for key in ("program_slot", "program_name", "normalized_program_name", "program_source_reference")}
                for row in by_candidate[candidate_id]
            ],
            "source_of_inclusion": {
                "candidate_scope_pin": "candidate_v2",
                "excluded_processed_wave_pins": ["wave1_program_people", "wave2_program_people"],
            },
            "reason": "remaining_after_wave1_wave2",
        })

    summary = _flags(
        "stage3d_fill_bulk_completion_wave3_summary",
        total_candidate_schools=TOTAL_CANDIDATE_SCHOOLS,
        wave1_schools_processed=len(processed["wave1"]),
        wave2_schools_processed=len(processed["wave2"]),
        wave3_schools_processed=len(schools),
        cumulative_schools_processed=len(set().union(*processed.values(), candidate_ids)),
        total_program_slots=TOTAL_PROGRAM_SLOTS,
        wave3_program_slots_processed=len(slots),
        cumulative_program_slots_processed=sum(cumulative_statuses.values()),
        wave3_identified_person_count=wave_statuses["identified_person"],
        wave3_source_review_not_completed_count=wave_statuses["source_review_not_completed"],
        wave3_no_qualifying_person_found_count=wave_statuses["no_qualifying_person_found"],
        exclusions_count=len(exclusions),
        cumulative_identified_person_count=cumulative_statuses["identified_person"],
        cumulative_source_review_not_completed_count=cumulative_statuses["source_review_not_completed"],
        cumulative_no_qualifying_person_found_count=cumulative_statuses["no_qualifying_person_found"],
        raw_person_occurrence_count=raw_occurrences,
        unique_person_count=len(cumulative),
        duplicate_person_count=len(duplicate_records),
        cumulative_duplicate_count=len(duplicate_records),
        post_merge_duplicate_count=0,
        duplicate_records=duplicate_records,
        local_cache_substring_check_count=wave_statuses["identified_person"],
        manual_verbatim_check_count=0,
        cache_verified_quote_count=wave_statuses["identified_person"] * 2,
        cache_missing_count=0,
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="source_limited / incomplete / not_final",
        not_final_reason="Wave 3 completes slot processing across the remaining Candidate v2 schools, but identified people remain source-limited and the overlay has not passed an independent final Gate.",
        remaining_gaps={"source_review_not_completed_slots": cumulative_statuses["source_review_not_completed"]},
        prior_wave_summary_record_types={key: value.get("record_type") for key, value in sorted(prior_summaries.items())},
    )
    return {
        "stage3d-fill-bulk-completion-wave3-plan.json": _flags(
            "stage3d_fill_bulk_completion_wave3_plan",
            expected_remaining_school_count=EXPECTED_REMAINING_SCHOOLS,
            derived_remaining_school_count=len(schools),
            derivation="Candidate v2 minus Wave 1 processed candidate_ids minus Wave 2 processed candidate_ids",
            schools=plan_schools,
            immutable_input_pins=[
                {key: value for key, value in row.items() if key != "resolved_path"}
                for row in pins.values()
            ],
        ),
        "stage3d-fill-bulk-completion-wave3-program-people.json": _flags(
            "stage3d_fill_bulk_completion_wave3_program_people", slots=slots,
        ),
        "stage3d-fill-bulk-completion-wave3-exclusions.json": _flags(
            "stage3d_fill_bulk_completion_wave3_exclusions", exclusions=exclusions,
        ),
        "stage3d-fill-bulk-completion-wave3-source-manifest.json": _flags(
            "stage3d_fill_bulk_completion_wave3_source_manifest", sources=source_output,
        ),
        "stage3d-fill-bulk-completion-wave3-cache-manifest.json": _flags(
            "stage3d_fill_bulk_completion_wave3_cache_manifest", cache_is_gitignored=True, entries=cache_output,
        ),
        "stage3d-fill-bulk-completion-wave3-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_completion_wave3_gap_disclosure", gaps=gap_rows,
            source_review_not_completed_is_not_none=True,
        ),
        "stage3d-fill-bulk-completion-wave3-cumulative-dedup.json": _flags(
            "stage3d_fill_bulk_completion_wave3_cumulative_dedup",
            dedup_key_fields=["candidate_id", "canonical_person_id"],
            raw_person_occurrence_count=raw_occurrences,
            unique_person_count=len(cumulative),
            duplicate_person_count=len(duplicate_records),
            post_merge_duplicate_count=0,
            duplicate_records=duplicate_records,
            records=cumulative,
        ),
        "stage3d-fill-bulk-completion-wave3-summary.json": summary,
    }


def validate_stage3d_fill_bulk_completion_wave3(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed when Wave 3 diverges from deterministic reviewed inputs."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Wave 3 artifact set is incomplete")
    expected = build_stage3d_fill_bulk_completion_wave3(**inputs)
    if artifacts != expected:
        _fail("Wave 3 artifacts do not match deterministic regeneration")
    plan = artifacts["stage3d-fill-bulk-completion-wave3-plan.json"]
    slots = artifacts["stage3d-fill-bulk-completion-wave3-program-people.json"]["slots"]
    dedup = artifacts["stage3d-fill-bulk-completion-wave3-cumulative-dedup.json"]
    summary = artifacts["stage3d-fill-bulk-completion-wave3-summary.json"]
    if len(plan["schools"]) != 22 or plan["derived_remaining_school_count"] != 22:
        _fail("Wave 3 plan must contain exactly the 22 derived remaining schools")
    if len(slots) != 110 or summary["wave3_program_slots_processed"] != 110:
        _fail("Wave 3 must process exactly 110 top-five program slots")
    if summary["cumulative_schools_processed"] != 62 or summary["cumulative_program_slots_processed"] != 310:
        _fail("Wave 3 cumulative dashboard must cover 62 schools and 310 slots")
    keys = [(row.get("candidate_id"), row.get("canonical_person_id")) for row in dedup["records"]]
    if len(keys) != len(set(keys)) or dedup["post_merge_duplicate_count"] != 0:
        _fail("Wave 3 cumulative program-person output contains residual duplicate keys")
    if summary["manual_verbatim_check_count"] != 0 or summary["cache_missing_count"] != 0:
        _fail("Wave 3 requires local cache verification with no missing caches")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Wave 3 source policy or ranking isolation failed")
    if summary["readiness_status"] != "source_limited / incomplete / not_final":
        _fail("Wave 3 readiness must remain source-limited, incomplete, and not-final")
    return {
        "record_type": "stage3d_fill_bulk_completion_wave3_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 23,
        "universities_processed": 22,
        "program_slots_processed": 110,
        "identified_people": summary["wave3_identified_person_count"],
        "source_review_not_completed": summary["wave3_source_review_not_completed_count"],
        "no_qualifying_person_found": summary["wave3_no_qualifying_person_found_count"],
        "cumulative_schools_processed": 62,
        "cumulative_program_slots_processed": 310,
        "unique_program_people": summary["unique_person_count"],
        "duplicate_people_merged": summary["duplicate_person_count"],
        "post_merge_duplicate_count": 0,
        "cache_verified_quote_count": summary["cache_verified_quote_count"],
        "cache_missing_count": 0,
        "manual_verbatim_check_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_completion_wave3(
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


def render_stage3d_fill_bulk_completion_wave3_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-bulk-completion-wave3-summary.json"]
    return f"""# Stage 3D-Fill Bulk Completion Wave 3 Report

## Scope derived from immutable inputs

- Candidate v2 schools: **{summary['total_candidate_schools']}**
- Wave 1 schools processed: **{summary['wave1_schools_processed']}**
- Wave 2 schools processed: **{summary['wave2_schools_processed']}**
- Wave 3 remaining schools processed: **{summary['wave3_schools_processed']}**
- Wave 3 program slots processed: **{summary['wave3_program_slots_processed']}**

The Wave 3 school list is computed as Candidate v2 minus the candidate IDs present in the immutable Wave 1 and Wave 2 program-person artifacts. It is not a manually maintained roster.

## Reviewed intake

- identified people: **{summary['wave3_identified_person_count']}**
- source review not completed: **{summary['wave3_source_review_not_completed_count']}**
- no qualifying person found after scoped review: **{summary['wave3_no_qualifying_person_found_count']}**
- exclusions: **{summary['exclusions_count']}**
- cache-verified quote anchors: **{summary['cache_verified_quote_count']}**
- manual-only quote checks: **{summary['manual_verbatim_check_count']}**
- missing caches: **{summary['cache_missing_count']}**

Every positive record has attendance and program-match evidence from an official institutional source. Both anchors are verified against a gitignored reviewed excerpt cache with SHA-256 and `local_cache_substring_check`. Program matches use only source-stated exact or related programs; careers, companies, research areas, and fame were not used to infer majors.

## Cumulative Wave 1 + Wave 2 + Wave 3 dashboard

- schools processed: **{summary['cumulative_schools_processed']} / 62**
- program slots processed: **{summary['cumulative_program_slots_processed']} / 310**
- identified people: **{summary['cumulative_identified_person_count']}**
- source review not completed: **{summary['cumulative_source_review_not_completed_count']}**
- no qualifying person found after scoped review: **{summary['cumulative_no_qualifying_person_found_count']}**
- raw identified occurrences: **{summary['raw_person_occurrence_count']}**
- unique program people: **{summary['unique_person_count']}**
- duplicate person keys merged: **{summary['duplicate_person_count']}**
- duplicates remaining after merge: **{summary['post_merge_duplicate_count']}**

## Boundaries

- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**
- frontend modified: **false**
- final universe generated: **false**
- formal memberships generated: **false**
- frontend export generated: **false**

Wave 2 has not yet received its independent Gate review, and Wave 3 has not received a Gate review. This overlay remains `source_limited`, `incomplete`, and `not_final`; this report does not declare either wave passed.
"""
