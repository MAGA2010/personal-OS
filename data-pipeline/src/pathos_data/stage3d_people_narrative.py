"""Deterministic, source-limited Stage 3D people and narrative overlay."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .stage3_program_mvp import FLAGS, _candidate_rows
from .universe_candidate_v2 import validate_source_policy_use


STAGE3_FILES = (
    "program-mvp-universities.json", "program-mvp-programs.json", "program-mvp-tuition.json",
    "program-mvp-student-faculty.json", "program-mvp-majors.json", "program-mvp-gap-disclosure.json",
    "program-mvp-summary.json", "program-mvp-validation-result.json",
)
STAGE3B_FILES = (
    "stage3b-mvp-universities.json", "stage3b-student-faculty.json", "stage3b-identity-gap-fill.json",
    "stage3b-tuition-gap-fill.json", "stage3b-majors-gap-fill.json", "stage3b-program-gap-fill.json",
    "stage3b-gap-disclosure.json", "stage3b-summary.json", "stage3b-validation-result.json",
)
STAGE3C_FILES = (
    "stage3c-universities.json", "stage3c-official-major-sources.json", "stage3c-official-majors.json",
    "stage3c-demo-programs-overlay.json", "stage3c-tuition-deepening.json", "stage3c-highest-lowest-tuition.json",
    "stage3c-gap-disclosure.json", "stage3c-summary.json", "stage3c-validation-result.json",
)
STAGE3C2_FILES = (
    "stage3c2-nearest-towns.json", "stage3c2-place-source-manifest.json", "stage3c2-place-observations.json",
    "stage3c2-gap-disclosure.json", "stage3c2-summary.json", "stage3c2-validation-result.json",
)
OUTPUT_FILES = (
    "stage3d-universities.json", "stage3d-source-manifest.json", "stage3d-person-identity-mappings.json",
    "stage3d-top-program-notable-students.json", "stage3d-notable-attendance.json", "stage3d-history.json",
    "stage3d-interesting-facts.json", "stage3d-gap-disclosure.json", "stage3d-summary.json",
)
ALLOWED_STUDENT_RELATIONSHIPS = {"graduated", "attended_no_degree", "alumnus_unspecified"}
EXCLUDED_RELATIONSHIPS = {"faculty_only", "honorary_degree_only", "donor_only", "unclear"}
ALLOWED_TOP_PROGRAM_STATUSES = {"identified", "no_qualifying_person_found", "source_review_not_completed"}
MAX_ANCHOR_CHARS = 280
FLAGS_3D = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DPeopleNarrativeValidationError(ValueError):
    """Raised when a Stage 3D people/narrative source or artifact is invalid."""


def _fail(message: str) -> None:
    raise Stage3DPeopleNarrativeValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3D input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3D input must be a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprints(directory: Path, names: Iterable[str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for name in names:
        path = directory / name
        if not path.exists():
            _fail(f"Missing immutable Stage 3D input: {path}")
        values[str(path)] = _sha256(path)
    return dict(sorted(values.items()))


def _flags_valid(value: Dict[str, Any]) -> bool:
    return (
        value.get("source_limited") is True and value.get("incomplete") is True and value.get("not_final") is True
        and value.get("final_universe_generated") is False
        and value.get("official_selection_memberships_generated") is False
        and value.get("frontend_export_generated") is False
    )


def _anchor(value: Any, manifest: Dict[str, Dict[str, Any]], domain: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or value.get("evidence_type") != "direct_quote":
        _fail("Affirmative Stage 3D facts require a direct-quote evidence anchor")
    source_id = value.get("source_id")
    quote = value.get("quote")
    if source_id not in manifest or not isinstance(quote, str) or not quote.strip() or len(quote) > MAX_ANCHOR_CHARS:
        _fail("Stage 3D evidence anchor must resolve to a source and remain short")
    if manifest[source_id].get("field_domain") != domain:
        _fail("Stage 3D anchor source domain does not match the asserted field")
    return {"source_id": source_id, "evidence_type": "direct_quote", "quote": quote.strip()}


def _load_inputs(
    source_manifest_path: Path, person_mappings_path: Path, program_alias_mappings_path: Path,
    top_program_observations_path: Path, attendance_observations_path: Path,
    history_observations_path: Path, interesting_fact_observations_path: Path,
) -> Dict[str, Dict[str, Any]]:
    paths = {
        "source": source_manifest_path, "mappings": person_mappings_path, "aliases": program_alias_mappings_path,
        "top_program": top_program_observations_path, "attendance": attendance_observations_path,
        "history": history_observations_path, "facts": interesting_fact_observations_path,
    }
    documents = {name: _read_json(path) for name, path in paths.items()}
    expected_types = {
        "source": "stage3d_source_manifest", "mappings": "stage3d_person_identity_mappings",
        "aliases": "stage3d_program_alias_mappings", "top_program": "stage3d_top_program_notable_student_observations",
        "attendance": "stage3d_notable_attendance_observations", "history": "stage3d_history_observations",
        "facts": "stage3d_interesting_fact_observations",
    }
    if any(documents[name].get("record_type") != record_type for name, record_type in expected_types.items()):
        _fail("Stage 3D structured observation input has an invalid record type")
    return documents


def _manifest_by_id(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    sources = document.get("sources", [])
    if not isinstance(sources, list):
        _fail("Stage 3D source manifest sources must be a list")
    by_id = {}
    for source in sources:
        required = ("source_id", "source_type", "field_domain", "source_title", "source_url_or_reference", "publisher", "source_confidence")
        if not isinstance(source, dict) or any(not source.get(key) for key in required):
            _fail("Stage 3D affirmative source manifest entry is incomplete")
        source_id = source["source_id"]
        if source_id in by_id or source.get("field_domain") not in {"people", "attendance", "history", "interesting_fact"}:
            _fail("Stage 3D source manifest has duplicate or unsupported source")
        validate_source_policy_use(str(source.get("publisher")), "detail", has_field_provenance=True)
        by_id[source_id] = dict(source)
    return by_id


def _demo_slots(stage3c_dir: Path, candidate_ids: set[str]) -> List[Dict[str, Any]]:
    document = _read_json(stage3c_dir / "stage3c-demo-programs-overlay.json")
    rows = document.get("universities", [])
    if not isinstance(rows, list) or len(rows) != 62 or {row.get("candidate_id") for row in rows} != candidate_ids:
        _fail("Stage 3D must read the fixed 62-school Stage 3C demo-program overlay")
    slots = []
    for row in sorted(rows, key=lambda item: item["candidate_id"]):
        programs = row.get("top_5_programs_for_demo", [])
        if len(programs) != 5:
            _fail("Stage 3D requires exactly five immutable Stage 3C demo programs per university")
        for program in programs:
            if not program.get("normalized_program_name") or not program.get("program_name"):
                _fail("Stage 3C demo program is missing its stable name")
            slots.append({
                "candidate_id": row["candidate_id"], "canonical_id": row["canonical_id"],
                "display_name": row["display_name"], "program_name": program["program_name"],
                "normalized_program_name": program["normalized_program_name"],
                "program_source_basis": program.get("source_basis"),
            })
    return slots


def _validate_person_mapping(mapping: Dict[str, Any], manifest: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if mapping.get("identity_status") != "resolved" or not mapping.get("canonical_person_id") or not mapping.get("display_name"):
        _fail("Stage 3D affirmative people require a resolved canonical identity mapping")
    source_id = mapping.get("identity_source_id")
    if source_id not in manifest or manifest[source_id].get("field_domain") not in {"people", "attendance"}:
        _fail("Stage 3D person identity mapping requires a people or attendance source")
    mapping = dict(mapping)
    mapping["evidence_anchor"] = _anchor(mapping.get("evidence_anchor"), manifest, manifest[source_id]["field_domain"])
    return mapping


def _unreviewed_slot(slot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **slot, "record_status": "source_review_not_completed", "display_value": None,
        "canonical_person_id": None, "person_display_name": None, "relationship_type": None,
        "major_name": None, "major_match_status": None, "notability_basis": None,
        "source_id": None, "evidence_anchor": None, "reviewed_scope": [], "reviewed_source_ids": [],
        "reviewed_scope_note": "No approved people-source type was reviewed in this Stage 3D structured input batch.",
        "null_reason": "stage3d_source_review_not_completed",
        "evidence_anchor_null_reason": "no_affirmative_person_claim_to_anchor",
    }


def _no_result_slot(slot: Dict[str, Any], observation: Dict[str, Any]) -> Dict[str, Any]:
    scope = observation.get("reviewed_scope")
    sources = observation.get("reviewed_source_ids")
    if observation.get("display_value") != "无" or not isinstance(scope, list) or not scope or not isinstance(sources, list) or not sources:
        _fail("A Stage 3D 无 record requires an explicitly non-empty reviewed scope and source list")
    if observation.get("null_reason") != "qualifying_student_major_evidence_not_found_in_reviewed_sources":
        _fail("A Stage 3D 无 record must use its scoped absence null reason")
    return {
        **slot, "record_status": "no_qualifying_person_found", "display_value": "无",
        "canonical_person_id": None, "person_display_name": None, "relationship_type": None,
        "major_name": None, "major_match_status": None, "notability_basis": None,
        "source_id": None, "evidence_anchor": None, "reviewed_scope": sorted(scope),
        "reviewed_source_ids": sorted(sources), "reviewed_scope_note": observation.get("reviewed_scope_note"),
        "null_reason": "qualifying_student_major_evidence_not_found_in_reviewed_sources",
        "evidence_anchor_null_reason": "no_affirmative_person_claim_to_anchor",
    }


def _identified_slot(
    slot: Dict[str, Any], observation: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], mappings: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    relationship = observation.get("relationship_type")
    person_id = observation.get("canonical_person_id")
    if relationship not in ALLOWED_STUDENT_RELATIONSHIPS or person_id not in mappings:
        _fail("Stage 3D top-program person requires a source-backed allowed student relationship")
    if observation.get("major_match_status") not in {"direct_program_match", "direct_related_program_match"} or not observation.get("major_name"):
        _fail("Stage 3D top-program person requires direct source-backed major match evidence")
    source_id = observation.get("source_id")
    if source_id not in manifest:
        _fail("Stage 3D top-program person source must be in the manifest")
    return {
        **slot, "record_status": "identified", "display_value": observation.get("person_display_name"),
        "canonical_person_id": person_id, "person_display_name": observation.get("person_display_name"),
        "relationship_type": relationship, "major_name": observation.get("major_name"),
        "major_match_status": observation.get("major_match_status"), "notability_basis": observation.get("notability_basis"),
        "source_id": source_id, "evidence_anchor": _anchor(observation.get("evidence_anchor"), manifest, "people"),
        "reviewed_scope": sorted(observation.get("reviewed_scope", [])),
        "reviewed_source_ids": sorted(observation.get("reviewed_source_ids", [source_id])),
        "reviewed_scope_note": observation.get("reviewed_scope_note"), "null_reason": None,
        "evidence_anchor_null_reason": None,
    }


def _affirmative_attendance(
    observation: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], mappings: Dict[str, Dict[str, Any]], candidate_ids: set[str],
) -> Dict[str, Any]:
    relationship = observation.get("relationship_type")
    if observation.get("candidate_id") not in candidate_ids or relationship not in ALLOWED_STUDENT_RELATIONSHIPS:
        _fail("Stage 3D attendance must be in scope and use a student relationship")
    person_id, source_id = observation.get("canonical_person_id"), observation.get("source_id")
    if person_id not in mappings or source_id not in manifest:
        _fail("Stage 3D attendance requires identity and source provenance")
    record = dict(observation)
    record["attendance_status_label"] = relationship
    record["evidence_anchor"] = _anchor(observation.get("evidence_anchor"), manifest, "attendance")
    if record.get("major_name") is None and record.get("null_reason") != "major_not_stated_in_accepted_source":
        _fail("Unknown attendance major must use an explicit source-scoped null reason")
    return record


def _narrative_fact(observation: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], domain: str, candidate_ids: set[str]) -> Dict[str, Any]:
    if observation.get("candidate_id") not in candidate_ids or not observation.get("fact_id") or not observation.get("fact_text"):
        _fail("Stage 3D narrative fact is incomplete or out of scope")
    fact_text = str(observation["fact_text"]).strip()
    if len(fact_text) > MAX_ANCHOR_CHARS:
        _fail("Stage 3D narrative text must be a short paraphrase")
    record = dict(observation)
    record["fact_text"] = fact_text
    record["evidence_anchor"] = _anchor(observation.get("evidence_anchor"), manifest, domain)
    return record


def build_stage3d_people_narrative(
    candidate_path: Path, stage3_dir: Path, stage3b_dir: Path, stage3c_dir: Path, stage3c2_dir: Path,
    source_manifest_path: Path, person_mappings_path: Path, program_alias_mappings_path: Path,
    top_program_observations_path: Path, attendance_observations_path: Path,
    history_observations_path: Path, interesting_fact_observations_path: Path,
) -> Dict[str, Dict[str, Any]]:
    """Build an independent Stage 3D overlay without mutating any upstream artifact."""
    candidate_rows = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidate_rows}
    if len(candidate_rows) != 62:
        _fail("Stage 3D requires the immutable 62-school Candidate v2 scope")
    input_hashes = {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3": _fingerprints(stage3_dir, STAGE3_FILES),
        "stage3b": _fingerprints(stage3b_dir, STAGE3B_FILES),
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3c2": _fingerprints(stage3c2_dir, STAGE3C2_FILES),
    }
    inputs = _load_inputs(
        source_manifest_path, person_mappings_path, program_alias_mappings_path, top_program_observations_path,
        attendance_observations_path, history_observations_path, interesting_fact_observations_path,
    )
    manifest = _manifest_by_id(inputs["source"])
    mappings = {
        row.get("canonical_person_id"): _validate_person_mapping(row, manifest)
        for row in inputs["mappings"].get("mappings", [])
    }
    if None in mappings or len(mappings) != len(inputs["mappings"].get("mappings", [])):
        _fail("Stage 3D person mappings must have unique canonical IDs")
    slots = _demo_slots(stage3c_dir, candidate_ids)
    slot_keys = {(row["candidate_id"], row["normalized_program_name"]) for row in slots}
    observations = inputs["top_program"].get("observations", [])
    by_slot = {}
    for observation in observations:
        key = (observation.get("candidate_id"), observation.get("normalized_program_name"))
        if key not in slot_keys or key in by_slot or observation.get("record_status") not in {"identified", "no_qualifying_person_found"}:
            _fail("Stage 3D top-program observation is duplicate, out of scope, or invalid")
        by_slot[key] = observation
    top_rows = []
    for slot in slots:
        observation = by_slot.get((slot["candidate_id"], slot["normalized_program_name"]))
        if observation is None:
            top_rows.append(_unreviewed_slot(slot))
        elif observation["record_status"] == "identified":
            top_rows.append(_identified_slot(slot, observation, manifest, mappings))
        else:
            top_rows.append(_no_result_slot(slot, observation))
    attendance_observations = inputs["attendance"].get("observations", [])
    attendance, exclusions = [], []
    for observation in attendance_observations:
        if observation.get("relationship_type") in EXCLUDED_RELATIONSHIPS:
            exclusions.append({
                "candidate_id": observation.get("candidate_id"), "canonical_person_id": observation.get("canonical_person_id"),
                "relationship_type": observation.get("relationship_type"),
                "exclusion_reason": "non_student_relationship_cannot_populate_attendance_or_alumni_content",
            })
        else:
            attendance.append(_affirmative_attendance(observation, manifest, mappings, candidate_ids))
    history_facts = [_narrative_fact(row, manifest, "history", candidate_ids) for row in inputs["history"].get("observations", [])]
    interesting_facts = [_narrative_fact(row, manifest, "interesting_fact", candidate_ids) for row in inputs["facts"].get("observations", [])]
    history_by_candidate = {row["candidate_id"] for row in history_facts}
    facts_by_candidate = {row["candidate_id"] for row in interesting_facts}
    university_rows = []
    for candidate in sorted(candidate_rows, key=lambda row: row["candidate_university_id"]):
        candidate_id = candidate["candidate_university_id"]
        university_rows.append({
            "candidate_id": candidate_id, "canonical_id": candidate["canonical_university_id"],
            "display_name": candidate["display_name"],
            "people_status": "accepted_people_facts_found" if any(row["candidate_id"] == candidate_id and row["record_status"] == "identified" for row in top_rows) else "source_review_not_completed",
            "history_status": "accepted_history_facts_found" if candidate_id in history_by_candidate else "source_review_not_completed",
            "interesting_fact_status": "accepted_interesting_facts_found" if candidate_id in facts_by_candidate else "source_review_not_completed",
            "null_reason": "stage3d_source_review_not_completed" if candidate_id not in history_by_candidate and candidate_id not in facts_by_candidate else None,
        })
    if input_hashes != {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)}, "stage3": _fingerprints(stage3_dir, STAGE3_FILES),
        "stage3b": _fingerprints(stage3b_dir, STAGE3B_FILES), "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3c2": _fingerprints(stage3c2_dir, STAGE3C2_FILES),
    }:
        _fail("Stage 3D may not mutate immutable upstream inputs")
    status_counts = {status: sum(row["record_status"] == status for row in top_rows) for status in sorted(ALLOWED_TOP_PROGRAM_STATUSES)}
    summary = {
        "record_type": "stage3d_people_narrative_summary", "total_universities": 62,
        "top_program_slot_count": len(top_rows), "top_program_identified_count": status_counts["identified"],
        "top_program_scoped_wu_count": status_counts["no_qualifying_person_found"],
        "top_program_source_review_not_completed_count": status_counts["source_review_not_completed"],
        "notable_attendance_count": len(attendance), "history_fact_count": len(history_facts),
        "interesting_fact_count": len(interesting_facts), "excluded_relationship_count": len(exclusions),
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "input_sha256": input_hashes, "deterministic_generation": True, **FLAGS_3D,
    }
    return {
        "stage3d-universities.json": {"metadata": {"record_type": "stage3d_universities", **FLAGS_3D}, "universities": university_rows},
        "stage3d-source-manifest.json": {"record_type": "stage3d_source_manifest", "sources": sorted(manifest.values(), key=lambda row: row["source_id"]), **FLAGS_3D},
        "stage3d-person-identity-mappings.json": {"record_type": "stage3d_person_identity_mappings", "mappings": sorted(mappings.values(), key=lambda row: row["canonical_person_id"]), **FLAGS_3D},
        "stage3d-top-program-notable-students.json": {"metadata": {"record_type": "stage3d_top_program_notable_students", **FLAGS_3D}, "records": top_rows},
        "stage3d-notable-attendance.json": {"metadata": {"record_type": "stage3d_notable_attendance", **FLAGS_3D}, "records": sorted(attendance, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))},
        "stage3d-history.json": {"metadata": {"record_type": "stage3d_history", **FLAGS_3D}, "facts": sorted(history_facts, key=lambda row: (row["candidate_id"], row.get("event_year") or 0, row["fact_id"]))},
        "stage3d-interesting-facts.json": {"metadata": {"record_type": "stage3d_interesting_facts", **FLAGS_3D}, "facts": sorted(interesting_facts, key=lambda row: (row["candidate_id"], row["fact_id"]))},
        "stage3d-gap-disclosure.json": {
            "record_type": "stage3d_gap_disclosure", "source_review_not_completed_slots": [
                {"candidate_id": row["candidate_id"], "normalized_program_name": row["normalized_program_name"], "null_reason": row["null_reason"], "reviewed_scope": row["reviewed_scope"]}
                for row in top_rows if row["record_status"] == "source_review_not_completed"
            ], "scoped_wu_slots": [row for row in top_rows if row["record_status"] == "no_qualifying_person_found"],
            "excluded_relationships": exclusions,
            "history_source_review_not_completed_candidate_ids": sorted(candidate_ids - history_by_candidate),
            "interesting_fact_source_review_not_completed_candidate_ids": sorted(candidate_ids - facts_by_candidate),
            "source_limitations": "No approved people/history source observations are committed in this initial Stage 3D batch; unreviewed fields are explicit collection gaps, not claims of absence.",
            **FLAGS_3D,
        },
        "stage3d-summary.json": summary,
    }


def render_stage3d_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-summary.json"]
    return "\n".join((
        "# Stage 3D — People + Narrative Enrichment Report", "",
        "## Scope and status", "",
        "Stage 3D is an independent source-limited, not-final People + Narrative overlay for the fixed 62-school Candidate v2 scope. It does not modify Stage 3, Stage 3B, Stage 3C, Stage 3C2, Candidate v2, frontend, ranking fields, final universe, official selection memberships, or frontend export.",
        "", "- This initial deterministic batch contains no approved affirmative people, attendance, history, or interesting-fact observations.",
        "- Unreviewed top-program slots are explicit `source_review_not_completed` gaps, not 「无」 results and not claims that a real person or fact does not exist.",
        "- A future 「无」 record is permitted only after a non-empty reviewed_scope and reviewed_source_ids establish that no qualifying evidence was found in those reviewed sources.",
        "", "## Coverage", "",
        f"- Universities: {summary['total_universities']}/62.",
        f"- Top-program slots: {summary['top_program_slot_count']}; identified: {summary['top_program_identified_count']}; scoped 无: {summary['top_program_scoped_wu_count']}; source review not completed: {summary['top_program_source_review_not_completed_count']}.",
        f"- Notable attendance records: {summary['notable_attendance_count']}; history facts: {summary['history_fact_count']}; interesting facts: {summary['interesting_fact_count']}.",
        "", "## Relationship, provenance, and narrative safeguards", "",
        "- Only graduated, attended_no_degree, and alumnus_unspecified can populate student/alumni content. faculty_only, donor_only, honorary_degree_only, and unclear are exclusions.",
        "- Every affirmative source must resolve through the Stage 3D source manifest and a short direct-quote evidence anchor.",
        "- Narrative text is a short paraphrase; long copied biographies or institutional webpages are not committed.",
        "- source_policy_violations = 0; ranking_field_contamination = 0.",
        "",
    ))


def _reject_ranking_contamination(artifacts: Dict[str, Dict[str, Any]]) -> None:
    forbidden = {"usnews_rank", "usnews_category", "ranking_family", "membership_reason", "national_top50_candidate", "program_top20_candidate"}
    for document in artifacts.values():
        stack: List[Any] = [document]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                if forbidden.intersection(value):
                    _fail("Stage 3D detail artifacts cannot contain ranking fields")
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)


def validate_stage3d_people_narrative(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3_dir: Path, stage3b_dir: Path, stage3c_dir: Path, stage3c2_dir: Path,
    source_manifest_path: Path, person_mappings_path: Path, program_alias_mappings_path: Path,
    top_program_observations_path: Path, attendance_observations_path: Path,
    history_observations_path: Path, interesting_fact_observations_path: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed on provenance, relationship semantics, scope, or artifact drift."""
    expected = build_stage3d_people_narrative(
        candidate_path, stage3_dir, stage3b_dir, stage3c_dir, stage3c2_dir, source_manifest_path,
        person_mappings_path, program_alias_mappings_path, top_program_observations_path,
        attendance_observations_path, history_observations_path, interesting_fact_observations_path,
    )
    if set(artifacts) != set(OUTPUT_FILES) or artifacts != expected:
        _fail("Stage 3D requires every deterministic artifact and no altered artifact")
    _reject_ranking_contamination(artifacts)
    candidate_ids = {row["candidate_university_id"] for row in _candidate_rows(candidate_path)}
    universities = artifacts["stage3d-universities.json"].get("universities", [])
    if len(universities) != 62 or {row.get("candidate_id") for row in universities} != candidate_ids:
        _fail("Stage 3D university scope must remain exactly Candidate v2's 62 schools")
    slots = artifacts["stage3d-top-program-notable-students.json"].get("records", [])
    if len(slots) != 310 or len({(row.get("candidate_id"), row.get("normalized_program_name")) for row in slots}) != 310:
        _fail("Stage 3D requires exactly one person result per immutable demo-program slot")
    for row in slots:
        status = row.get("record_status")
        if status not in ALLOWED_TOP_PROGRAM_STATUSES:
            _fail("Stage 3D top-program status is invalid")
        if status == "source_review_not_completed":
            if row.get("display_value") is not None or row.get("reviewed_scope") != [] or row.get("reviewed_source_ids") != [] or row.get("null_reason") != "stage3d_source_review_not_completed" or not row.get("reviewed_scope_note"):
                _fail("Unreviewed top-program slots must remain explicit, non-无 collection gaps")
        elif status == "no_qualifying_person_found":
            if row.get("display_value") != "无" or not row.get("reviewed_scope") or not row.get("reviewed_source_ids") or row.get("null_reason") != "qualifying_student_major_evidence_not_found_in_reviewed_sources":
                _fail("Scoped 无 result is incomplete or misleading")
        elif row.get("relationship_type") not in ALLOWED_STUDENT_RELATIONSHIPS or not row.get("source_id") or not row.get("evidence_anchor"):
            _fail("Identified top-program person requires student relationship and source evidence")
    attendance = artifacts["stage3d-notable-attendance.json"].get("records", [])
    if any(row.get("relationship_type") not in ALLOWED_STUDENT_RELATIONSHIPS for row in attendance):
        _fail("Faculty, donor, honorary-degree, and unclear relationships cannot appear as attendance")
    summary = artifacts["stage3d-summary.json"]
    if summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0 or not _flags_valid(summary):
        _fail("Stage 3D summary violates policy or output boundary flags")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("Stage 3D report is required for formal validation")
        raise AssertionError("unreachable") from error
    required = ("source_review_not_completed", "not 「无」", "source_policy_violations = 0", "ranking_field_contamination = 0")
    if any(value not in report for value in required):
        _fail("Stage 3D report omits collection-gap or policy disclosure")
    return {
        "record_type": "stage3d_people_narrative_validation_result", "result": "passed", "total_universities": 62,
        "top_program_slot_count": 310, "source_policy_violations": 0, "ranking_field_contamination": 0,
        **FLAGS_3D,
    }


def write_stage3d_artifacts(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    """Write only the independent Stage 3D artifact bundle with stable JSON formatting."""
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3d-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
