"""Deterministic Stage 2I source-limited university-universe candidate v2."""

import json
from pathlib import Path
from typing import Any, Dict

from .official_program_sweep import EDITION, FAMILY as PROGRAM_FAMILY, SCOPE_STREAMS
from .national_completion import FAMILY as NATIONAL_FAMILY


NATIONAL_REASON = "national_top_50_candidate"
PROGRAM_REASON = "program_top_20_candidate"
ALLOWED_REASONS = {NATIONAL_REASON, PROGRAM_REASON}


class UniverseCandidateV2ValidationError(ValueError):
    """Raised when candidate v2 leaves its verified, non-final boundary."""


def _fail(message: str) -> None:
    raise UniverseCandidateV2ValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read required v2 input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(document, dict):
        _fail(f"v2 input must be a JSON object: {path}")
    return document


def _identity_index(root: Path) -> Dict[str, Dict[str, Any]]:
    mappings: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.rglob("*.json")):
        document = _read_json(path)
        for mapping in document.get("mappings", []):
            if not isinstance(mapping, dict) or not mapping.get("record_id"):
                continue
            record_id = mapping["record_id"]
            current = mappings.get(record_id)
            if current and current != mapping:
                _fail(f"Conflicting identity mappings for {record_id}")
            mappings[record_id] = mapping
    return mappings


def _valid_record(record: Dict[str, Any], family: str) -> bool:
    if record.get("ranking_system") != "u_s_news" or record.get("ranking_family") != family:
        return False
    if record.get("edition") != EDITION or record.get("verification_status") != "verified":
        return False
    if family == NATIONAL_FAMILY:
        return record.get("category_id") == "national-universities"
    return record.get("category_id") in SCOPE_STREAMS


def _record_key(record: Dict[str, Any]) -> tuple[str, str, int]:
    return (
        record["category_id"],
        record["school_display_name"].casefold(),
        record["numeric_rank"],
    )


def _excluded_observation_counts(root: Path) -> Dict[str, int]:
    """Count non-accepted observations for transparent v2 exclusion disclosure."""
    counts = {"partial": 0, "unresolved": 0, "outside_scope": 0}
    for path in sorted(root.rglob("*.json")):
        if "completion-programs-top20-attempt" in path.parts:
            continue
        document = _read_json(path)
        for observation in document.get("observations", []):
            if not isinstance(observation, dict):
                continue
            status = observation.get("verification_status") or observation.get("disposition")
            if status == "partially_verified":
                counts["partial"] += 1
            elif status == "unresolved":
                counts["unresolved"] += 1
            elif status == "outside_top20_scope":
                counts["outside_scope"] += 1
    return counts


def load_v2_inputs(root: Path) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Return exact accepted National and program inputs, excluding all observations."""
    identities = _identity_index(root)
    national_path = root / "completion-national" / "national-universities-top-50.json"
    national_document = _read_json(national_path)
    national = [record for record in national_document.get("records", []) if isinstance(record, dict) and _valid_record(record, NATIONAL_FAMILY)]
    if len(national) != 50:
        _fail("Candidate v2 requires exactly 50 accepted National completion records")

    program: list[Dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if "completion-national" in path.parts or "completion-programs-top20-attempt" in path.parts:
            continue
        document = _read_json(path)
        for record in document.get("records", []):
            if isinstance(record, dict) and _valid_record(record, PROGRAM_FAMILY):
                program.append(record)
    program_keys = [_record_key(record) for record in program]
    if len(program_keys) != len(set(program_keys)):
        _fail("Candidate v2 program inputs contain a duplicate accepted ranking record")
    if len(program) != 80:
        _fail("Candidate v2 requires the Stage 2H total of 80 accepted program records")

    for record in [*national, *program]:
        mapping = identities.get(record.get("record_id"))
        if not isinstance(mapping, dict) or mapping.get("resolution_status") != "resolved":
            _fail(f"Accepted record has no resolved identity mapping: {record.get('record_id')}")
        if not isinstance(mapping.get("canonical_identity_id"), str) or not mapping["canonical_identity_id"]:
            _fail("Candidate v2 does not allow an unresolved or guessed identity")
        if mapping.get("unitid") is not None:
            _fail("Candidate v2 must not use unreviewed UNITID enrichment")
    return national, program, identities


def _anchor_refs(record: Dict[str, Any]) -> list[Dict[str, str]]:
    anchors = record.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        _fail(f"Accepted v2 input lacks anchors: {record.get('record_id')}")
    refs = []
    for anchor in anchors:
        if not isinstance(anchor, dict) or not all(isinstance(anchor.get(field), str) and anchor[field] for field in ("field", "source_id")):
            _fail("Candidate v2 input has invalid evidence anchor")
        refs.append({"record_id": record["record_id"], "field": anchor["field"], "source_id": anchor["source_id"]})
    return refs


def _flags() -> Dict[str, bool]:
    return {
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "final_universe": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
    }


def build_candidate_v2(root: Path, stage2h_summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build deterministic v2 artifacts from the accepted completed-National/program corpus."""
    national, program, identities = load_v2_inputs(root)
    exclusions = _excluded_observation_counts(root)
    required_summary = {
        "streams_assessed": 28,
        "total_accepted_program_records": 80,
        "complete_stream_count": 0,
        "incomplete_stream_count": 27,
        "manual_seed_needed_stream_count": 1,
        "program_top20_completion_ready": False,
    }
    for field, expected in required_summary.items():
        if stage2h_summary.get(field) != expected:
            _fail(f"Stage 2H readiness summary {field} is not the accepted baseline")

    candidates: Dict[str, Dict[str, Any]] = {}
    memberships: Dict[tuple[str, str], Dict[str, Any]] = {}
    sources: Dict[str, Dict[str, Any]] = {}
    identity_refs: Dict[str, Dict[str, Any]] = {}
    for record in sorted([*national, *program], key=lambda item: item["record_id"]):
        mapping = identities[record["record_id"]]
        canonical_id = mapping["canonical_identity_id"]
        candidate_id = f"candidate-v2:{canonical_id.removeprefix('institution:')}"
        reason = NATIONAL_REASON if record["ranking_family"] == NATIONAL_FAMILY else PROGRAM_REASON
        candidate = candidates.setdefault(canonical_id, {
            "canonical_university_id": canonical_id,
            "candidate_university_id": candidate_id,
            "display_name": mapping.get("official_institution_name") or record["school_display_name"],
            "source_names": [], "aliases": [], "source_membership_reasons": [],
            "supporting_ranking_record_ids": [], "supporting_streams": [], "source_ids": [],
            "evidence_anchor_references": [], "identity_mapping_references": [],
            "identity_confidence": mapping.get("identity_confidence"), "verification_status": "verified_source_limited",
            "unitid": None,
            "source_limitation_flags": _flags(),
            "notes": ["Source-limited candidate v2; not a final universe or official selection membership."],
        })
        candidate["source_names"].append(record["school_display_name"])
        candidate["aliases"].extend(mapping.get("aliases", []))
        candidate["source_membership_reasons"].append(reason)
        candidate["supporting_ranking_record_ids"].append(record["record_id"])
        candidate["supporting_streams"].append(record["category_id"])
        candidate["source_ids"].append(record["source"]["source_id"])
        candidate["evidence_anchor_references"].extend(_anchor_refs(record))
        candidate["identity_mapping_references"].append(record["record_id"])
        source = record["source"]
        sources.setdefault(source["source_id"], {
            "source_id": source["source_id"], "url": source.get("url"), "source_type": source.get("source_type"),
            "record_ids": [], "ranking_families": [],
        })["record_ids"].append(record["record_id"])
        sources[source["source_id"]]["ranking_families"].append(record["ranking_family"])
        identity_refs[record["record_id"]] = {
            "record_id": record["record_id"], "canonical_university_id": canonical_id,
            "source_display_name": record["school_display_name"], "official_institution_name": candidate["display_name"],
            "unitid": None, "resolution_status": mapping["resolution_status"],
            "identity_confidence": mapping.get("identity_confidence"),
        }
        membership = memberships.setdefault((canonical_id, reason), {
            "candidate_university_id": candidate_id, "canonical_university_id": canonical_id,
            "membership_reason": reason, "supporting_ranking_record_ids": [], "supporting_streams": [],
            "source_ids": [], "evidence_anchor_references": [],
        })
        membership["supporting_ranking_record_ids"].append(record["record_id"])
        membership["supporting_streams"].append(record["category_id"])
        membership["source_ids"].append(record["source"]["source_id"])
        membership["evidence_anchor_references"].extend(_anchor_refs(record))

    for candidate in candidates.values():
        for field in ("source_names", "aliases", "source_membership_reasons", "supporting_ranking_record_ids", "supporting_streams", "source_ids", "identity_mapping_references"):
            candidate[field] = sorted(set(candidate[field]))
        candidate["evidence_anchor_references"] = sorted(candidate["evidence_anchor_references"], key=lambda item: (item["record_id"], item["field"], item["source_id"]))
    for membership in memberships.values():
        for field in ("supporting_ranking_record_ids", "supporting_streams", "source_ids"):
            membership[field] = sorted(set(membership[field]))
        membership["evidence_anchor_references"] = sorted(membership["evidence_anchor_references"], key=lambda item: (item["record_id"], item["field"], item["source_id"]))
    for source in sources.values():
        source["record_ids"] = sorted(set(source["record_ids"]))
        source["ranking_families"] = sorted(set(source["ranking_families"]))

    university_rows = sorted(candidates.values(), key=lambda item: item["candidate_university_id"])
    membership_rows = sorted(memberships.values(), key=lambda item: (item["candidate_university_id"], item["membership_reason"]))
    national_ids = {identities[record["record_id"]]["canonical_identity_id"] for record in national}
    program_ids = {identities[record["record_id"]]["canonical_identity_id"] for record in program}
    common_flags = _flags()
    disclosure = {
        **common_flags,
        "national_top50_accepted": True,
        "national_top50_record_count": len(national),
        "program_accepted_record_count": len(program),
        "program_stream_count": 28,
        "program_complete_stream_count": 0,
        "program_incomplete_stream_count": 27,
        "economics_manual_seed_needed": True,
        "program_top20_corpus_complete": False,
        "excluded_partial_record_count": exclusions["partial"],
        "excluded_unresolved_record_count": exclusions["unresolved"],
        "excluded_outside_scope_observation_count": exclusions["outside_scope"],
        "candidate_allowed_for_deep_dataset_planning": True,
        "candidate_allowed_for_final_product": False,
        "final_universe_requires_future_gate": True,
    }
    summary = {
        "record_type": "university_universe_candidate_v2_generation_summary", "edition": EDITION,
        "candidate_university_count": len(university_rows), "national_only_count": len(national_ids - program_ids),
        "program_only_count": len(program_ids - national_ids), "both_count": len(national_ids & program_ids),
        "supporting_national_record_count": len(national), "supporting_program_record_count": len(program),
        "excluded_partial_record_count": exclusions["partial"], "excluded_unresolved_record_count": exclusions["unresolved"],
        "excluded_outside_scope_observation_count": exclusions["outside_scope"], "program_complete_stream_count": 0,
        "program_incomplete_stream_count": 27, "economics_manual_seed_needed": True,
        "deterministic_generation": True, **common_flags,
    }
    return {
        "candidate-universities.json": {"metadata": {"record_type": "university_universe_candidate_v2", "edition": EDITION, **common_flags}, "universities": university_rows},
        "candidate-memberships.json": {"metadata": {"record_type": "university_universe_candidate_v2_memberships", **common_flags}, "memberships": membership_rows},
        "candidate-source-manifest.json": {"record_type": "university_universe_candidate_v2_source_manifest", "edition": EDITION, "sources": sorted(sources.values(), key=lambda item: item["source_id"])},
        "candidate-identity-mappings.json": {"record_type": "university_universe_candidate_v2_identity_mappings", "mappings": sorted(identity_refs.values(), key=lambda item: item["record_id"])},
        "candidate-gap-disclosure.json": {"record_type": "university_universe_candidate_v2_gap_disclosure", "edition": EDITION, **disclosure},
        "candidate-generation-summary.json": summary,
        "candidate-dedupe-report.json": {"record_type": "university_universe_candidate_v2_dedupe_report", "input_record_count": len(national) + len(program), "candidate_university_count": len(university_rows), "duplicate_identity_occurrences_merged": len(national) + len(program) - len(university_rows), "duplicate_ranking_records_excluded": 0, **common_flags},
    }


def _validate_source_policy(policy_text: str) -> None:
    required = ("CollegeData", "field-level provenance", "Times Higher Education", "THE", "QS", "xuanxiao.org", "不得写入 US News ranking", "US News ranking fields")
    if any(term not in policy_text for term in required):
        _fail("Source policy lacks the required detail-versus-US-News ranking boundary")


def validate_source_policy_use(source: str, field_domain: str, *, has_field_provenance: bool) -> None:
    """Enforce the M-1 source boundary for future field-level enrichment use."""
    if field_domain == "usnews_ranking" and source in {"CollegeData", "THE", "QS", "xuanxiao.org"}:
        _fail(f"{source} cannot populate a U.S. News ranking field")
    if source == "CollegeData" and field_domain == "detail" and not has_field_provenance:
        _fail("CollegeData detail enrichment requires field-level provenance")


def validate_candidate_v2_artifacts(artifacts: Dict[str, Dict[str, Any]], root: Path, stage2h_summary: Dict[str, Any], policy_text: str) -> Dict[str, Any]:
    """Fail closed by requiring byte-identical deterministic regeneration."""
    _validate_source_policy(policy_text)
    expected = build_candidate_v2(root, stage2h_summary)
    required = set(expected)
    if set(artifacts) != required:
        _fail("Candidate v2 requires every deterministic artifact and no extras")
    if artifacts != expected:
        _fail("Candidate v2 artifact does not match deterministic accepted-record generation")
    candidates = artifacts["candidate-universities.json"]["universities"]
    memberships = artifacts["candidate-memberships.json"]["memberships"]
    candidate_ids = {item["candidate_university_id"] for item in candidates}
    if len(candidate_ids) != len(candidates):
        _fail("Candidate v2 failed canonical identity dedupe")
    if any(item.get("membership_reason") not in ALLOWED_REASONS for item in memberships):
        _fail("Candidate v2 memberships must preserve only atomic reasons")
    if any(item.get("membership_reason") == "both_candidate" for item in memberships):
        _fail("Candidate v2 cannot use both as a membership reason")
    if any(item.get("candidate_university_id") not in candidate_ids for item in memberships):
        _fail("Candidate v2 membership references unknown university")
    return {"record_type": "university_universe_candidate_v2_validation_result", "edition": EDITION, "candidate_university_count": len(candidates), "membership_count": len(memberships), "result": "passed", **_flags()}


def write_candidate_v2_bundle(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payloads = {**artifacts, "candidate-validation-result.json": validation}
    for name, document in payloads.items():
        (output / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
