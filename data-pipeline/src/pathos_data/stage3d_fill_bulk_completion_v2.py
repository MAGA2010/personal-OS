"""Independent, cache-verified Stage 3D-Fill Bulk Completion v2 overlay."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from .stage3_program_mvp import FLAGS, _candidate_rows
from .stage3d_fill_batch1_history_anecdotes import _read_json, _sha256, _slots
from .universe_candidate_v2 import validate_source_policy_use


OUTPUT_FILES = (
    "stage3d-fill-bulk-v2-plan.json", "stage3d-fill-bulk-v2-history.json",
    "stage3d-fill-bulk-v2-anecdotes.json", "stage3d-fill-bulk-v2-notable-attendance.json",
    "stage3d-fill-bulk-v2-program-people.json", "stage3d-fill-bulk-v2-exclusions.json",
    "stage3d-fill-bulk-v2-source-manifest.json", "stage3d-fill-bulk-v2-cache-manifest.json",
    "stage3d-fill-bulk-v2-gap-disclosure.json", "stage3d-fill-bulk-v2-summary.json",
)
FLAGS_BULK = {**FLAGS, "final_universe_generated": False, "official_selection_memberships_generated": False, "frontend_export_generated": False}
ALLOWED_RELATIONSHIPS = {"graduated", "attended_no_degree", "alumnus_unspecified"}
MAX_QUOTE = 280
MAX_PARAPHRASE = 280


class Stage3DFillBulkCompletionV2ValidationError(ValueError):
    """Raised whenever Bulk v2 cannot prove its independent provenance boundary."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkCompletionV2ValidationError(message)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _source_maps(*directories: Path) -> Dict[str, Dict[str, Any]]:
    sources: Dict[str, Dict[str, Any]] = {}
    for directory in directories:
        for path in directory.glob("*-source-manifest.json"):
            document = _read_json(path)
            for row in document.get("sources", []):
                source_id = row.get("source_id")
                if source_id and source_id not in sources:
                    validate_source_policy_use(str(row.get("publisher")), "detail", has_field_provenance=True)
                    sources[source_id] = dict(row)
    return sources


def _cache_config(path: Path) -> tuple[Dict[str, Any], str]:
    document = _read_json(path)
    if document.get("record_type") != "stage3d_fill_bulk_v2_cache_configuration" or document.get("cache_is_gitignored") is not True:
        _fail("Bulk v2 must use a gitignored reviewed cache configuration")
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) != 1:
        _fail("Bulk v2 cache configuration must have one reviewed-excerpt entry")
    entry = entries[0]
    if entry.get("source_ids") != ["*"] or entry.get("quote_verification_method") != "local_cache_substring_check":
        _fail("Bulk v2 positive facts must default to local_cache_substring_check")
    cache_path = Path(entry.get("cache_path", ""))
    if not cache_path.is_absolute():
        cache_path = path.parents[2] / cache_path
    if not cache_path.is_file():
        _fail("Bulk v2 reviewed excerpt cache is missing")
    content = cache_path.read_text(encoding="utf-8")
    if hashlib.sha256(cache_path.read_bytes()).hexdigest() != entry.get("sha256"):
        _fail("Bulk v2 reviewed excerpt cache SHA-256 mismatch")
    if not entry.get("retrieval_or_review_notes"):
        _fail("Bulk v2 cache configuration requires review notes")
    return {**entry, "resolved_cache_path": str(cache_path)}, content


def _verify_anchor(row: Dict[str, Any], source: Dict[str, Any], cache: Dict[str, Any], content: str, domain: str) -> Dict[str, Any]:
    anchor = dict(row.get("evidence_anchor") or {})
    quote = anchor.get("quote")
    if row.get("source_id") != source.get("source_id") or anchor.get("source_id") != row.get("source_id"):
        _fail("Bulk v2 positive fact source IDs must resolve exactly")
    if anchor.get("evidence_type") != "direct_quote":
        _fail("Bulk v2 positive fact must retain a direct_quote evidence type")
    if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE:
        _fail("Bulk v2 evidence quote is missing or exceeds the short-quote limit")
    if quote not in content or source.get("source_url_or_reference") not in content:
        _fail("Bulk v2 direct quote must be a substring of its reviewed local cache")
    if source.get("field_domain") not in {domain, "attendance", "program_people"}:
        _fail("Bulk v2 source field domain is not allowed for this detail fact")
    return {"source_id": row["source_id"], "evidence_type": "direct_quote", "quote": quote, "quote_verification_method": "local_cache_substring_check"}


def _batch_facts(directory: Path, name: str) -> list[Dict[str, Any]]:
    return [dict(row) for row in _read_json(directory / name).get("facts", []) if row.get("source_id")]


def _status_rows(candidates: list[Dict[str, Any]], facts: list[Dict[str, Any]], kind: str, sources: Dict[str, Dict[str, Any]], cache: Dict[str, Any], content: str) -> list[Dict[str, Any]]:
    by_candidate = {row["candidate_id"]: row for row in facts}
    rows = []
    for candidate in candidates:
        candidate_id = candidate["candidate_university_id"]
        fact = by_candidate.get(candidate_id)
        base = {"candidate_id": candidate_id, "canonical_id": candidate["canonical_university_id"], "university_display_name": candidate["display_name"]}
        if fact is None:
            text_key = "history_summary" if kind == "history" else "anecdote_text"
            rows.append({**base, text_key: None, f"{kind}_status": "source_review_not_completed", "source_id": None, "source_url": None, "publisher": None, "evidence_anchor": None, "quote_verification_method": None, "confidence": None, "null_reason": f"stage3d_fill_bulk_v2_{kind}_source_review_not_completed"})
            continue
        source = sources.get(fact["source_id"])
        if source is None:
            _fail("Bulk v2 imported Batch fact lacks a source-manifest entry")
        anchor = _verify_anchor(fact, source, cache, content, kind)
        paraphrase = fact.get("history_summary") if kind == "history" else fact.get("anecdote_text")
        if not isinstance(paraphrase, str) or not paraphrase or len(paraphrase) > MAX_PARAPHRASE:
            _fail("Bulk v2 narrative paraphrase is missing or too long")
        record = {**base, **({"history_summary": paraphrase} if kind == "history" else {"anecdote_text": paraphrase, "anecdote_type": fact.get("anecdote_type")}), "source_id": fact["source_id"], "source_url": source["source_url_or_reference"], "publisher": source.get("publisher"), "evidence_anchor": anchor, "evidence_type": "direct_quote", "quote_verification_method": "local_cache_substring_check", "cache_reference": cache["cache_path"], "confidence": fact.get("confidence") or source.get("source_confidence"), "null_reason": None, "paraphrase_notes": fact.get("paraphrase_notes") or "Short paraphrase; the evidence anchor is the only direct quote."}
        rows.append(record)
    return sorted(rows, key=lambda row: row["candidate_id"])


def _person_id_valid(row: Dict[str, Any]) -> bool:
    person_id = row.get("canonical_person_id", "")
    return isinstance(person_id, str) and person_id.startswith("person:") and person_id.count(":") >= 3 and _slug(row.get("person_name", "")) in person_id


def _attendance_rows(pilot_dir: Path, candidates: Dict[str, Dict[str, Any]], sources: Dict[str, Dict[str, Any]], cache: Dict[str, Any], content: str, observations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    if observations:
        _fail("Bulk v2 does not accept unreviewed attendance observations; add a reviewed source intake first")
    records = []
    for row in _read_json(pilot_dir / "stage3d-fill-people-pilot-notable-attendance.json").get("records", []):
        if row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS or not _person_id_valid(row):
            _fail("Bulk v2 attendance must use allowed relationship and disambiguated canonical person ID")
        source = sources.get(row.get("source_id"))
        if source is None or row.get("candidate_id") not in candidates:
            _fail("Bulk v2 imported People Pilot attendance is out of scope or missing source")
        anchor = _verify_anchor(row, source, cache, content, "attendance")
        if row.get("major_or_program") is None and row.get("null_reason") != "major_not_stated_in_accepted_source":
            _fail("Bulk v2 unknown attendance major needs a scoped null reason")
        records.append({**row, "source_url": source["source_url_or_reference"], "publisher": source.get("publisher"), "evidence_anchor": anchor, "quote_verification_method": "local_cache_substring_check", "cache_reference": cache["cache_path"]})
    return sorted(records, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))


def _program_rows(stage3c_dir: Path, candidate_ids: set[str], observations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    if observations:
        for row in observations:
            if row.get("record_status") == "no_qualifying_person_found" and (not row.get("reviewed_scope") or not row.get("reviewed_source_ids")):
                _fail("Bulk v2 no_qualifying_person_found requires reviewed scope and source IDs")
            _fail("Bulk v2 program-person facts require a reviewed cache-backed intake and are not inferred from occupations")
    rows = []
    for slot in _slots(stage3c_dir, candidate_ids):
        rows.append({**slot, "record_status": "source_review_not_completed", "display_value": None, "person_name": None, "canonical_person_id": None, "attendance_relationship": None, "source_id": None, "source_url": None, "evidence_anchor": None, "quote_verification_method": None, "reviewed_scope": [], "reviewed_source_ids": [], "null_reason": "stage3d_fill_bulk_v2_program_source_review_not_completed"})
    return rows


def _reject_ranking_fields(value: Any) -> None:
    forbidden = {"usnews_rank", "numeric_rank", "displayed_rank", "ranking_family", "ranking_category"}
    if isinstance(value, dict):
        if forbidden & set(value):
            _fail("Detail/narrative overlay must not contaminate ranking fields")
        for item in value.values(): _reject_ranking_fields(item)
    elif isinstance(value, list):
        for item in value: _reject_ranking_fields(item)


def build_stage3d_fill_bulk_completion_v2(candidate_path: Path, stage3c_dir: Path, batch1_dir: Path, batch2_dir: Path, people_pilot_dir: Path, source_manifest_path: Path, cache_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path, attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path) -> Dict[str, Dict[str, Any]]:
    """Build a deterministic, independent Bulk v2 overlay from reviewed inputs only."""
    candidates = _candidate_rows(candidate_path)
    if len(candidates) != 62:
        _fail("Bulk v2 scope must remain Candidate v2's 62 universities")
    candidate_by_id = {row["candidate_university_id"]: row for row in candidates}
    input_docs = [_read_json(path) for path in (source_manifest_path, history_observations_path, anecdote_observations_path, attendance_observations_path, program_people_observations_path, exclusions_path)]
    expected_types = ("stage3d_fill_bulk_v2_source_intake_policy", "stage3d_fill_bulk_v2_history_observations", "stage3d_fill_bulk_v2_anecdote_observations", "stage3d_fill_bulk_v2_attendance_observations", "stage3d_fill_bulk_v2_program_people_observations", "stage3d_fill_bulk_v2_exclusions")
    if any(doc.get("record_type") != record_type for doc, record_type in zip(input_docs, expected_types)):
        _fail("Bulk v2 input document type is invalid")
    cache, content = _cache_config(cache_manifest_path)
    sources = _source_maps(batch1_dir, batch2_dir, people_pilot_dir)
    for source in input_docs[0].get("sources", []):
        source_id = source.get("source_id")
        if not source_id or source_id in sources or source.get("source_type") not in {"official_institutional", "official_archive", "trusted_reference"}:
            _fail("Bulk v2 new source must be unique and use an allowed reviewed source type")
        validate_source_policy_use(str(source.get("publisher")), "detail", has_field_provenance=True)
        sources[source_id] = dict(source)
    history_facts = _batch_facts(batch1_dir, "stage3d-fill-batch1-history.json") + _batch_facts(batch2_dir, "stage3d-fill-batch2-history.json") + list(input_docs[1].get("observations", []))
    anecdote_facts = _batch_facts(batch1_dir, "stage3d-fill-batch1-anecdotes.json") + _batch_facts(batch2_dir, "stage3d-fill-batch2-anecdotes.json") + list(input_docs[2].get("observations", []))
    history = _status_rows(candidates, history_facts, "history", sources, cache, content)
    anecdotes = _status_rows(candidates, anecdote_facts, "anecdote", sources, cache, content)
    attendance = _attendance_rows(people_pilot_dir, candidate_by_id, sources, cache, content, input_docs[3].get("observations", []))
    program_people = _program_rows(stage3c_dir, set(candidate_by_id), input_docs[4].get("observations", []))
    exclusions = input_docs[5].get("records", [])
    if exclusions:
        _fail("Bulk v2 exclusions require a reviewed cache-backed intake")
    positive = [row for row in history if row["source_id"]] + [row for row in anecdotes if row["source_id"]] + attendance
    used_sources = {row["source_id"] for row in positive}
    used_manifest = [sources[source_id] for source_id in sorted(used_sources)]
    cache_entries = [{"source_id": source_id, "source_url_or_reference": sources[source_id]["source_url_or_reference"], "cache_path": cache["cache_path"], "sha256": cache["sha256"], "cache_status": "cached", "quote_verification_method": "local_cache_substring_check", "retrieval_or_review_notes": cache["retrieval_or_review_notes"]} for source_id in sorted(used_sources)]
    counts = Counter(row["evidence_anchor"]["quote_verification_method"] for row in positive)
    history_gaps = sum(row["source_id"] is None for row in history)
    anecdote_gaps = sum(row["source_id"] is None for row in anecdotes)
    remaining_gaps = (
        f"History gaps: {history_gaps}; anecdote gaps: {anecdote_gaps}; "
        "program-person slots remain intentionally deferred and are not inferred."
    )
    summary = {"record_type": "stage3d_fill_bulk_v2_summary", "total_universities": 62, "history_resolved_count": 62 - history_gaps, "history_source_review_not_completed_count": history_gaps, "anecdotes_resolved_count": 62 - anecdote_gaps, "anecdotes_source_review_not_completed_count": anecdote_gaps, "notable_attendance_resolved_count": len(attendance), "notable_attendance_unresolved_count": 62 - len({row["candidate_id"] for row in attendance}), "program_people_identified_count": 0, "program_people_source_review_not_completed_count": len(program_people), "program_people_no_qualifying_person_found_count": 0, "exclusions_count": 0, "local_cache_substring_check_count": counts["local_cache_substring_check"], "manual_verbatim_check_count": 0, "cache_verified_quote_count": len(positive), "cache_missing_count": 0, "source_policy_violations": 0, "ranking_field_contamination": 0, "readiness_status": "history_anecdote_checkpoint_complete" if history_gaps == anecdote_gaps == 0 else "source_review_in_progress", "remaining_gaps": remaining_gaps, "not_final_reason": "Source-limited independent overlay; not a final People/Narrative dataset.", "deterministic_generation": True, **FLAGS_BULK}
    artifacts = {
        "stage3d-fill-bulk-v2-plan.json": {"record_type": "stage3d_fill_bulk_v2_plan", "scope_candidate_ids": sorted(candidate_by_id), "strategy": "Reuse reviewed upstream facts and add only cache-verified official history/anecdote observations; preserve any unreviewed field as source_review_not_completed.", **FLAGS_BULK},
        "stage3d-fill-bulk-v2-history.json": {"metadata": {"record_type": "stage3d_fill_bulk_v2_history", **FLAGS_BULK}, "universities": history},
        "stage3d-fill-bulk-v2-anecdotes.json": {"metadata": {"record_type": "stage3d_fill_bulk_v2_anecdotes", **FLAGS_BULK}, "universities": anecdotes},
        "stage3d-fill-bulk-v2-notable-attendance.json": {"metadata": {"record_type": "stage3d_fill_bulk_v2_notable_attendance", **FLAGS_BULK}, "records": attendance},
        "stage3d-fill-bulk-v2-program-people.json": {"metadata": {"record_type": "stage3d_fill_bulk_v2_program_people", **FLAGS_BULK}, "records": program_people},
        "stage3d-fill-bulk-v2-exclusions.json": {"record_type": "stage3d_fill_bulk_v2_exclusions", "records": [], **FLAGS_BULK},
        "stage3d-fill-bulk-v2-source-manifest.json": {"record_type": "stage3d_fill_bulk_v2_source_manifest", "sources": used_manifest, **FLAGS_BULK},
        "stage3d-fill-bulk-v2-cache-manifest.json": {"record_type": "stage3d_fill_bulk_v2_cache_manifest", "cache_root": "cache/stage3d-fill-bulk-completion-v2/", "cache_is_gitignored": True, "entries": cache_entries, **FLAGS_BULK},
        "stage3d-fill-bulk-v2-gap-disclosure.json": {"record_type": "stage3d_fill_bulk_v2_gap_disclosure", "history_source_review_not_completed_candidate_ids": [row["candidate_id"] for row in history if row["source_id"] is None], "anecdote_source_review_not_completed_candidate_ids": [row["candidate_id"] for row in anecdotes if row["source_id"] is None], "program_people_status": "All unreviewed slots remain source_review_not_completed; no fake none records were generated.", "source_limitations": "Local caches preserve short reviewed excerpts only; they are gitignored and not page snapshots.", **FLAGS_BULK},
        "stage3d-fill-bulk-v2-summary.json": summary,
    }
    _reject_ranking_fields(artifacts)
    return artifacts


def render_stage3d_fill_bulk_completion_v2_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-bulk-v2-summary.json"]
    return "\n".join((
        "# Stage 3D-Fill Bulk Completion v2", "",
        "This independent overlay combines prior reviewed facts with additional reviewed official university history and anecdote intake. Every positive anchor uses local_cache_substring_check. It is source-limited, incomplete, and not final.", "",
        "## Coverage", "",
        f"- History: {summary['history_resolved_count']}/62 reviewed; {summary['history_source_review_not_completed_count']}/62 remain source_review_not_completed.",
        f"- Anecdotes: {summary['anecdotes_resolved_count']}/62 reviewed; {summary['anecdotes_source_review_not_completed_count']}/62 remain source_review_not_completed.",
        f"- Notable attendance: {summary['notable_attendance_resolved_count']} reviewed records.",
        f"- Program people: {summary['program_people_identified_count']}/310 identified; no unreviewed slot is displayed as 无.", "",
        "## Safeguards", "",
        "- Each positive direct_quote is copied verbatim into a gitignored minimal reviewed-excerpt cache; SHA-256 and substring checks are fail-closed.",
        "- Only graduated, attended_no_degree, and alumnus_unspecified can appear in attendance. Faculty, donor, honorary degree, visitor, speaker, unclear, and same-name ambiguity are not positive attendance.",
        "- Person IDs contain normalized name, candidate context, and a source-backed disambiguator; profession never supplies a program match.",
        "- source_policy_violations = 0; ranking_field_contamination = 0. No frontend, final universe, official memberships, or frontend export is generated.", "",
    ))


def validate_stage3d_fill_bulk_completion_v2(artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, batch1_dir: Path, batch2_dir: Path, people_pilot_dir: Path, source_manifest_path: Path, cache_manifest_path: Path, history_observations_path: Path, anecdote_observations_path: Path, attendance_observations_path: Path, program_people_observations_path: Path, exclusions_path: Path, report_path: Path) -> Dict[str, Any]:
    expected = build_stage3d_fill_bulk_completion_v2(candidate_path, stage3c_dir, batch1_dir, batch2_dir, people_pilot_dir, source_manifest_path, cache_manifest_path, history_observations_path, anecdote_observations_path, attendance_observations_path, program_people_observations_path, exclusions_path)
    if artifacts != expected or set(artifacts) != set(OUTPUT_FILES): _fail("Bulk v2 artifacts must equal deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-v2-summary.json"]
    if summary["total_universities"] != 62 or summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0 or summary["manual_verbatim_check_count"] != 0: _fail("Bulk v2 summary violates scope or source policy")
    if len(artifacts["stage3d-fill-bulk-v2-program-people.json"]["records"]) != 310: _fail("Bulk v2 must preserve all immutable demo-program slots")
    for row in artifacts["stage3d-fill-bulk-v2-notable-attendance.json"]["records"]:
        if row["attendance_relationship"] not in ALLOWED_RELATIONSHIPS or not _person_id_valid(row): _fail("Bulk v2 attendance relationship or person identity is invalid")
    report = report_path.read_text(encoding="utf-8")
    for phrase in ("local_cache_substring_check", "source_review_not_completed", "source-limited, incomplete, and not final", "source_policy_violations = 0", "ranking_field_contamination = 0"):
        if phrase not in report: _fail("Bulk v2 report lacks required limitation disclosure")
    return {"record_type": "stage3d_fill_bulk_v2_validation_result", "result": "passed", "total_universities": 62, "program_slot_count": 310, "cache_verified_quote_count": summary["cache_verified_quote_count"], "source_policy_violations": 0, "ranking_field_contamination": 0, **FLAGS_BULK}


def write_stage3d_fill_bulk_completion_v2(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3d-fill-bulk-v2-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
