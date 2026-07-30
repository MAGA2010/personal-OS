"""Stage 2H evidence-bound assessment of program Top-20 completion readiness.

This module deliberately does not manufacture missing rankings.  It aggregates
only previously accepted, direct-evidence program records and records whether a
stream has enough evidence to establish its first 20 eligible entries and the
boundary tie group.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from .official_program_sweep import EDITION, FAMILY, SCOPE_STREAMS, STREAM_NAMES, _record_key
from .ranking_collection import RankingCollectionValidationError


class ProgramTop20CompletionValidationError(RankingCollectionValidationError):
    """Raised when a Stage 2H completion-attempt bundle is not auditable."""


def _fail(message: str) -> None:
    raise ProgramTop20CompletionValidationError(message)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read completion-attempt artifact: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(document, dict):
        _fail(f"Completion-attempt artifact must be an object: {path}")
    return document


def _load_prior_records(root: Path) -> list[Dict[str, Any]]:
    """Read accepted in-scope records, excluding this attempt's own bundle."""
    records: list[Dict[str, Any]] = []
    for path in root.rglob("*.json"):
        if "completion-programs-top20-attempt" in path.parts:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict) or not isinstance(document.get("records"), list):
            continue
        for record in document["records"]:
            if (
                isinstance(record, dict)
                and record.get("ranking_family") == FAMILY
                and record.get("verification_status") == "verified"
                and record.get("category_id") in SCOPE_STREAMS
            ):
                records.append(record)
    return records


def _assert_false_output_flags(document: Dict[str, Any], label: str) -> None:
    for field in (
        "canonical_universe_created",
        "selection_memberships_created",
        "frontend_export_created",
    ):
        if document.get(field) is not False:
            _fail(f"{label} must keep {field}=false")


def _source_ids(manifest: Dict[str, Any]) -> set[str]:
    if manifest.get("record_type") != "program_top20_completion_attempt_source_manifest":
        _fail("Completion-attempt source manifest type is invalid")
    if manifest.get("edition") != EDITION or not isinstance(manifest.get("sources"), list):
        _fail("Completion-attempt source manifest requires its edition and sources")
    resolved: set[str] = set()
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            _fail("Completion-attempt source manifest has an invalid source")
        if source["source_id"] in resolved:
            _fail("Completion-attempt source manifest contains duplicate source_id")
        for field in ("publisher", "source_type", "url", "accessibility_status"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                _fail(f"Completion-attempt source {source['source_id']} lacks {field}")
        resolved.add(source["source_id"])
    return resolved


def _validate_seed_batches(document: Dict[str, Any]) -> None:
    if document.get("record_type") != "program_top20_completion_attempt_seed_batches":
        _fail("Completion-attempt seed batch type is invalid")
    if document.get("edition") != EDITION or not isinstance(document.get("batches"), list):
        _fail("Completion-attempt seed batches require edition and batches")
    # Stage 2H may legitimately add no rows when no lawful complete source is
    # available.  Any record would need the pre-existing hardened validator;
    # this attempt intentionally records no new accepted evidence.
    if any(not isinstance(batch, dict) or batch.get("records") for batch in document["batches"]):
        _fail("Completion-attempt must not claim new accepted records without a separate hardened seed import")


def _validate_coverage(coverage: Dict[str, Any], existing: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if coverage.get("record_type") != "program_top20_completion_attempt_coverage_matrix" or coverage.get("edition") != EDITION:
        _fail("Completion-attempt coverage matrix type or edition is invalid")
    _assert_false_output_flags(coverage, "Completion-attempt coverage matrix")
    rows = coverage.get("streams")
    if not isinstance(rows, list) or len(rows) != len(SCOPE_STREAMS):
        _fail("Completion-attempt coverage must represent all in-scope streams")
    counts = {stream: 0 for stream in SCOPE_STREAMS}
    for record in existing:
        counts[record["category_id"]] += 1
    by_stream: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("stream_id") not in SCOPE_STREAMS:
            _fail("Completion-attempt coverage contains an out-of-scope stream")
        stream = row["stream_id"]
        if stream in by_stream:
            _fail("Completion-attempt coverage contains a duplicate stream")
        if row.get("accepted_record_count") != counts[stream]:
            _fail("Completion-attempt coverage count does not match accepted corpus evidence")
        if row.get("newly_added_accepted_count") != 0:
            _fail("Completion-attempt must not claim unvalidated new accepted records")
        status = row.get("stream_status")
        if status not in {"complete", "incomplete", "manual_seed_needed", "no_verified_records", "partial_only", "source_blocked_or_unavailable"}:
            _fail("Completion-attempt coverage has an invalid stream status")
        proof = row.get("completion_proof")
        is_complete = status == "complete"
        if is_complete:
            if not isinstance(proof, dict) or proof.get("first_20_entries_verified") is not True or proof.get("boundary_tie_group_verified") is not True:
                _fail("A stream may be complete only with first-20 and boundary-tie proof")
            if counts[stream] < 20:
                _fail("A complete stream cannot have fewer than 20 accepted entries")
        elif row.get("complete_top20_with_boundary_ties") is not False:
            _fail("Non-complete stream must disclose incomplete Top-20 boundary coverage")
        if counts[stream] == 0 and status not in {"manual_seed_needed", "no_verified_records", "partial_only", "source_blocked_or_unavailable"}:
            _fail("A stream with no accepted evidence cannot be marked incomplete or complete")
        if counts[stream] > 0 and status == "no_verified_records":
            _fail("A stream with accepted evidence cannot be marked no_verified_records")
        by_stream[stream] = row
    if set(by_stream) != SCOPE_STREAMS:
        _fail("Completion-attempt coverage omitted an in-scope stream")
    return by_stream


def _validate_supporting_documents(
    identities: Dict[str, Any], candidates: Dict[str, Any], gap_report: Dict[str, Any],
    dedupe: Dict[str, Any], manual_seed: Dict[str, Any], summary: Dict[str, Any],
    coverage: Dict[str, Dict[str, Any]], source_ids: set[str], existing: list[Dict[str, Any]],
) -> None:
    if identities.get("record_type") != "program_top20_completion_attempt_identity_mappings" or identities.get("mappings") != []:
        _fail("Completion-attempt cannot add or mutate identity mappings")
    if candidates.get("record_type") != "program_top20_completion_attempt_candidate_observations" or not isinstance(candidates.get("observations"), list):
        _fail("Completion-attempt candidate observations are invalid")
    for observation in candidates["observations"]:
        if observation.get("source_id") not in source_ids or observation.get("category_id") not in SCOPE_STREAMS:
            _fail("Completion-attempt observation must resolve its source and stream")
        if observation.get("disposition") not in {"outside_top20_scope", "insufficient_direct_evidence", "source_blocked_or_unavailable"}:
            _fail("Completion-attempt observation has an invalid disposition")
    if gap_report.get("record_type") != "program_top20_completion_attempt_gap_report":
        _fail("Completion-attempt gap report type is invalid")
    _assert_false_output_flags(gap_report, "Completion-attempt gap report")
    gaps = gap_report.get("stream_gaps")
    if not isinstance(gaps, list) or {gap.get("stream_id") for gap in gaps if isinstance(gap, dict)} != SCOPE_STREAMS:
        _fail("Completion-attempt gap report must disclose every stream")
    if dedupe.get("record_type") != "program_top20_completion_attempt_dedupe_report":
        _fail("Completion-attempt dedupe report type is invalid")
    _assert_false_output_flags(dedupe, "Completion-attempt dedupe report")
    keys = [_record_key(record) for record in existing]
    if dedupe.get("accepted_records_considered") != len(existing) or dedupe.get("duplicate_accepted_records_found") != len(keys) - len(set(keys)):
        _fail("Completion-attempt dedupe report is inconsistent with the accepted corpus")
    if manual_seed.get("record_type") != "program_top20_completion_attempt_manual_seed_needed_report":
        _fail("Completion-attempt manual-seed report type is invalid")
    _assert_false_output_flags(manual_seed, "Completion-attempt manual-seed report")
    needs = manual_seed.get("streams_requiring_complete_top20_evidence")
    if not isinstance(needs, list) or {item.get("stream_id") for item in needs if isinstance(item, dict)} != SCOPE_STREAMS:
        _fail("Completion-attempt manual-seed report must represent every incomplete stream")
    if not any(item.get("stream_id") == "undergraduate-economics" and item.get("manual_seed_needed") is True for item in needs):
        _fail("Economics must remain explicitly manual-seed-needed when no Top-20 record is accepted")
    if summary.get("record_type") != "program_top20_completion_attempt_readiness_summary" or summary.get("edition") != EDITION:
        _fail("Completion-attempt readiness summary is invalid")
    _assert_false_output_flags(summary, "Completion-attempt readiness summary")
    if summary.get("streams_assessed") != len(SCOPE_STREAMS) or summary.get("total_accepted_program_records") != len(existing):
        _fail("Completion-attempt readiness summary counts are inconsistent")
    statuses = [row["stream_status"] for row in coverage.values()]
    if summary.get("complete_stream_count") != statuses.count("complete") or summary.get("incomplete_stream_count") != statuses.count("incomplete") or summary.get("manual_seed_needed_stream_count") != statuses.count("manual_seed_needed") or summary.get("no_verified_records_stream_count") != statuses.count("no_verified_records"):
        _fail("Completion-attempt readiness summary status counts are inconsistent")
    if summary.get("program_top20_completion_ready") is not False or summary.get("newly_added_accepted_records") != 0:
        _fail("Completion-attempt must not claim completed program corpus readiness or invented records")


def validate_program_top20_completion_attempt_artifacts(
    seed_batches: Dict[str, Any], identities: Dict[str, Any], candidates: Dict[str, Any],
    coverage: Dict[str, Any], manifest: Dict[str, Any], gap_report: Dict[str, Any],
    dedupe: Dict[str, Any], manual_seed: Dict[str, Any], summary: Dict[str, Any], existing_root: Path,
) -> Dict[str, Any]:
    source_ids = _source_ids(manifest)
    _validate_seed_batches(seed_batches)
    existing = _load_prior_records(existing_root)
    resolved_coverage = _validate_coverage(coverage, existing)
    _validate_supporting_documents(identities, candidates, gap_report, dedupe, manual_seed, summary, resolved_coverage, source_ids, existing)
    return {
        "record_type": "program_top20_completion_attempt_validation_result",
        "edition": EDITION,
        "streams_assessed": len(SCOPE_STREAMS),
        "accepted_program_records_considered": len(existing),
        "new_verified_records_stageable": 0,
        "complete_stream_count": sum(row["stream_status"] == "complete" for row in resolved_coverage.values()),
        "incomplete_stream_count": sum(row["stream_status"] == "incomplete" for row in resolved_coverage.values()),
        "manual_seed_needed_stream_count": sum(row["stream_status"] == "manual_seed_needed" for row in resolved_coverage.values()),
        "no_verified_records_stream_count": sum(row["stream_status"] == "no_verified_records" for row in resolved_coverage.values()),
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
        "result": "passed",
    }


def build_program_top20_completion_attempt_bundle(existing_root: Path) -> Dict[str, Dict[str, Any]]:
    """Produce the honest Stage 2H readiness bundle without collecting new rows."""
    existing = _load_prior_records(existing_root)
    counts = {stream: 0 for stream in SCOPE_STREAMS}
    for record in existing:
        counts[record["category_id"]] += 1
    coverage = []
    gaps = []
    manual_needs = []
    for stream in sorted(SCOPE_STREAMS):
        status = "manual_seed_needed" if stream == "undergraduate-economics" else "incomplete"
        reason = (
            "A renewed official-source attempt did not yield a directly supported 2026 Economics Top-20 entry; the earlier Baylor No. 99 observation is outside scope."
            if stream == "undergraduate-economics"
            else "Accepted direct official records exist, but they do not establish the first 20 eligible entries and the boundary tie group."
        )
        row = {
            "stream_id": stream,
            "category_name": STREAM_NAMES[stream],
            "accepted_record_count": counts[stream],
            "newly_added_accepted_count": 0,
            "partial_count": 0,
            "unresolved_count": 0,
            "duplicate_skipped_count": 0,
            "stream_status": status,
            "complete_top20_with_boundary_ties": False,
            "completion_proof": None,
            "gap_reason": reason,
            "recommended_next_action": "Obtain a lawful complete Top-20 plus boundary-tie source, or a properly disclosed manual seed for independent review.",
        }
        coverage.append(row)
        gaps.append({"stream_id": stream, "stream_status": status, "accepted_record_count": counts[stream], "gap_reason": reason})
        manual_needs.append({"stream_id": stream, "category_name": STREAM_NAMES[stream], "current_stream_status": status, "accepted_record_count": counts[stream], "manual_seed_needed": True, "required_evidence": "First 20 eligible entries and the boundary tie group, with edition/category/rank evidence for every accepted record."})
    sources = [
        {
            "source_id": "usnews-program-pages-normal-access-attempt-2026",
            "publisher": "U.S. News & World Report",
            "source_type": "ranking_publisher_official",
            "url": "https://www.usnews.com/best-colleges/rankings/business-overall",
            "accessibility_status": "source_blocked_or_unavailable",
            "source_role": "completion_attempt_only",
            "used_for_accepted_records": False,
            "limitation_note": "Normal page access in the execution environment returned a non-retryable error; no bypass or alternate access path was used.",
        },
        {
            "source_id": "baylor-economics-outside-top20-2026",
            "publisher": "Baylor University",
            "source_type": "university_official_news",
            "url": "https://news.web.baylor.edu/news/story/2025/baylor-leaps-no-4-us-news-rankings-first-year-experiences-stays-top-10-learning",
            "accessibility_status": "publicly_accessible",
            "source_role": "outside_top20_observation",
            "used_for_accepted_records": False,
            "limitation_note": "The official page supports an Economics observation outside the Top-20 scope and therefore cannot create an accepted seed.",
        },
    ]
    common_flags = {"canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False}
    return {
        "accepted-seed-batches.json": {"record_type": "program_top20_completion_attempt_seed_batches", "edition": EDITION, "batches": [], "newly_added_accepted_records": 0},
        "source-manifest.json": {"record_type": "program_top20_completion_attempt_source_manifest", "edition": EDITION, "accessed_at": "2026-07-12", "sources": sources},
        "identity-mappings.json": {"record_type": "program_top20_completion_attempt_identity_mappings", "mappings": []},
        "candidate-observations.json": {"record_type": "program_top20_completion_attempt_candidate_observations", "edition_target": EDITION, "observations": [{"observation_id": "stage2h-economics-baylor-99", "source_id": "baylor-economics-outside-top20-2026", "category_id": "undergraduate-economics", "school_display_name": "Baylor University", "observed_rank": 99, "disposition": "outside_top20_scope", "reason": "Official 2026 Baylor evidence is outside the PathOS program Top-20 completion target."}]},
        "coverage-matrix.json": {"record_type": "program_top20_completion_attempt_coverage_matrix", "edition": EDITION, "streams": coverage, **common_flags},
        "gap-report.json": {"record_type": "program_top20_completion_attempt_gap_report", "edition": EDITION, "stream_gaps": gaps, **common_flags},
        "duplicate-dedupe-report.json": {"record_type": "program_top20_completion_attempt_dedupe_report", "edition": EDITION, "accepted_records_considered": len(existing), "duplicate_accepted_records_found": len(existing) - len({_record_key(record) for record in existing}), "duplicate_skipped_records": [], **common_flags},
        "manual-seed-needed-report.json": {"record_type": "program_top20_completion_attempt_manual_seed_needed_report", "edition": EDITION, "streams_requiring_complete_top20_evidence": manual_needs, **common_flags},
        "completion-readiness-summary.json": {"record_type": "program_top20_completion_attempt_readiness_summary", "edition": EDITION, "streams_assessed": len(SCOPE_STREAMS), "total_accepted_program_records": len(existing), "newly_added_accepted_records": 0, "complete_stream_count": 0, "incomplete_stream_count": len(SCOPE_STREAMS) - 1, "manual_seed_needed_stream_count": 1, "no_verified_records_stream_count": 0, "program_top20_completion_ready": False, "completed_program_corpus_gate_ready": False, "claude_gate_review_recommended": True, "review_scope": "Source-limit and manual-seed acquisition review only; not acceptance of a completed program corpus.", **common_flags},
    }


def write_program_top20_completion_attempt_bundle(bundle: Dict[str, Dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, document in bundle.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_program_top20_completion_attempt_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
