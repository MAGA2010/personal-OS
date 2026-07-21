"""Stage 2G-B all-stream, official-source undergraduate-program sweep.

The sweep is intentionally additive.  It validates only newly collected direct
official evidence, then aggregates it with pre-existing accepted program seeds
for stream-level coverage.  It does not create a universe or memberships.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .ranking_collection import RankingCollectionValidationError
from .schema_validation import SchemaValidationError, load_schema, validate_instance


EDITION = "2026 Best Colleges"
FAMILY = "undergraduate_program"
REQUIRED_DIRECT_FIELDS = {
    "school_display_name", "ranking_family", "category_id", "edition",
    "numeric_rank", "displayed_rank",
}
SCOPE_STREAMS = {
    "undergraduate-business-programs",
    "business-accounting",
    "business-analytics",
    "business-entrepreneurship",
    "business-finance",
    "business-international-business",
    "business-management",
    "business-management-information-systems",
    "business-marketing",
    "business-production-operations-management",
    "business-real-estate",
    "business-supply-chain-management-logistics",
    "undergraduate-engineering-doctorate",
    "undergraduate-engineering-no-doctorate",
    "engineering-aerospace",
    "engineering-biomedical",
    "engineering-chemical",
    "engineering-civil",
    "engineering-computer",
    "engineering-electrical",
    "engineering-environmental",
    "engineering-industrial",
    "engineering-materials",
    "engineering-mechanical",
    "undergraduate-computer-science",
    "undergraduate-nursing",
    "undergraduate-economics",
    "undergraduate-psychology",
}
STREAM_NAMES = {
    "undergraduate-business-programs": "Undergraduate Business Programs",
    "business-accounting": "Accounting",
    "business-analytics": "Analytics",
    "business-entrepreneurship": "Entrepreneurship",
    "business-finance": "Finance",
    "business-international-business": "International Business",
    "business-management": "Management",
    "business-management-information-systems": "Management Information Systems",
    "business-marketing": "Marketing",
    "business-production-operations-management": "Production/Operations Management",
    "business-real-estate": "Real Estate",
    "business-supply-chain-management-logistics": "Supply Chain Management/Logistics",
    "undergraduate-engineering-doctorate": "Undergraduate Engineering Programs (Doctorate)",
    "undergraduate-engineering-no-doctorate": "Undergraduate Engineering Programs (No Doctorate)",
    "engineering-aerospace": "Aerospace Engineering",
    "engineering-biomedical": "Biomedical Engineering",
    "engineering-chemical": "Chemical Engineering",
    "engineering-civil": "Civil Engineering",
    "engineering-computer": "Computer Engineering",
    "engineering-electrical": "Electrical Engineering",
    "engineering-environmental": "Environmental Engineering",
    "engineering-industrial": "Industrial Engineering",
    "engineering-materials": "Materials Engineering",
    "engineering-mechanical": "Mechanical Engineering",
    "undergraduate-computer-science": "Undergraduate Computer Science Programs",
    "undergraduate-nursing": "Undergraduate Nursing Programs",
    "undergraduate-economics": "Undergraduate Economics Programs",
    "undergraduate-psychology": "Undergraduate Psychology Programs",
}


class OfficialProgramSweepValidationError(RankingCollectionValidationError):
    """Raised when an all-stream sweep is missing auditable official evidence."""


def _fail(message: str) -> None:
    raise OfficialProgramSweepValidationError(message)


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _record_key(record: Dict[str, Any]) -> tuple[str, str, int]:
    return (
        record.get("category_id", ""),
        record.get("school_display_name", "").casefold(),
        record.get("numeric_rank", -1),
    )


def _load_existing_records(root: Path) -> list[Dict[str, Any]]:
    """Load accepted program records already committed before the sweep.

    This deliberately excludes the sweep folder itself so reruns remain stable.
    """
    records: list[Dict[str, Any]] = []
    for path in root.rglob("*.json"):
        # The Stage 2G-B baseline consists only of artifacts that predate the
        # sweep. Later completion bundles must never change its frozen totals.
        if {"completion-programs-official-sweep", "completion-programs-gap-repair"} & set(path.parts):
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


def _validate_manifest(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if document.get("record_type") != "official_program_sweep_source_manifest" or document.get("edition") != EDITION:
        _fail("Official sweep source manifest has the wrong type or edition")
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail("Official sweep source manifest requires sources")
    resolved: Dict[str, Dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            _fail("Official sweep source must be an object")
        for field in ("source_id", "publisher", "source_type", "url", "source_access_type", "source_confidence"):
            _nonempty(source.get(field), f"source.{field}")
        if source["source_id"] in resolved:
            _fail("Official sweep source manifest contains duplicate source_id")
        if source["source_type"] not in {"university_official_news", "university_official_rankings"}:
            _fail("Accepted sweep records require a university or college official source")
        if source["source_access_type"] != "public_web_page" or source["source_confidence"] != "official_institutional":
            _fail("Accepted sweep sources must be publicly accessible official institutional pages")
        if source.get("official_usnews_source") is True or source.get("manual_seed") is True:
            _fail("This sweep must not relabel university pages as official U.S. News or manual seeds")
        resolved[source["source_id"]] = source
    return resolved


def _validate_record(record: Dict[str, Any], source_ids: set[str], seen: set[tuple[str, str, int]], existing: set[tuple[str, str, int]]) -> None:
    for field in (
        "record_id", "ranking_system", "ranking_family", "category_id", "edition",
        "school_display_name", "source_display_name", "displayed_rank", "verification_status",
        "verification_basis", "source_confidence", "edition_evidence",
    ):
        _nonempty(record.get(field), f"record.{field}")
    if record.get("ranking_system") != "u_s_news" or record.get("ranking_family") != FAMILY:
        _fail("Official sweep contains National, Global, Graduate, or other non-undergraduate-program data")
    if record.get("category_id") not in SCOPE_STREAMS or record.get("edition") != EDITION:
        _fail("Official sweep record is outside the in-scope undergraduate program inventory")
    if record.get("verification_status") != "verified" or record.get("verification_basis") != "official_school_or_college_page_direct":
        _fail("Partially verified and unresolved observations cannot enter accepted sweep seeds")
    if record.get("source_confidence") != "official_institutional" or record.get("edition_evidence") != "edition_direct":
        _fail("Accepted sweep records require official confidence and direct 2026 edition evidence")
    if not isinstance(record.get("numeric_rank"), int) or isinstance(record.get("numeric_rank"), bool) or not 1 <= record["numeric_rank"] <= 20:
        _fail("Accepted sweep records must be within the Top-20 program scope")
    if not isinstance(record.get("tied"), bool):
        _fail("Official sweep tied field must be boolean")
    source = record.get("source")
    if not isinstance(source, dict) or source.get("source_id") not in source_ids:
        _fail("Official sweep record source is absent from its manifest")
    for field in ("url", "source_type", "accessed_at"):
        _nonempty(source.get(field), f"record.source.{field}")
    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        _fail("Official sweep record requires field-level evidence")
    direct = set(evidence.get("directly_supported_fields", []))
    if not REQUIRED_DIRECT_FIELDS.issubset(direct):
        _fail("Official sweep record lacks required directly supported fields")
    if record["tied"] and "tied" not in direct:
        _nonempty(record.get("inference_notes"), "inference_notes")
        if "tie inferred" not in record["inference_notes"].casefold():
            _fail("Inferred ties must disclose their repeated-rank inference")
    if not record["tied"] and "tied" in direct:
        _fail("A false tie must not masquerade as direct support")
    anchors = record.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        _fail("Official sweep record requires evidence anchors")
    anchored = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            _fail("Official sweep evidence anchor must be an object")
        for field in ("field", "source_id", "quote", "evidence_type"):
            _nonempty(anchor.get(field), f"evidence_anchor.{field}")
        if anchor["source_id"] not in source_ids or anchor["field"] not in direct:
            _fail("Official sweep evidence anchor has an unresolved source or unsupported field")
        if anchor["evidence_type"] != "direct_quote":
            _fail("Official sweep anchors must use short direct quotes")
        anchored.add(anchor["field"])
    if not direct.issubset(anchored):
        _fail("Official sweep record is missing an anchor for a directly supported field")
    key = _record_key(record)
    if key in existing:
        _fail("Official sweep must not recreate a stream/school/rank record already accepted in an earlier artifact")
    if key in seen:
        _fail("Official sweep contains a duplicate stream/school/rank record")
    seen.add(key)


def _validate_batch(batches: list[Dict[str, Any]], source_ids: set[str], existing: set[tuple[str, str, int]]) -> list[Dict[str, Any]]:
    if len(batches) != 1:
        _fail("Official sweep validation requires exactly one full seed batch")
    batch = batches[0]
    try:
        validate_instance(batch, load_schema("manual-ranking-seed-batch.json"))
    except SchemaValidationError as error:
        raise OfficialProgramSweepValidationError(str(error)) from error
    if batch.get("batch_id") != "stage-2g-b-official-program-source-sweep" or set(batch.get("scope_streams", [])) != SCOPE_STREAMS:
        _fail("Official sweep batch scope is invalid")
    records = batch.get("records")
    if not isinstance(records, list) or not records:
        _fail("Official sweep requires newly accepted official records")
    seen: set[tuple[str, str, int]] = set()
    for record in records:
        _validate_record(record, source_ids, seen, existing)
    return records


def _validate_mappings(document: Dict[str, Any], records: list[Dict[str, Any]], source_ids: set[str]) -> int:
    if document.get("record_type") != "pilot_identity_mappings" or not isinstance(document.get("mappings"), list):
        _fail("Official sweep requires identity mappings")
    by_id = {record["record_id"]: record for record in records}
    if len(document["mappings"]) != len(records):
        _fail("Every new sweep record requires exactly one identity mapping")
    seen = set()
    for mapping in document["mappings"]:
        record = by_id.get(mapping.get("record_id"))
        if record is None or mapping.get("record_id") in seen:
            _fail("Official sweep identity mapping is unknown or duplicated")
        seen.add(mapping["record_id"])
        if mapping.get("resolution_status") != "resolved" or mapping.get("unitid") is not None:
            _fail("Official sweep mappings may resolve names but must not guess UNITID")
        for field in ("source_display_name", "normalized_display_name", "official_institution_name", "canonical_identity_id"):
            _nonempty(mapping.get(field), f"identity.{field}")
        if mapping["source_display_name"] != record["school_display_name"]:
            _fail("Identity mapping must preserve the source display name")
        source = mapping.get("identity_source")
        if not isinstance(source, dict) or source.get("source_id") not in source_ids:
            _fail("Official sweep identity source is absent from source manifest")
    return len(seen)


def _validate_supporting_artifacts(
    candidates: Dict[str, Any], coverage: Dict[str, Any], gaps: Dict[str, Any], duplicates: Dict[str, Any],
    new_records: list[Dict[str, Any]], existing_records: list[Dict[str, Any]],
) -> None:
    if candidates.get("record_type") != "ranking_collection_candidate_observations" or candidates.get("edition_target") != EDITION or candidates.get("observations") != []:
        _fail("Official sweep must retain an explicit empty candidate-observations artifact")
    if coverage.get("record_type") != "official_program_sweep_coverage_matrix" or coverage.get("edition") != EDITION:
        _fail("Official sweep coverage matrix is invalid")
    rows = coverage.get("streams")
    if not isinstance(rows, list) or {row.get("stream_id") for row in rows} != SCOPE_STREAMS or len(rows) != len(SCOPE_STREAMS):
        _fail("Official sweep coverage must represent every in-scope program stream exactly once")
    aggregate: Dict[str, list[Dict[str, Any]]] = {stream: [] for stream in SCOPE_STREAMS}
    for record in [*existing_records, *new_records]:
        aggregate[record["category_id"]].append(record)
    for row in rows:
        stream = row["stream_id"]
        records = aggregate[stream]
        if row.get("category_name") != STREAM_NAMES[stream]:
            _fail("Coverage matrix category name does not match the inventory")
        if row.get("accepted_records") != len(records) or row.get("partial_records") != 0 or row.get("unresolved_records") != 0:
            _fail("Coverage counts must equal aggregated accepted records and disclose no accepted partials")
        if sorted(row.get("numeric_ranks_covered", [])) != sorted({record["numeric_rank"] for record in records}):
            _fail("Coverage numeric ranks do not match aggregated accepted records")
        status = row.get("stream_status")
        if status == "complete":
            proof = row.get("completion_proof")
            if not isinstance(proof, dict) or proof.get("first_20_entries_verified") is not True or proof.get("boundary_tie_group_verified") is not True:
                _fail("A stream may be complete only with explicit Top-20 and boundary-tie proof")
        elif status not in {"incomplete", "no_verified_records", "partial_only", "source_blocked_or_unavailable"}:
            _fail("Official sweep coverage has an invalid stream status")
        expected = {"incomplete"} if records else {"no_verified_records", "partial_only", "source_blocked_or_unavailable"}
        if status not in expected:
            _fail("Coverage status does not honestly reflect available verified records")
        if row.get("complete_top20_with_boundary_ties") is not (status == "complete"):
            _fail("Coverage completion flag must match stream status")
    if gaps.get("record_type") != "official_program_sweep_gap_report" or {item.get("stream_id") for item in gaps.get("stream_gaps", [])} != SCOPE_STREAMS:
        _fail("Official sweep requires an explicit gap for every stream")
    if duplicates.get("record_type") != "official_program_sweep_duplicate_dedupe_report" or not isinstance(duplicates.get("existing_records_considered"), int):
        _fail("Official sweep requires a duplicate/dedupe report")
    if duplicates["existing_records_considered"] != len(existing_records):
        _fail("Duplicate report must disclose every pre-sweep accepted record considered")
    for document in (coverage, gaps, duplicates):
        for field in ("canonical_universe_created", "selection_memberships_created", "frontend_export_created"):
            if document.get(field) is not False:
                _fail("Official program sweep must not create universe, memberships, or frontend export")


def validate_official_program_sweep_artifacts(
    batches: list[Dict[str, Any]], identity_document: Dict[str, Any], candidates: Dict[str, Any], coverage: Dict[str, Any],
    source_manifest: Dict[str, Any], gaps: Dict[str, Any], duplicates: Dict[str, Any], existing_root: Path,
) -> Dict[str, Any]:
    """Validate full official sweep artifacts and cross-check previously accepted records."""
    sources = _validate_manifest(source_manifest)
    existing_records = _load_existing_records(existing_root)
    records = _validate_batch(batches, set(sources), {_record_key(record) for record in existing_records})
    resolved = _validate_mappings(identity_document, records, set(sources))
    _validate_supporting_artifacts(candidates, coverage, gaps, duplicates, records, existing_records)
    streams_with_new = len({record["category_id"] for record in records})
    return {
        "record_type": "official_program_sweep_validation_result",
        "edition": EDITION,
        "new_verified_records_stageable": len(records),
        "existing_verified_records_considered": len(existing_records),
        "streams_represented": len(SCOPE_STREAMS),
        "streams_with_new_records": streams_with_new,
        "partially_verified_records_excluded_from_staging": 0,
        "unresolved_records_excluded_from_staging": 0,
        "identity_resolved": resolved,
        "identity_unresolved": 0,
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
        "result": "passed",
    }


def write_official_program_sweep_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _anchors(source_id: str, quotes: Dict[str, str], direct_fields: Iterable[str]) -> list[Dict[str, str]]:
    return [
        {"field": field, "source_id": source_id, "quote": quotes[field], "evidence_type": "direct_quote"}
        for field in direct_fields
    ]


def build_official_program_sweep_bundle(input_document: Dict[str, Any], existing_root: Path) -> Dict[str, Dict[str, Any]]:
    """Build an auditable, additive sweep bundle from reviewed direct-page observations."""
    if input_document.get("record_type") != "official_program_sweep_seed_input" or input_document.get("edition") != EDITION:
        _fail("Official sweep input has the wrong type or edition")
    if set(input_document.get("scope_streams", [])) != SCOPE_STREAMS:
        _fail("Official sweep input must declare every in-scope stream")
    sources = input_document.get("sources")
    observations = input_document.get("records")
    if not isinstance(sources, list) or not isinstance(observations, list):
        _fail("Official sweep input requires source and record arrays")
    manifest = {"record_type": "official_program_sweep_source_manifest", "edition": EDITION, "accessed_at": input_document.get("accessed_at"), "sources": sources}
    source_by_id = _validate_manifest(manifest)
    records = []
    mappings = []
    for observation in observations:
        source_id = observation.get("source_id")
        source = source_by_id.get(source_id)
        quotes = observation.get("anchor_quotes")
        if source is None or not isinstance(quotes, dict):
            _fail("Official sweep observation needs a known official source and anchor quotes")
        direct_fields = sorted(REQUIRED_DIRECT_FIELDS)
        if observation.get("tied_direct") is True:
            direct_fields.append("tied")
        for field in direct_fields:
            _nonempty(quotes.get(field), f"sweep_input.anchor_quotes.{field}")
        record = {
            "record_id": observation.get("record_id"), "ranking_system": "u_s_news", "ranking_family": FAMILY,
            "category_id": observation.get("category_id"), "edition": EDITION,
            "school_display_name": observation.get("school_display_name"), "source_display_name": observation.get("school_display_name"),
            "numeric_rank": observation.get("numeric_rank"), "displayed_rank": observation.get("displayed_rank", f"#{observation.get('numeric_rank')}"),
            "tied": observation.get("tied"), "source_access_type": source["source_access_type"],
            "source_confidence": source["source_confidence"], "verification_basis": "official_school_or_college_page_direct",
            "source": {"source_id": source_id, "url": source["url"], "source_type": source["source_type"], "accessed_at": input_document["accessed_at"]},
            "evidence": {"directly_supported_fields": direct_fields}, "edition_evidence": "edition_direct",
            "evidence_anchors": _anchors(source_id, quotes, direct_fields), "entered_by": "pathos-stage-2g-b",
            "entered_at": input_document["accessed_at"], "verification_status": "verified",
        }
        if record["tied"]:
            if "tied" not in direct_fields:
                record["inference_notes"] = "Tie inferred from repeated rank within the official source list; tied is not directly supported."
        else:
            record["inference_notes"] = "No tie marker was published on this official page; tied=false means no tie was observed in this incremental sweep, not cutoff-wide tie coverage."
        records.append(record)
        mappings.append({
            "record_id": record["record_id"], "source_display_name": record["school_display_name"],
            "normalized_display_name": record["school_display_name"], "official_institution_name": observation.get("official_institution_name"),
            "aliases": observation.get("aliases", [record["school_display_name"]]), "unitid": None,
            "unitid_status": "not_collected", "identity_confidence": "high",
            "identity_source": {"source_id": source_id, "url": source["url"]}, "resolution_status": "resolved",
            "canonical_identity_id": observation.get("canonical_identity_id"),
        })
    existing_records = _load_existing_records(existing_root)
    aggregate: Dict[str, list[Dict[str, Any]]] = {stream: [] for stream in SCOPE_STREAMS}
    for record in [*existing_records, *records]:
        aggregate[record["category_id"]].append(record)
    coverage_rows = []
    gaps = []
    for stream in sorted(SCOPE_STREAMS):
        stream_records = aggregate[stream]
        status = "incomplete" if stream_records else "no_verified_records"
        reason = (
            "Official direct-evidence records exist, but no full first-20-entry plus boundary-tie group was assembled."
            if stream_records else "Official-source sweep found no qualifying direct 2026 institution/category/rank evidence for this stream."
        )
        coverage_rows.append({
            "stream_id": stream, "category_name": STREAM_NAMES[stream], "accepted_records": len(stream_records),
            "partial_records": 0, "unresolved_records": 0, "duplicate_skipped_count": 0,
            "verified_institutions": sorted({record["school_display_name"] for record in stream_records}),
            "numeric_ranks_covered": sorted({record["numeric_rank"] for record in stream_records}),
            "boundary_entry": None, "boundary_tie_group_status": "not_determined",
            "stream_status": status, "complete_top20_with_boundary_ties": False, "gap_reason": reason,
            "recommended_next_action": "Obtain a lawful complete Top-20 source or more direct official school/college evidence.",
        })
        gaps.append({"stream_id": stream, "stream_status": status, "gap_reason": reason})
    return {
        "official-program-sweep.json": {"record_type": "manual_ranking_seed_batch", "schema_version": "v1", "batch_id": "stage-2g-b-official-program-source-sweep", "created_at": input_document["accessed_at"], "scope_streams": sorted(SCOPE_STREAMS), "records": records},
        "source-manifest.json": manifest,
        "identity-mappings.json": {"record_type": "pilot_identity_mappings", "mappings": mappings},
        "candidate-observations.json": {"record_type": "ranking_collection_candidate_observations", "edition_target": EDITION, "observations": []},
        "coverage-matrix.json": {"record_type": "official_program_sweep_coverage_matrix", "edition": EDITION, "generated_at": input_document["accessed_at"], "streams": coverage_rows, "canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False},
        "gap-report.json": {"record_type": "official_program_sweep_gap_report", "edition": EDITION, "stream_gaps": gaps, "canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False},
        "duplicate-dedupe-report.json": {"record_type": "official_program_sweep_duplicate_dedupe_report", "edition": EDITION, "existing_records_considered": len(existing_records), "new_records_created": len(records), "duplicate_skipped_records": [], "dedupe_policy": "Reject a newly accepted record when category_id, school_display_name, and numeric_rank duplicate a prior accepted program seed; retain the earlier evidence without mutation.", "canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False},
    }


def write_official_program_sweep_bundle(bundle: Dict[str, Dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, document in bundle.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
