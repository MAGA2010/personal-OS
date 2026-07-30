"""Independent reviewed History + Anecdotes Batch 1 overlay for Stage 3D-Fill."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .stage3_program_mvp import FLAGS, _candidate_rows
from .universe_candidate_v2 import validate_source_policy_use


STAGE3C_FILES = (
    "stage3c-universities.json", "stage3c-official-major-sources.json", "stage3c-official-majors.json",
    "stage3c-demo-programs-overlay.json", "stage3c-tuition-deepening.json", "stage3c-highest-lowest-tuition.json",
    "stage3c-gap-disclosure.json", "stage3c-summary.json", "stage3c-validation-result.json",
)
STAGE3D_FILL_SEED_FILES = (
    "stage3d-fill-program-people.json", "stage3d-fill-notable-attendance.json", "stage3d-fill-history.json",
    "stage3d-fill-anecdotes.json", "stage3d-fill-exclusions.json", "stage3d-fill-source-manifest.json",
    "stage3d-fill-gap-disclosure.json", "stage3d-fill-summary.json", "stage3d-fill-validation-result.json",
)
OUTPUT_FILES = (
    "stage3d-fill-batch1-history.json", "stage3d-fill-batch1-anecdotes.json",
    "stage3d-fill-batch1-notable-attendance.json", "stage3d-fill-batch1-program-people.json",
    "stage3d-fill-batch1-source-manifest.json", "stage3d-fill-batch1-exclusions.json",
    "stage3d-fill-batch1-gap-disclosure.json", "stage3d-fill-batch1-summary.json",
)
ALLOWED_DOMAINS = {"history", "anecdote", "attendance", "program_people"}
ALLOWED_RELATIONSHIPS = {"graduated", "attended_no_degree", "alumnus_unspecified"}
EXCLUDED_RELATIONSHIPS = {"faculty_only", "donor_only", "honorary_degree_only", "unclear"}
ALLOWED_MAJOR_CONFIDENCE = {"direct", "inferred_from_degree", "unknown"}
QUOTE_VERIFICATION_METHODS = {"manual_verbatim_check", "local_cache_substring_check"}
MAX_SHORT_TEXT = 280
FLAGS_BATCH1 = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillBatch1ValidationError(ValueError):
    """Raised when Batch 1 source intake or outputs violate provenance policy."""


def _fail(message: str) -> None:
    raise Stage3DFillBatch1ValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3D-Fill Batch 1 input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3D-Fill Batch 1 input must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprints(directory: Path, names: Iterable[str]) -> Dict[str, str]:
    values = {}
    for name in names:
        path = directory / name
        if not path.exists():
            _fail(f"Missing immutable Batch 1 input: {path}")
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
    source_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    paths = {
        "sources": source_manifest_path, "history": history_observations_path, "anecdote": anecdote_observations_path,
        "attendance": attendance_observations_path, "program_people": program_people_observations_path,
        "exclusions": exclusions_path,
    }
    documents = {name: _read_json(path) for name, path in paths.items()}
    expected_types = {
        "sources": "stage3d_fill_batch1_source_manifest",
        "history": "stage3d_fill_batch1_history_observations",
        "anecdote": "stage3d_fill_batch1_anecdote_observations",
        "attendance": "stage3d_fill_batch1_attendance_observations",
        "program_people": "stage3d_fill_batch1_program_people_observations",
        "exclusions": "stage3d_fill_batch1_exclusions",
    }
    if any(documents[name].get("record_type") != record_type for name, record_type in expected_types.items()):
        _fail("Stage 3D-Fill Batch 1 input record type is invalid")
    return documents


def _manifest(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for source in document.get("sources", []):
        required = (
            "source_id", "candidate_id", "field_domain", "source_type", "source_title",
            "source_url_or_reference", "publisher", "accessed_date", "source_confidence",
        )
        if not isinstance(source, dict) or any(not source.get(field) for field in required):
            _fail("Batch 1 source manifest entry is incomplete")
        if source["source_id"] in result or source["field_domain"] not in ALLOWED_DOMAINS:
            _fail("Batch 1 source manifest has duplicate or unsupported source")
        quotes = source.get("verified_direct_quotes")
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(quote, str) or not quote.strip() or len(quote.strip()) > MAX_SHORT_TEXT for quote in quotes
        ):
            _fail("Batch 1 source manifest requires reviewed short direct quotes")
        validate_source_policy_use(str(source["publisher"]), "detail", has_field_provenance=True)
        result[source["source_id"]] = dict(source)
    return result


def _anchor(value: Any, manifest: Dict[str, Dict[str, Any]], domain: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or value.get("evidence_type") != "direct_quote":
        _fail("Batch 1 affirmative fact requires a direct-quote evidence anchor")
    source_id, quote, method = value.get("source_id"), value.get("quote"), value.get("quote_verification_method")
    if source_id not in manifest or manifest[source_id].get("field_domain") != domain:
        _fail("Batch 1 anchor source cannot resolve to its asserted field domain")
    if not isinstance(quote, str) or not quote.strip() or len(quote.strip()) > MAX_SHORT_TEXT:
        _fail("Batch 1 quote must be a short non-empty string")
    if method not in QUOTE_VERIFICATION_METHODS:
        _fail("Batch 1 direct quote needs an accepted verbatim verification method")
    quote = quote.strip()
    if quote not in manifest[source_id]["verified_direct_quotes"]:
        _fail("Batch 1 direct quote must match the reviewed source-manifest allowlist")
    return {
        "source_id": source_id,
        "evidence_type": "direct_quote",
        "quote": quote,
        "quote_verification_method": method,
    }


def _slots(stage3c_dir: Path, candidate_ids: set[str]) -> List[Dict[str, Any]]:
    rows = _read_json(stage3c_dir / "stage3c-demo-programs-overlay.json").get("universities", [])
    if len(rows) != 62 or {row.get("candidate_id") for row in rows} != candidate_ids:
        _fail("Batch 1 must use immutable Stage 3C's 62-school demo-program scope")
    slots: List[Dict[str, Any]] = []
    for university in sorted(rows, key=lambda row: row["candidate_id"]):
        programs = university.get("top_5_programs_for_demo", [])
        if len(programs) != 5:
            _fail("Batch 1 requires exactly five immutable demo programs per school")
        for program in programs:
            if not program.get("program_name") or not program.get("normalized_program_name"):
                _fail("Batch 1 demo program lacks a stable name")
            slots.append({
                "candidate_id": university["candidate_id"], "canonical_id": university["canonical_id"],
                "display_name": university["display_name"], "program_name": program["program_name"],
                "normalized_program_name": program["normalized_program_name"],
            })
    return slots


def _reject_ranking_fields(value: Any) -> None:
    forbidden = {
        "usnews_rank", "usnews_category", "ranking_family", "membership_reason",
        "national_top50_candidate", "program_top20_candidate",
    }
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden.intersection(current):
                _fail("Batch 1 detail output cannot contain U.S. News ranking fields")
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _narrative_fact(
    observation: Dict[str, Any], manifest: Dict[str, Dict[str, Any]], domain: str,
    candidates_by_id: Dict[str, Dict[str, Any]], text_key: str,
) -> Dict[str, Any]:
    candidate_id = observation.get("candidate_id")
    if candidate_id not in candidates_by_id or not observation.get("fact_id"):
        _fail("Batch 1 narrative observation is outside the fixed candidate scope")
    text = observation.get(text_key)
    if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_SHORT_TEXT:
        _fail("Batch 1 narrative must be a short non-empty paraphrase")
    source_id = observation.get("source_id")
    if source_id not in manifest:
        _fail("Batch 1 narrative source must resolve through the manifest")
    result = dict(observation)
    candidate = candidates_by_id[candidate_id]
    result["canonical_id"] = candidate["canonical_university_id"]
    result["display_name"] = candidate["display_name"]
    result[text_key] = text.strip()
    result["source_reference"] = manifest[source_id]["source_url_or_reference"]
    result["evidence_anchor"] = _anchor(observation.get("evidence_anchor"), manifest, domain)
    result["evidence_type"] = "direct_quote"
    result["quote_verification_method"] = result["evidence_anchor"]["quote_verification_method"]
    if domain == "anecdote" and observation.get("anecdote_type") not in {
        "founding", "campus_tradition", "notable_event", "academic_milestone", "cultural_fact", "other",
    }:
        _fail("Batch 1 anecdote requires an allowed anecdote_type")
    return result


def _status_rows(candidates: List[Dict[str, Any]], facts: List[Dict[str, Any]], status_key: str, text_key: str) -> List[Dict[str, Any]]:
    by_candidate = {fact["candidate_id"]: fact for fact in facts}
    rows = []
    for candidate in sorted(candidates, key=lambda row: row["candidate_university_id"]):
        candidate_id = candidate["candidate_university_id"]
        fact = by_candidate.get(candidate_id)
        rows.append({
            "candidate_id": candidate_id,
            "canonical_id": candidate["canonical_university_id"],
            "display_name": candidate["display_name"],
            status_key: "reviewed_fact_found" if fact else "source_review_not_completed",
            text_key: fact.get(text_key) if fact else None,
            "source_id": fact.get("source_id") if fact else None,
            "source_reference": fact.get("source_reference") if fact else None,
            "evidence_anchor": fact.get("evidence_anchor") if fact else None,
            "evidence_type": "direct_quote" if fact else None,
            "quote_verification_method": fact.get("evidence_anchor", {}).get("quote_verification_method") if fact else None,
            "confidence": fact.get("confidence") if fact else None,
            "null_reason": None if fact else f"stage3d_fill_batch1_{status_key}_source_review_not_completed",
        })
    return rows


def _program_records(slots: List[Dict[str, Any]], observations: List[Dict[str, Any]], manifest: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key = {}
    valid_keys = {(row["candidate_id"], row["normalized_program_name"]) for row in slots}
    for observation in observations:
        key = (observation.get("candidate_id"), observation.get("normalized_program_name"))
        if key not in valid_keys or key in by_key:
            _fail("Batch 1 program-person observation is duplicate or outside immutable slot scope")
        if observation.get("relationship_type") not in ALLOWED_RELATIONSHIPS or not observation.get("canonical_person_id") or not observation.get("person_name") or not observation.get("major_or_program"):
            _fail("Batch 1 program person requires resolved identity, allowed relationship, and direct major")
        source_id = observation.get("source_id")
        if source_id not in manifest:
            _fail("Batch 1 program person source must resolve through the manifest")
        by_key[key] = observation
    records = []
    for slot in slots:
        observation = by_key.get((slot["candidate_id"], slot["normalized_program_name"]))
        if observation is None:
            records.append({
                **slot, "record_status": "source_review_not_completed", "display_value": None,
                "canonical_person_id": None, "person_name": None, "relationship_type": None,
                "major_or_program": None, "source_id": None, "source_reference": None,
                "evidence_anchor": None, "reviewed_scope": [], "reviewed_source_ids": [],
                "null_reason": "stage3d_fill_batch1_program_source_review_not_completed",
            })
            continue
        source_id = observation["source_id"]
        records.append({
            **slot, "record_status": "identified", "display_value": observation["person_name"],
            "canonical_person_id": observation["canonical_person_id"], "person_name": observation["person_name"],
            "relationship_type": observation["relationship_type"], "major_or_program": observation["major_or_program"],
            "source_id": source_id, "source_reference": manifest[source_id]["source_url_or_reference"],
            "evidence_anchor": _anchor(observation.get("evidence_anchor"), manifest, "program_people"),
            "reviewed_scope": sorted(observation.get("reviewed_scope", [])),
            "reviewed_source_ids": sorted(observation.get("reviewed_source_ids", [source_id])), "null_reason": None,
        })
    return records


def _attendance_records(observations: List[Dict[str, Any]], candidates_by_id: Dict[str, Dict[str, Any]], manifest: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for observation in observations:
        relationship = observation.get("attendance_relationship")
        if relationship in EXCLUDED_RELATIONSHIPS:
            _fail("Faculty, donor, honorary, or unclear person cannot enter Batch 1 attendance")
        candidate_id = observation.get("candidate_id")
        if candidate_id not in candidates_by_id or relationship not in ALLOWED_RELATIONSHIPS:
            _fail("Batch 1 attendance needs an in-scope allowed student/alumni relationship")
        if not observation.get("canonical_person_id") or not observation.get("person_name"):
            _fail("Batch 1 attendance needs a resolved canonical person identity")
        if observation.get("major_confidence") not in ALLOWED_MAJOR_CONFIDENCE:
            _fail("Batch 1 attendance requires an allowed major confidence value")
        source_id = observation.get("source_id")
        if source_id not in manifest:
            _fail("Batch 1 attendance source must resolve through the manifest")
        if observation.get("major_or_program") is None and observation.get("null_reason") != "major_not_stated_in_accepted_source":
            _fail("Batch 1 attendance unknown major needs a scoped null reason")
        if observation.get("major_or_program") is None and observation.get("major_confidence") != "unknown":
            _fail("Batch 1 attendance unknown major must use unknown major confidence")
        result = dict(observation)
        candidate = candidates_by_id[candidate_id]
        result["canonical_id"] = candidate["canonical_university_id"]
        result["display_name"] = candidate["display_name"]
        result["source_reference"] = manifest[source_id]["source_url_or_reference"]
        result["evidence_anchor"] = _anchor(observation.get("evidence_anchor"), manifest, "attendance")
        result["evidence_type"] = "direct_quote"
        result["quote_verification_method"] = result["evidence_anchor"]["quote_verification_method"]
        records.append(result)
    return sorted(records, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))


def build_stage3d_fill_batch1(
    candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path, source_manifest_path: Path,
    history_observations_path: Path, anecdote_observations_path: Path, attendance_observations_path: Path,
    program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    """Build the deterministic, independent Stage 3D-Fill Batch 1 overlay."""
    candidates = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidates}
    candidates_by_id = {row["candidate_university_id"]: row for row in candidates}
    if len(candidates) != 62:
        _fail("Batch 1 scope must remain the 62 Candidate v2 universities")
    fingerprints = {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
    }
    inputs = _load_inputs(source_manifest_path, history_observations_path, anecdote_observations_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    manifest = _manifest(inputs["sources"])
    history = [_narrative_fact(row, manifest, "history", candidates_by_id, "history_summary") for row in inputs["history"].get("observations", [])]
    anecdotes = [_narrative_fact(row, manifest, "anecdote", candidates_by_id, "anecdote_text") for row in inputs["anecdote"].get("observations", [])]
    if len({row["candidate_id"] for row in history}) != len(history) or len({row["candidate_id"] for row in anecdotes}) != len(anecdotes):
        _fail("Batch 1 permits at most one reviewed history and anecdote fact per university")
    slots = _slots(stage3c_dir, candidate_ids)
    program_people = _program_records(slots, inputs["program_people"].get("observations", []), manifest)
    attendance = _attendance_records(inputs["attendance"].get("observations", []), candidates_by_id, manifest)
    history_rows = _status_rows(candidates, history, "history_status", "history_summary")
    anecdote_rows = _status_rows(candidates, anecdotes, "anecdote_status", "anecdote_text")
    methods = Counter(
        fact["evidence_anchor"]["quote_verification_method"] for fact in [*history, *anecdotes, *attendance]
    )
    if fingerprints != {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
    }:
        _fail("Batch 1 must not mutate Candidate v2, Stage 3C, or Stage 3D-Fill seed inputs")
    summary = {
        "record_type": "stage3d_fill_batch1_summary", "total_universities": 62,
        "history_resolved_count": len(history), "history_unresolved_count": 62 - len(history),
        "anecdotes_resolved_count": len(anecdotes), "anecdotes_unresolved_count": 62 - len(anecdotes),
        "notable_attendance_resolved_count": len(attendance),
        "program_people_identified_count": sum(row["record_status"] == "identified" for row in program_people),
        "program_people_source_review_not_completed_count": sum(row["record_status"] == "source_review_not_completed" for row in program_people),
        "scoped_none_count": 0,
        "source_review_not_completed_count": (62 - len(history)) + (62 - len(anecdotes)) + sum(row["record_status"] == "source_review_not_completed" for row in program_people),
        "quote_verification_method_counts": dict(sorted(methods.items())),
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "readiness_for_frontend_people_narrative_display": "partial" if history or anecdotes or attendance else "source_review_in_progress",
        "remaining_people_narrative_gaps": "Unreviewed fields remain explicit source_review_not_completed gaps; this Batch 1 overlay is not a final people or narrative database.",
        "input_sha256": fingerprints, "deterministic_generation": True, **FLAGS_BATCH1,
    }
    artifacts = {
        "stage3d-fill-batch1-history.json": {"metadata": {"record_type": "stage3d_fill_batch1_history", **FLAGS_BATCH1}, "universities": history_rows, "facts": sorted(history, key=lambda row: row["candidate_id"])},
        "stage3d-fill-batch1-anecdotes.json": {"metadata": {"record_type": "stage3d_fill_batch1_anecdotes", **FLAGS_BATCH1}, "universities": anecdote_rows, "facts": sorted(anecdotes, key=lambda row: row["candidate_id"])},
        "stage3d-fill-batch1-notable-attendance.json": {"metadata": {"record_type": "stage3d_fill_batch1_notable_attendance", **FLAGS_BATCH1}, "records": attendance},
        "stage3d-fill-batch1-program-people.json": {"metadata": {"record_type": "stage3d_fill_batch1_program_people", **FLAGS_BATCH1}, "records": program_people},
        "stage3d-fill-batch1-source-manifest.json": {"record_type": "stage3d_fill_batch1_source_manifest", "sources": sorted(manifest.values(), key=lambda row: row["source_id"]), **FLAGS_BATCH1},
        "stage3d-fill-batch1-exclusions.json": {"record_type": "stage3d_fill_batch1_exclusions", "records": sorted(inputs["exclusions"].get("records", []), key=lambda row: str(row)), **FLAGS_BATCH1},
        "stage3d-fill-batch1-gap-disclosure.json": {"record_type": "stage3d_fill_batch1_gap_disclosure", "history_source_gap_candidate_ids": sorted(candidate_ids - {row["candidate_id"] for row in history}), "anecdote_source_gap_candidate_ids": sorted(candidate_ids - {row["candidate_id"] for row in anecdotes}), "unreviewed_program_slots": [{"candidate_id": row["candidate_id"], "normalized_program_name": row["normalized_program_name"], "null_reason": row["null_reason"]} for row in program_people if row["record_status"] == "source_review_not_completed"], "source_limitations": "Only version-controlled reviewed sources create affirmative Batch 1 facts; no unreviewed field is rendered as 无.", **FLAGS_BATCH1},
        "stage3d-fill-batch1-summary.json": summary,
    }
    _reject_ranking_fields(artifacts)
    return artifacts


def render_stage3d_fill_batch1_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-batch1-summary.json"]
    return "\n".join((
        "# Stage 3D-Fill Batch 1 — Reviewed History + Anecdotes Report", "",
        "Batch 1 is an independent, source-limited, not-final overlay for the fixed Candidate v2 62-school scope. It does not modify upstream artifacts, frontend, ranking fields, final universe, official selection memberships, or frontend export.",
        "", "## Coverage", "",
        f"- History: {summary['history_resolved_count']}/62 reviewed facts; unresolved: {summary['history_unresolved_count']}.",
        f"- Anecdotes: {summary['anecdotes_resolved_count']}/62 reviewed facts; unresolved: {summary['anecdotes_unresolved_count']}.",
        f"- Notable attendance: {summary['notable_attendance_resolved_count']}; program people identified: {summary['program_people_identified_count']}/310.",
        f"- Program slots kept as source_review_not_completed: {summary['program_people_source_review_not_completed_count']}; scoped 无: {summary['scoped_none_count']}.",
        "", "## Provenance safeguards", "",
        "- direct_quote must be copied verbatim from the cited source. Paraphrases must not be labeled as direct_quote.",
        "- Each positive fact records manual_verbatim_check or local_cache_substring_check and matches a reviewed short-quote allowlist.",
        "- source_review_not_completed is an explicit intake gap, never a claim that a person, history, or anecdote does not exist.",
        "- Only graduated, attended_no_degree, and alumnus_unspecified can be rendered as alumni/attendees; faculty, donor, honorary, and unclear relationships are excluded.",
        "- History and anecdotes are short paraphrases; no full webpage, long biography, or long source text is committed.",
        "- source_policy_violations = 0; ranking_field_contamination = 0.", "",
    ))


def validate_stage3d_fill_batch1(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path,
    source_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed on Batch 1 scope, provenance, quote, policy, or output drift."""
    expected = build_stage3d_fill_batch1(candidate_path, stage3c_dir, stage3d_fill_seed_dir, source_manifest_path, history_observations_path, anecdote_observations_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    if set(artifacts) != set(OUTPUT_FILES) or artifacts != expected:
        _fail("Batch 1 artifacts must equal deterministic regeneration")
    _reject_ranking_fields(artifacts)
    history = artifacts["stage3d-fill-batch1-history.json"]
    anecdotes = artifacts["stage3d-fill-batch1-anecdotes.json"]
    program_people = artifacts["stage3d-fill-batch1-program-people.json"]["records"]
    attendance = artifacts["stage3d-fill-batch1-notable-attendance.json"]["records"]
    if len(history.get("universities", [])) != 62 or len(anecdotes.get("universities", [])) != 62 or len(program_people) != 310:
        _fail("Batch 1 must disclose 62 history/anecdote status rows and 310 program slots")
    if any(row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS for row in attendance):
        _fail("Batch 1 attendance cannot include excluded relationship types")
    if any(row.get("record_status") == "source_review_not_completed" and row.get("display_value") is not None for row in program_people):
        _fail("Unreviewed Batch 1 program slot cannot render a person or 无")
    summary = artifacts["stage3d-fill-batch1-summary.json"]
    if not _flags_valid(summary) or summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0:
        _fail("Batch 1 flags or policy counters are invalid")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("Batch 1 formal validation requires its report")
        raise AssertionError("unreachable") from error
    for text in ("direct_quote must be copied verbatim", "source_review_not_completed", "source_policy_violations = 0", "ranking_field_contamination = 0"):
        if text not in report:
            _fail("Batch 1 report lacks mandatory provenance disclosure")
    return {"record_type": "stage3d_fill_batch1_validation_result", "result": "passed", "total_universities": 62, "program_slot_count": 310, "source_policy_violations": 0, "ranking_field_contamination": 0, **FLAGS_BATCH1}


def write_stage3d_fill_batch1(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    """Write only independent Batch 1 artifacts, never upstream or frontend files."""
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3d-fill-batch1-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
