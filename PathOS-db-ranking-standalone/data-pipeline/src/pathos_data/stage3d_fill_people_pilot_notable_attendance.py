"""Independent Stage 3D-Fill People Pilot for reviewed notable attendance."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from .stage3_program_mvp import FLAGS, _candidate_rows
from .stage3d_fill_batch1_history_anecdotes import (
    ALLOWED_RELATIONSHIPS,
    OUTPUT_FILES as _BATCH1_OUTPUT_FILES,
    STAGE3C_FILES,
    STAGE3D_FILL_SEED_FILES,
    Stage3DFillBatch1ValidationError,
    _anchor,
    _fingerprints,
    _manifest,
    _read_json,
    _reject_ranking_fields,
    _sha256,
    _slots,
)
from .stage3d_fill_batch2_history_anecdotes import OUTPUT_FILES as BATCH2_OUTPUT_FILES


BATCH1_FILES = (*_BATCH1_OUTPUT_FILES, "stage3d-fill-batch1-validation-result.json")
OUTPUT_FILES = (
    "stage3d-fill-people-pilot-notable-attendance.json",
    "stage3d-fill-people-pilot-program-people.json",
    "stage3d-fill-people-pilot-exclusions.json",
    "stage3d-fill-people-pilot-source-manifest.json",
    "stage3d-fill-people-pilot-reviewed-source-cache-manifest.json",
    "stage3d-fill-people-pilot-gap-disclosure.json",
    "stage3d-fill-people-pilot-summary.json",
)
ALLOWED_PROGRAM_MATCHES = {"direct_program_match", "direct_related_program_match"}
ALLOWED_MAJOR_CONFIDENCE = {"direct", "inferred_from_degree", "unknown"}
MAX_SHORT_TEXT = 280
FLAGS_PEOPLE_PILOT = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillPeoplePilotValidationError(ValueError):
    """Raised when the notable-attendance pilot breaches a provenance boundary."""


def _fail(message: str) -> None:
    raise Stage3DFillPeoplePilotValidationError(message)


def _person_slug(person_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", person_name.lower()).strip("-")


def _candidate_suffix(candidate_id: str) -> str:
    return _person_slug(candidate_id.removeprefix("candidate-v2:"))


def _expected_person_id(row: Dict[str, Any]) -> str:
    return ":".join((
        "person",
        _person_slug(row["person_name"]),
        _candidate_suffix(row["candidate_id"]),
        _person_slug(row["person_identity_disambiguator_source_id"]),
    ))


def _load_inputs(
    source_manifest_path: Path, cache_manifest_path: Path, attendance_observations_path: Path,
    program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    documents = {
        "sources": _read_json(source_manifest_path),
        "cache": _read_json(cache_manifest_path),
        "attendance": _read_json(attendance_observations_path),
        "program_people": _read_json(program_people_observations_path),
        "exclusions": _read_json(exclusions_path),
    }
    expected = {
        "sources": "stage3d_fill_people_pilot_source_manifest",
        "cache": "stage3d_fill_people_pilot_reviewed_source_cache_manifest",
        "attendance": "stage3d_fill_people_pilot_notable_attendance_observations",
        "program_people": "stage3d_fill_people_pilot_program_people_observations",
        "exclusions": "stage3d_fill_people_pilot_exclusions",
    }
    if any(documents[name].get("record_type") != value for name, value in expected.items()):
        _fail("People Pilot input record type is invalid")
    return documents


def _validate_cache_manifest(
    document: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], cache_manifest_path: Path,
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    if document.get("cache_is_gitignored") is not True or not isinstance(document.get("cache_root"), str):
        _fail("People Pilot cache manifest must disclose its gitignored cache root")
    entries: Dict[str, Dict[str, Any]] = {}
    cache_texts: Dict[str, str] = {}
    for row in document.get("entries", []):
        source_id = row.get("source_id")
        if source_id not in manifest or source_id in entries or row.get("cache_status") not in {"not_cached", "cached"}:
            _fail("People Pilot cache manifest has an invalid source entry")
        if row.get("source_url_or_reference") != manifest[source_id].get("source_url_or_reference"):
            _fail("People Pilot cache manifest source reference must resolve to the reviewed source")
        method = row.get("quote_verification_method")
        cache_path: Path | None = None
        if method not in {"manual_verbatim_check", "local_cache_substring_check"}:
            _fail("People Pilot cache manifest needs an allowed quote verification method")
        if row["cache_status"] == "not_cached":
            if method != "manual_verbatim_check" or row.get("cache_path") is not None or row.get("sha256") is not None:
                _fail("A non-cached People Pilot source cannot claim cache content")
        elif method != "local_cache_substring_check" or not isinstance(row.get("cache_path"), str) or not row.get("sha256"):
            _fail("A cached People Pilot source needs cache path and SHA-256")
        if row["cache_status"] == "cached":
            cache_path = Path(row["cache_path"])
            if not cache_path.is_absolute():
                cache_path = cache_manifest_path.parents[2] / cache_path
            if not cache_path.is_file():
                _fail("A cached People Pilot source must have a readable local cache")
            if hashlib.sha256(cache_path.read_bytes()).hexdigest() != row["sha256"]:
                _fail("A cached People Pilot source must pass its local substring-check cache integrity prerequisite")
        if row["cache_status"] == "cached":
            cache_text = cache_path.read_text(encoding="utf-8")
            if manifest[source_id]["source_url_or_reference"] not in cache_text:
                _fail("People Pilot reviewed cache must include its source reference")
            cache_texts[source_id] = cache_text
        if not row.get("retrieval_or_review_notes"):
            _fail("People Pilot cache entry needs review notes")
        entries[source_id] = dict(row)
    if set(entries) != set(manifest):
        _fail("People Pilot cache manifest must represent every reviewed source")
    return entries, cache_texts


def _validate_person_identity(
    row: Dict[str, Any], candidate_ids: set[str], canonical_people: Dict[str, tuple[str, str, str]],
    manifest: Dict[str, Dict[str, Any]],
) -> None:
    person_name = row.get("person_name")
    person_id = row.get("canonical_person_id")
    if row.get("candidate_id") not in candidate_ids or not isinstance(person_name, str) or not person_name.strip():
        _fail("People Pilot person must have an in-scope named institution")
    disambiguator_source_id = row.get("person_identity_disambiguator_source_id")
    if disambiguator_source_id not in manifest or manifest[disambiguator_source_id].get("candidate_id") != row["candidate_id"]:
        _fail("People Pilot person identity needs a source-backed candidate-context disambiguator")
    if person_id != _expected_person_id(row):
        _fail("People Pilot canonical person ID must include name, candidate context, and source-backed disambiguator")
    context = (person_name, row["candidate_id"], disambiguator_source_id)
    existing = canonical_people.setdefault(person_id, context)
    if existing != context:
        _fail("People Pilot canonical person ID cannot point to different source contexts")
    if not row.get("person_identity_notes"):
        _fail("People Pilot person needs identity-resolution notes")


def _verify_anchor_cache(
    anchor: Dict[str, Any], cache_entries: Dict[str, Dict[str, Any]], cache_texts: Dict[str, str],
) -> None:
    source_id = anchor["source_id"]
    entry = cache_entries[source_id]
    method = anchor["quote_verification_method"]
    if method != entry["quote_verification_method"]:
        _fail("People Pilot anchor verification method must match its cache manifest entry")
    if method == "local_cache_substring_check":
        if source_id not in cache_texts or anchor["quote"] not in cache_texts[source_id]:
            _fail("People Pilot local cache must contain the asserted direct quote verbatim")
    elif entry["cache_status"] != "not_cached":
        _fail("People Pilot cached source cannot downgrade an anchor to manual-only verification")


def _attendance_records(
    observations: list[Dict[str, Any]], candidates_by_id: Dict[str, Dict[str, Any]], manifest: Dict[str, Dict[str, Any]],
    cache_entries: Dict[str, Dict[str, Any]], cache_texts: Dict[str, str],
) -> list[Dict[str, Any]]:
    candidate_ids = set(candidates_by_id)
    canonical_people: Dict[str, str] = {}
    records = []
    for row in observations:
        if row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail("Faculty, donor, honorary, unclear, or unknown relationship cannot enter notable attendance")
        _validate_person_identity(row, candidate_ids, canonical_people, manifest)
        if row.get("major_confidence") not in ALLOWED_MAJOR_CONFIDENCE:
            _fail("People Pilot attendance needs an allowed major-confidence value")
        if row.get("major_or_program") is None:
            if row.get("major_confidence") != "unknown" or row.get("null_reason") != "major_not_stated_in_accepted_source":
                _fail("Unknown People Pilot major needs a scoped null reason and unknown confidence")
        elif row.get("major_confidence") == "unknown":
            _fail("A stated People Pilot major cannot use unknown confidence")
        if not row.get("degree_or_program") and row.get("attendance_relationship") == "graduated":
            _fail("Graduated People Pilot record needs an explicitly supported degree or program")
        source_id = row.get("source_id")
        if (
            source_id not in manifest
            or manifest[source_id].get("field_domain") != "attendance"
            or manifest[source_id].get("candidate_id") != row["candidate_id"]
        ):
            _fail("People Pilot attendance source must resolve to attendance domain")
        result = dict(row)
        candidate = candidates_by_id[row["candidate_id"]]
        result["canonical_id"] = candidate["canonical_university_id"]
        result["university_display_name"] = candidate["display_name"]
        result["source_reference"] = manifest[source_id]["source_url_or_reference"]
        try:
            result["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, "attendance")
        except Stage3DFillBatch1ValidationError as error:
            _fail(str(error))
        _verify_anchor_cache(result["evidence_anchor"], cache_entries, cache_texts)
        result["evidence_type"] = "direct_quote"
        result["quote_verification_method"] = result["evidence_anchor"]["quote_verification_method"]
        if not result.get("relationship_notes") or len(result["relationship_notes"]) > MAX_SHORT_TEXT:
            _fail("People Pilot relationship notes must be a short non-empty explanation")
        records.append(result)
    if not 8 <= len(records) <= 12 or len({(row["candidate_id"], row["canonical_person_id"]) for row in records}) != len(records):
        _fail("People Pilot needs 8–12 unique reviewed notable-attendance records")
    return sorted(records, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))


def _program_records(
    slots: list[Dict[str, Any]], observations: list[Dict[str, Any]], manifest: Dict[str, Dict[str, Any]],
    attendance: list[Dict[str, Any]], cache_entries: Dict[str, Dict[str, Any]], cache_texts: Dict[str, str],
) -> list[Dict[str, Any]]:
    valid_slots = {(row["candidate_id"], row["normalized_program_name"]): row for row in slots}
    attended = {(row["candidate_id"], row["canonical_person_id"], row["attendance_relationship"]) for row in attendance}
    by_slot: Dict[tuple[str, str], Dict[str, Any]] = {}
    canonical_people: Dict[str, str] = {}
    for row in observations:
        key = (row.get("candidate_id"), row.get("normalized_program_name"))
        if key not in valid_slots or key in by_slot:
            _fail("People Pilot program-person record is duplicate or outside immutable slot scope")
        _validate_person_identity(row, {slot["candidate_id"] for slot in slots}, canonical_people, manifest)
        if row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail("People Pilot program person needs an allowed attendance relationship")
        if (row["candidate_id"], row["canonical_person_id"], row["attendance_relationship"]) not in attended:
            _fail("People Pilot program person must have a matching reviewed attendance record")
        if row.get("relationship_to_program") not in ALLOWED_PROGRAM_MATCHES or not row.get("match_notes"):
            _fail("People Pilot program person requires direct match type and short match notes")
        source_id = row.get("source_id")
        if (
            source_id not in manifest
            or manifest[source_id].get("field_domain") != "program_people"
            or manifest[source_id].get("candidate_id") != row["candidate_id"]
        ):
            _fail("People Pilot program person source must resolve to program_people domain")
        result = {**valid_slots[key], **row}
        result["source_reference"] = manifest[source_id]["source_url_or_reference"]
        try:
            result["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, "program_people")
        except Stage3DFillBatch1ValidationError as error:
            _fail(str(error))
        _verify_anchor_cache(result["evidence_anchor"], cache_entries, cache_texts)
        result["evidence_type"] = "direct_quote"
        result["quote_verification_method"] = result["evidence_anchor"]["quote_verification_method"]
        result["record_status"] = "identified"
        result["display_value"] = row["person_name"]
        by_slot[key] = result
    records = []
    for slot in slots:
        record = by_slot.get((slot["candidate_id"], slot["normalized_program_name"]))
        records.append(record or {
            **slot,
            "record_status": "source_review_not_completed",
            "display_value": None,
            "person_name": None,
            "canonical_person_id": None,
            "attendance_relationship": None,
            "relationship_to_program": None,
            "source_id": None,
            "source_reference": None,
            "evidence_anchor": None,
            "quote_verification_method": None,
            "match_notes": None,
            "confidence": None,
            "reviewed_scope": [],
            "reviewed_source_ids": [],
            "null_reason": "stage3d_fill_people_pilot_program_source_review_not_completed",
        })
    return records


def _exclusions(
    observations: list[Dict[str, Any]], candidate_ids: set[str], manifest: Dict[str, Dict[str, Any]]) -> list[Dict[str, Any]]:
    allowed = {"faculty_only", "donor_only", "honorary_degree_only", "unclear", "same_name_unresolved", "campus_mismatch", "source_insufficient"}
    records = []
    for row in observations:
        if row.get("candidate_id") not in candidate_ids or not row.get("person_name") or row.get("observed_relationship") not in allowed:
            _fail("People Pilot exclusion needs an in-scope person and allowed exclusion relationship")
        source_id = row.get("source_id")
        if source_id not in manifest or manifest[source_id].get("field_domain") != "exclusion":
            _fail("People Pilot exclusion needs an exclusion-domain source")
        result = dict(row)
        try:
            result["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, "exclusion")
        except Stage3DFillBatch1ValidationError as error:
            _fail(str(error))
        records.append(result)
    return sorted(records, key=lambda row: (row["candidate_id"], row["person_name"]))


def _build(
    candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path, batch1_dir: Path, batch2_dir: Path,
    source_manifest_path: Path, cache_manifest_path: Path, attendance_observations_path: Path,
    program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    candidates = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidates}
    candidates_by_id = {row["candidate_university_id"]: row for row in candidates}
    if len(candidates) != 62:
        _fail("People Pilot scope must remain the 62 Candidate v2 universities")
    fingerprints = {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
        "batch1": _fingerprints(batch1_dir, BATCH1_FILES),
        "batch2": _fingerprints(batch2_dir, (*BATCH2_OUTPUT_FILES, "stage3d-fill-batch2-validation-result.json")),
    }
    inputs = _load_inputs(source_manifest_path, cache_manifest_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    try:
        manifest = _manifest(inputs["sources"])
    except Stage3DFillBatch1ValidationError as error:
        _fail(str(error))
    cache_manifest, cache_texts = _validate_cache_manifest(inputs["cache"], manifest, cache_manifest_path)
    attendance = _attendance_records(
        inputs["attendance"].get("observations", []), candidates_by_id, manifest, cache_manifest, cache_texts,
    )
    slots = _slots(stage3c_dir, candidate_ids)
    program_people = _program_records(
        slots, inputs["program_people"].get("observations", []), manifest, attendance, cache_manifest, cache_texts,
    )
    exclusions = _exclusions(inputs["exclusions"].get("records", []), candidate_ids, manifest)
    if fingerprints != {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
        "batch1": _fingerprints(batch1_dir, BATCH1_FILES),
        "batch2": _fingerprints(batch2_dir, (*BATCH2_OUTPUT_FILES, "stage3d-fill-batch2-validation-result.json")),
    }:
        _fail("People Pilot must not mutate immutable upstream or Batch 1/2 inputs")
    methods = Counter(
        row["evidence_anchor"]["quote_verification_method"] for row in [*attendance, *[item for item in program_people if item["record_status"] == "identified"], *exclusions]
    )
    resolved_candidate_ids = {row["candidate_id"] for row in attendance}
    summary = {
        "record_type": "stage3d_fill_people_pilot_summary",
        "total_universities": 62,
        "notable_attendance_resolved_count": len(attendance),
        "notable_attendance_unresolved_count": 62 - len(resolved_candidate_ids),
        "program_people_identified_count": sum(row["record_status"] == "identified" for row in program_people),
        "program_people_source_review_not_completed_count": sum(row["record_status"] == "source_review_not_completed" for row in program_people),
        "exclusions_count": len(exclusions),
        "relationship_type_counts": dict(sorted(Counter(row["attendance_relationship"] for row in attendance).items())),
        "quote_verification_method_counts": dict(sorted(methods.items())),
        "local_cache_substring_check_count": methods["local_cache_substring_check"],
        "manual_verbatim_check_count": methods["manual_verbatim_check"],
        "cache_verified_quote_count": methods["local_cache_substring_check"],
        "cache_missing_count": methods["manual_verbatim_check"],
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "remaining_people_gaps": "The pilot validates a small reviewed attendance path; unreviewed program slots remain source_review_not_completed and no coverage-completeness claim is made.",
        "ready_for_claude_gate_review": True,
        "input_sha256": fingerprints,
        "deterministic_generation": True,
        **FLAGS_PEOPLE_PILOT,
    }
    artifacts = {
        "stage3d-fill-people-pilot-notable-attendance.json": {"metadata": {"record_type": "stage3d_fill_people_pilot_notable_attendance", **FLAGS_PEOPLE_PILOT}, "records": attendance},
        "stage3d-fill-people-pilot-program-people.json": {"metadata": {"record_type": "stage3d_fill_people_pilot_program_people", **FLAGS_PEOPLE_PILOT}, "records": program_people},
        "stage3d-fill-people-pilot-exclusions.json": {"record_type": "stage3d_fill_people_pilot_exclusions", "records": exclusions, **FLAGS_PEOPLE_PILOT},
        "stage3d-fill-people-pilot-source-manifest.json": {"record_type": "stage3d_fill_people_pilot_source_manifest", "sources": sorted(manifest.values(), key=lambda row: row["source_id"]), **FLAGS_PEOPLE_PILOT},
        "stage3d-fill-people-pilot-reviewed-source-cache-manifest.json": {"record_type": "stage3d_fill_people_pilot_reviewed_source_cache_manifest", "cache_root": inputs["cache"]["cache_root"], "cache_is_gitignored": True, "entries": sorted(cache_manifest.values(), key=lambda row: row["source_id"]), **FLAGS_PEOPLE_PILOT},
        "stage3d-fill-people-pilot-gap-disclosure.json": {"record_type": "stage3d_fill_people_pilot_gap_disclosure", "notable_attendance_source_gap_candidate_ids": sorted(candidate_ids - resolved_candidate_ids), "unreviewed_program_slots": [{"candidate_id": row["candidate_id"], "normalized_program_name": row["normalized_program_name"], "null_reason": row["null_reason"]} for row in program_people if row["record_status"] == "source_review_not_completed"], "source_limitations": "Only small-batch reviewed sources are included; unreviewed people and program slots remain source_review_not_completed rather than 无.", **FLAGS_PEOPLE_PILOT},
        "stage3d-fill-people-pilot-summary.json": summary,
    }
    _reject_ranking_fields(artifacts)
    return artifacts


def build_stage3d_fill_people_pilot(*args: Any, **kwargs: Any) -> Dict[str, Dict[str, Any]]:
    """Build the deterministic independent notable-attendance People Pilot."""
    return _build(*args, **kwargs)


def render_stage3d_fill_people_pilot_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-people-pilot-summary.json"]
    return "\n".join((
        "# Stage 3D-Fill People Pilot — Bulk Readiness Hardening", "",
        "This is a small, independent, source-limited and not-final People Pilot. It does not modify upstream artifacts, Batch 1/2, frontend, ranking fields, final universe, official selection memberships, or frontend export.", "",
        "## Coverage", "",
        f"- Reviewed notable attendance: {summary['notable_attendance_resolved_count']} records across {62 - summary['notable_attendance_unresolved_count']}/62 universities.",
        f"- Program people: {summary['program_people_identified_count']}/310 identified; {summary['program_people_source_review_not_completed_count']}/310 remain source_review_not_completed.",
        f"- Relationship types: {summary['relationship_type_counts']}; exclusions: {summary['exclusions_count']}.", "",
        "## Provenance and relationship safeguards", "",
        "- direct_quote must be copied verbatim from the cited source and match the reviewed short-quote allowlist. Paraphrases must not be labeled as direct_quote.",
        f"- Quote verification: {summary['cache_verified_quote_count']} local_cache_substring_check; {summary['cache_missing_count']} manual-only fallback. The cache manifest is committed, but full source caches remain gitignored and are never committed.",
        "- canonical_person_id includes normalized name, candidate context, and a source-backed disambiguator. Same-name facts from a different candidate/source context cannot auto-merge; unresolved ambiguity belongs in same_name_unresolved exclusions.",
        "- Only graduated, attended_no_degree, and alumnus_unspecified appear in attendance. Faculty, donor, honorary degree, unclear, campus mismatch, and same-name ambiguity are exclusions only.",
        "- Program people require a source-backed direct program or related-program match; career fame never supplies a major match. Unreviewed slots are not fake 无 records.",
        "- source_policy_violations = 0; ranking_field_contamination = 0. ready_for_claude_gate_review=true means auditable review input, not a PASS or complete claim.", "",
    ))


def validate_stage3d_fill_people_pilot(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path,
    batch1_dir: Path, batch2_dir: Path, source_manifest_path: Path, cache_manifest_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed on scope, relation, quote, cache-manifest, and output drift."""
    expected = _build(candidate_path, stage3c_dir, stage3d_fill_seed_dir, batch1_dir, batch2_dir, source_manifest_path, cache_manifest_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    if set(artifacts) != set(OUTPUT_FILES) or artifacts != expected:
        _fail("People Pilot artifacts must equal deterministic regeneration")
    _reject_ranking_fields(artifacts)
    attendance = artifacts["stage3d-fill-people-pilot-notable-attendance.json"]["records"]
    program_people = artifacts["stage3d-fill-people-pilot-program-people.json"]["records"]
    if not 8 <= len(attendance) <= 12 or len(program_people) != 310:
        _fail("People Pilot must retain its small attendance scope and all 310 program slots")
    if any(row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS for row in attendance):
        _fail("People Pilot cannot display excluded relationship types as attendance")
    if any(row["record_status"] == "source_review_not_completed" and row.get("display_value") is not None for row in program_people):
        _fail("Unreviewed People Pilot program slot cannot render a person or 无")
    summary = artifacts["stage3d-fill-people-pilot-summary.json"]
    if summary.get("total_universities") != 62 or summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0 or summary.get("ready_for_claude_gate_review") is not True:
        _fail("People Pilot summary is missing required scope, policy, or Gate-review disclosure")
    positive_count = len(attendance) + sum(row["record_status"] == "identified" for row in program_people)
    if (
        summary.get("cache_verified_quote_count") != summary.get("local_cache_substring_check_count")
        or summary.get("cache_missing_count") != summary.get("manual_verbatim_check_count")
        or summary["cache_verified_quote_count"] + summary["cache_missing_count"] != positive_count
    ):
        _fail("People Pilot summary must reconcile cache-verified and manual quote counts")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("People Pilot formal validation requires its report")
        raise AssertionError("unreachable") from error
    for text in ("direct_quote must be copied verbatim", "source_review_not_completed", "local_cache_substring_check", "source-backed disambiguator", "not a PASS or complete claim", "source_policy_violations = 0", "ranking_field_contamination = 0"):
        if text not in report:
            _fail("People Pilot report lacks required provenance disclosure")
    return {
        "record_type": "stage3d_fill_people_pilot_validation_result",
        "result": "passed",
        "total_universities": 62,
        "program_slot_count": 310,
        "local_cache_substring_check_count": summary["local_cache_substring_check_count"],
        "manual_verbatim_check_count": summary["manual_verbatim_check_count"],
        "cache_verified_quote_count": summary["cache_verified_quote_count"],
        "cache_missing_count": summary["cache_missing_count"],
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        **FLAGS_PEOPLE_PILOT,
    }


def write_stage3d_fill_people_pilot(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    """Write only independent People Pilot artifacts."""
    output.mkdir(parents=True, exist_ok=True)
    values = {**artifacts, "stage3d-fill-people-pilot-validation-result.json": validation}
    for name, value in values.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
