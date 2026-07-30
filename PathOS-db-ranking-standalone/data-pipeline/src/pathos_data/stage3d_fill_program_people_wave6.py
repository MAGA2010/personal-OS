"""High-yield reviewed program-person expansion for Stage 3D-Fill Wave 6."""

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


PIN_RECORD_TYPE = "stage3d_fill_program_people_wave6_immutable_input_pin_manifest"
TOTAL_CANDIDATE_SCHOOLS = 62
TOTAL_PROGRAM_SLOTS = 310
ATTEMPTED_SLOTS = 100
PRIOR_IDENTIFIED_SLOTS = 62
PRIOR_PENDING_SLOTS = 248
OUTPUT_FILES = (
    "stage3d-fill-program-people-wave6-plan.json",
    "stage3d-fill-program-people-wave6-program-people.json",
    "stage3d-fill-program-people-wave6-exclusions.json",
    "stage3d-fill-program-people-wave6-source-manifest.json",
    "stage3d-fill-program-people-wave6-cache-manifest.json",
    "stage3d-fill-program-people-wave6-gap-disclosure.json",
    "stage3d-fill-program-people-wave6-dedup-report.json",
    "stage3d-fill-program-people-wave6-summary.json",
)
VALIDATION_FILE = "stage3d-fill-program-people-wave6-validation-result.json"
ALLOWED_MATCH_BASES = {"source_stated_exact_program", "source_stated_related_program"}
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
HIGH_YIELD_TERMS = (
    "computer science",
    "computer and information",
    "computer engineering",
    "artificial intelligence",
    "data science",
    "data analytics",
    "electrical",
    "engineering",
    "mechanical",
    "aerospace",
    "aeronaut",
    "biomedical",
    "bioengineering",
    "business",
    "management",
    "econom",
    "finance",
    "biology",
    "biological",
    "political science",
    "government",
)


class Stage3DFillProgramPeopleWave6ValidationError(ValueError):
    """Raised when Wave 6 violates scope, evidence, or integrity rules."""


def _fail(message: str) -> None:
    raise Stage3DFillProgramPeopleWave6ValidationError(message)


def validate_preflight_state(current_head: str, status_short: str, expected_head: str) -> None:
    """Fail closed if the operator starts from a dirty or stale Wave 5 baseline."""
    if status_short.strip():
        _fail("Wave 6 preflight requires a clean worktree")
    if current_head.strip() != expected_head.strip():
        _fail("Wave 6 preflight HEAD does not match the expected Wave 5 baseline")


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read Wave 6 input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _reject_detail_ranking_fields(value: Any, path: str) -> None:
    try:
        _reject_ranking_fields(value, path)
    except ValueError as error:
        _fail(str(error))


def _verify_pins(
    manifest_path: Path,
    candidate_path: Path,
    programs_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    document, pins = load_and_verify_input_pins(
        manifest_path,
        expected_record_type=PIN_RECORD_TYPE,
        fail=_fail,
    )
    expected = {
        "candidate_v2": Path(candidate_path).resolve(),
        "stage3c_demo_programs": Path(programs_path).resolve(),
    }
    for pin_id, path in expected.items():
        if pin_id not in pins or Path(pins[pin_id]["resolved_path"]).resolve() != path:
            _fail(f"Wave 6 argument does not match immutable pin {pin_id}")
    descriptors = document.get("prior_wave_inputs")
    expected_waves = ["wave1", "wave2", "wave3", "wave4", "wave5"]
    if not isinstance(descriptors, list) or [row.get("wave_id") for row in descriptors] != expected_waves:
        _fail("Wave 6 requires ordered immutable Wave 1 through Wave 5 inputs")
    for row in descriptors:
        if row.get("program_people_pin_id") not in pins or row.get("summary_pin_id") not in pins:
            _fail("Wave 6 prior-wave descriptor has an unresolved immutable pin")
        if row.get("collection_field") != "slots":
            _fail("Wave 6 prior-wave scope must be derived from slot artifacts")
    if document.get("prior_cumulative_pin_id") not in pins:
        _fail("Wave 6 prior cumulative program-person pin is unresolved")
    return document, pins


def _candidate_scope(candidate_path: Path) -> dict[str, dict[str, Any]]:
    rows = _read(candidate_path).get("universities", [])
    candidates = {row.get("candidate_university_id"): row for row in rows}
    if (
        len(rows) != TOTAL_CANDIDATE_SCHOOLS
        or len(candidates) != TOTAL_CANDIDATE_SCHOOLS
        or None in candidates
    ):
        _fail("Wave 6 requires the immutable 62-school Candidate v2 scope")
    return candidates


def _prior_wave_state(
    pin_document: dict[str, Any],
    pins: dict[str, dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    base_slots: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    expected_lengths = {
        "wave1": 100,
        "wave2": 100,
        "wave3": 110,
        "wave4": 100,
        "wave5": 100,
    }
    for descriptor in pin_document["prior_wave_inputs"]:
        wave_id = descriptor["wave_id"]
        document = _read(Path(pins[descriptor["program_people_pin_id"]]["resolved_path"]))
        rows = deepcopy(document.get(descriptor["collection_field"], []))
        if len(rows) != expected_lengths[wave_id]:
            _fail(f"Wave 6 pinned {wave_id} slot count is invalid")
        if any(row.get("candidate_id") not in candidates for row in rows):
            _fail(f"Wave 6 pinned {wave_id} contains a school outside Candidate v2")
        if wave_id in {"wave4", "wave5"}:
            if len(base_slots) != TOTAL_PROGRAM_SLOTS:
                _fail("Wave 6 must load the complete Waves 1-3 inventory before overlays")
            for row in rows:
                slot_id = row.get("slot_id")
                if (
                    slot_id not in base_slots
                    or base_slots[slot_id].get("slot_status") != "source_review_not_completed"
                ):
                    _fail(f"Wave 6 {wave_id} overlay must target a prior pending slot")
                base_slots[slot_id] = row
        else:
            for row in rows:
                slot_id = row.get("slot_id")
                if not slot_id or slot_id in base_slots:
                    _fail("Wave 6 Waves 1-3 must provide unique base slots")
                base_slots[slot_id] = row
        summaries[wave_id] = _read(Path(pins[descriptor["summary_pin_id"]]["resolved_path"]))
    all_slots = [deepcopy(base_slots[slot_id]) for slot_id in sorted(base_slots)]
    statuses = Counter(row.get("slot_status") for row in all_slots)
    if len(all_slots) != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 6 prior waves must provide exactly 310 unique program slots")
    if statuses != Counter(
        {
            "identified_person": PRIOR_IDENTIFIED_SLOTS,
            "source_review_not_completed": PRIOR_PENDING_SLOTS,
        }
    ):
        _fail("Wave 6 baseline must be 62 identified and 248 pending")
    return all_slots, summaries


def _program_inventory(
    programs_path: Path,
    candidates: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_id = {
        row.get("candidate_id"): row
        for row in _read(programs_path).get("universities", [])
    }
    inventory: dict[str, dict[str, Any]] = {}
    for candidate_id, candidate in sorted(candidates.items()):
        programs = by_id.get(candidate_id, {}).get("top_5_programs_for_demo", [])
        if len(programs) != 5:
            _fail(f"Wave 6 requires five immutable demo programs for {candidate_id}")
        for index, program in enumerate(programs, 1):
            if (
                not program.get("program_name")
                or not program.get("normalized_program_name")
                or not program.get("source_id")
            ):
                _fail("Wave 6 demo-program provenance is incomplete")
            slot_id = f"{candidate_id}:slot-{index}"
            inventory[slot_id] = {
                "slot_id": slot_id,
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
            }
    if len(inventory) != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 6 immutable demo-program inventory must contain 310 slots")
    return inventory


def _is_high_yield(program_name: str, normalized_program_name: str) -> bool:
    text = f"{program_name} {normalized_program_name}".casefold()
    return any(term in text for term in HIGH_YIELD_TERMS)


def _select_slots(
    prior_slots: list[dict[str, Any]],
    inventory: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for prior in prior_slots:
        if prior["slot_status"] != "source_review_not_completed":
            continue
        slot = deepcopy(inventory.get(prior["slot_id"]))
        if not slot:
            _fail("Wave 6 pending slot does not resolve to the demo-program inventory")
        if _is_high_yield(slot["program_name"], slot["normalized_program_name"]):
            slot["priority_tier"] = 1
            pending.append(slot)
    if len(pending) < ATTEMPTED_SLOTS:
        _fail("Wave 6 lacks 100 high-yield remaining slots")
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in pending:
        by_candidate.setdefault(row["candidate_id"], []).append(row)
    for rows in by_candidate.values():
        rows.sort(key=lambda row: (row["program_slot"], row["slot_id"]))
    selected: list[dict[str, Any]] = []
    for position in range(5):
        layer = [
            rows[position]
            for _, rows in sorted(by_candidate.items())
            if len(rows) > position
        ]
        selected.extend(layer[: ATTEMPTED_SLOTS - len(selected)])
        if len(selected) == ATTEMPTED_SLOTS:
            break
    if len(selected) != ATTEMPTED_SLOTS:
        _fail("Wave 6 must attempt exactly 100 high-yield pending slots")
    return selected


def _source_cache(
    source_manifest_path: Path,
    cache_manifest_path: Path,
    selected_candidate_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    source_doc = _read(source_manifest_path)
    cache_doc = _read(cache_manifest_path)
    if source_doc.get("record_type") != "stage3d_fill_program_people_wave6_source_manifest_input":
        _fail("Wave 6 source manifest has an invalid record type")
    if (
        cache_doc.get("record_type")
        != "stage3d_fill_program_people_wave6_cache_manifest_input"
        or cache_doc.get("cache_is_gitignored") is not True
    ):
        _fail("Wave 6 cache manifest must declare a gitignored reviewed cache")
    sources: dict[str, dict[str, Any]] = {}
    for original in source_doc.get("sources", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if (
            not source_id
            or source_id in sources
            or row.get("candidate_id") not in selected_candidate_ids
        ):
            _fail("Wave 6 source IDs must be unique and resolve to selected schools")
        _reject_detail_ranking_fields(row, "wave6_source")
        if (
            row.get("source_type") != "official_institutional"
            or not row.get("source_url")
            or not row.get("publisher")
        ):
            _fail("Wave 6 positive sources must be complete official institutional sources")
        quotes = row.get("verified_direct_quotes")
        if (
            not isinstance(quotes, list)
            or not quotes
            or any(
                not isinstance(quote, str)
                or not quote
                or len(quote) > MAX_QUOTE_LENGTH
                for quote in quotes
            )
        ):
            _fail("Wave 6 sources require short verified direct quotes")
        validate_source_policy_use(
            str(row["publisher"]),
            "detail",
            has_field_provenance=True,
        )
        sources[source_id] = row
    caches: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    for original in cache_doc.get("entries", []):
        row = deepcopy(original)
        source_id = row.get("source_id")
        if not source_id or source_id in caches or source_id not in sources:
            _fail("Wave 6 cache entries must resolve one-to-one to reviewed sources")
        if row.get("quote_verification_method") != "local_cache_substring_check":
            _fail("Wave 6 disallows manual-only quote verification")
        path = _resolve_cache_path(str(row.get("cache_path", "")))
        if not path.is_file() or _sha256(path) != row.get("sha256"):
            _fail("Wave 6 cache is missing or fails SHA-256 verification")
        text = path.read_text(encoding="utf-8")
        source = sources[source_id]
        if source["source_url"] not in text or any(
            quote not in text for quote in source["verified_direct_quotes"]
        ):
            _fail("Wave 6 source URL or reviewed quote is absent from cache")
        caches[source_id] = row
        texts[source_id] = text
    if set(caches) != set(sources):
        _fail("Wave 6 requires one cache entry for every reviewed source")
    return sources, caches, texts


def _empty_slot(
    slot: dict[str, Any],
    *,
    status: str = "source_review_not_completed",
    reviewed_scope: list[str] | None = None,
    reviewed_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        **slot,
        "slot_status": status,
        "person_id": None,
        "canonical_person_id": None,
        "person_name": None,
        "relationship_type": None,
        "match_type": None,
        "program_match_basis": None,
        "source_ids": [],
        "source_id": None,
        "source_url": None,
        "source_urls": {},
        "source_sha256": {},
        "cache_sha256": None,
        "evidence_anchor": None,
        "quote_verification_method": None,
        "match_notes": None,
        "reviewed_scope": reviewed_scope or [],
        "reviewed_source_ids": reviewed_source_ids or [],
        "null_reason": status,
        "display_as_none": status == "no_qualifying_person_found",
    }


def _anchor(source_id: str, quote: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "evidence_type": "direct_quote",
        "quote": quote,
        "quote_verification_method": "local_cache_substring_check",
    }


def _apply_observations(
    observations_path: Path,
    selected: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    caches: dict[str, dict[str, Any]],
    cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    document = _read(observations_path)
    if (
        document.get("record_type")
        != "stage3d_fill_program_people_wave6_program_people_observations"
    ):
        _fail("Wave 6 observations have an invalid record type")
    selected_by_id = {row["slot_id"]: row for row in selected}
    observations: dict[str, dict[str, Any]] = {}
    for original in document.get("observations", []):
        row = deepcopy(original)
        _reject_detail_ranking_fields(row, "wave6_observation")
        slot_id = row.get("slot_id")
        slot = selected_by_id.get(slot_id)
        if (
            slot is None
            or slot_id in observations
            or row.get("candidate_id") != slot["candidate_id"]
            or row.get("program_slot") != slot["program_slot"]
        ):
            _fail("Wave 6 observation must resolve exactly once to a selected slot")
        status = row.get("slot_status")
        if status not in SLOT_STATUSES:
            _fail("Wave 6 slot status is invalid")
        if status == "no_qualifying_person_found":
            reviewed_source_ids = row.get("reviewed_source_ids")
            if not row.get("reviewed_scope") or not reviewed_source_ids:
                _fail("Wave 6 no_qualifying_person_found requires reviewed scope and sources")
            if any(
                source_id not in sources
                or source_id not in caches
                or sources[source_id].get("candidate_id") != row["candidate_id"]
                for source_id in reviewed_source_ids
            ):
                _fail(
                    "Wave 6 no_qualifying_person_found requires cache-verified "
                    "reviewed sources for the same school"
                )
        elif status == "identified_person":
            source_ids = row.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                _fail("Wave 6 identified person requires source-backed dual evidence")
            if any(
                source_id not in sources
                or sources[source_id].get("candidate_id") != row["candidate_id"]
                for source_id in source_ids
            ):
                _fail("Wave 6 identified source does not resolve to the same school")
            attendance_source_id = row.get("attendance_source_id") or source_ids[0]
            program_source_id = row.get("program_source_id") or source_ids[-1]
            for source_id, quote, role in (
                (attendance_source_id, row.get("attendance_quote"), "attendance"),
                (program_source_id, row.get("program_quote"), "program match"),
            ):
                if (
                    source_id not in source_ids
                    or not isinstance(quote, str)
                    or quote not in sources[source_id]["verified_direct_quotes"]
                    or quote not in cache_texts[source_id]
                ):
                    _fail(f"Wave 6 identified {role} quote is absent from reviewed cache")
            if row.get("relationship_type") not in ALLOWED_RELATIONSHIPS:
                _fail("Wave 6 identified person uses a forbidden attendance relationship")
            if row.get("match_type") not in ALLOWED_MATCH_TYPES:
                _fail("Wave 6 identified person uses an invalid program match")
            if row.get("program_match_basis") not in ALLOWED_MATCH_BASES:
                _fail(
                    "Wave 6 program match must be source-stated, never inferred from "
                    "career, company, research, or fame"
                )
            if not row.get("match_notes") or len(str(row["match_notes"])) > MAX_NOTES_LENGTH:
                _fail("Wave 6 program match requires concise notes")
            identity = {
                **row,
                "person_identity_disambiguator_source_id": source_ids[0],
            }
            if row.get("person_id") != _expected_person_id(identity):
                _fail("Wave 6 person ID must include name, candidate, and source context")
        observations[slot_id] = row
    result: list[dict[str, Any]] = []
    for slot in selected:
        observation = observations.get(slot["slot_id"])
        if observation is None:
            result.append(_empty_slot(slot))
            continue
        if observation["slot_status"] != "identified_person":
            result.append(
                _empty_slot(
                    slot,
                    status=observation["slot_status"],
                    reviewed_scope=observation.get("reviewed_scope", []),
                    reviewed_source_ids=observation.get("reviewed_source_ids", []),
                )
            )
            continue
        source_ids = observation["source_ids"]
        attendance_source_id = observation.get("attendance_source_id") or source_ids[0]
        program_source_id = observation.get("program_source_id") or source_ids[-1]
        result.append(
            {
                **slot,
                "slot_status": "identified_person",
                "person_id": observation["person_id"],
                "canonical_person_id": observation["person_id"],
                "person_name": observation["person_name"],
                "relationship_type": observation["relationship_type"],
                "match_type": observation["match_type"],
                "program_match_basis": observation["program_match_basis"],
                "source_ids": source_ids,
                "source_id": source_ids[0],
                "source_url": sources[source_ids[0]]["source_url"],
                "source_urls": {
                    source_id: sources[source_id]["source_url"]
                    for source_id in source_ids
                },
                "source_sha256": {
                    source_id: caches[source_id]["sha256"] for source_id in source_ids
                },
                "cache_sha256": caches[source_ids[0]]["sha256"],
                "evidence_anchor": {
                    "attendance": _anchor(
                        attendance_source_id,
                        observation["attendance_quote"],
                    ),
                    "program_match": _anchor(
                        program_source_id,
                        observation["program_quote"],
                    ),
                },
                "quote_verification_method": "local_cache_substring_check",
                "match_notes": observation["match_notes"],
                "reviewed_scope": observation["reviewed_scope"],
                "reviewed_source_ids": source_ids,
                "null_reason": None,
                "display_as_none": False,
            }
        )
    return result


def _deduplicate(
    prior_rows: list[dict[str, Any]],
    wave_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    occurrences = [deepcopy(row) for row in prior_rows]
    for row in wave_rows:
        if row["slot_status"] == "identified_person":
            clone = deepcopy(row)
            clone["origin_waves"] = ["wave6"]
            occurrences.append(clone)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in occurrences:
        canonical_id = row.get("canonical_person_id") or row.get("person_id")
        key = (row.get("candidate_id"), canonical_id)
        if not all(key):
            _fail("Wave 6 cumulative program person lacks a dedup key")
        row["canonical_person_id"] = canonical_id
        row["person_id"] = canonical_id
        grouped.setdefault(key, []).append(row)
    merged: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        names = {row.get("person_name") for row in rows}
        if len(names) != 1:
            _fail("Wave 6 cumulative duplicate key maps to different people")
        primary = deepcopy(rows[0])
        origins = sorted(
            {
                origin
                for row in rows
                for origin in row.get("origin_waves", row.get("origin_batches", []))
            }
        )
        primary["origin_waves"] = origins
        primary["origin_batches"] = origins
        primary["source_ids"] = sorted(
            {
                source_id
                for row in rows
                for source_id in row.get("source_ids", [])
            }
        )
        primary["program_slots"] = sorted(
            {
                row.get("program_slot")
                for row in rows
                if row.get("program_slot")
            }
        )
        merged.append(primary)
        if len(rows) > 1:
            duplicates.append(
                {
                    "candidate_id": key[0],
                    "canonical_person_id": key[1],
                    "person_name": next(iter(names)),
                    "input_occurrence_count": len(rows),
                    "origin_waves": origins,
                    "resolution": (
                        "merged_by_candidate_and_canonical_person_id_preserving_provenance"
                    ),
                }
            )
    if duplicates:
        _fail("Wave 6 introduces a duplicate candidate/person key")
    keys = [(row["candidate_id"], row["canonical_person_id"]) for row in merged]
    if len(keys) != len(set(keys)):
        _fail("Wave 6 cumulative output retains duplicate person keys")
    return merged, duplicates, len(occurrences)


def _validate_prior_cumulative_people(
    prior_slots: list[dict[str, Any]],
    prior_cumulative: list[dict[str, Any]],
) -> None:
    slot_keys = {
        (
            row.get("candidate_id"),
            row.get("canonical_person_id") or row.get("person_id"),
        )
        for row in prior_slots
        if row.get("slot_status") == "identified_person"
    }
    cumulative_keys = [
        (
            row.get("candidate_id"),
            row.get("canonical_person_id") or row.get("person_id"),
        )
        for row in prior_cumulative
    ]
    if (
        len(slot_keys) != PRIOR_IDENTIFIED_SLOTS
        or len(cumulative_keys) != PRIOR_IDENTIFIED_SLOTS
        or len(cumulative_keys) != len(set(cumulative_keys))
        or set(cumulative_keys) != slot_keys
    ):
        _fail(
            "Wave 6 pinned cumulative people must match the 62 identified "
            "Waves 1-5 slot records exactly"
        )


def build_stage3d_fill_program_people_wave6(
    *,
    candidate_path: Path,
    programs_path: Path,
    input_pin_manifest_path: Path,
    source_manifest_path: Path,
    cache_manifest_path: Path,
    observations_path: Path,
    exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build the independent Wave 6 overlay from pinned Waves 1-5."""
    pin_document, pins = _verify_pins(
        input_pin_manifest_path,
        candidate_path,
        programs_path,
    )
    candidates = _candidate_scope(candidate_path)
    prior_slots, prior_summaries = _prior_wave_state(pin_document, pins, candidates)
    inventory = _program_inventory(programs_path, candidates)
    selected = _select_slots(prior_slots, inventory)
    sources, caches, cache_texts = _source_cache(
        source_manifest_path,
        cache_manifest_path,
        {row["candidate_id"] for row in selected},
    )
    slots = _apply_observations(
        observations_path,
        selected,
        sources,
        caches,
        cache_texts,
    )
    exclusions_doc = _read(exclusions_path)
    if exclusions_doc.get("record_type") != "stage3d_fill_program_people_wave6_exclusions_input":
        _fail("Wave 6 exclusions input has an invalid record type")
    exclusions = deepcopy(exclusions_doc.get("exclusions", []))
    for row in exclusions:
        _reject_detail_ranking_fields(row, "wave6_exclusion")
        if row.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            _fail("Wave 6 exclusion reason is invalid")
    prior_cumulative_doc = _read(
        Path(pins[pin_document["prior_cumulative_pin_id"]]["resolved_path"])
    )
    prior_cumulative = deepcopy(prior_cumulative_doc.get("records", []))
    _validate_prior_cumulative_people(prior_slots, prior_cumulative)
    cumulative_people, duplicate_records, raw_occurrences = _deduplicate(
        prior_cumulative,
        slots,
    )
    wave_statuses = Counter(row["slot_status"] for row in slots)
    cumulative_by_slot = {row["slot_id"]: row["slot_status"] for row in prior_slots}
    for row in slots:
        cumulative_by_slot[row["slot_id"]] = row["slot_status"]
    cumulative_statuses = Counter(cumulative_by_slot.values())
    if len(cumulative_by_slot) != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 6 cumulative dashboard must account for all 310 slots")
    if (
        len(cumulative_people) != cumulative_statuses["identified_person"]
        or raw_occurrences
        != PRIOR_IDENTIFIED_SLOTS + wave_statuses["identified_person"]
    ):
        _fail("Wave 6 cumulative people and slot-derived identified counts diverge")
    prior_counts = {
        "wave1": prior_summaries["wave1"].get("program_people_identified_count"),
        "wave2": prior_summaries["wave2"].get("program_people_identified_count"),
        "wave3": prior_summaries["wave3"].get("wave3_identified_person_count"),
        "wave4": prior_summaries["wave4"].get("wave4_identified_count"),
        "wave5": prior_summaries["wave5"].get("wave5_identified_count"),
    }
    if prior_counts != {
        "wave1": 20,
        "wave2": 8,
        "wave3": 10,
        "wave4": 14,
        "wave5": 10,
    }:
        _fail("Wave 6 prior summaries do not match the 62-person baseline")
    source_output = [
        {
            **sources[source_id],
            "cache_path": caches[source_id]["cache_path"],
            "sha256": caches[source_id]["sha256"],
            "quote_verification_method": "local_cache_substring_check",
        }
        for source_id in sorted(sources)
    ]
    cache_output = [deepcopy(caches[source_id]) for source_id in sorted(caches)]
    selected_plan = [
        {
            key: row[key]
            for key in (
                "slot_id",
                "candidate_id",
                "canonical_id",
                "university_name",
                "program_slot",
                "program_name",
                "normalized_program_name",
                "program_source_reference",
                "priority_tier",
            )
        }
        for row in selected
    ]
    gaps = [
        deepcopy(row)
        for row in slots
        if row["slot_status"] != "identified_person"
    ]
    summary = _flags(
        "stage3d_fill_program_people_wave6_summary",
        total_candidate_schools=TOTAL_CANDIDATE_SCHOOLS,
        total_program_slots=TOTAL_PROGRAM_SLOTS,
        prior_source_review_not_completed_slots=PRIOR_PENDING_SLOTS,
        attempted_remaining_slots=len(slots),
        slots_attempted=len(slots),
        prior_cumulative_identified_person_count=PRIOR_IDENTIFIED_SLOTS,
        wave1_identified_count=prior_counts["wave1"],
        wave2_identified_count=prior_counts["wave2"],
        wave3_identified_count=prior_counts["wave3"],
        wave4_identified_count=prior_counts["wave4"],
        wave5_identified_count=prior_counts["wave5"],
        wave6_identified_count=wave_statuses["identified_person"],
        wave6_source_review_not_completed_count=wave_statuses[
            "source_review_not_completed"
        ],
        wave6_no_qualifying_person_found_count=wave_statuses[
            "no_qualifying_person_found"
        ],
        exclusions_count=len(exclusions),
        cumulative_program_slots_processed=TOTAL_PROGRAM_SLOTS,
        cumulative_identified_person_count=cumulative_statuses["identified_person"],
        cumulative_source_review_not_completed_count=cumulative_statuses[
            "source_review_not_completed"
        ],
        cumulative_no_qualifying_person_found_count=cumulative_statuses[
            "no_qualifying_person_found"
        ],
        coverage_delta_from_wave5=wave_statuses["identified_person"],
        raw_person_occurrence_count=raw_occurrences,
        unique_person_count=len(cumulative_people),
        duplicate_person_count=len(duplicate_records),
        cumulative_duplicate_count=len(duplicate_records),
        post_merge_duplicate_count=0,
        duplicate_records=duplicate_records,
        local_cache_substring_check_count=wave_statuses["identified_person"],
        cache_verified_quote_count=wave_statuses["identified_person"] * 2,
        manual_verbatim_check_count=0,
        cache_missing_count=0,
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="source_limited / incomplete / not_final",
        not_final_reason=(
            "Wave 6 expands high-yield reviewed program-person coverage but "
            f"{cumulative_statuses['source_review_not_completed']} slots remain "
            "source-review gaps and no final Gate or export is authorized."
        ),
        remaining_gaps={
            "source_review_not_completed_slots": cumulative_statuses[
                "source_review_not_completed"
            ]
        },
    )
    return {
        "stage3d-fill-program-people-wave6-plan.json": _flags(
            "stage3d_fill_program_people_wave6_plan",
            remaining_slots_before_wave6=PRIOR_PENDING_SLOTS,
            high_yield_remaining_slots_before_wave6=sum(
                1
                for row in prior_slots
                if row["slot_status"] == "source_review_not_completed"
                and _is_high_yield(
                    inventory[row["slot_id"]]["program_name"],
                    inventory[row["slot_id"]]["normalized_program_name"],
                )
            ),
            attempted_remaining_slots=len(selected),
            selection_order=(
                "high_yield_program_family_then_school_round_robin_then_program_slot"
            ),
            high_yield_program_terms=list(HIGH_YIELD_TERMS),
            derivation=(
                "Waves 1-5 cumulative source_review_not_completed slots joined to "
                "immutable Candidate v2 and Stage 3C demo-program inventory"
            ),
            selected_slots=selected_plan,
            immutable_input_pins=[
                {
                    key: value
                    for key, value in row.items()
                    if key != "resolved_path"
                }
                for row in pins.values()
            ],
        ),
        "stage3d-fill-program-people-wave6-program-people.json": _flags(
            "stage3d_fill_program_people_wave6_program_people",
            slots=slots,
        ),
        "stage3d-fill-program-people-wave6-exclusions.json": _flags(
            "stage3d_fill_program_people_wave6_exclusions",
            exclusions=exclusions,
        ),
        "stage3d-fill-program-people-wave6-source-manifest.json": _flags(
            "stage3d_fill_program_people_wave6_source_manifest",
            sources=source_output,
        ),
        "stage3d-fill-program-people-wave6-cache-manifest.json": _flags(
            "stage3d_fill_program_people_wave6_cache_manifest",
            cache_is_gitignored=True,
            entries=cache_output,
        ),
        "stage3d-fill-program-people-wave6-gap-disclosure.json": _flags(
            "stage3d_fill_program_people_wave6_gap_disclosure",
            gaps=gaps,
            attempted_source_review_not_completed_count=wave_statuses[
                "source_review_not_completed"
            ],
            unattempted_source_review_not_completed_count=(
                PRIOR_PENDING_SLOTS - ATTEMPTED_SLOTS
            ),
            source_review_not_completed_is_not_none=True,
        ),
        "stage3d-fill-program-people-wave6-dedup-report.json": _flags(
            "stage3d_fill_program_people_wave6_dedup_report",
            dedup_key_fields=["candidate_id", "canonical_person_id"],
            raw_person_occurrence_count=raw_occurrences,
            unique_person_count=len(cumulative_people),
            duplicate_person_count=len(duplicate_records),
            post_merge_duplicate_count=0,
            duplicate_records=duplicate_records,
            records=cumulative_people,
        ),
        "stage3d-fill-program-people-wave6-summary.json": summary,
    }


def validate_stage3d_fill_program_people_wave6(
    artifacts: dict[str, dict[str, Any]],
    **inputs: Any,
) -> dict[str, Any]:
    """Fail closed when Wave 6 diverges from reviewed deterministic inputs."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Wave 6 artifact set is incomplete")
    expected = build_stage3d_fill_program_people_wave6(**inputs)
    if artifacts != expected:
        _fail("Wave 6 artifacts do not match deterministic regeneration")
    plan = artifacts["stage3d-fill-program-people-wave6-plan.json"]
    slots = artifacts["stage3d-fill-program-people-wave6-program-people.json"][
        "slots"
    ]
    summary = artifacts["stage3d-fill-program-people-wave6-summary.json"]
    dedup = artifacts["stage3d-fill-program-people-wave6-dedup-report.json"]
    if len(plan["selected_slots"]) != ATTEMPTED_SLOTS or len(slots) != ATTEMPTED_SLOTS:
        _fail("Wave 6 must deterministically attempt 100 remaining slots")
    if any(row["priority_tier"] != 1 for row in slots):
        _fail("Wave 6 selection must stay within declared high-yield families")
    if any(row["slot_status"] not in SLOT_STATUSES for row in slots):
        _fail("Wave 6 contains an invalid slot status")
    if summary["cumulative_program_slots_processed"] != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 6 cumulative dashboard must retain 310 processed slots")
    if sum(
        summary[key]
        for key in (
            "cumulative_identified_person_count",
            "cumulative_source_review_not_completed_count",
            "cumulative_no_qualifying_person_found_count",
        )
    ) != TOTAL_PROGRAM_SLOTS:
        _fail("Wave 6 cumulative dashboard does not sum to 310 slots")
    keys = [
        (row["candidate_id"], row["canonical_person_id"])
        for row in dedup["records"]
    ]
    if (
        len(keys) != len(set(keys))
        or dedup["duplicate_person_count"] != 0
        or dedup["post_merge_duplicate_count"] != 0
        or len(keys) != summary["cumulative_identified_person_count"]
        or dedup["raw_person_occurrence_count"]
        != summary["cumulative_identified_person_count"]
    ):
        _fail("Wave 6 cumulative output retains duplicate keys")
    if (
        summary["manual_verbatim_check_count"] != 0
        or summary["cache_missing_count"] != 0
    ):
        _fail("Wave 6 requires complete local-cache verification")
    if (
        summary["source_policy_violations"] != 0
        or summary["ranking_field_contamination"] != 0
    ):
        _fail("Wave 6 source policy or ranking isolation failed")
    if summary["readiness_status"] != "source_limited / incomplete / not_final":
        _fail("Wave 6 readiness must remain source-limited, incomplete, and not-final")
    return {
        "record_type": "stage3d_fill_program_people_wave6_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 23,
        "slots_attempted": len(slots),
        "identified_people": summary["wave6_identified_count"],
        "source_review_not_completed": summary[
            "wave6_source_review_not_completed_count"
        ],
        "no_qualifying_person_found": summary[
            "wave6_no_qualifying_person_found_count"
        ],
        "cumulative_identified_people": summary[
            "cumulative_identified_person_count"
        ],
        "cumulative_program_slots_processed": TOTAL_PROGRAM_SLOTS,
        "post_merge_duplicate_count": 0,
        "cache_verified_quote_count": summary["cache_verified_quote_count"],
        "cache_missing_count": 0,
        "manual_verbatim_check_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_program_people_wave6(
    artifacts: dict[str, dict[str, Any]],
    output_dir: Path,
    validation: dict[str, Any],
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        (output_dir / name).write_text(
            json.dumps(
                artifacts[name],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    (output_dir / VALIDATION_FILE).write_text(
        json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_stage3d_fill_program_people_wave6_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-program-people-wave6-summary.json"]
    return f"""# Stage 3D-Fill Program People Coverage Expansion Wave 6 Report

## High-yield reviewed intake

- prior source-review gaps: **{summary['prior_source_review_not_completed_slots']}**
- high-yield slots attempted: **{summary['slots_attempted']}**
- newly identified people: **{summary['wave6_identified_count']}**
- attempted slots still source review not completed: **{summary['wave6_source_review_not_completed_count']}**
- no qualifying person found after scoped review: **{summary['wave6_no_qualifying_person_found_count']}**
- exclusions: **{summary['exclusions_count']}**

Wave 6 derives its scope from immutable Waves 1-5 and selects only remaining Computer Science, Engineering, Business, Economics, Biology, AI/Data Science, Finance, and Political Science families. Processed slots are not presented as identified people.

## Evidence and integrity

- local-cache verified positive records: **{summary['local_cache_substring_check_count']}**
- cache-verified quote anchors: **{summary['cache_verified_quote_count']}**
- manual-only quote checks: **{summary['manual_verbatim_check_count']}**
- missing caches: **{summary['cache_missing_count']}**
- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**

Every positive record has source-stated attendance and program evidence from an official institutional source. Both anchors are exact substrings of a gitignored, SHA-256-pinned reviewed excerpt. Careers, companies, research fields, and fame were not used to infer programs.

## Cumulative Wave 1-6 dashboard

- total program slots processed: **{summary['cumulative_program_slots_processed']} / 310**
- identified program people: **{summary['cumulative_identified_person_count']}**
- source review not completed: **{summary['cumulative_source_review_not_completed_count']}**
- no qualifying person found after scoped review: **{summary['cumulative_no_qualifying_person_found_count']}**
- coverage delta from Wave 5: **+{summary['coverage_delta_from_wave5']}**
- raw person occurrences: **{summary['raw_person_occurrence_count']}**
- unique program people: **{summary['unique_person_count']}**
- duplicate keys: **{summary['duplicate_person_count']}**
- duplicates remaining after merge: **{summary['post_merge_duplicate_count']}**

## Boundaries

- frontend modified: **false**
- upstream Waves 1-5 artifacts modified: **false**
- final universe generated: **false**
- formal memberships generated: **false**
- frontend export generated: **false**

This independent overlay remains `source_limited`, `incomplete`, and `not_final`. It does not declare a Gate result.
"""
