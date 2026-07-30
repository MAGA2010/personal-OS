"""Verified-only staging and identity safeguards for the Stage 2B1 pilot."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from .schema_validation import SchemaValidationError, load_schema, validate_instance


class RankingCollectionValidationError(SchemaValidationError):
    """Raised when a pilot ranking record lacks sufficient evidence or identity controls."""


REQUIRED_EVIDENCE_FIELDS = {
    "school_display_name", "ranking_family", "category_id", "edition",
    "numeric_rank", "displayed_rank", "tied",
}
VERIFICATION_STATUSES = {"verified", "partially_verified", "unresolved"}
EDITION_EVIDENCE_STATUSES = {
    "edition_direct", "edition_inferred_from_release_cycle", "edition_ambiguous",
}
EVIDENCE_TYPES = {"direct_quote"}


def _fail(message: str) -> None:
    raise RankingCollectionValidationError(message)


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _validate_seed_shape(batch: Dict[str, Any]) -> None:
    try:
        validate_instance(batch, load_schema("manual-ranking-seed-batch.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    if not isinstance(batch.get("stream"), dict):
        _fail("Pilot batch requires stream metadata")


def _validate_evidence_anchors(record: Dict[str, Any]) -> None:
    """Require manually reviewable anchors for every claimed direct field."""
    evidence = record.get("evidence")
    direct_fields = set(evidence.get("directly_supported_fields", [])) if isinstance(evidence, dict) else set()
    anchors = record.get("evidence_anchors")
    if record.get("verification_status") == "verified" and not isinstance(anchors, list):
        _fail("Verified record requires evidence_anchors")
    if anchors is None:
        return
    if not isinstance(anchors, list) or not anchors:
        _fail("evidence_anchors must be a non-empty array")
    anchored_fields = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            _fail("Evidence anchor must be an object")
        for field in ("field", "source_id", "quote", "evidence_type"):
            _nonempty(anchor.get(field), f"evidence_anchor.{field}")
        if anchor["field"] not in direct_fields:
            _fail("Evidence anchor field must be directly supported")
        if anchor["evidence_type"] not in EVIDENCE_TYPES:
            _fail("Unsupported evidence anchor type")
        anchored_fields.add(anchor["field"])
    if record.get("verification_status") == "verified" and not direct_fields.issubset(anchored_fields):
        _fail("Verified record is missing an evidence anchor for a direct field")


def _validate_edition_evidence(record: Dict[str, Any]) -> None:
    status = record.get("edition_evidence")
    if status not in EDITION_EVIDENCE_STATUSES:
        _fail("Record requires a valid edition_evidence status")
    direct_fields = set(record.get("evidence", {}).get("directly_supported_fields", []))
    if status != "edition_direct" and "edition" in direct_fields:
        _fail("Inferred or ambiguous edition cannot be directly supported")
    if record.get("verification_status") == "verified":
        if status != "edition_direct" or "edition" not in direct_fields:
            _fail("Verified record requires direct edition evidence")


def validate_pilot_stream(batch: Dict[str, Any]) -> None:
    """Validate a seed stream without claiming it is complete coverage."""
    _validate_seed_shape(batch)
    stream = batch["stream"]
    for field in ("stream_id", "ranking_system", "ranking_family", "category_id", "edition"):
        _nonempty(stream.get(field), f"stream.{field}")
    cutoff = stream.get("expected_cutoff")
    if not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 1:
        _fail("stream.expected_cutoff must be a positive integer")

    seen = set()
    for record in batch["records"]:
        for field in ("record_id", "ranking_system", "ranking_family", "category_id", "edition", "school_display_name", "displayed_rank", "entered_by", "entered_at", "verification_status"):
            _nonempty(record.get(field), f"record.{field}")
        if record["ranking_system"] != stream["ranking_system"]:
            _fail("Ranking system mismatch between record and stream")
        if record["ranking_family"] != stream["ranking_family"]:
            _fail("Ranking family mismatch between record and stream")
        if record["category_id"] != stream["category_id"]:
            _fail("Category mismatch between record and stream")
        if record["edition"] != stream["edition"]:
            _fail("Edition mismatch between record and stream")
        if record["verification_status"] not in VERIFICATION_STATUSES:
            _fail("Unknown verification status")
        rank = record.get("numeric_rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1 or rank > cutoff:
            _fail("Record numeric rank is outside stream cutoff")
        if not isinstance(record.get("tied"), bool):
            _fail("Record tied flag must be boolean")
        source = record.get("source")
        if not isinstance(source, dict):
            _fail("Record requires a source")
        for field in ("source_id", "url", "source_type", "accessed_at"):
            _nonempty(source.get(field), f"source.{field}")
        evidence = record.get("evidence")
        if not isinstance(evidence, dict) or not isinstance(evidence.get("directly_supported_fields"), list):
            _fail("Record requires structured evidence")
        if record["verification_status"] == "verified" and not REQUIRED_EVIDENCE_FIELDS.issubset(set(evidence["directly_supported_fields"])):
            _fail("Verified record lacks full direct evidence")
        _validate_edition_evidence(record)
        _validate_evidence_anchors(record)
        key = (record["ranking_system"], record["ranking_family"], record["category_id"], record["edition"], record["school_display_name"].strip().casefold())
        if key in seen:
            _fail("Duplicate pilot ranking record")
        seen.add(key)


def validate_identity_mappings(document: Dict[str, Any]) -> None:
    """Validate explicit identity mappings; unresolved entries cannot create identities."""
    try:
        validate_instance(document, load_schema("ranking-pilot-identity-mappings.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    seen = set()
    for mapping in document["mappings"]:
        for field in ("record_id", "source_display_name", "normalized_display_name", "resolution_status", "identity_confidence"):
            _nonempty(mapping.get(field), f"identity.{field}")
        if mapping["record_id"] in seen:
            _fail("Duplicate identity mapping record_id")
        seen.add(mapping["record_id"])
        identity_source = mapping.get("identity_source")
        if not isinstance(identity_source, dict):
            _fail("Identity mapping requires identity_source")
        for field in ("source_id", "url"):
            _nonempty(identity_source.get(field), f"identity_source.{field}")
        if mapping["resolution_status"] == "resolved":
            _nonempty(mapping.get("canonical_identity_id"), "canonical_identity_id")
            _nonempty(mapping.get("official_institution_name"), "official_institution_name")
        elif mapping["resolution_status"] == "unresolved":
            if mapping.get("canonical_identity_id") is not None or mapping.get("official_institution_name") is not None:
                _fail("Unresolved identity must not declare a canonical institution")
        else:
            _fail("Unknown identity resolution status")


def build_identity_index(document: Dict[str, Any]) -> Dict[str, list[Dict[str, Any]]]:
    """Group aliases by explicit canonical identity, without manufacturing new identities."""
    validate_identity_mappings(document)
    index: Dict[str, list[Dict[str, Any]]] = {}
    for mapping in document["mappings"]:
        identity_id = mapping.get("canonical_identity_id")
        if identity_id:
            index.setdefault(identity_id, []).append(mapping)
    return index


def stage_verified_pilot_stream(batch: Dict[str, Any], identity_document: Dict[str, Any]) -> Dict[str, Any]:
    """Create staging records only for verified seeds; never creates canonical universities."""
    validate_pilot_stream(batch)
    validate_identity_mappings(identity_document)
    mappings = {item["record_id"]: item for item in identity_document["mappings"]}
    staged_records = []
    for record in batch["records"]:
        if record["verification_status"] != "verified":
            _fail("Only verified records may enter formal ranking staging")
        mapping = mappings.get(record["record_id"])
        if mapping is None:
            _fail("Verified record has no identity mapping")
        staged_records.append({
            "record_id": record["record_id"],
            "ranking_system": record["ranking_system"],
            "ranking_family": record["ranking_family"],
            "category_id": record["category_id"],
            "edition": record["edition"],
            "source_display_name": record["school_display_name"],
            "numeric_rank": record["numeric_rank"],
            "displayed_rank": record["displayed_rank"],
            "tied": record["tied"],
            "source": record["source"],
            "verification_status": record["verification_status"],
            "identity_resolution_status": mapping["resolution_status"],
            "canonical_university_id": mapping.get("canonical_identity_id") if mapping["resolution_status"] == "resolved" else None,
        })
    return {
        "record_type": "pilot_ranking_staging",
        "stream": batch["stream"],
        "records": staged_records,
    }


def _validate_source_manifest(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    try:
        validate_instance(document, load_schema("ranking-pilot-source-manifest.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    sources: Dict[str, Dict[str, Any]] = {}
    for source in document["sources"]:
        for field in ("source_id", "publisher", "source_type", "url", "accessibility_status"):
            _nonempty(source.get(field), f"source_manifest.{field}")
        if source["source_id"] in sources:
            _fail("Duplicate pilot source_id")
        sources[source["source_id"]] = source
    return sources


def _validate_candidate_observations(document: Dict[str, Any], edition: str, source_ids: set[str]) -> None:
    try:
        validate_instance(document, load_schema("ranking-pilot-candidate-observations.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    if document.get("edition_target") != edition:
        _fail("Candidate observation edition target mismatch")
    seen = set()
    for candidate in document["observations"]:
        for field in ("candidate_id", "ranking_system", "ranking_family", "category_id", "school_display_name", "source_id", "verification_status", "reason_not_staged", "identity_resolution_status"):
            _nonempty(candidate.get(field), f"candidate.{field}")
        if candidate["candidate_id"] in seen:
            _fail("Duplicate candidate observation")
        seen.add(candidate["candidate_id"])
        if candidate["verification_status"] not in {"partially_verified", "unresolved"}:
            _fail("Candidate observations must not be verified or staged")
        if candidate["source_id"] not in source_ids:
            _fail("Candidate source is absent from source manifest")
        if candidate.get("edition") == edition:
            _fail("Unverified candidate must not claim the target edition")
        if candidate.get("edition_evidence") not in {"edition_inferred_from_release_cycle", "edition_ambiguous"}:
            _fail("Candidate requires inferred or ambiguous edition evidence")
        if "edition" in set(candidate.get("directly_supported_fields", [])):
            _fail("Candidate cannot declare edition as direct support")


def _validate_coverage_matrix(document: Dict[str, Any], expected: Dict[str, Dict[str, int]]) -> None:
    try:
        validate_instance(document, load_schema("ranking-pilot-coverage-matrix.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    seen = set()
    for row in document["streams"]:
        stream_id = row.get("stream_id")
        _nonempty(stream_id, "coverage.stream_id")
        if stream_id in seen:
            _fail("Duplicate coverage stream")
        seen.add(stream_id)
        if stream_id not in expected:
            if all(row.get(field) == 0 for field in ("discovered_records", "verified_records", "partially_verified_records", "unresolved_records", "ties_observed", "source_count", "official_source_count", "university_official_cross_source_count", "identity_resolved_count", "identity_unresolved_count")) and isinstance(row.get("no_verified_reason"), str) and row["no_verified_reason"].strip() and row.get("complete_cutoff_coverage") is False:
                continue
            _fail("Coverage contains an unvalidated stream without a no_verified_reason")
        for field, value in expected[stream_id].items():
            if row.get(field) != value:
                _fail(f"Coverage matrix mismatch for {stream_id}.{field}")
        if row.get("complete_cutoff_coverage") is not False:
            _fail("Pilot coverage must not claim a complete cutoff")
    if not set(expected).issubset(seen):
        _fail("Coverage matrix is missing a pilot stream")


def validate_pilot_artifacts(
    batches: list[Dict[str, Any]], identity_document: Dict[str, Any],
    candidates: Dict[str, Any], coverage: Dict[str, Any], source_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Cross-validate the controlled pilot and return a truthful, non-universe result."""
    source_by_id = _validate_source_manifest(source_manifest)
    validate_identity_mappings(identity_document)
    mappings = {item["record_id"]: item for item in identity_document["mappings"]}
    if not batches:
        _fail("Pilot requires at least one seed batch")
    edition = batches[0].get("stream", {}).get("edition")
    _nonempty(edition, "stream.edition")
    _validate_candidate_observations(candidates, edition, set(source_by_id))

    expected: Dict[str, Dict[str, int]] = {}
    staged_total = 0
    for batch in batches:
        staged = stage_verified_pilot_stream(batch, identity_document)
        stream = staged["stream"]
        if stream["edition"] != edition:
            _fail("Pilot seed batches have mixed editions")
        stream_id = stream["stream_id"]
        if stream_id in expected:
            _fail("Duplicate pilot stream")
        records = batch["records"]
        for record in records:
            if record["source"]["source_id"] not in source_by_id:
                _fail("Verified seed source is absent from source manifest")
            for anchor in record.get("evidence_anchors", []):
                if anchor["source_id"] not in source_by_id:
                    _fail("Evidence anchor source is absent from source manifest")
        candidates_for_stream = [item for item in candidates["observations"] if item["category_id"] == stream["category_id"]]
        stream_sources = {record["source"]["source_id"] for record in records}
        stream_sources.update(item["source_id"] for item in candidates_for_stream)
        identity_items = [mappings[record["record_id"]] for record in records]
        identity_items.extend(item for item in candidates_for_stream if item.get("identity_resolution_status") in {"resolved", "unresolved"})
        expected[stream_id] = {
            "discovered_records": len(records) + len(candidates_for_stream),
            "verified_records": len(records),
            "partially_verified_records": sum(item["verification_status"] == "partially_verified" for item in candidates_for_stream),
            "unresolved_records": sum(item["verification_status"] == "unresolved" for item in candidates_for_stream),
            "ties_observed": sum(record["tied"] for record in records) + sum(item.get("tied") is True for item in candidates_for_stream),
            "source_count": len(stream_sources),
            "official_source_count": sum(source_by_id[source_id]["source_type"].startswith("official_") for source_id in stream_sources),
            "university_official_cross_source_count": sum(source_by_id[source_id]["source_type"] == "university_official_news" for source_id in stream_sources),
            "identity_resolved_count": sum(item.get("resolution_status", item.get("identity_resolution_status")) == "resolved" for item in identity_items),
            "identity_unresolved_count": sum(item.get("resolution_status", item.get("identity_resolution_status")) == "unresolved" for item in identity_items),
        }
        staged_total += len(staged["records"])

    _validate_coverage_matrix(coverage, expected)
    partial = sum(item["verification_status"] == "partially_verified" for item in candidates["observations"])
    unresolved = sum(item["verification_status"] == "unresolved" for item in candidates["observations"])
    return {
        "record_type": "ranking_collection_pilot_validation_result",
        "edition": edition,
        "seed_batches_validated": len(batches),
        "verified_records_stageable": staged_total,
        "partially_verified_records_excluded_from_staging": partial,
        "unresolved_records_excluded_from_staging": unresolved,
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
        "result": "passed",
    }


def write_pilot_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    """Persist only a result returned by successful artifact validation."""
    try:
        validate_instance(result, load_schema("ranking-pilot-validation-result.json"))
    except SchemaValidationError as error:
        raise RankingCollectionValidationError(str(error)) from error
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
