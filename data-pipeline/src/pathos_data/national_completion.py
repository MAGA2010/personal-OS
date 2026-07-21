"""Stage 2F validation for the explicitly disclosed National Top-50 manual seed."""

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any, Dict

from .ranking_collection import RankingCollectionValidationError
from .schema_validation import SchemaValidationError, load_schema, validate_instance


PDF_SOURCE_ID = "source_think_academy_top100_2026_pdf"
OFFICIAL_TOP3_SOURCE_ID = "usn-2026-best-colleges-press-release"
EDITION = "2026 Best Colleges"
FAMILY = "national_universities"
CATEGORY = "national-universities"
BOUNDARY_RANK = 46
BOUNDARY_ENTRY = "University of Rochester"
BOUNDARY_GROUP = {
    "Lehigh University", "Northeastern University", "Purdue University—Main Campus",
    "University of Georgia", "University of Rochester",
}
RANK_51_EXCLUSIONS = {
    "Case Western Reserve University", "Florida State University", "Texas A&M University",
    "Virginia Tech", "Wake Forest University", "William & Mary",
}
REQUIRED_DIRECT_FIELDS = {"school_display_name", "numeric_rank", "displayed_rank"}
REQUIRED_MANUAL_MAPPING_FIELDS = {"edition", "ranking_family", "category"}


class NationalCompletionValidationError(RankingCollectionValidationError):
    """Raised when the Stage 2F manual National completion violates its contract."""


def _fail(message: str) -> None:
    raise NationalCompletionValidationError(message)


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")


def _slug(name: str) -> str:
    value = name.replace("—", "-").replace("–", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold())
    return value.strip("-")


def _identity_id(name: str) -> str:
    known = {
        "Princeton University": "institution:princeton-university",
        "Massachusetts Institute of Technology": "institution:massachusetts-institute-of-technology",
        "Harvard University": "institution:harvard-university",
        "Carnegie Mellon University": "institution:carnegie-mellon-university",
        "Georgia Institute of Technology": "institution:georgia-institute-of-technology",
        "University of Florida": "institution:university-of-florida",
        "The Ohio State University": "institution:ohio-state-university",
    }
    return known.get(name, f"institution:{_slug(name)}")


def _validate_source_manifest(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    try:
        validate_instance(document, load_schema("national-completion-source-manifest.json"))
    except SchemaValidationError as error:
        raise NationalCompletionValidationError(str(error)) from error
    if document.get("edition") != EDITION:
        _fail("National source manifest edition mismatch")
    sources = {item.get("source_id"): item for item in document["sources"]}
    if len(sources) != len(document["sources"]):
        _fail("Duplicate National completion source_id")
    pdf = sources.get(PDF_SOURCE_ID)
    if not isinstance(pdf, dict):
        _fail("National completion requires the user-provided PDF source")
    required_pdf = {
        "source_title": "Top 100 College Ranking Shifts 2026 vs. 2025",
        "source_publisher": "Think Academy",
        "source_access_type": "user_provided_document",
        "source_role": "manual_seed_reference",
        "official_usnews_source": False,
        "source_confidence": "secondary_user_provided",
    }
    for field, expected in required_pdf.items():
        if pdf.get(field) != expected:
            _fail(f"User-provided PDF manifest field {field} is invalid")
    for field in ("source_file", "permission_note", "limitation_note"):
        _nonempty(pdf.get(field), f"pdf_manifest.{field}")
    if "not treated as official" not in pdf["permission_note"].casefold():
        _fail("PDF permission note must disclose that it is not official")
    if "third-party" not in pdf["limitation_note"].casefold():
        _fail("PDF limitation note must disclose third-party status")
    official = sources.get(OFFICIAL_TOP3_SOURCE_ID)
    if not isinstance(official, dict) or official.get("official_usnews_source") is not True:
        _fail("National completion requires the separate official Top-3 supplement")
    return sources


def _validate_anchor_fields(record: Dict[str, Any], source_ids: set[str]) -> None:
    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        _fail("National record requires evidence")
    direct = set(evidence.get("directly_supported_fields", []))
    mapped = set(evidence.get("manual_seed_mapped_fields", []))
    anchors = record.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        _fail("National record requires non-empty evidence anchors")
    anchored = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            _fail("Evidence anchor must be an object")
        for field in ("field", "source_id", "quote", "evidence_type"):
            _nonempty(anchor.get(field), f"evidence_anchor.{field}")
        if anchor["source_id"] not in source_ids:
            _fail("Evidence anchor source is absent from source manifest")
        if anchor["evidence_type"] != "direct_quote":
            _fail("National evidence anchor must be a direct quote")
        if anchor["field"] not in direct | mapped:
            _fail("Evidence anchor is neither direct nor disclosed manual mapping support")
        anchored.add(anchor["field"])
    if not REQUIRED_DIRECT_FIELDS.issubset(direct):
        _fail("National record lacks direct PDF or official name/rank evidence")
    if not (REQUIRED_DIRECT_FIELDS | mapped).issubset(anchored):
        _fail("National record is missing a required evidence anchor")
    if record.get("tied") is True or record.get("tied") is False:
        if "tied" in direct:
            _fail("Tie must be inferred from repeated rank, not claimed as a direct quote")
        _nonempty(record.get("inference_notes"), "inference_notes")
        if "tie inferred" not in record["inference_notes"].casefold():
            _fail("National record must disclose tie inference")
    else:
        _fail("National record tied must be boolean")


def _validate_records(batches: list[Dict[str, Any]], sources: Dict[str, Dict[str, Any]]) -> list[Dict[str, Any]]:
    if len(batches) != 1:
        _fail("National completion requires exactly one full seed batch")
    batch = batches[0]
    try:
        validate_instance(batch, load_schema("manual-ranking-seed-batch.json"))
    except SchemaValidationError as error:
        raise NationalCompletionValidationError(str(error)) from error
    stream = batch.get("stream")
    if not isinstance(stream, dict) or stream != {
        "stream_id": "national-universities-completion",
        "ranking_system": "u_s_news",
        "ranking_family": FAMILY,
        "category_id": CATEGORY,
        "edition": EDITION,
        "selection_rule": "first_50_us_domestic_entries_with_boundary_tie_group",
    }:
        _fail("National completion stream metadata is invalid")
    records = batch["records"]
    if len(records) != 50:
        _fail("National completion must import exactly the first 50 U.S.-domestic entries")
    seen_ids = set()
    seen_entries = set()
    for index, record in enumerate(records, start=1):
        for field in ("record_id", "school_display_name", "displayed_rank", "verification_status", "verification_basis"):
            _nonempty(record.get(field), f"record.{field}")
        if record["record_id"] in seen_ids or record["school_display_name"] in seen_entries:
            _fail("Duplicate National completion record")
        seen_ids.add(record["record_id"])
        seen_entries.add(record["school_display_name"])
        if record.get("source_entry_index") != index:
            _fail("National records must retain first-50 source entry order")
        if record.get("ranking_system") != "u_s_news" or record.get("ranking_family") != FAMILY or record.get("category_id") != CATEGORY or record.get("edition") != EDITION:
            _fail("National completion contains non-National, Global, Graduate, or wrong-edition data")
        if not isinstance(record.get("numeric_rank"), int) or record["numeric_rank"] < 1 or record["numeric_rank"] >= 51:
            _fail("National completion rank must preserve the source rank through the rank-46 boundary")
        if record["displayed_rank"] != str(record["numeric_rank"]):
            _fail("National completion displayed_rank must preserve the PDF Rank (2026) value")
        if record["verification_status"] != "verified":
            _fail("National manual seed records must be explicitly verified manual imports")
        source = record.get("source")
        if not isinstance(source, dict) or source.get("source_id") not in sources:
            _fail("National record source is absent from source manifest")
        if index <= 3:
            if source["source_id"] != OFFICIAL_TOP3_SOURCE_ID or record["verification_basis"] != "official_usnews_release_cross_check":
                _fail("Top 3 must retain the official U.S. News release supplement")
        else:
            if source["source_id"] != PDF_SOURCE_ID or record["verification_basis"] != "manual_seed_user_provided_pdf" or record.get("source_confidence") != "secondary_user_provided":
                _fail("Top 4 onward must be disclosed user-provided PDF manual seeds")
            if not REQUIRED_MANUAL_MAPPING_FIELDS.issubset(set(record.get("evidence", {}).get("manual_seed_mapped_fields", []))):
                _fail("Manual PDF record must disclose non-direct category/family/edition mapping")
        _validate_anchor_fields(record, set(sources))
    if records[-1]["school_display_name"] != BOUNDARY_ENTRY or records[-1]["numeric_rank"] != BOUNDARY_RANK:
        _fail("University of Rochester at original rank 46 must be the boundary entry")
    boundary = {record["school_display_name"] for record in records if record["numeric_rank"] == BOUNDARY_RANK}
    if boundary != BOUNDARY_GROUP:
        _fail("Rank-46 boundary tie group is incomplete or contaminated")
    return records


def _validate_identity_mappings(document: Dict[str, Any], records: list[Dict[str, Any]], source_ids: set[str]) -> int:
    if document.get("record_type") != "pilot_identity_mappings" or not isinstance(document.get("mappings"), list):
        _fail("National completion requires identity mappings")
    if len(document["mappings"]) != len(records):
        _fail("Every National record requires one identity mapping")
    record_by_id = {record["record_id"]: record for record in records}
    for mapping in document["mappings"]:
        record = record_by_id.get(mapping.get("record_id"))
        if record is None:
            _fail("Identity mapping introduces an unknown National record")
        if mapping.get("resolution_status") != "resolved" or mapping.get("unitid") is not None:
            _fail("National identity mappings must resolve names without guessing UNITID")
        if mapping.get("source_display_name") != record["school_display_name"] or mapping.get("normalized_display_name") != record["school_display_name"]:
            _fail("Identity mapping must preserve the PDF source display name")
        if mapping.get("canonical_identity_id") != _identity_id(record["school_display_name"]):
            _fail("National identity mapping has an unstable or non-reused canonical id")
        source = mapping.get("identity_source")
        if not isinstance(source, dict) or source.get("source_id") not in source_ids:
            _fail("Identity source is absent from manifest")
    return len(document["mappings"])


def _validate_supporting_artifacts(candidates: Dict[str, Any], coverage: Dict[str, Any], excluded: Dict[str, Any], records: list[Dict[str, Any]]) -> None:
    if candidates.get("record_type") != "ranking_collection_candidate_observations" or candidates.get("edition_target") != EDITION or candidates.get("observations") != []:
        _fail("National completion has no partial or unresolved entries in this supplied Top-50 PDF slice")
    expected_coverage = {
        "accepted_us_domestic_entries": 50,
        "expected_us_domestic_entries": 50,
        "numeric_ranks_covered": [1, 2, 3, 4, 6, 7, 11, 12, 13, 15, 17, 20, 24, 26, 28, 29, 30, 32, 36, 40, 41, 42, 46],
        "highest_included_original_rank": 46,
        "boundary_entry": BOUNDARY_ENTRY,
        "boundary_tie_group_rank": 46,
        "boundary_tie_group_complete": True,
        "excluded_non_us_entries_count": 0,
        "partial_records": 0,
        "unresolved_records": 0,
        "national_completion_accepted": True,
        "source_limited_manual_seed": True,
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
    }
    if coverage.get("record_type") != "national_completion_coverage_matrix":
        _fail("National completion coverage matrix has wrong record type")
    for field, expected in expected_coverage.items():
        if coverage.get(field) != expected:
            _fail(f"National completion coverage {field} is invalid")
    entries = excluded.get("entries") if isinstance(excluded, dict) else None
    if excluded.get("record_type") != "national_completion_excluded_entries" or not isinstance(entries, list):
        _fail("National completion requires excluded entries report")
    if {item.get("school_display_name") for item in entries} != RANK_51_EXCLUSIONS or {item.get("numeric_rank") for item in entries} != {51}:
        _fail("Rank-51 entries must be fully recorded and excluded")
    if any(item.get("reason") != "beyond_first_50_us_domestic_entries" for item in entries):
        _fail("Rank-51 exclusions must disclose the first-50 entry boundary rule")
    if len(records) != coverage["accepted_us_domestic_entries"]:
        _fail("Coverage accepted count does not match records")


def validate_national_completion_artifacts(
    batches: list[Dict[str, Any]], identity_document: Dict[str, Any], candidates: Dict[str, Any],
    coverage: Dict[str, Any], source_manifest: Dict[str, Any], excluded_entries: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate the full-artifact manual import without creating a canonical universe."""
    sources = _validate_source_manifest(source_manifest)
    records = _validate_records(batches, sources)
    resolved = _validate_identity_mappings(identity_document, records, set(sources))
    _validate_supporting_artifacts(candidates, coverage, excluded_entries, records)
    return {
        "record_type": "national_completion_validation_result",
        "edition": EDITION,
        "accepted_us_domestic_entries": len(records),
        "partial_records_excluded": 0,
        "unresolved_records_excluded": 0,
        "identity_resolved": resolved,
        "identity_unresolved": 0,
        "highest_included_original_rank": BOUNDARY_RANK,
        "boundary_entry": BOUNDARY_ENTRY,
        "boundary_tie_group_complete": True,
        "rank_51_entries_excluded": len(RANK_51_EXCLUSIONS),
        "excluded_non_us_entries_count": 0,
        "national_completion_accepted": True,
        "source_limited_manual_seed": True,
        "canonical_universe_created": False,
        "selection_memberships_created": False,
        "frontend_export_created": False,
        "result": "passed",
    }


def build_identity_mappings(batch: Dict[str, Any]) -> Dict[str, Any]:
    """Generate explicit, name-preserving mappings without any UNITID lookup."""
    mappings = []
    for record in batch["records"]:
        mappings.append({
            "record_id": record["record_id"],
            "source_display_name": record["school_display_name"],
            "normalized_display_name": record["school_display_name"],
            "official_institution_name": record["school_display_name"],
            "aliases": [record["school_display_name"]],
            "unitid": None,
            "unitid_status": "not_collected",
            "identity_confidence": "high",
            "identity_source": {"source_id": record["source"]["source_id"], "url": record["source"].get("url", "user-provided-file")},
            "resolution_status": "resolved",
            "canonical_identity_id": _identity_id(record["school_display_name"]),
        })
    return {"record_type": "pilot_identity_mappings", "mappings": mappings}


def build_national_manual_seed_bundle(input_document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Transform the user-reviewed PDF transcription into explicit Stage 2F artifacts."""
    try:
        validate_instance(input_document, load_schema("national-manual-seed-input.json"))
    except SchemaValidationError as error:
        raise NationalCompletionValidationError(str(error)) from error
    source = input_document.get("source_document")
    if not isinstance(source, dict) or source.get("title") != "Top 100 College Ranking Shifts 2026 vs. 2025":
        _fail("National manual seed input must name the provided Think Academy PDF")
    entries = input_document.get("entries")
    if not isinstance(entries, list) or len(entries) < 56:
        _fail("National manual seed input must include the first 50 entries plus rank-51 exclusions")
    rank_counts: Dict[int, int] = {}
    for entry in entries:
        rank = entry.get("rank_2026")
        if not isinstance(rank, int):
            _fail("National manual seed Rank (2026) must be an integer")
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    records = []
    for index, entry in enumerate(entries[:50], start=1):
        name = entry.get("institution")
        _nonempty(name, "manual_seed.institution")
        rank = entry["rank_2026"]
        is_tied = rank_counts[rank] > 1
        pdf_anchors = [
            {"field": "school_display_name", "source_id": PDF_SOURCE_ID, "quote": name, "evidence_type": "direct_quote"},
            {"field": "numeric_rank", "source_id": PDF_SOURCE_ID, "quote": str(rank), "evidence_type": "direct_quote"},
            {"field": "displayed_rank", "source_id": PDF_SOURCE_ID, "quote": str(rank), "evidence_type": "direct_quote"},
            {"field": "edition", "source_id": PDF_SOURCE_ID, "quote": "Rank (2026)", "evidence_type": "direct_quote"},
            {"field": "ranking_family", "source_id": PDF_SOURCE_ID, "quote": "Top 100 College Ranking Shifts", "evidence_type": "direct_quote"},
            {"field": "category", "source_id": PDF_SOURCE_ID, "quote": "Top 100 College Ranking Shifts", "evidence_type": "direct_quote"},
        ]
        record = {
            "record_id": f"completion-national-{_slug(name)}",
            "source_entry_index": index,
            "ranking_system": "u_s_news",
            "ranking_family": FAMILY,
            "category_id": CATEGORY,
            "edition": EDITION,
            "school_display_name": name,
            "numeric_rank": rank,
            "displayed_rank": str(rank),
            "tied": is_tied,
            "entered_by": "pathos-stage-2f-manual-seed-import",
            "entered_at": input_document["imported_at"],
            "verification_status": "verified",
            "source_confidence": "secondary_user_provided",
            "verification_basis": "manual_seed_user_provided_pdf",
            "source": {"source_id": PDF_SOURCE_ID, "source_type": "user_provided_document", "source_file": source["source_file"], "accessed_at": input_document["imported_at"]},
            "evidence": {
                "directly_supported_fields": ["school_display_name", "numeric_rank", "displayed_rank"],
                "manual_seed_mapped_fields": ["edition", "ranking_family", "category"],
            },
            "evidence_anchors": pdf_anchors,
            "inference_notes": "Tie inferred from multiple institutions sharing the same Rank (2026) value in the user-provided table." if is_tied else "No tie inferred: this Rank (2026) value appears once in the imported first-50 entries.",
            "notes": f"PDF table row retained with Rank (2025)={entry.get('rank_2025')} and Change={entry.get('change')}; only Rank (2026) populates ranking fields.",
        }
        if index <= 3:
            official_quote = f"{rank}. {name}"
            record.update({
                "source_confidence": "official_cross_check",
                "verification_basis": "official_usnews_release_cross_check",
                "source": {"source_id": OFFICIAL_TOP3_SOURCE_ID, "source_type": "official_press_release_syndication", "url": "https://www.prnewswire.com/news-releases/us-news-announces-2026-best-colleges-rankings-302563669.html", "accessed_at": input_document["imported_at"]},
                "evidence": {"directly_supported_fields": ["school_display_name", "edition", "ranking_family", "category", "numeric_rank", "displayed_rank"], "manual_seed_mapped_fields": []},
                "evidence_anchors": [
                    {"field": "school_display_name", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": official_quote, "evidence_type": "direct_quote"},
                    {"field": "edition", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": "2026 Best Colleges", "evidence_type": "direct_quote"},
                    {"field": "ranking_family", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": "2026 Best National Universities", "evidence_type": "direct_quote"},
                    {"field": "category", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": "National Universities – Top 3", "evidence_type": "direct_quote"},
                    {"field": "numeric_rank", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": official_quote, "evidence_type": "direct_quote"},
                    {"field": "displayed_rank", "source_id": OFFICIAL_TOP3_SOURCE_ID, "quote": official_quote, "evidence_type": "direct_quote"},
                ],
            })
        records.append(record)
    batch = {
        "record_type": "manual_ranking_seed_batch",
        "schema_version": "v1",
        "batch_id": "stage-2f-national-universities-top-50-user-provided-pdf",
        "created_at": input_document["imported_at"],
        "stream": {"stream_id": "national-universities-completion", "ranking_system": "u_s_news", "ranking_family": FAMILY, "category_id": CATEGORY, "edition": EDITION, "selection_rule": "first_50_us_domestic_entries_with_boundary_tie_group"},
        "records": records,
    }
    manifest = {
        "record_type": "national_completion_source_manifest",
        "edition": EDITION,
        "accessed_at": input_document["imported_at"],
        "sources": [
            {"source_id": PDF_SOURCE_ID, "source_title": source["title"], "source_publisher": "Think Academy", "source_access_type": "user_provided_document", "source_role": "manual_seed_reference", "source_file": source["source_file"], "official_usnews_source": False, "source_confidence": "secondary_user_provided", "permission_note": "User provided document for manual seed extraction; not treated as official U.S. News source.", "limitation_note": "Third-party compiled ranking table; official U.S. News full ranking page was not accessible in execution environment."},
            {"source_id": OFFICIAL_TOP3_SOURCE_ID, "source_title": "U.S. News Announces 2026 Best Colleges Rankings", "source_publisher": "U.S. News & World Report L.P. via PR Newswire", "source_access_type": "public_web_page", "source_role": "official_top3_cross_check", "url": "https://www.prnewswire.com/news-releases/us-news-announces-2026-best-colleges-rankings-302563669.html", "official_usnews_source": True, "source_confidence": "official", "permission_note": "Public official U.S. News release used only to cross-check the first three entries.", "limitation_note": "The release does not provide the complete National Top-50 table."},
        ],
    }
    excluded = [{"school_display_name": item["institution"], "numeric_rank": item["rank_2026"], "source_page": item.get("source_page"), "reason": "beyond_first_50_us_domestic_entries"} for item in entries[50:] if item.get("rank_2026") == 51]
    coverage = {"record_type": "national_completion_coverage_matrix", "edition": EDITION, "selection_rule": "first_50_us_domestic_entries_with_boundary_tie_group", "accepted_us_domestic_entries": 50, "expected_us_domestic_entries": 50, "numeric_ranks_covered": sorted({record["numeric_rank"] for record in records}), "highest_included_original_rank": 46, "boundary_entry": BOUNDARY_ENTRY, "boundary_tie_group_rank": 46, "boundary_tie_group_complete": True, "rank_51_excluded_count": len(excluded), "excluded_non_us_entries_count": 0, "partial_records": 0, "unresolved_records": 0, "identity_resolved": 50, "identity_unresolved": 0, "national_completion_accepted": True, "source_limited_manual_seed": True, "canonical_universe_created": False, "selection_memberships_created": False, "frontend_export_created": False, "remaining_gaps": "Official U.S. News full-page verification remains unavailable; this completion is manual-seed-based and requires Gate review."}
    return {"national-universities-top-50.json": batch, "source-manifest.json": manifest, "identity-mappings.json": build_identity_mappings(batch), "candidate-observations.json": {"record_type": "ranking_collection_candidate_observations", "edition_target": EDITION, "observations": []}, "coverage-matrix.json": coverage, "excluded-entries.json": {"record_type": "national_completion_excluded_entries", "entries": excluded}}


def write_national_manual_seed_bundle(bundle: Dict[str, Dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, document in bundle.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_national_completion_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    try:
        validate_instance(result, load_schema("national-completion-validation-result.json"))
    except SchemaValidationError as error:
        raise NationalCompletionValidationError(str(error)) from error
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
