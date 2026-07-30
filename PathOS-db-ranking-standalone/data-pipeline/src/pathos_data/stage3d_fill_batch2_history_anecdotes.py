"""Independent reviewed History + Anecdotes Batch 2 overlay for Stage 3D-Fill."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from .stage3_program_mvp import FLAGS, _candidate_rows
from .stage3d_fill_batch1_history_anecdotes import (
    ALLOWED_RELATIONSHIPS,
    OUTPUT_FILES as BATCH1_OUTPUT_FILES,
    STAGE3C_FILES,
    STAGE3D_FILL_SEED_FILES,
    Stage3DFillBatch1ValidationError,
    _anchor,
    _attendance_records,
    _fingerprints,
    _flags_valid,
    _manifest,
    _narrative_fact,
    _program_records,
    _read_json,
    _reject_ranking_fields,
    _sha256,
    _slots,
    _status_rows as _batch1_status_rows,
)


BATCH1_FILES = (*BATCH1_OUTPUT_FILES, "stage3d-fill-batch1-validation-result.json")
OUTPUT_FILES = (
    "stage3d-fill-batch2-history.json", "stage3d-fill-batch2-anecdotes.json",
    "stage3d-fill-batch2-notable-attendance.json", "stage3d-fill-batch2-program-people.json",
    "stage3d-fill-batch2-source-manifest.json", "stage3d-fill-batch2-exclusions.json",
    "stage3d-fill-batch2-gap-disclosure.json", "stage3d-fill-batch2-summary.json",
)
FLAGS_BATCH2 = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillBatch2ValidationError(ValueError):
    """Raised when Batch 2 violates reviewed-source or overlay provenance rules."""


def _fail(message: str) -> None:
    raise Stage3DFillBatch2ValidationError(message)


def _status_rows(
    candidates: list[Dict[str, Any]], facts: list[Dict[str, Any]], status_key: str, text_key: str,
) -> list[Dict[str, Any]]:
    """Retain Batch 1's schema while identifying Batch 2's own intake gaps."""
    rows = _batch1_status_rows(candidates, facts, status_key, text_key)
    for row in rows:
        if row[status_key] == "source_review_not_completed":
            row["null_reason"] = f"stage3d_fill_batch2_{status_key}_source_review_not_completed"
    return rows


def _batch2_program_records(
    slots: list[Dict[str, Any]], observations: list[Dict[str, Any]], manifest: Dict[str, Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """Reuse strict person validation without leaking Batch 1 gap identifiers."""
    records = _program_records(slots, observations, manifest)
    for row in records:
        if row["record_status"] == "source_review_not_completed":
            row["null_reason"] = "stage3d_fill_batch2_program_source_review_not_completed"
    return records


def _batch1_counts(batch1_dir: Path, candidate_ids: set[str]) -> Dict[str, int]:
    paths = {name: batch1_dir / name for name in BATCH1_FILES}
    if any(not path.exists() for path in paths.values()):
        _fail("Batch 2 requires the immutable complete Batch 1 artifact bundle")
    history = _read_json(paths["stage3d-fill-batch1-history.json"])
    anecdotes = _read_json(paths["stage3d-fill-batch1-anecdotes.json"])
    result = _read_json(paths["stage3d-fill-batch1-validation-result.json"])
    if result.get("result") != "passed" or {
        row.get("candidate_id") for row in history.get("universities", [])
    } != candidate_ids or {row.get("candidate_id") for row in anecdotes.get("universities", [])} != candidate_ids:
        _fail("Batch 2 requires a valid immutable 62-school Batch 1 baseline")
    return {
        "history": len(history.get("facts", [])),
        "anecdotes": len(anecdotes.get("facts", [])),
    }


def _load_inputs(
    source_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    documents = {
        "sources": _read_json(source_manifest_path), "history": _read_json(history_observations_path),
        "anecdote": _read_json(anecdote_observations_path), "attendance": _read_json(attendance_observations_path),
        "program_people": _read_json(program_people_observations_path), "exclusions": _read_json(exclusions_path),
    }
    expected = {
        "sources": "stage3d_fill_batch2_source_manifest",
        "history": "stage3d_fill_batch2_history_observations",
        "anecdote": "stage3d_fill_batch2_anecdote_observations",
        "attendance": "stage3d_fill_batch2_attendance_observations",
        "program_people": "stage3d_fill_batch2_program_people_observations",
        "exclusions": "stage3d_fill_batch2_exclusions",
    }
    if any(documents[name].get("record_type") != value for name, value in expected.items()):
        _fail("Stage 3D-Fill Batch 2 input record type is invalid")
    return documents


def _build(
    candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path, batch1_dir: Path,
    source_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path,
) -> Dict[str, Dict[str, Any]]:
    candidates = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidates}
    candidates_by_id = {row["candidate_university_id"]: row for row in candidates}
    if len(candidates) != 62:
        _fail("Batch 2 scope must remain the 62 Candidate v2 universities")
    fingerprints = {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
        "batch1": _fingerprints(batch1_dir, BATCH1_FILES),
    }
    counts = _batch1_counts(batch1_dir, candidate_ids)
    inputs = _load_inputs(
        source_manifest_path, history_observations_path, anecdote_observations_path,
        attendance_observations_path, program_people_observations_path, exclusions_path,
    )
    try:
        manifest = _manifest(inputs["sources"])
        history = [_narrative_fact(row, manifest, "history", candidates_by_id, "history_summary") for row in inputs["history"].get("observations", [])]
        anecdotes = [_narrative_fact(row, manifest, "anecdote", candidates_by_id, "anecdote_text") for row in inputs["anecdote"].get("observations", [])]
        slots = _slots(stage3c_dir, candidate_ids)
        program_people = _batch2_program_records(slots, inputs["program_people"].get("observations", []), manifest)
        attendance = _attendance_records(inputs["attendance"].get("observations", []), candidates_by_id, manifest)
    except Stage3DFillBatch1ValidationError as error:
        _fail(str(error))
    if len({row["candidate_id"] for row in history}) != len(history) or len({row["candidate_id"] for row in anecdotes}) != len(anecdotes):
        _fail("Batch 2 permits at most one reviewed history and anecdote fact per university")
    batch1_history = _read_json(batch1_dir / "stage3d-fill-batch1-history.json").get("facts", [])
    batch1_anecdotes = _read_json(batch1_dir / "stage3d-fill-batch1-anecdotes.json").get("facts", [])
    if {row["candidate_id"] for row in history}.intersection(row["candidate_id"] for row in batch1_history):
        _fail("Batch 2 history facts cannot duplicate immutable Batch 1 facts")
    if {row["candidate_id"] for row in anecdotes}.intersection(row["candidate_id"] for row in batch1_anecdotes):
        _fail("Batch 2 anecdote facts cannot duplicate immutable Batch 1 facts")
    if any(row.get("record_status") == "no_qualifying_person_found" for row in program_people):
        _fail("Batch 2 scoped 无 requires a separately reviewed non-empty source scope")
    history_rows = _status_rows(candidates, history, "history_status", "history_summary")
    anecdote_rows = _status_rows(candidates, anecdotes, "anecdote_status", "anecdote_text")
    methods = Counter(fact["evidence_anchor"]["quote_verification_method"] for fact in [*history, *anecdotes, *attendance])
    if fingerprints != {
        "candidate_v2": {str(candidate_path): _sha256(candidate_path)},
        "stage3c": _fingerprints(stage3c_dir, STAGE3C_FILES),
        "stage3d_fill_seed": _fingerprints(stage3d_fill_seed_dir, STAGE3D_FILL_SEED_FILES),
        "batch1": _fingerprints(batch1_dir, BATCH1_FILES),
    }:
        _fail("Batch 2 must not mutate Candidate v2, Stage 3C, Stage 3D-Fill seed, or Batch 1 inputs")
    summary = {
        "record_type": "stage3d_fill_batch2_summary", "total_universities": 62,
        "batch2_history_resolved_count": len(history), "batch2_anecdotes_resolved_count": len(anecdotes),
        "cumulative_history_resolved_count_after_batch2": counts["history"] + len(history),
        "cumulative_anecdotes_resolved_count_after_batch2": counts["anecdotes"] + len(anecdotes),
        "notable_attendance_resolved_count": len(attendance),
        "program_people_identified_count": sum(row["record_status"] == "identified" for row in program_people),
        "program_people_source_review_not_completed_count": sum(row["record_status"] == "source_review_not_completed" for row in program_people),
        "source_review_not_completed_count": (62 - len(history)) + (62 - len(anecdotes)) + sum(row["record_status"] == "source_review_not_completed" for row in program_people),
        "scoped_none_count": 0, "quote_verification_method_counts": dict(sorted(methods.items())),
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "remaining_people_narrative_gaps": "Batch 2 is a small reviewed-source expansion; all unreviewed fields remain source_review_not_completed rather than 无.",
        "ready_for_claude_gate_review": True, "input_sha256": fingerprints, "deterministic_generation": True,
        **FLAGS_BATCH2,
    }
    artifacts = {
        "stage3d-fill-batch2-history.json": {"metadata": {"record_type": "stage3d_fill_batch2_history", **FLAGS_BATCH2}, "universities": history_rows, "facts": sorted(history, key=lambda row: row["candidate_id"])},
        "stage3d-fill-batch2-anecdotes.json": {"metadata": {"record_type": "stage3d_fill_batch2_anecdotes", **FLAGS_BATCH2}, "universities": anecdote_rows, "facts": sorted(anecdotes, key=lambda row: row["candidate_id"])},
        "stage3d-fill-batch2-notable-attendance.json": {"metadata": {"record_type": "stage3d_fill_batch2_notable_attendance", **FLAGS_BATCH2}, "records": attendance},
        "stage3d-fill-batch2-program-people.json": {"metadata": {"record_type": "stage3d_fill_batch2_program_people", **FLAGS_BATCH2}, "records": program_people},
        "stage3d-fill-batch2-source-manifest.json": {"record_type": "stage3d_fill_batch2_source_manifest", "sources": sorted(manifest.values(), key=lambda row: row["source_id"]), **FLAGS_BATCH2},
        "stage3d-fill-batch2-exclusions.json": {"record_type": "stage3d_fill_batch2_exclusions", "records": sorted(inputs["exclusions"].get("records", []), key=lambda row: str(row)), **FLAGS_BATCH2},
        "stage3d-fill-batch2-gap-disclosure.json": {"record_type": "stage3d_fill_batch2_gap_disclosure", "history_source_gap_candidate_ids": sorted(candidate_ids - {row["candidate_id"] for row in history}), "anecdote_source_gap_candidate_ids": sorted(candidate_ids - {row["candidate_id"] for row in anecdotes}), "unreviewed_program_slots": [{"candidate_id": row["candidate_id"], "normalized_program_name": row["normalized_program_name"], "null_reason": row["null_reason"]} for row in program_people if row["record_status"] == "source_review_not_completed"], "source_limitations": "Batch 2 only adds version-controlled reviewed direct evidence and leaves unreviewed fields as source_review_not_completed.", **FLAGS_BATCH2},
        "stage3d-fill-batch2-summary.json": summary,
    }
    _reject_ranking_fields(artifacts)
    return artifacts


def build_stage3d_fill_batch2(*args: Any, **kwargs: Any) -> Dict[str, Dict[str, Any]]:
    """Build the deterministic, independent Stage 3D-Fill Batch 2 overlay."""
    return _build(*args, **kwargs)


def render_stage3d_fill_batch2_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-batch2-summary.json"]
    return "\n".join((
        "# Stage 3D-Fill Batch 2 — Reviewed History + Anecdotes Report", "",
        "Batch 2 is a small, independent, source-limited, not-final overlay. It does not modify Batch 1 or upstream artifacts, frontend, ranking fields, final universe, official selection memberships, or frontend export.",
        "", "## Coverage", "",
        f"- Batch 2 history: {summary['batch2_history_resolved_count']}/62; cumulative reviewed history after Batch 2: {summary['cumulative_history_resolved_count_after_batch2']}/62.",
        f"- Batch 2 anecdotes: {summary['batch2_anecdotes_resolved_count']}/62; cumulative reviewed anecdotes after Batch 2: {summary['cumulative_anecdotes_resolved_count_after_batch2']}/62.",
        f"- Notable attendance: {summary['notable_attendance_resolved_count']}; program people identified: {summary['program_people_identified_count']}/310.",
        f"- Program slots kept as source_review_not_completed: {summary['program_people_source_review_not_completed_count']}; scoped 无: {summary['scoped_none_count']}.",
        "", "## Provenance safeguards", "",
        "- direct_quote must be copied verbatim from the cited source and match the reviewed short-quote allowlist. Paraphrases must not be labeled as direct_quote.",
        "- Each positive fact records manual_verbatim_check or local_cache_substring_check. History and anecdotes are short paraphrases, not copied source text.",
        "- source_review_not_completed is an intake gap, not a claim that a person, history, or anecdote does not exist; this Batch 2 did not fabricate 无.",
        "- Only graduated, attended_no_degree, and alumnus_unspecified can appear as alumni/attendees. Faculty, donor, honorary, and unclear relationships are excluded.",
        "- source_policy_violations = 0; ranking_field_contamination = 0. Batch 2 is ready for a future combined Claude Gate review, not a PASS claim.", "",
    ))


def validate_stage3d_fill_batch2(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, stage3d_fill_seed_dir: Path,
    batch1_dir: Path, source_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path,
    attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed on Batch 2 provenance, scope, cumulative-count, or output drift."""
    expected = _build(candidate_path, stage3c_dir, stage3d_fill_seed_dir, batch1_dir, source_manifest_path, history_observations_path, anecdote_observations_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    if set(artifacts) != set(OUTPUT_FILES) or artifacts != expected:
        _fail("Batch 2 artifacts must equal deterministic regeneration")
    _reject_ranking_fields(artifacts)
    history = artifacts["stage3d-fill-batch2-history.json"]
    anecdotes = artifacts["stage3d-fill-batch2-anecdotes.json"]
    program_people = artifacts["stage3d-fill-batch2-program-people.json"]["records"]
    attendance = artifacts["stage3d-fill-batch2-notable-attendance.json"]["records"]
    if len(history.get("universities", [])) != 62 or len(anecdotes.get("universities", [])) != 62 or len(program_people) != 310:
        _fail("Batch 2 must disclose 62 history/anecdote status rows and 310 program slots")
    if any(row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS for row in attendance):
        _fail("Batch 2 attendance cannot include excluded relationship types")
    if any(row.get("record_status") == "source_review_not_completed" and row.get("display_value") is not None for row in program_people):
        _fail("Unreviewed Batch 2 program slot cannot render a person or 无")
    summary = artifacts["stage3d-fill-batch2-summary.json"]
    if not _flags_valid(summary) or summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0 or summary.get("ready_for_claude_gate_review") is not True:
        _fail("Batch 2 flags, policy counters, or Claude-review readiness are invalid")
    if summary.get("cumulative_history_resolved_count_after_batch2") != 16 or summary.get("cumulative_anecdotes_resolved_count_after_batch2") != 16:
        _fail("Batch 2 cumulative coverage must reconcile with immutable Batch 1")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("Batch 2 formal validation requires its report")
        raise AssertionError("unreachable") from error
    for text in ("direct_quote must be copied verbatim", "source_review_not_completed", "source_policy_violations = 0", "ranking_field_contamination = 0", "not a PASS claim"):
        if text not in report:
            _fail("Batch 2 report lacks mandatory provenance disclosure")
    return {"record_type": "stage3d_fill_batch2_validation_result", "result": "passed", "total_universities": 62, "program_slot_count": 310, "source_policy_violations": 0, "ranking_field_contamination": 0, **FLAGS_BATCH2}


def write_stage3d_fill_batch2(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    """Write only independent Batch 2 artifacts, never Batch 1, upstream, or frontend files."""
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3d-fill-batch2-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
