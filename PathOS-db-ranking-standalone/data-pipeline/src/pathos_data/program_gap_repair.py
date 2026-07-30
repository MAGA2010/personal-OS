"""Stage 2G-C focused repair of remaining undergraduate-program ranking gaps."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from .official_program_sweep import (
    EDITION, FAMILY, REQUIRED_DIRECT_FIELDS, SCOPE_STREAMS, STREAM_NAMES,
    _nonempty, _record_key,
)
from .ranking_collection import RankingCollectionValidationError
from .schema_validation import SchemaValidationError, load_schema, validate_instance


class ProgramGapRepairValidationError(RankingCollectionValidationError):
    """Raised when focused repair artifacts violate ranking evidence boundaries."""


def _fail(message: str) -> None:
    raise ProgramGapRepairValidationError(message)


def _load_prior_records(root: Path) -> list[Dict[str, Any]]:
    """Read pre-repair accepted program records without re-ingesting this bundle."""
    records: list[Dict[str, Any]] = []
    for path in root.rglob("*.json"):
        if "completion-programs-gap-repair" in path.parts:
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
    if document.get("record_type") != "program_gap_repair_source_manifest" or document.get("edition") != EDITION:
        _fail("Gap repair source manifest has the wrong type or edition")
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail("Gap repair source manifest requires sources")
    resolved = {}
    for source in sources:
        if not isinstance(source, dict):
            _fail("Gap repair source must be an object")
        for field in ("source_id", "publisher", "source_type", "url", "source_access_type", "source_confidence"):
            _nonempty(source.get(field), f"source.{field}")
        if source["source_id"] in resolved:
            _fail("Gap repair source manifest contains duplicate source_id")
        if source["source_type"] not in {"university_official_news", "university_official_rankings"}:
            _fail("Gap repair accepted evidence must be a university or college official page")
        if source["source_access_type"] != "public_web_page" or source["source_confidence"] != "official_institutional":
            _fail("Gap repair sources must disclose public official institutional provenance")
        if source.get("official_usnews_source") is True or source.get("manual_seed") is True:
            _fail("This official-source repair cannot relabel a source as U.S. News or manual")
        resolved[source["source_id"]] = source
    return resolved


def _validate_record(record: Dict[str, Any], source_ids: set[str], existing: set[tuple[str, str, int]], seen: set[tuple[str, str, int]]) -> None:
    for field in ("record_id", "ranking_system", "ranking_family", "category_id", "edition", "school_display_name", "source_display_name", "displayed_rank", "verification_status", "verification_basis", "source_confidence", "edition_evidence"):
        _nonempty(record.get(field), f"record.{field}")
    if record.get("ranking_system") != "u_s_news" or record.get("ranking_family") != FAMILY or record.get("category_id") not in SCOPE_STREAMS or record.get("edition") != EDITION:
        _fail("Gap repair may only contain in-scope 2026 undergraduate program records")
    if record.get("verification_status") != "verified" or record.get("verification_basis") != "official_school_or_college_page_direct" or record.get("edition_evidence") != "edition_direct" or record.get("source_confidence") != "official_institutional":
        _fail("Partial, unresolved, inferred-edition, or non-official records cannot enter accepted repair seeds")
    rank = record.get("numeric_rank")
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 20:
        _fail("Gap repair accepted record must be within Top-20 scope")
    if not isinstance(record.get("tied"), bool):
        _fail("Gap repair tied field must be boolean")
    source = record.get("source")
    if not isinstance(source, dict) or source.get("source_id") not in source_ids:
        _fail("Gap repair record source does not resolve in the manifest")
    evidence = record.get("evidence")
    direct = set(evidence.get("directly_supported_fields", [])) if isinstance(evidence, dict) else set()
    if not REQUIRED_DIRECT_FIELDS.issubset(direct):
        _fail("Gap repair record lacks required directly supported fields")
    anchors = record.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        _fail("Gap repair record requires evidence anchors")
    anchored = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            _fail("Gap repair evidence anchor must be an object")
        for field in ("field", "source_id", "quote", "evidence_type"):
            _nonempty(anchor.get(field), f"anchor.{field}")
        if anchor["source_id"] not in source_ids or anchor["field"] not in direct or anchor["evidence_type"] != "direct_quote":
            _fail("Gap repair evidence anchor is invalid")
        anchored.add(anchor["field"])
    if not direct.issubset(anchored):
        _fail("Gap repair record lacks a direct anchor for a declared direct field")
    if record["tied"] and "tied" not in direct:
        _nonempty(record.get("inference_notes"), "inference_notes")
    if not record["tied"] and "tied" in direct:
        _fail("False tie cannot be declared direct")
    key = _record_key(record)
    if key in existing or key in seen:
        _fail("Gap repair must not duplicate a previous or same-batch stream/school/rank record")
    seen.add(key)


def _validate_records(batches: list[Dict[str, Any]], source_ids: set[str], existing: set[tuple[str, str, int]]) -> list[Dict[str, Any]]:
    if len(batches) != 1:
        _fail("Gap repair requires exactly one seed batch")
    batch = batches[0]
    try:
        validate_instance(batch, load_schema("manual-ranking-seed-batch.json"))
    except SchemaValidationError as error:
        raise ProgramGapRepairValidationError(str(error)) from error
    if batch.get("batch_id") != "stage-2g-c-program-ranking-gap-repair":
        _fail("Gap repair batch id is invalid")
    records = batch.get("records")
    if not isinstance(records, list) or not records:
        _fail("Gap repair requires at least one newly accepted record")
    seen: set[tuple[str, str, int]] = set()
    for record in records:
        _validate_record(record, source_ids, existing, seen)
    return records


def _validate_mappings(document: Dict[str, Any], records: list[Dict[str, Any]], source_ids: set[str]) -> int:
    if document.get("record_type") != "pilot_identity_mappings" or not isinstance(document.get("mappings"), list) or len(document["mappings"]) != len(records):
        _fail("Gap repair requires one identity mapping per accepted record")
    by_id = {record["record_id"]: record for record in records}
    seen = set()
    for mapping in document["mappings"]:
        record = by_id.get(mapping.get("record_id"))
        if record is None or mapping.get("record_id") in seen:
            _fail("Gap repair identity mapping is unknown or duplicated")
        seen.add(mapping["record_id"])
        if mapping.get("resolution_status") != "resolved" or mapping.get("unitid") is not None:
            _fail("Gap repair mappings must not guess UNITID")
        if mapping.get("source_display_name") != record["school_display_name"]:
            _fail("Gap repair mapping must preserve source display name")
        for field in ("normalized_display_name", "official_institution_name", "canonical_identity_id"):
            _nonempty(mapping.get(field), f"mapping.{field}")
        if not isinstance(mapping.get("identity_source"), dict) or mapping["identity_source"].get("source_id") not in source_ids:
            _fail("Gap repair identity source does not resolve")
    return len(seen)


def _validate_supporting_artifacts(candidates: Dict[str, Any], coverage: Dict[str, Any], gap_report: Dict[str, Any], dedupe: Dict[str, Any], new: list[Dict[str, Any]], existing: list[Dict[str, Any]], source_ids: set[str]) -> None:
    if candidates.get("record_type") != "program_gap_repair_candidate_observations" or candidates.get("edition_target") != EDITION:
        _fail("Gap repair requires candidate observations")
    observations = candidates.get("observations")
    if not isinstance(observations, list):
        _fail("Gap repair candidate observations must be an array")
    for observation in observations:
        if observation.get("source_id") not in source_ids or observation.get("category_id") not in SCOPE_STREAMS:
            _fail("Gap repair candidate observation must have an in-scope source")
        if observation.get("disposition") not in {"outside_top20_scope", "insufficient_direct_evidence", "source_blocked_or_unavailable"}:
            _fail("Gap repair candidate observation has invalid disposition")
    if coverage.get("record_type") != "program_gap_repair_coverage_matrix" or coverage.get("edition") != EDITION:
        _fail("Gap repair coverage matrix is invalid")
    rows = coverage.get("streams")
    if not isinstance(rows, list) or {row.get("stream_id") for row in rows} != SCOPE_STREAMS or len(rows) != len(SCOPE_STREAMS):
        _fail("Gap repair coverage must represent every in-scope stream")
    old_counts = {stream: 0 for stream in SCOPE_STREAMS}
    new_counts = {stream: 0 for stream in SCOPE_STREAMS}
    for record in existing: old_counts[record["category_id"]] += 1
    for record in new: new_counts[record["category_id"]] += 1
    for row in rows:
        stream = row["stream_id"]
        if row.get("previous_accepted_count") != old_counts[stream] or row.get("newly_added_accepted_count") != new_counts[stream] or row.get("total_accepted_count_after_repair") != old_counts[stream] + new_counts[stream]:
            _fail("Gap repair coverage counts are inconsistent")
        status = row.get("stream_status_after_repair")
        total = old_counts[stream] + new_counts[stream]
        if status == "complete":
            proof = row.get("completion_proof")
            if not isinstance(proof, dict) or proof.get("first_20_entries_verified") is not True or proof.get("boundary_tie_group_verified") is not True:
                _fail("Gap repair cannot claim complete without Top-20 and boundary proof")
        elif total and status != "incomplete":
            _fail("Streams with partial coverage must remain incomplete")
        elif not total and status not in {"no_verified_records", "partial_only", "source_blocked_or_unavailable"}:
            _fail("Streams with no accepted records need an honest empty-coverage status")
    if gap_report.get("record_type") != "program_gap_repair_report" or {item.get("stream_id") for item in gap_report.get("stream_gaps", [])} != SCOPE_STREAMS:
        _fail("Gap repair report must disclose every stream")
    if dedupe.get("record_type") != "program_gap_repair_duplicate_dedupe_report" or dedupe.get("existing_records_considered") != len(existing):
        _fail("Gap repair duplicate report is invalid")
    for document in (coverage, gap_report, dedupe):
        for field in ("canonical_universe_created", "selection_memberships_created", "frontend_export_created"):
            if document.get(field) is not False:
                _fail("Gap repair must not create a universe, memberships, or frontend export")


def validate_program_gap_repair_artifacts(batches: list[Dict[str, Any]], identities: Dict[str, Any], candidates: Dict[str, Any], coverage: Dict[str, Any], manifest: Dict[str, Any], gap_report: Dict[str, Any], dedupe: Dict[str, Any], existing_root: Path) -> Dict[str, Any]:
    sources = _validate_manifest(manifest)
    existing = _load_prior_records(existing_root)
    new = _validate_records(batches, set(sources), {_record_key(record) for record in existing})
    resolved = _validate_mappings(identities, new, set(sources))
    _validate_supporting_artifacts(candidates, coverage, gap_report, dedupe, new, existing, set(sources))
    return {"record_type":"program_gap_repair_validation_result","edition":EDITION,"new_verified_records_stageable":len(new),"previous_verified_records_considered":len(existing),"streams_represented":len(SCOPE_STREAMS),"psychology_newly_added":sum(record["category_id"] == "undergraduate-psychology" for record in new),"economics_newly_added":sum(record["category_id"] == "undergraduate-economics" for record in new),"identity_resolved":resolved,"identity_unresolved":0,"canonical_universe_created":False,"selection_memberships_created":False,"frontend_export_created":False,"result":"passed"}


def write_program_gap_repair_validation_result(result: Dict[str, Any], output: Path, command: str) -> None:
    persisted = dict(result)
    persisted["generated_at"] = datetime.now(timezone.utc).isoformat()
    persisted["validator"] = {"command": command, "python": "python3"}
    output.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_program_gap_repair_bundle(input_document: Dict[str, Any], existing_root: Path) -> Dict[str, Dict[str, Any]]:
    if input_document.get("record_type") != "program_gap_repair_seed_input" or input_document.get("edition") != EDITION:
        _fail("Gap repair input has the wrong type or edition")
    sources = input_document.get("sources"); observations = input_document.get("records")
    if not isinstance(sources, list) or not isinstance(observations, list):
        _fail("Gap repair input requires source and record arrays")
    manifest = {"record_type":"program_gap_repair_source_manifest","edition":EDITION,"accessed_at":input_document.get("accessed_at"),"sources":sources}
    by_source = _validate_manifest(manifest)
    records=[]; mappings=[]
    for obs in observations:
        source = by_source.get(obs.get("source_id")); quotes = obs.get("anchor_quotes")
        if source is None or not isinstance(quotes, dict): _fail("Gap repair observation needs a known source and quotes")
        direct = sorted(REQUIRED_DIRECT_FIELDS)
        if obs.get("tied_direct") is True: direct.append("tied")
        for field in direct: _nonempty(quotes.get(field), f"gap_input.anchor_quotes.{field}")
        record={"record_id":obs.get("record_id"),"ranking_system":"u_s_news","ranking_family":FAMILY,"category_id":obs.get("category_id"),"edition":EDITION,"school_display_name":obs.get("school_display_name"),"source_display_name":obs.get("school_display_name"),"numeric_rank":obs.get("numeric_rank"),"displayed_rank":obs.get("displayed_rank",f"#{obs.get('numeric_rank')}"),"tied":obs.get("tied"),"source_access_type":source["source_access_type"],"source_confidence":source["source_confidence"],"verification_basis":"official_school_or_college_page_direct","source":{"source_id":obs["source_id"],"url":source["url"],"source_type":source["source_type"],"accessed_at":input_document["accessed_at"]},"evidence":{"directly_supported_fields":direct},"edition_evidence":"edition_direct","evidence_anchors":[{"field":field,"source_id":obs["source_id"],"quote":quotes[field],"evidence_type":"direct_quote"} for field in direct],"entered_by":"pathos-stage-2g-c","entered_at":input_document["accessed_at"],"verification_status":"verified"}
        if record["tied"] and "tied" not in direct: record["inference_notes"]="Tie inferred from repeated rank within the official source list; tied is not directly supported."
        if not record["tied"]: record["inference_notes"]="No tie marker was published on this official page; tied=false means no tie was observed in this repair, not cutoff-wide tie coverage."
        records.append(record)
        mappings.append({"record_id":record["record_id"],"source_display_name":record["school_display_name"],"normalized_display_name":record["school_display_name"],"official_institution_name":obs.get("official_institution_name"),"aliases":[record["school_display_name"]],"unitid":None,"unitid_status":"not_collected","identity_confidence":"high","identity_source":{"source_id":obs["source_id"],"url":source["url"]},"resolution_status":"resolved","canonical_identity_id":obs.get("canonical_identity_id")})
    existing=_load_prior_records(existing_root)
    old={s:0 for s in SCOPE_STREAMS}; added={s:0 for s in SCOPE_STREAMS}
    for r in existing: old[r["category_id"]]+=1
    for r in records: added[r["category_id"]]+=1
    attempts=input_document.get("candidate_observations", [])
    coverage=[]; gaps=[]
    for stream in sorted(SCOPE_STREAMS):
        total=old[stream]+added[stream]
        status="incomplete" if total else "no_verified_records"
        reason=("Direct official records exist, but no complete first-20-entry plus boundary-tie proof is available." if total else "Official sources were checked; no direct 2026 Top-20 record met accepted-seed requirements.")
        coverage.append({"stream_id":stream,"category_name":STREAM_NAMES[stream],"previous_accepted_count":old[stream],"newly_added_accepted_count":added[stream],"total_accepted_count_after_repair":total,"partial_count":0,"unresolved_count":0,"duplicate_skipped_count":0,"stream_status_after_repair":status,"complete_top20_with_boundary_ties":False,"gap_reason":reason,"recommended_next_action":"Obtain lawful complete Top-20 and boundary-tie evidence or additional direct official institutional records."})
        gaps.append({"stream_id":stream,"stream_status_after_repair":status,"gap_reason":reason})
    return {"program-gap-repair.json":{"record_type":"manual_ranking_seed_batch","schema_version":"v1","batch_id":"stage-2g-c-program-ranking-gap-repair","created_at":input_document["accessed_at"],"records":records},"source-manifest.json":manifest,"identity-mappings.json":{"record_type":"pilot_identity_mappings","mappings":mappings},"candidate-observations.json":{"record_type":"program_gap_repair_candidate_observations","edition_target":EDITION,"observations":attempts},"coverage-matrix.json":{"record_type":"program_gap_repair_coverage_matrix","edition":EDITION,"streams":coverage,"canonical_universe_created":False,"selection_memberships_created":False,"frontend_export_created":False},"gap-repair-report.json":{"record_type":"program_gap_repair_report","edition":EDITION,"stream_gaps":gaps,"canonical_universe_created":False,"selection_memberships_created":False,"frontend_export_created":False},"duplicate-dedupe-report.json":{"record_type":"program_gap_repair_duplicate_dedupe_report","edition":EDITION,"existing_records_considered":len(existing),"new_records_created":len(records),"duplicate_skipped_records":[],"canonical_universe_created":False,"selection_memberships_created":False,"frontend_export_created":False}}


def write_program_gap_repair_bundle(bundle: Dict[str, Dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, document in bundle.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
