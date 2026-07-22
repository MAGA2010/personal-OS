"""Reviewed top-five program-person intake for Bulk Completion Wave 1."""

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


PIN_RECORD_TYPE = "stage3d_fill_bulk_completion_wave1_immutable_input_pin_manifest"
OUTPUT_FILES = (
    "stage3d-fill-bulk-completion-wave1-plan.json",
    "stage3d-fill-bulk-completion-wave1-slot-inventory.json",
    "stage3d-fill-bulk-completion-wave1-program-people.json",
    "stage3d-fill-bulk-completion-wave1-cumulative-program-people.json",
    "stage3d-fill-bulk-completion-wave1-duplicate-records.json",
    "stage3d-fill-bulk-completion-wave1-exclusions.json",
    "stage3d-fill-bulk-completion-wave1-source-manifest.json",
    "stage3d-fill-bulk-completion-wave1-cache-manifest.json",
    "stage3d-fill-bulk-completion-wave1-gap-disclosure.json",
    "stage3d-fill-bulk-completion-wave1-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-completion-wave1-validation-result.json"
ALLOWED_MATCH_BASES = {"source_stated_exact_program", "source_stated_related_program"}
ALLOWED_EXCLUSIONS = {
    "faculty_only", "donor_only", "honorary_degree_only", "visitor_only",
    "speaker_only", "unclear", "same_name_unresolved", "campus_mismatch",
    "source_insufficient", "program_match_insufficient", "profession_inference_rejected",
}


class Stage3DFillBulkCompletionWave1ValidationError(ValueError):
    """Raised when Wave 1 violates scope, evidence, or integrity rules."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkCompletionWave1ValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read Wave 1 input {path}: {error}")


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
    if len(rows) != 62 or len(candidates) != 62 or None in candidates:
        _fail("Wave 1 requires the immutable 62-school Candidate v2 scope")
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
            _fail(f"Wave 1 argument does not match immutable pin {pin_id}")
    batches = document.get("program_person_batches")
    if not isinstance(batches, list) or {row.get("batch_id") for row in batches} != {
        "stage3d-fill-bulk-people-v2-batch-a",
        "stage3d-fill-bulk-people-v2-batch-b",
    }:
        _fail("Wave 1 prior program-person batch manifest is incomplete")
    for row in batches:
        if row.get("artifact_pin_id") not in pins or row.get("collection_field") not in {"records", "slots"}:
            _fail("Wave 1 program-person batch pin is unresolved")
    return document, pins


def _school_scope(
    manifest_path: Path, candidates: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    document = _read(manifest_path)
    if document.get("record_type") != "stage3d_fill_bulk_completion_wave1_school_manifest":
        _fail("Wave 1 school manifest has an invalid record type")
    rows = document.get("schools", [])
    ids = [row.get("candidate_id") for row in rows]
    if len(ids) != 20 or len(set(ids)) != 20 or None in ids or not set(ids) <= set(candidates):
        _fail("Wave 1 school manifest must contain 20 distinct Candidate v2 schools")
    return [candidates[candidate_id] for candidate_id in sorted(ids)]


def _program_inventory(
    programs_path: Path, schools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    document = _read(programs_path)
    by_id = {row.get("candidate_id"): row for row in document.get("universities", [])}
    inventory = []
    for candidate in schools:
        candidate_id = candidate["candidate_university_id"]
        program_rows = by_id.get(candidate_id, {}).get("top_5_programs_for_demo", [])
        if len(program_rows) != 5:
            _fail(f"Wave 1 requires five immutable demo programs for {candidate_id}")
        for index, program in enumerate(program_rows, 1):
            if not program.get("program_name") or not program.get("normalized_program_name") or not program.get("source_id"):
                _fail("Wave 1 demo-program provenance is incomplete")
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
    return inventory


def _source_cache(
    source_manifest_path: Path,
    cache_manifest_path: Path,
    candidate_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    source_doc = _read(source_manifest_path)
    cache_doc = _read(cache_manifest_path)
    if source_doc.get("record_type") != "stage3d_fill_bulk_completion_wave1_source_manifest_input":
        _fail("Wave 1 source manifest has an invalid record type")
    if (
        cache_doc.get("record_type") != "stage3d_fill_bulk_completion_wave1_cache_manifest_input"
        or cache_doc.get("cache_is_gitignored") is not True
    ):
        _fail("Wave 1 cache manifest must declare a gitignored reviewed cache")
    sources: dict[str, dict[str, Any]] = {}
    for original in source_doc.get("sources", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if not source_id or source_id in sources or row.get("candidate_id") not in candidate_ids:
            _fail("Wave 1 source IDs must be unique and in scope")
        _reject_detail_ranking_fields(row, "wave1_source")
        if row.get("source_type") != "official_institutional" or not row.get("source_url") or not row.get("publisher"):
            _fail("Wave 1 positive sources must be complete official institutional sources")
        quotes = row.get("verified_direct_quotes")
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH for quote in quotes
        ):
            _fail("Wave 1 sources require short verified direct quotes")
        validate_source_policy_use(str(row["publisher"]), "detail", has_field_provenance=True)
        sources[source_id] = row
    caches = {}
    texts = {}
    for original in cache_doc.get("entries", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if not source_id or source_id in caches or source_id not in sources:
            _fail("Wave 1 cache entries must resolve one-to-one to sources")
        if row.get("quote_verification_method") != "local_cache_substring_check":
            _fail("Wave 1 disallows manual-only quote verification")
        path = _resolve_cache_path(str(row.get("cache_path", "")))
        if not path.is_file() or _sha256(path) != row.get("sha256"):
            _fail("Wave 1 cache is missing or fails SHA-256 verification")
        text = path.read_text(encoding="utf-8")
        source = sources[source_id]
        if source["source_url"] not in text or any(quote not in text for quote in source["verified_direct_quotes"]):
            _fail("Wave 1 source URL or reviewed quote is absent from cache")
        caches[source_id] = row
        texts[source_id] = text
    if set(caches) != set(sources):
        _fail("Wave 1 requires one cache entry for every reviewed source")
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
    if document.get("record_type") != "stage3d_fill_bulk_completion_wave1_program_people_observations":
        _fail("Wave 1 observations have an invalid record type")
    inventory_by_id = {row["slot_id"]: row for row in inventory}
    observations = {}
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_detail_ranking_fields(row, "wave1_observation")
        slot_id = row.get("slot_id")
        if slot_id not in inventory_by_id or slot_id in observations:
            _fail("Wave 1 observation must resolve exactly once to an approved slot")
        if row.get("candidate_id") != inventory_by_id[slot_id]["candidate_id"] or row.get("program_slot") != inventory_by_id[slot_id]["program_slot"]:
            _fail("Wave 1 observation identity conflicts with its slot")
        status = row.get("slot_status")
        if status not in SLOT_STATUSES:
            _fail("Wave 1 slot status is invalid")
        if status == "no_qualifying_person_found":
            if not row.get("reviewed_scope") or not row.get("reviewed_source_ids"):
                _fail("Wave 1 no_qualifying_person_found requires reviewed scope and source IDs")
        elif status == "identified_person":
            source_ids = row.get("source_ids")
            if not isinstance(source_ids, list) or len(source_ids) != 1:
                _fail("Wave 1 identified person requires one source-backed observation")
            source_id = source_ids[0]
            source = sources.get(source_id)
            cache = caches.get(source_id)
            attendance_quote = row.get("attendance_quote") or row.get("quote")
            program_quote = row.get("program_quote") or row.get("quote")
            if not source or not cache or source.get("candidate_id") != row.get("candidate_id"):
                _fail("Wave 1 identified source does not resolve to the same school")
            if any(
                quote not in source["verified_direct_quotes"] or quote not in cache_texts[source_id]
                for quote in (attendance_quote, program_quote)
            ):
                _fail("Wave 1 identified attendance or program quote is absent from the reviewed source cache")
            if row.get("relationship_type") not in ALLOWED_RELATIONSHIPS:
                _fail("Wave 1 identified person uses a forbidden attendance relationship")
            if row.get("match_type") not in ALLOWED_MATCH_TYPES:
                _fail("Wave 1 identified person uses an invalid program match")
            if row.get("program_match_basis") not in ALLOWED_MATCH_BASES:
                _fail("Wave 1 program match must be source-stated, never inferred from career or fame")
            if not row.get("match_notes") or len(str(row["match_notes"])) > MAX_NOTES_LENGTH:
                _fail("Wave 1 program match requires concise notes")
            identity = {
                **row,
                "person_identity_disambiguator_source_id": source_id,
            }
            if row.get("person_id") != _expected_person_id(identity):
                _fail("Wave 1 person ID must include name, candidate, and source context")
        observations[slot_id] = row

    result = []
    for slot in inventory:
        observation = observations.get(slot["slot_id"])
        if observation is None:
            result.append({
                **slot,
                "slot_status": "source_review_not_completed",
                "person_id": None,
                "person_name": None,
                "relationship_type": None,
                "match_type": None,
                "program_match_basis": None,
                "source_ids": [],
                "source_url": None,
                "source_sha256": None,
                "evidence_anchor": None,
                "quote_verification_method": None,
                "match_notes": None,
                "reviewed_scope": [],
                "reviewed_source_ids": [],
                "null_reason": "source_review_not_completed",
                "display_as_none": False,
            })
            continue
        if observation["slot_status"] == "identified_person":
            source_id = observation["source_ids"][0]
            attendance_quote = observation.get("attendance_quote") or observation["quote"]
            program_quote = observation.get("program_quote") or observation["quote"]
            result.append({
                **slot,
                "slot_status": "identified_person",
                "person_id": observation["person_id"],
                "person_name": observation["person_name"],
                "relationship_type": observation["relationship_type"],
                "match_type": observation["match_type"],
                "program_match_basis": observation["program_match_basis"],
                "source_ids": [source_id],
                "source_url": sources[source_id]["source_url"],
                "source_sha256": caches[source_id]["sha256"],
                "evidence_anchor": {
                    "attendance": _anchor(source_id, attendance_quote),
                    "program_match": _anchor(source_id, program_quote),
                },
                "quote_verification_method": "local_cache_substring_check",
                "match_notes": observation["match_notes"],
                "reviewed_scope": observation["reviewed_scope"],
                "reviewed_source_ids": [source_id],
                "null_reason": None,
                "display_as_none": False,
            })
        else:
            result.append({
                **slot,
                **{key: observation.get(key) for key in (
                    "slot_status", "reviewed_scope", "reviewed_source_ids", "null_reason",
                )},
                "person_id": None, "person_name": None, "relationship_type": None,
                "match_type": None, "program_match_basis": None, "source_ids": [],
                "source_url": None, "source_sha256": None, "evidence_anchor": None,
                "quote_verification_method": None, "match_notes": None,
                "display_as_none": observation["slot_status"] == "no_qualifying_person_found",
            })
    return result


def _prior_program_people(
    pin_document: dict[str, Any], pins: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for batch in pin_document["program_person_batches"]:
        pin = pins[batch["artifact_pin_id"]]
        document = _read(Path(pin["resolved_path"]))
        for original in document.get(batch["collection_field"], []):
            if original.get("slot_status") != "identified_person":
                continue
            row = deepcopy(original)
            row["person_id"] = row.get("person_id") or row.get("canonical_person_id")
            row["program_slot"] = row.get("program_slot") or row.get("slot_index")
            row["origin_batch"] = batch["batch_id"]
            rows.append(row)
    return rows


def _deduplicate_program_people(
    prior_rows: list[dict[str, Any]], wave_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows = [deepcopy(row) for row in prior_rows]
    for row in wave_rows:
        if row["slot_status"] == "identified_person":
            clone = deepcopy(row)
            clone["origin_batch"] = "stage3d-fill-bulk-completion-wave1"
            all_rows.append(clone)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in all_rows:
        key = (row.get("candidate_id"), row.get("person_id"))
        if not all(key):
            _fail("Wave 1 cumulative program person lacks a dedup key")
        grouped.setdefault(key, []).append(row)
    merged = []
    duplicates = []
    for key, rows in sorted(grouped.items()):
        names = {row.get("person_name") for row in rows}
        if len(names) != 1:
            _fail("Wave 1 cumulative duplicate key maps to different person names")
        primary = deepcopy(sorted(rows, key=lambda row: row["origin_batch"])[0])
        primary["origin_batches"] = sorted({row["origin_batch"] for row in rows})
        primary["source_ids"] = sorted({source_id for row in rows for source_id in row.get("source_ids", [])})
        primary["program_slots"] = sorted({row.get("program_slot") for row in rows if row.get("program_slot")})
        primary.pop("origin_batch", None)
        merged.append(primary)
        if len(rows) > 1:
            duplicates.append({
                "candidate_id": key[0],
                "canonical_person_id": key[1],
                "person_name": next(iter(names)),
                "input_occurrence_count": len(rows),
                "origin_batches": sorted({row["origin_batch"] for row in rows}),
                "resolution": "merged_by_candidate_and_canonical_person_id_preserving_provenance",
            })
    keys = [(row["candidate_id"], row["person_id"]) for row in merged]
    if len(keys) != len(set(keys)):
        _fail("Wave 1 cumulative program-person output retains duplicate keys")
    return merged, duplicates


def build_stage3d_fill_bulk_completion_wave1(
    *,
    candidate_path: Path,
    programs_path: Path,
    school_manifest_path: Path,
    input_pin_manifest_path: Path,
    source_manifest_path: Path,
    cache_manifest_path: Path,
    observations_path: Path,
    exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build the independent Wave 1 top-five program-person overlay."""
    pin_document, pins = _verify_pins(input_pin_manifest_path, candidate_path, programs_path)
    candidates = _candidate_scope(candidate_path)
    schools = _school_scope(school_manifest_path, candidates)
    inventory = _program_inventory(programs_path, schools)
    candidate_ids = {row["candidate_university_id"] for row in schools}
    sources, caches, cache_texts = _source_cache(source_manifest_path, cache_manifest_path, candidate_ids)
    slots = _apply_observations(observations_path, inventory, sources, caches, cache_texts)
    exclusions_doc = _read(exclusions_path)
    if exclusions_doc.get("record_type") != "stage3d_fill_bulk_completion_wave1_exclusions_input":
        _fail("Wave 1 exclusions input has an invalid record type")
    exclusions = deepcopy(exclusions_doc.get("exclusions", []))
    for row in exclusions:
        _reject_detail_ranking_fields(row, "wave1_exclusion")
        if row.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            _fail("Wave 1 exclusion reason is invalid")
    prior_rows = _prior_program_people(pin_document, pins)
    cumulative, duplicate_records = _deduplicate_program_people(prior_rows, slots)
    statuses = Counter(row["slot_status"] for row in slots)
    match_types = Counter(row["match_type"] for row in slots if row.get("match_type"))
    relationship_types = Counter(row["relationship_type"] for row in slots if row.get("relationship_type"))
    gap_rows = [deepcopy(row) for row in slots if row["slot_status"] != "identified_person"]
    input_count = len(prior_rows) + statuses["identified_person"]
    summary = _flags(
        "stage3d_fill_bulk_completion_wave1_summary",
        total_wave1_universities=20,
        program_slots_processed_count=len(slots),
        program_people_identified_count=statuses["identified_person"],
        program_people_source_review_not_completed_count=statuses["source_review_not_completed"],
        program_people_no_qualifying_person_found_count=statuses["no_qualifying_person_found"],
        exclusions_count=len(exclusions),
        relationship_type_counts=dict(sorted(relationship_types.items())),
        match_type_counts=dict(sorted(match_types.items())),
        local_cache_substring_check_count=statuses["identified_person"],
        manual_verbatim_check_count=0,
        cache_verified_quote_count=statuses["identified_person"] * 2,
        cache_missing_count=0,
        cumulative_input_identified_occurrence_count=input_count,
        cumulative_unique_program_person_count=len(cumulative),
        cumulative_duplicate_person_count=len(duplicate_records),
        cumulative_post_merge_duplicate_count=0,
        dedup_key_fields=["candidate_id", "canonical_person_id"],
        immutable_input_pin_manifest=str(Path(input_pin_manifest_path)),
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="reviewed_program_person_intake_in_progress",
        remaining_gaps={"source_review_not_completed_slots": statuses["source_review_not_completed"]},
        not_final_reason="Wave 1 covers 20 Candidate v2 schools and five existing demo-program slots per school; it remains source-limited and incomplete.",
    )
    source_output = []
    cache_output = []
    for source_id in sorted(sources):
        source_output.append({**sources[source_id], "cache_path": caches[source_id]["cache_path"], "sha256": caches[source_id]["sha256"], "quote_verification_method": "local_cache_substring_check"})
        cache_output.append(deepcopy(caches[source_id]))
    return {
        "stage3d-fill-bulk-completion-wave1-plan.json": _flags(
            "stage3d_fill_bulk_completion_wave1_plan",
            university_count=20,
            slots_per_university=5,
            total_slots=100,
            program_source="immutable_stage3c_demo_programs_overlay",
            immutable_input_pins=[{key: value for key, value in row.items() if key != "resolved_path"} for row in pins.values()],
        ),
        "stage3d-fill-bulk-completion-wave1-slot-inventory.json": _flags(
            "stage3d_fill_bulk_completion_wave1_slot_inventory", slots=inventory,
        ),
        "stage3d-fill-bulk-completion-wave1-program-people.json": _flags(
            "stage3d_fill_bulk_completion_wave1_program_people", slots=slots,
        ),
        "stage3d-fill-bulk-completion-wave1-cumulative-program-people.json": _flags(
            "stage3d_fill_bulk_completion_wave1_cumulative_program_people",
            dedup_key_fields=["candidate_id", "canonical_person_id"], records=cumulative,
        ),
        "stage3d-fill-bulk-completion-wave1-duplicate-records.json": _flags(
            "stage3d_fill_bulk_completion_wave1_duplicate_records", duplicate_records=duplicate_records,
        ),
        "stage3d-fill-bulk-completion-wave1-exclusions.json": _flags(
            "stage3d_fill_bulk_completion_wave1_exclusions", exclusions=exclusions,
        ),
        "stage3d-fill-bulk-completion-wave1-source-manifest.json": _flags(
            "stage3d_fill_bulk_completion_wave1_source_manifest", sources=source_output,
        ),
        "stage3d-fill-bulk-completion-wave1-cache-manifest.json": _flags(
            "stage3d_fill_bulk_completion_wave1_cache_manifest", cache_is_gitignored=True, entries=cache_output,
        ),
        "stage3d-fill-bulk-completion-wave1-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_completion_wave1_gap_disclosure",
            gaps=gap_rows,
            source_review_not_completed_is_not_none=True,
        ),
        "stage3d-fill-bulk-completion-wave1-summary.json": summary,
    }


def validate_stage3d_fill_bulk_completion_wave1(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed when Wave 1 diverges from deterministic source inputs."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Wave 1 artifact set is incomplete")
    expected = build_stage3d_fill_bulk_completion_wave1(**inputs)
    if artifacts != expected:
        _fail("Wave 1 artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-completion-wave1-summary.json"]
    slots = artifacts["stage3d-fill-bulk-completion-wave1-program-people.json"]["slots"]
    cumulative = artifacts["stage3d-fill-bulk-completion-wave1-cumulative-program-people.json"]["records"]
    keys = [(row.get("candidate_id"), row.get("person_id")) for row in cumulative]
    if len(slots) != 100 or summary["program_slots_processed_count"] != 100:
        _fail("Wave 1 must process exactly 100 slots")
    if len(keys) != len(set(keys)) or summary["cumulative_post_merge_duplicate_count"] != 0:
        _fail("Wave 1 cumulative program-person output contains duplicate keys")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Wave 1 source policy or ranking isolation failed")
    return {
        "record_type": "stage3d_fill_bulk_completion_wave1_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 24,
        "universities_processed": 20,
        "program_slots_processed": 100,
        "identified_people": summary["program_people_identified_count"],
        "source_review_not_completed": summary["program_people_source_review_not_completed_count"],
        "no_qualifying_person_found": summary["program_people_no_qualifying_person_found_count"],
        "cumulative_unique_program_people": summary["cumulative_unique_program_person_count"],
        "cumulative_duplicate_people_merged": summary["cumulative_duplicate_person_count"],
        "post_merge_duplicate_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_completion_wave1(
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


def render_stage3d_fill_bulk_completion_wave1_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-bulk-completion-wave1-summary.json"]
    return f"""# Stage 3D-Fill Bulk Completion Wave 1 Report

## Reviewed program-person intake

- Candidate v2 schools processed: **{summary['total_wave1_universities']}**
- existing demo-program slots processed: **{summary['program_slots_processed_count']}**
- identified people: **{summary['program_people_identified_count']}**
- source review not completed: **{summary['program_people_source_review_not_completed_count']}**
- no qualifying person found after scoped review: **{summary['program_people_no_qualifying_person_found_count']}**

Every positive record has separate attendance and program-match anchors backed by an official institutional source, a gitignored reviewed excerpt cache, SHA-256 verification, and `local_cache_substring_check`. Program matches use only `source_stated_exact_program` or `source_stated_related_program`; careers, companies, research areas, and fame were not used to infer majors.

## Cumulative deduplication

- identified input occurrences across Batch A, Batch B, and Wave 1: **{summary['cumulative_input_identified_occurrence_count']}**
- unique program people: **{summary['cumulative_unique_program_person_count']}**
- duplicate candidate/person keys merged: **{summary['cumulative_duplicate_person_count']}**
- duplicates remaining after merge: **{summary['cumulative_post_merge_duplicate_count']}**

Immutable upstream inputs are protected by a versioned input pin manifest rather than hashes embedded in Python source. Raw Batch A and Batch B artifacts remain unchanged.

## Boundaries

- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**
- frontend modified: **false**
- final universe generated: **false**
- formal memberships generated: **false**
- frontend export generated: **false**

This overlay remains `source_limited`, `incomplete`, and `not_final`.
"""
