"""Independent reviewed-source fill overlay for the Stage 3D framework."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .stage3_program_mvp import FLAGS, _candidate_rows
from .universe_candidate_v2 import validate_source_policy_use


STAGE3C_FILES = (
    "stage3c-universities.json", "stage3c-official-major-sources.json", "stage3c-official-majors.json",
    "stage3c-demo-programs-overlay.json", "stage3c-tuition-deepening.json", "stage3c-highest-lowest-tuition.json",
    "stage3c-gap-disclosure.json", "stage3c-summary.json", "stage3c-validation-result.json",
)
STAGE3D_FILES = (
    "stage3d-universities.json", "stage3d-source-manifest.json", "stage3d-person-identity-mappings.json",
    "stage3d-top-program-notable-students.json", "stage3d-notable-attendance.json", "stage3d-history.json",
    "stage3d-interesting-facts.json", "stage3d-gap-disclosure.json", "stage3d-summary.json",
    "stage3d-validation-result.json",
)
OUTPUT_FILES = (
    "stage3d-fill-program-people.json", "stage3d-fill-notable-attendance.json", "stage3d-fill-history.json",
    "stage3d-fill-anecdotes.json", "stage3d-fill-exclusions.json", "stage3d-fill-source-manifest.json",
    "stage3d-fill-gap-disclosure.json", "stage3d-fill-summary.json",
)
ALLOWED_STUDENT_RELATIONSHIPS = {"graduated", "attended_no_degree", "alumnus_unspecified"}
EXCLUDED_RELATIONSHIPS = {"faculty_only", "donor_only", "honorary_degree_only", "unclear"}
ALLOWED_PROGRAM_STATUSES = {"identified", "no_qualifying_person_found", "source_review_not_completed"}
ALLOWED_DOMAINS = {"program_people", "attendance", "history", "anecdote"}
MAX_SHORT_TEXT = 280
QUOTE_VERIFICATION_METHODS = {"manual_verbatim_check", "local_cache_substring_check"}
FLAGS_FILL = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillValidationError(ValueError):
    """Raised for invalid reviewed-source Stage 3D-Fill input or output."""


def _fail(message: str) -> None:
    raise Stage3DFillValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3D-Fill input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3D-Fill input must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprints(directory: Path, names: Iterable[str]) -> Dict[str, str]:
    values = {}
    for name in names:
        path = directory / name
        if not path.exists():
            _fail(f"Missing immutable Stage 3D-Fill input: {path}")
        values[str(path)] = _sha256(path)
    return dict(sorted(values.items()))


def _flags_valid(value: Dict[str, Any]) -> bool:
    return (
        value.get("source_limited") is True and value.get("incomplete") is True and value.get("not_final") is True
        and value.get("final_universe_generated") is False
        and value.get("official_selection_memberships_generated") is False
        and value.get("frontend_export_generated") is False
    )


def _load_inputs(
    source_manifest_path: Path, person_mappings_path: Path, program_observations_path: Path,
    attendance_observations_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
) -> Dict[str, Dict[str, Any]]:
    paths = {
        "sources": source_manifest_path, "mappings": person_mappings_path, "program": program_observations_path,
        "attendance": attendance_observations_path, "history": history_observations_path, "anecdote": anecdote_observations_path,
    }
    documents = {name: _read_json(path) for name, path in paths.items()}
    record_types = {
        "sources": "stage3d_fill_source_manifest", "mappings": "stage3d_fill_person_identity_mappings",
        "program": "stage3d_fill_program_people_observations", "attendance": "stage3d_fill_notable_attendance_observations",
        "history": "stage3d_fill_history_observations", "anecdote": "stage3d_fill_anecdote_observations",
    }
    if any(documents[name].get("record_type") != record_type for name, record_type in record_types.items()):
        _fail("Stage 3D-Fill input record type is invalid")
    return documents


def _manifest_by_id(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for source in document.get("sources", []):
        required = (
            "source_id", "candidate_id", "field_domain", "source_type", "source_title",
            "source_url_or_reference", "publisher", "accessed_date", "source_confidence",
        )
        if not isinstance(source, dict) or any(not source.get(field) for field in required):
            _fail("Reviewed Stage 3D-Fill source manifest entry is incomplete")
        if source["source_id"] in result or source["field_domain"] not in ALLOWED_DOMAINS:
            _fail("Stage 3D-Fill source manifest has duplicate or unsupported source")
        verified_quotes = source.get("verified_direct_quotes")
        if verified_quotes is not None and (
            not isinstance(verified_quotes, list)
            or not verified_quotes
            or any(not isinstance(quote, str) or not quote.strip() or len(quote.strip()) > MAX_SHORT_TEXT for quote in verified_quotes)
        ):
            _fail("Reviewed direct-quote manifest entries must be short non-empty strings")
        validate_source_policy_use(str(source["publisher"]), "detail", has_field_provenance=True)
        result[source["source_id"]] = dict(source)
    return result


def _anchor(value: Any, manifest: Dict[str, Dict[str, Any]], domain: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or value.get("evidence_type") != "direct_quote":
        _fail("Affirmative Stage 3D-Fill claim requires a direct-quote anchor")
    source_id, quote = value.get("source_id"), value.get("quote")
    verification_method = value.get("quote_verification_method")
    if source_id not in manifest or manifest[source_id].get("field_domain") != domain:
        _fail("Stage 3D-Fill anchor source cannot resolve to the asserted field domain")
    if not isinstance(quote, str) or not quote.strip() or len(quote.strip()) > MAX_SHORT_TEXT:
        _fail("Stage 3D-Fill anchor quote must be a short non-empty quote")
    if verification_method not in QUOTE_VERIFICATION_METHODS:
        _fail("Stage 3D-Fill direct quote needs an accepted verbatim verification method")
    quote = quote.strip()
    reviewed_quotes = manifest[source_id].get("verified_direct_quotes")
    if reviewed_quotes is not None and quote not in reviewed_quotes:
        _fail("Stage 3D-Fill direct quote must match a reviewed verbatim source quote")
    return {
        "source_id": source_id,
        "evidence_type": "direct_quote",
        "quote": quote,
        "quote_verification_method": verification_method,
    }


def _slots(stage3c_dir: Path, candidate_ids: set[str]) -> List[Dict[str, Any]]:
    rows = _read_json(stage3c_dir / "stage3c-demo-programs-overlay.json").get("universities", [])
    if len(rows) != 62 or {row.get("candidate_id") for row in rows} != candidate_ids:
        _fail("Stage 3D-Fill must use immutable Stage 3C's 62-school demo-program scope")
    slots = []
    for row in sorted(rows, key=lambda item: item["candidate_id"]):
        programs = row.get("top_5_programs_for_demo", [])
        if len(programs) != 5:
            _fail("Stage 3D-Fill requires exactly five immutable demo programs per school")
        for program in programs:
            slots.append({
                "candidate_id": row["candidate_id"], "canonical_id": row["canonical_id"],
                "display_name": row["display_name"], "program_name": program.get("program_name"),
                "normalized_program_name": program.get("normalized_program_name"),
                "program_source_basis": program.get("source_basis"),
            })
    if any(not slot["program_name"] or not slot["normalized_program_name"] for slot in slots):
        _fail("Stage 3C demo slot lacks a stable program name")
    return slots


def _unreviewed_program(slot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **slot, "record_status": "source_review_not_completed", "display_value": None,
        "canonical_person_id": None, "person_display_name": None, "relationship_type": None,
        "major_name": None, "notability_basis": None, "source_id": None, "evidence_anchor": None,
        "reviewed_scope": [], "reviewed_source_ids": [],
        "reviewed_scope_note": "No approved people-source type was reviewed for this slot in the Stage 3D-Fill input batch.",
        "null_reason": "stage3d_fill_source_review_not_completed",
    }


def _validate_person_mapping(row: Dict[str, Any], manifest: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if row.get("identity_status") != "resolved" or not row.get("canonical_person_id") or not row.get("display_name"):
        _fail("Affirmative Stage 3D-Fill person requires a resolved canonical person identity")
    source_id = row.get("identity_source_id")
    if source_id not in manifest or manifest[source_id]["field_domain"] not in {"program_people", "attendance"}:
        _fail("Stage 3D-Fill person identity needs a reviewed people or attendance source")
    result = dict(row)
    result["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, manifest[source_id]["field_domain"])
    return result


def _program_record(
    slot: Dict[str, Any], observation: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], mappings: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    status = observation.get("record_status")
    if status == "no_qualifying_person_found":
        if observation.get("display_value") != "无" or not observation.get("reviewed_scope") or not observation.get("reviewed_source_ids"):
            _fail("Scoped 无 requires non-empty reviewed_scope and reviewed_source_ids")
        if any(source_id not in manifest for source_id in observation["reviewed_source_ids"]):
            _fail("Scoped 无 reviewed source must resolve through the manifest")
        return {
            **_unreviewed_program(slot), "record_status": status, "display_value": "无",
            "reviewed_scope": sorted(observation["reviewed_scope"]),
            "reviewed_source_ids": sorted(observation["reviewed_source_ids"]),
            "reviewed_scope_note": observation.get("reviewed_scope_note"),
            "null_reason": "qualifying_student_major_evidence_not_found_in_reviewed_sources",
        }
    if status != "identified":
        _fail("Program person observation status must be identified or scoped 无")
    person_id, relationship, source_id = observation.get("canonical_person_id"), observation.get("relationship_type"), observation.get("source_id")
    if person_id not in mappings or relationship not in ALLOWED_STUDENT_RELATIONSHIPS or source_id not in manifest:
        _fail("Positive program person requires a resolved person, allowed relationship, and reviewed source")
    if not observation.get("person_display_name") or not observation.get("major_name"):
        _fail("Positive program person requires a direct, non-null major")
    return {
        **slot, "record_status": "identified", "display_value": observation["person_display_name"],
        "canonical_person_id": person_id, "person_display_name": observation["person_display_name"],
        "relationship_type": relationship, "major_name": observation["major_name"],
        "notability_basis": observation.get("notability_basis"), "source_id": source_id,
        "evidence_anchor": _anchor(observation.get("evidence_anchor"), manifest, "program_people"),
        "reviewed_scope": sorted(observation.get("reviewed_scope", [])),
        "reviewed_source_ids": sorted(observation.get("reviewed_source_ids", [source_id])),
        "reviewed_scope_note": observation.get("reviewed_scope_note"), "null_reason": None,
    }


def _narrative_record(row: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], domain: str, candidate_ids: set[str]) -> Dict[str, Any]:
    if row.get("candidate_id") not in candidate_ids or not row.get("fact_id") or not isinstance(row.get("paraphrase"), str):
        _fail("Stage 3D-Fill narrative observation is incomplete or outside candidate scope")
    if not row["paraphrase"].strip() or len(row["paraphrase"].strip()) > MAX_SHORT_TEXT:
        _fail("Stage 3D-Fill narrative must be a short paraphrase")
    result = dict(row)
    result["paraphrase"] = row["paraphrase"].strip()
    result["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, domain)
    return result


def _reject_ranking_fields(value: Any) -> None:
    forbidden = {"usnews_rank", "usnews_category", "ranking_family", "membership_reason", "national_top50_candidate", "program_top20_candidate"}
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden.intersection(current):
                _fail("Stage 3D-Fill detail output cannot contain U.S. News ranking fields")
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def build_stage3d_fill(
    candidate_path: Path, stage3c_dir: Path, stage3d_dir: Path, source_manifest_path: Path,
    person_mappings_path: Path, program_observations_path: Path, attendance_observations_path: Path,
    history_observations_path: Path, anecdote_observations_path: Path,
) -> Dict[str, Dict[str, Any]]:
    """Build a deterministic reviewed-source fill without mutating Stage 3D framework inputs."""
    candidates = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidates}
    if len(candidates) != 62:
        _fail("Stage 3D-Fill scope must remain the 62 Candidate v2 universities")
    fingerprints = {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_framework": _fingerprints(stage3d_dir, STAGE3D_FILES),
    }
    inputs = _load_inputs(source_manifest_path, person_mappings_path, program_observations_path, attendance_observations_path, history_observations_path, anecdote_observations_path)
    manifest = _manifest_by_id(inputs["sources"])
    mappings = {row.get("canonical_person_id"): _validate_person_mapping(row, manifest) for row in inputs["mappings"].get("mappings", [])}
    if None in mappings or len(mappings) != len(inputs["mappings"].get("mappings", [])):
        _fail("Stage 3D-Fill person mappings must have unique canonical IDs")
    slots = _slots(stage3c_dir, candidate_ids)
    valid_keys = {(row["candidate_id"], row["normalized_program_name"]) for row in slots}
    by_slot: Dict[tuple, Dict[str, Any]] = {}
    for observation in inputs["program"].get("observations", []):
        key = (observation.get("candidate_id"), observation.get("normalized_program_name"))
        if key not in valid_keys or key in by_slot:
            _fail("Stage 3D-Fill program observation is duplicate or outside immutable demo slots")
        by_slot[key] = observation
    program_records = [_program_record(slot, by_slot[(slot["candidate_id"], slot["normalized_program_name"])], manifest, mappings) if (slot["candidate_id"], slot["normalized_program_name"]) in by_slot else _unreviewed_program(slot) for slot in slots]
    attendance, exclusions = [], list(inputs["anecdote"].get("exclusions", []))
    for row in inputs["attendance"].get("observations", []):
        relationship = row.get("relationship_type")
        if relationship in EXCLUDED_RELATIONSHIPS:
            exclusions.append({"candidate_id": row.get("candidate_id"), "canonical_person_id": row.get("canonical_person_id"), "relationship_type": relationship, "exclusion_reason": "non_student_relationship_cannot_be_rendered_as_student_or_alumnus"})
            continue
        if row.get("candidate_id") not in candidate_ids or relationship not in ALLOWED_STUDENT_RELATIONSHIPS or row.get("canonical_person_id") not in mappings:
            _fail("Positive attendance requires an in-scope resolved person and student relationship")
        if row.get("source_id") not in manifest:
            _fail("Positive attendance source must resolve through the manifest")
        record = dict(row)
        record["attendance_status_label"] = relationship
        record["evidence_anchor"] = _anchor(row.get("evidence_anchor"), manifest, "attendance")
        if record.get("major_name") is None and record.get("null_reason") != "major_not_stated_in_accepted_source":
            _fail("Unknown attendance major requires a scoped null reason")
        attendance.append(record)
    history = [_narrative_record(row, manifest, "history", candidate_ids) for row in inputs["history"].get("observations", [])]
    anecdotes = [_narrative_record(row, manifest, "anecdote", candidate_ids) for row in inputs["anecdote"].get("observations", [])]
    history_ids = {row["candidate_id"] for row in history}
    anecdote_ids = {row["candidate_id"] for row in anecdotes}
    history_universities = []
    for candidate in sorted(candidates, key=lambda row: row["candidate_university_id"]):
        candidate_id = candidate["candidate_university_id"]
        history_universities.append({
            "candidate_id": candidate_id, "canonical_id": candidate["canonical_university_id"], "display_name": candidate["display_name"],
            "history_status": "reviewed_history_found" if candidate_id in history_ids else "source_review_not_completed",
            "null_reason": None if candidate_id in history_ids else "stage3d_fill_history_source_review_not_completed",
        })
    if fingerprints != {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)}, "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES), "stage3d_framework": _fingerprints(stage3d_dir, STAGE3D_FILES),
    }:
        _fail("Stage 3D-Fill may not mutate immutable Candidate v2, Stage 3C, or Stage 3D framework inputs")
    summary = {
        "record_type": "stage3d_fill_summary", "total_universities": 62, "program_slot_count": 310,
        "program_people_identified_count": sum(row["record_status"] == "identified" for row in program_records),
        "program_people_scoped_wu_count": sum(row["record_status"] == "no_qualifying_person_found" for row in program_records),
        "program_people_source_gap_count": sum(row["record_status"] == "source_review_not_completed" for row in program_records),
        "notable_attendance_count": len(attendance), "history_fact_count": len(history), "history_source_gap_count": 62 - len(history_ids),
        "anecdote_count": len(anecdotes), "anecdote_source_gap_count": 62 - len(anecdote_ids), "exclusion_count": len(exclusions),
        "source_policy_violations": 0, "ranking_field_contamination": 0, "input_sha256": fingerprints,
        "deterministic_generation": True, **FLAGS_FILL,
    }
    artifacts = {
        "stage3d-fill-program-people.json": {"metadata": {"record_type": "stage3d_fill_program_people", **FLAGS_FILL}, "records": program_records},
        "stage3d-fill-notable-attendance.json": {"metadata": {"record_type": "stage3d_fill_notable_attendance", **FLAGS_FILL}, "records": sorted(attendance, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))},
        "stage3d-fill-history.json": {"metadata": {"record_type": "stage3d_fill_history", **FLAGS_FILL}, "universities": history_universities, "facts": sorted(history, key=lambda row: (row["candidate_id"], row["fact_id"]))},
        "stage3d-fill-anecdotes.json": {"metadata": {"record_type": "stage3d_fill_anecdotes", **FLAGS_FILL}, "facts": sorted(anecdotes, key=lambda row: (row["candidate_id"], row["fact_id"]))},
        "stage3d-fill-exclusions.json": {"record_type": "stage3d_fill_exclusions", "records": sorted(exclusions, key=lambda row: (str(row.get("candidate_id")), str(row.get("canonical_person_id")))), **FLAGS_FILL},
        "stage3d-fill-source-manifest.json": {"record_type": "stage3d_fill_source_manifest", "sources": sorted(manifest.values(), key=lambda row: row["source_id"]), **FLAGS_FILL},
        "stage3d-fill-gap-disclosure.json": {"record_type": "stage3d_fill_gap_disclosure", "unreviewed_program_slots": [{"candidate_id": row["candidate_id"], "normalized_program_name": row["normalized_program_name"], "null_reason": row["null_reason"]} for row in program_records if row["record_status"] == "source_review_not_completed"], "scoped_wu_program_slots": [row for row in program_records if row["record_status"] == "no_qualifying_person_found"], "history_source_gap_candidate_ids": sorted(candidate_ids - history_ids), "anecdote_source_gap_candidate_ids": sorted(candidate_ids - anecdote_ids), "source_limitations": "Only version-controlled reviewed sources can create affirmative Stage 3D-Fill facts; all other fields remain explicit source gaps.", **FLAGS_FILL},
        "stage3d-fill-summary.json": summary,
    }
    _reject_ranking_fields(artifacts)
    return artifacts


def render_stage3d_fill_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-summary.json"]
    return "\n".join((
        "# Stage 3D-Fill — Reviewed People + Narrative Source Fill Report", "",
        "Stage 3D-Fill is an independent, source-limited, not-final overlay for Candidate v2's fixed 62-university scope. It does not modify Candidate v2, Stage 3/3B/3C/3C2/3D framework artifacts, frontend, ranking fields, final universe, official selection memberships, or frontend export.",
        "", "## Coverage", "",
        f"- Universities: {summary['total_universities']}/62.",
        f"- Demo-program slots: {summary['program_slot_count']}; identified: {summary['program_people_identified_count']}; scoped 无: {summary['program_people_scoped_wu_count']}; source-review gaps: {summary['program_people_source_gap_count']}.",
        f"- Notable attendance: {summary['notable_attendance_count']}; history facts: {summary['history_fact_count']}; anecdotes: {summary['anecdote_count']}.",
        "", "## Provenance safeguards", "",
        "- 无 means only that recorded reviewed source types and IDs yielded no qualifying evidence; it is not an absolute real-world absence claim.",
        "- source_review_not_completed means the source scope has not been reviewed and is never rendered as 无.",
        "- Only graduated, attended_no_degree, and alumnus_unspecified can populate student/alumni content. faculty_only, donor_only, honorary_degree_only, and unclear are excluded.",
        "- History and anecdotes are short paraphrases; evidence anchors are short quotes. direct_quote must be copied verbatim from the cited source; paraphrases must not be labeled as direct_quote.",
        "- Each direct quote records manual_verbatim_check or local_cache_substring_check; when a reviewed short-quote manifest is present, the anchor must match it exactly.",
        "- source_policy_violations = 0; ranking_field_contamination = 0.", "",
    ))


def validate_stage3d_fill(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, stage3d_dir: Path,
    source_manifest_path: Path, person_mappings_path: Path, program_observations_path: Path,
    attendance_observations_path: Path, history_observations_path: Path, anecdote_observations_path: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed if reviewed-source semantics, scope, or deterministic output drift."""
    expected = build_stage3d_fill(candidate_path, stage3c_dir, stage3d_dir, source_manifest_path, person_mappings_path, program_observations_path, attendance_observations_path, history_observations_path, anecdote_observations_path)
    if set(artifacts) != set(OUTPUT_FILES) or artifacts != expected:
        _fail("Stage 3D-Fill artifacts must equal complete deterministic regeneration")
    _reject_ranking_fields(artifacts)
    records = artifacts["stage3d-fill-program-people.json"].get("records", [])
    if len(records) != 310 or len({(row.get("candidate_id"), row.get("normalized_program_name")) for row in records}) != 310:
        _fail("Stage 3D-Fill requires exactly one result per immutable demo-program slot")
    for row in records:
        if row.get("record_status") not in ALLOWED_PROGRAM_STATUSES:
            _fail("Stage 3D-Fill program record has an unsupported status")
        if row["record_status"] == "source_review_not_completed" and (row.get("display_value") is not None or row.get("reviewed_scope") != [] or row.get("reviewed_source_ids") != []):
            _fail("Unreviewed program source gap cannot be rendered as 无 or an affirmative person")
        if row["record_status"] == "no_qualifying_person_found" and (row.get("display_value") != "无" or not row.get("reviewed_scope") or not row.get("reviewed_source_ids")):
            _fail("Scoped 无 requires reviewed scope and source IDs")
        if row["record_status"] == "identified" and row.get("relationship_type") not in ALLOWED_STUDENT_RELATIONSHIPS:
            _fail("Excluded relationship cannot populate a program person record")
    attendance = artifacts["stage3d-fill-notable-attendance.json"].get("records", [])
    if any(row.get("relationship_type") not in ALLOWED_STUDENT_RELATIONSHIPS for row in attendance):
        _fail("Excluded relationship cannot populate notable attendance")
    history = artifacts["stage3d-fill-history.json"].get("universities", [])
    if len(history) != 62:
        _fail("Stage 3D-Fill must disclose history coverage for every candidate university")
    summary = artifacts["stage3d-fill-summary.json"]
    if summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0 or not _flags_valid(summary):
        _fail("Stage 3D-Fill policy counters or output flags are invalid")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("Stage 3D-Fill formal validation requires its report")
        raise AssertionError("unreachable") from error
    if any(value not in report for value in ("source_review_not_completed", "not an absolute real-world absence claim", "source_policy_violations = 0", "ranking_field_contamination = 0")):
        _fail("Stage 3D-Fill report lacks required reviewed-source disclosures")
    return {"record_type": "stage3d_fill_validation_result", "result": "passed", "total_universities": 62, "program_slot_count": 310, "source_policy_violations": 0, "ranking_field_contamination": 0, **FLAGS_FILL}


def write_stage3d_fill(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    """Write only the independent Stage 3D-Fill artifact bundle."""
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3d-fill-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
