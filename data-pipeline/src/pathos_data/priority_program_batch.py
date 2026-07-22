"""Stage 2G-A validator for incomplete, official-source program seed batches."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from .ranking_collection import RankingCollectionValidationError
from .schema_validation import SchemaValidationError, load_schema, validate_instance


EDITION = "2026 Best Colleges"
FAMILY = "undergraduate_program"
PRIORITY_STREAMS = {
    "undergraduate-business-programs",
    "business-entrepreneurship",
    "business-finance",
    "business-international-business",
    "business-marketing",
    "undergraduate-engineering-no-doctorate",
    "undergraduate-computer-science",
    "undergraduate-nursing",
    "undergraduate-economics",
    "undergraduate-psychology",
}
REQUIRED_DIRECT_FIELDS = {
    "school_display_name",
    "ranking_family",
    "category_id",
    "edition",
    "numeric_rank",
    "displayed_rank",
}


class PriorityProgramBatchValidationError(RankingCollectionValidationError):
    """Raised when an official-source incremental priority-program batch is unsafe."""


def _fail(message: str) -> None:
    raise PriorityProgramBatchValidationError(message)


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _validate_manifest(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if document.get("record_type") != "priority_program_official_source_manifest":
        _fail("Priority batch source manifest has the wrong record_type")
    if document.get("edition") != EDITION or not isinstance(document.get("sources"), list):
        _fail("Priority batch source manifest has an invalid edition or sources")
    sources: Dict[str, Dict[str, Any]] = {}
    for source in document["sources"]:
        if not isinstance(source, dict):
            _fail("Priority batch source must be an object")
        for field in (
            "source_id", "publisher", "source_type", "url", "accessibility_status",
            "source_access_type", "source_confidence",
        ):
            _nonempty(source.get(field), f"source.{field}")
        if source["source_id"] in sources:
            _fail("Priority batch source manifest contains a duplicate source_id")
        if source["source_type"] not in {"university_official_news", "university_official_rankings"}:
            _fail("Accepted priority batch records require a university or college official source")
        if source["source_access_type"] != "public_web_page" or source["source_confidence"] != "official_institutional":
            _fail("Priority batch source must disclose official public-web provenance")
        if source.get("official_usnews_source") is True or source.get("manual_seed") is True:
            _fail("This official-source batch must not relabel sources as U.S. News or manual seeds")
        sources[source["source_id"]] = source
    if not sources:
        _fail("Priority batch source manifest requires at least one source")
    return sources


def _validate_record(record: Dict[str, Any], source_ids: set[str], seen: set[tuple[str, str]]) -> None:
    for field in (
        "record_id", "ranking_system", "ranking_family", "category_id", "edition",
        "school_display_name", "displayed_rank", "verification_status", "verification_basis",
        "source_confidence", "source_display_name", "edition_evidence",
    ):
        _nonempty(record.get(field), f"record.{field}")
    if record.get("ranking_system") != "u_s_news" or record.get("ranking_family") != FAMILY:
        _fail("Priority batch contains a National, Global, Graduate, or other non-undergraduate-program record")
    if record.get("category_id") not in PRIORITY_STREAMS or record.get("edition") != EDITION:
        _fail("Priority batch record is outside the designated priority scope or edition")
    if record.get("verification_status") != "verified":
        _fail("Partially verified and unresolved records cannot enter accepted priority seeds")
    if record.get("verification_basis") != "official_school_or_college_page_direct":
        _fail("Priority batch accepted record requires official direct verification basis")
    if record.get("source_confidence") != "official_institutional" or record.get("edition_evidence") != "edition_direct":
        _fail("Priority batch accepted record needs official confidence and direct edition evidence")
    rank = record.get("numeric_rank")
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 20:
        _fail("Priority batch record rank must be an integer in the Top-20 scope")
    if not isinstance(record.get("tied"), bool):
        _fail("Priority batch record tied field must be boolean")
    source = record.get("source")
    if not isinstance(source, dict) or source.get("source_id") not in source_ids:
        _fail("Priority batch record source is absent from the source manifest")
    for field in ("url", "source_type", "accessed_at"):
        _nonempty(source.get(field), f"record.source.{field}")
    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        _fail("Priority batch record requires evidence")
    direct_fields = set(evidence.get("directly_supported_fields", []))
    if not REQUIRED_DIRECT_FIELDS.issubset(direct_fields):
        _fail("Priority batch record lacks required direct fields")
    if record["tied"] and "tied" not in direct_fields:
        _nonempty(record.get("inference_notes"), "inference_notes")
        if "tie inferred" not in record["inference_notes"].casefold():
            _fail("An inferred tie requires a disclosed inference rule")
    if not record["tied"] and "tied" in direct_fields:
        _fail("A false tie flag must not be represented as direct evidence")
    anchors = record.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        _fail("Priority batch record requires non-empty evidence anchors")
    anchored = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            _fail("Priority evidence anchor must be an object")
        for field in ("field", "source_id", "quote", "evidence_type"):
            _nonempty(anchor.get(field), f"evidence_anchor.{field}")
        if anchor["source_id"] not in source_ids or anchor["field"] not in direct_fields:
            _fail("Priority evidence anchor has an unresolved source or non-direct field")
        if anchor["evidence_type"] != "direct_quote":
            _fail("Priority evidence anchors must be short direct quotes")
        anchored.add(anchor["field"])
    if not direct_fields.issubset(anchored):
        _fail("Priority batch record is missing an anchor for a direct field")
    key = (record["category_id"], record["school_display_name"].casefold())
    if key in seen:
        _fail("Priority batch contains a duplicate school/category ranking record")
    seen.add(key)


def _validate_batches(batches: list[Dict[str, Any]], source_ids: set[str]) -> list[Dict[str, Any]]:
    if len(batches) != 1:
        _fail("Priority official batch validation requires exactly one seed batch")
    batch = batches[0]
    try:
        validate_instance(batch, load_schema("manual-ranking-seed-batch.json"))
    except SchemaValidationError as error:
        raise PriorityProgramBatchValidationError(str(error)) from error
    if batch.get("batch_id") != "stage-2g-a-priority-programs-official-batch-01":
        _fail("Priority batch_id is invalid")
    if set(batch.get("priority_streams", [])) != PRIORITY_STREAMS:
        _fail("Priority batch must declare exactly the Stage 2E priority streams")
    records = batch.get("records")
    if not isinstance(records, list) or not records:
        _fail("Priority batch requires accepted records")
    seen: set[tuple[str, str]] = set()
    for record in records:
        _validate_record(record, source_ids, seen)
    return records


def _validate_identity_mappings(document: Dict[str, Any], records: list[Dict[str, Any]], source_ids: set[str]) -> int:
    if document.get("record_type") != "pilot_identity_mappings" or not isinstance(document.get("mappings"), list):
        _fail("Priority batch requires identity mappings")
    by_record = {record["record_id"]: record for record in records}
    if len(document["mappings"]) != len(records):
        _fail("Every accepted priority record requires one identity mapping")
    seen = set()
    for mapping in document["mappings"]:
        record = by_record.get(mapping.get("record_id"))
        if record is None or mapping.get("record_id") in seen:
            _fail("Priority identity mappings must map every accepted record exactly once")
        seen.add(mapping["record_id"])
        if mapping.get("resolution_status") != "resolved" or mapping.get("unitid") is not None:
            _fail("Priority identity mappings must resolve names without guessing UNITID")
        for field in ("source_display_name", "normalized_display_name", "official_institution_name", "canonical_identity_id"):
            _nonempty(mapping.get(field), f"identity.{field}")
        if mapping["source_display_name"] != record["school_display_name"]:
            _fail("Priority identity mapping must preserve the source display name")
        identity_source = mapping.get("identity_source")
        if not isinstance(identity_source, dict) or identity_source.get("source_id") not in source_ids:
            _fail("Priority identity source is absent from the source manifest")
    return len(seen)


def _validate_supporting_artifacts(
    candidates: Dict[str, Any], coverage: Dict[str, Any], gaps: Dict[str, Any], records: list[Dict[str, Any]], sources: Dict[str, Dict[str, Any]],
) -> None:
    if candidates.get("record_type") != "ranking_collection_candidate_observations" or candidates.get("edition_target") != EDITION or candidates.get("observations") != []:
        _fail("This accepted-only batch must retain an explicit empty candidate-observations artifact")
    if coverage.get("record_type") != "priority_program_official_batch_coverage_matrix" or coverage.get("edition") != EDITION:
        _fail("Priority coverage matrix has the wrong type or edition")
    rows = coverage.get("streams")
    if not isinstance(rows, list) or {row.get("stream_id") for row in rows} != PRIORITY_STREAMS:
        _fail("Priority coverage must represent every Stage 2E priority stream exactly once")
    counts = {stream: 0 for stream in PRIORITY_STREAMS}
    source_counts = {stream: set() for stream in PRIORITY_STREAMS}
    for record in records:
        counts[record["category_id"]] += 1
        source_counts[record["category_id"]].add(record["source"]["source_id"])
    for row in rows:
        stream_id = row["stream_id"]
        if row.get("accepted_records") != counts[stream_id] or row.get("partial_records") != 0 or row.get("unresolved_records") != 0:
            _fail("Priority coverage counts do not match accepted records")
        if row.get("source_count") != len(source_counts[stream_id]):
            _fail("Priority coverage source count does not match records")
        if row.get("complete_top20_with_boundary_ties") is not False:
            _fail("An incremental priority batch must never claim a completed Top-20 stream")
        expected_status = "incomplete" if counts[stream_id] else "not_collected_in_batch"
        if row.get("coverage_status") != expected_status:
            _fail("Priority coverage status must distinguish incomplete from not collected")
    if gaps.get("record_type") != "priority_program_official_batch_gap_report" or gaps.get("edition") != EDITION:
        _fail("Priority batch requires a gap report")
    gap_streams = {item.get("stream_id") for item in gaps.get("stream_gaps", [])}
    if gap_streams != PRIORITY_STREAMS:
        _fail("Priority gap report must disclose every priority stream")
    for field in ("canonical_universe_created", "selection_memberships_created", "frontend_export_created"):
        if coverage.get(field) is not False or gaps.get(field) is not False:
            _fail("Priority batch must not generate a final universe, memberships, or frontend export")


def validate_priority_program_batch_artifacts(
    batches: list[Dict[str, Any]], identity_document: Dict[str, Any], candidates: Dict[str, Any],
    coverage: Dict[str, Any], source_manifest: Dict[str, Any], gaps: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate the full official-source artifact bundle without completing a stream."""
    sources = _validate_manifest(source_manifest)
    records = _validate_batches(batches, set(sources))
    resolved = _validate_identity_mappings(identity_document, records, set(sources))
    _validate_supporting_artifacts(candidates, coverage, gaps, records, sources)
    return {
        "record_type": "priority_program_official_batch_validation_result",
        "edition": EDITION,
        "seed_batches_validated": len(batches),
        "verified_records_stageable": len(records),
        "partially_verified_records_excluded_from_staging": 0,
        "unresolved_records_excluded_from_staging": 0,
        "identity_resolved": resolved,
        "identity_unresolved": 0,
        "all_priority_streams_incomplete": True,
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
        "result": "passed",
    }


def write_priority_program_batch_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    """Persist only a full-artifact result produced by this validator."""
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_priority_program_batch_bundle(input_document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Turn reviewed official-page observations into a full, explicit artifact bundle."""
    if input_document.get("record_type") != "priority_program_official_seed_input":
        _fail("Priority seed input has the wrong record_type")
    if input_document.get("edition") != EDITION or set(input_document.get("priority_streams", [])) != PRIORITY_STREAMS:
        _fail("Priority seed input has an invalid edition or scope")
    input_sources = input_document.get("sources")
    input_records = input_document.get("records")
    if not isinstance(input_sources, list) or not isinstance(input_records, list):
        _fail("Priority seed input requires source and record arrays")
    manifest = {
        "record_type": "priority_program_official_source_manifest",
        "edition": EDITION,
        "accessed_at": input_document.get("accessed_at"),
        "sources": input_sources,
    }
    source_by_id = _validate_manifest(manifest)
    records = []
    mappings = []
    for observation in input_records:
        source_id = observation.get("source_id")
        source = source_by_id.get(source_id)
        quotes = observation.get("anchor_quotes")
        if source is None or not isinstance(quotes, dict):
            _fail("Priority seed observation needs a known source and anchor quotes")
        direct_fields = list(REQUIRED_DIRECT_FIELDS)
        if observation.get("tied") is True:
            direct_fields.append("tied")
        for field in direct_fields:
            _nonempty(quotes.get(field), f"seed_input.anchor_quotes.{field}")
        record = {
            "record_id": observation.get("record_id"),
            "ranking_system": "u_s_news",
            "ranking_family": FAMILY,
            "category_id": observation.get("category_id"),
            "edition": EDITION,
            "school_display_name": observation.get("school_display_name"),
            "source_display_name": observation.get("school_display_name"),
            "numeric_rank": observation.get("numeric_rank"),
            "displayed_rank": f"#{observation.get('numeric_rank')}",
            "tied": observation.get("tied"),
            "source_access_type": source["source_access_type"],
            "source_confidence": source["source_confidence"],
            "verification_basis": "official_school_or_college_page_direct",
            "source": {
                "source_id": source_id,
                "url": source["url"],
                "source_type": source["source_type"],
                "accessed_at": input_document["accessed_at"],
            },
            "evidence": {"directly_supported_fields": direct_fields},
            "edition_evidence": "edition_direct",
            "evidence_anchors": [
                {"field": field, "source_id": source_id, "quote": quotes[field], "evidence_type": "direct_quote"}
                for field in direct_fields
            ],
            "entered_by": "pathos-stage-2g-a",
            "entered_at": input_document["accessed_at"],
            "verification_status": "verified",
        }
        if record["tied"] is False:
            record["inference_notes"] = "No tie marker was published on this official page; tied=false means no tie was observed in this incremental batch, not cutoff-wide tie coverage."
        records.append(record)
        mappings.append({
            "record_id": record["record_id"],
            "source_display_name": record["school_display_name"],
            "normalized_display_name": record["school_display_name"],
            "official_institution_name": observation.get("official_institution_name"),
            "aliases": observation.get("aliases", [record["school_display_name"]]),
            "unitid": None,
            "unitid_status": "not_collected",
            "identity_confidence": "high",
            "identity_source": {"source_id": source_id, "url": source["url"]},
            "resolution_status": "resolved",
            "canonical_identity_id": observation.get("canonical_identity_id"),
        })
    counts = {stream: 0 for stream in PRIORITY_STREAMS}
    source_counts = {stream: set() for stream in PRIORITY_STREAMS}
    for record in records:
        counts[record["category_id"]] += 1
        source_counts[record["category_id"]].add(record["source"]["source_id"])
    coverage_rows = []
    gap_rows = []
    for stream in sorted(PRIORITY_STREAMS):
        accepted = counts[stream]
        status = "incomplete" if accepted else "not_collected_in_batch"
        reason = (
            "Official-source records were collected incrementally; no complete Top-20 plus boundary-tie evidence was assembled."
            if accepted else "No qualifying official direct-evidence record was collected in this batch."
        )
        coverage_rows.append({
            "stream_id": stream,
            "expected_cutoff": "first 20 eligible entries plus boundary tie group",
            "accepted_records": accepted,
            "partial_records": 0,
            "unresolved_records": 0,
            "source_count": len(source_counts[stream]),
            "identity_resolved": accepted,
            "identity_unresolved": 0,
            "coverage_status": status,
            "complete_top20_with_boundary_ties": False,
            "coverage_note": reason,
        })
        gap_rows.append({"stream_id": stream, "coverage_status": status, "gap_reason": reason})
    return {
        "priority-programs-official-batch-01.json": {
            "record_type": "manual_ranking_seed_batch",
            "schema_version": "v1",
            "batch_id": "stage-2g-a-priority-programs-official-batch-01",
            "created_at": input_document["accessed_at"],
            "priority_streams": sorted(PRIORITY_STREAMS),
            "records": records,
        },
        "source-manifest.json": manifest,
        "identity-mappings.json": {"record_type": "pilot_identity_mappings", "mappings": mappings},
        "candidate-observations.json": {"record_type": "ranking_collection_candidate_observations", "edition_target": EDITION, "observations": []},
        "coverage-matrix.json": {
            "record_type": "priority_program_official_batch_coverage_matrix", "edition": EDITION,
            "generated_at": input_document["accessed_at"], "streams": coverage_rows,
            "canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False,
        },
        "gap-report.json": {
            "record_type": "priority_program_official_batch_gap_report", "edition": EDITION,
            "stream_gaps": gap_rows, "canonical_universe_created": False,
            "selection_memberships_created": False, "frontend_export_created": False,
        },
    }


def write_priority_program_batch_bundle(bundle: Dict[str, Dict[str, Any]], output: Path) -> None:
    """Write the generated artifacts from reviewed source observations."""
    output.mkdir(parents=True, exist_ok=True)
    for name, document in bundle.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
