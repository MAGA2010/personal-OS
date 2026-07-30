"""Deterministic Stage 3B overlay for demo-critical detail gaps.

The module treats Candidate v2 and Stage 3 as immutable inputs.  It resolves
only explicit, reviewed aliases to exact IPEDS institution names; it never
performs fuzzy identity matching or writes ranking fields from detail sources.
"""

import copy
import csv
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .stage3_program_mvp import (
    FLAGS,
    IPEDS_URL,
    Stage3ProgramMvpValidationError,
    _amount,
    _base_university,
    _candidate_rows,
    _cip_titles,
    _csv_from_zip,
    _major_rows,
    _normal,
    _tuition_records,
    validate_undergraduate_tuition_record,
)
from .universe_candidate_v2 import validate_source_policy_use


SCORECARD_DOWNLOAD_URL = (
    "https://ed-public-download.scorecard.network/downloads/"
    "Most-Recent-Cohorts-Institution_05192025.zip"
)
SCORECARD_REFERENCE_URL = "https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf"
SCORECARD_ZIP = "Most-Recent-Cohorts-Institution_05192025.zip"
SCORECARD_CSV = "Most-Recent-Cohorts-Institution_05192025.csv"
STAGE3_FILES = (
    "program-mvp-universities.json",
    "program-mvp-programs.json",
    "program-mvp-tuition.json",
    "program-mvp-majors.json",
)
STAGE3B_FLAGS = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3BValidationError(ValueError):
    """Raised when an overlay crosses Stage 3B identity/detail boundaries."""


def _fail(message: str) -> None:
    raise Stage3BValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3B input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3B input must be a JSON object: {path}")
    return value


def _read_stage3(stage3_dir: Path) -> Dict[str, Dict[str, Any]]:
    documents = {name: _read_json(stage3_dir / name) for name in STAGE3_FILES}
    universities = documents["program-mvp-universities.json"].get("universities")
    if not isinstance(universities, list) or len(universities) != 62:
        _fail("Stage 3 overlay requires all 62 Stage 3 university rows")
    return documents


def _scorecard_rows(cache: Path) -> Dict[str, Dict[str, str]]:
    path = cache / SCORECARD_ZIP
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open(SCORECARD_CSV) as raw:
                rows = list(csv.DictReader(line.decode("utf-8-sig") for line in raw))
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        _fail(f"Missing official College Scorecard cache input: {path}")
        raise AssertionError("unreachable") from error
    if not rows or "UNITID" not in rows[0] or "STUFACR" not in rows[0]:
        _fail("College Scorecard input must contain UNITID and STUFACR")
    return {row["UNITID"]: row for row in rows if row.get("UNITID")}


def _mapping_rows(path: Path, candidates: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    document = _read_json(path)
    rows = document.get("mappings")
    if document.get("record_type") != "stage3b_reviewed_identity_alias_mappings" or not isinstance(rows, list):
        _fail("Stage 3B requires reviewed identity alias mappings")
    resolved: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        required = ("mapping_id", "candidate_id", "reviewed_candidate_alias", "exact_ipeds_instnm", "review_note", "evidence_anchor")
        if not all(row.get(field) for field in required):
            _fail("Reviewed alias mapping lacks required fields")
        candidate = candidates.get(row["candidate_id"])
        if candidate is None:
            _fail("Reviewed alias mapping references a non-candidate university")
        aliases = {candidate["display_name"], *candidate.get("aliases", []), *candidate.get("source_names", [])}
        if row["reviewed_candidate_alias"] not in aliases:
            _fail("Reviewed alias must be an explicit Candidate v2 name or alias")
        if row["candidate_id"] in resolved:
            _fail("A candidate may have at most one Stage 3B reviewed alias mapping")
        resolved[row["candidate_id"]] = row
    return resolved


def _program_observations(path: Path, candidates: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    document = _read_json(path)
    rows = document.get("observations")
    if document.get("record_type") != "stage3b_official_undergraduate_program_observations" or not isinstance(rows, list):
        _fail("Stage 3B requires official undergraduate program observations")
    values: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    prohibited = re.compile(r"\b(graduate|mba|law|medical|professional)\b", re.IGNORECASE)
    for row in rows:
        required = ("candidate_id", "program_name", "source_id", "source_type", "source_url", "evidence_anchor", "undergraduate_status", "source_basis")
        if not all(row.get(field) for field in required):
            _fail("Official program observation lacks required provenance")
        if row["candidate_id"] not in candidates:
            _fail("Official program observation references a non-candidate university")
        if row["source_type"] != "official_institutional" or row["undergraduate_status"] != "undergraduate":
            _fail("Stage 3B program observation must be official and undergraduate")
        if prohibited.search(row["program_name"]):
            _fail("Graduate-only or professional program cannot enter Stage 3B demo programs")
        anchor = row["evidence_anchor"]
        if not isinstance(anchor, dict) or anchor.get("source_id") != row["source_id"] or not anchor.get("quote"):
            _fail("Official program observation requires a source-resolving evidence anchor")
        values[row["candidate_id"]].append(row)
    return values


def _exact_hd_row(mapping: Dict[str, Any], hd_by_name: Dict[str, List[Dict[str, str]]]) -> Optional[Dict[str, str]]:
    matches = hd_by_name.get(_normal(mapping["exact_ipeds_instnm"]), [])
    if len(matches) != 1:
        return None
    row = matches[0]
    if row.get("INSTNM") != mapping["exact_ipeds_instnm"]:
        _fail("Reviewed identity mapping must resolve to the exact declared IPEDS INSTNM")
    return row


def _overlay_base(
    candidate: Dict[str, Any],
    stage3_row: Dict[str, Any],
    mapping: Optional[Dict[str, Any]],
    hd_by_name: Dict[str, List[Dict[str, str]]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    original_gap = stage3_row.get("unitid") is None
    if not original_gap:
        return copy.deepcopy(stage3_row), {
            "candidate_id": candidate["candidate_university_id"], "original_identity_gap": False,
            "unitid": stage3_row.get("unitid"), "resolution_status": "not_applicable_already_resolved",
            "match_method": None, "mapping_id": None, "source_id": stage3_row.get("identity_source_id"),
            "evidence_anchor": None, "null_reason": None,
        }
    if mapping is None:
        return copy.deepcopy(stage3_row), {
            "candidate_id": candidate["candidate_university_id"], "original_identity_gap": True,
            "unitid": None, "resolution_status": "unresolved", "match_method": None,
            "mapping_id": None, "source_id": None, "evidence_anchor": None,
            "null_reason": "no_reviewed_alias_mapping",
        }
    hd = _exact_hd_row(mapping, hd_by_name)
    if hd is None:
        return copy.deepcopy(stage3_row), {
            "candidate_id": candidate["candidate_university_id"], "original_identity_gap": True,
            "unitid": None, "resolution_status": "unresolved", "match_method": None,
            "mapping_id": mapping["mapping_id"], "source_id": "source_ipeds_hd2024",
            "evidence_anchor": mapping["evidence_anchor"], "null_reason": "reviewed_alias_did_not_resolve_to_one_exact_ipeds_row",
        }
    base = _base_university(candidate, hd)
    return base, {
        "candidate_id": candidate["candidate_university_id"], "original_identity_gap": True,
        "unitid": base["unitid"], "resolution_status": "resolved", "match_method": "reviewed_alias_exact_ipeds_instnm",
        "mapping_id": mapping["mapping_id"], "source_id": "source_ipeds_hd2024",
        "source_reference": IPEDS_URL, "evidence_anchor": mapping["evidence_anchor"], "null_reason": None,
        "review_note": mapping["review_note"], "exact_ipeds_instnm": mapping["exact_ipeds_instnm"],
    }


def _ratio_row(base: Dict[str, Any], scorecard: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    common = {
        "candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "display_name": base["display_name"],
        "reporting_year": "College Scorecard institution release 2025-05-19", "source_type": "college_scorecard",
        "source_id": "source_college_scorecard_institution_2025_05_19", "source_reference": SCORECARD_DOWNLOAD_URL,
        "source_url": SCORECARD_REFERENCE_URL, "derived_ratio": False, "derivation_formula": None,
        "derivation_variable_sources": None, "confidence": "high",
    }
    if not base.get("unitid"):
        return {**common, "student_faculty_ratio": None, "evidence_anchor": None,
                "extraction_notes": "No ratio was populated because identity remains unresolved.",
                "definition_notes": "No local ratio derivation was performed.",
                "null_reason": "identity_ipeds_match_not_resolved"}
    row = scorecard.get(str(base["unitid"]))
    value = _amount(row.get("STUFACR")) if row else None
    if value is None:
        return {**common, "student_faculty_ratio": None, "evidence_anchor": None,
                "extraction_notes": "College Scorecard had no usable STUFACR value for this UNITID.",
                "definition_notes": "No local ratio derivation was performed.",
                "null_reason": "official_college_scorecard_student_faculty_ratio_not_published"}
    return {**common, "student_faculty_ratio": value,
            "evidence_anchor": {"source_id": common["source_id"], "evidence_type": "dataset_row", "quote": f"UNITID={base['unitid']}; STUFACR={row.get('STUFACR')}"},
            "extraction_notes": "Read direct STUFACR from the public College Scorecard institution-level release; no local calculation was applied.",
            "definition_notes": "Direct College Scorecard STUFACR field. It is retained as the federal published ratio and is not represented as a school facts-page ratio.",
            "null_reason": None}


def _supplement_programs(
    stage3_programs: List[Dict[str, Any]], observations: Iterable[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    programs = copy.deepcopy(stage3_programs)
    existing = {_normal(row["normalized_program_name"]) for row in programs}
    added: List[Dict[str, Any]] = []
    for observation in observations:
        if len(programs) >= 5:
            break
        normalized = observation["program_name"]
        if _normal(normalized) in existing:
            continue
        row = {
            "program_name": observation["program_name"], "normalized_program_name": normalized,
            "college_or_school": observation.get("college_or_school"),
            "source_basis": observation["source_basis"], "usnews_category": None, "usnews_rank": None,
            "confidence": "medium", "source_id": observation["source_id"],
            "source_url": observation["source_url"], "source_type": observation["source_type"],
            "undergraduate_status": observation["undergraduate_status"], "evidence_anchor": observation["evidence_anchor"],
            "null_reason": None, "source_note": "Official undergraduate program supplement for demo display; not a U.S. News ranking record.",
        }
        programs.append(row)
        added.append(row)
        existing.add(_normal(normalized))
    return programs[:5], added


def _flags_valid(value: Dict[str, Any]) -> bool:
    return (
        value.get("source_limited") is True and value.get("incomplete") is True and value.get("not_final") is True
        and value.get("final_universe_generated") is False
        and value.get("official_selection_memberships_generated") is False
        and value.get("frontend_export_generated") is False
    )


def build_stage3b_gap_fill(
    *, candidate_path: Path, stage3_dir: Path, ipeds_cache: Path, official_cache: Path,
    alias_mappings_path: Path, program_observations_path: Path,
) -> Dict[str, Dict[str, Any]]:
    """Build a Stage 3B overlay without modifying any Stage 3 input artifact."""
    validate_source_policy_use("IPEDS", "detail", has_field_provenance=True)
    validate_source_policy_use("College Scorecard", "detail", has_field_provenance=True)
    candidates_list = _candidate_rows(candidate_path)
    candidates = {row["candidate_university_id"]: row for row in candidates_list}
    stage3 = _read_stage3(stage3_dir)
    stage3_universities = {row["candidate_id"]: row for row in stage3["program-mvp-universities.json"]["universities"]}
    stage3_programs = {row["candidate_id"]: row for row in stage3["program-mvp-programs.json"]["universities"]}
    if set(stage3_universities) != set(candidates) or set(stage3_programs) != set(candidates):
        _fail("Stage 3 inputs do not cover the fixed Candidate v2 universe")

    aliases = _mapping_rows(alias_mappings_path, candidates)
    observations = _program_observations(program_observations_path, candidates)
    hd_rows = _csv_from_zip(ipeds_cache, "HD2024.zip", "HD2024.csv")
    hd_by_name: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in hd_rows:
        hd_by_name[_normal(row["INSTNM"])].append(row)
    tuition_by_unitid = {row["UNITID"]: row for row in _csv_from_zip(ipeds_cache, "IC2023_AY.zip", "ic2023_ay.csv")}
    completions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in _csv_from_zip(ipeds_cache, "C2023_A.zip", "C2023_a.csv"):
        completions[row["UNITID"]].append(row)
    cip_titles = _cip_titles(ipeds_cache)
    scorecard = _scorecard_rows(official_cache)

    universities: List[Dict[str, Any]] = []
    ratio_rows: List[Dict[str, Any]] = []
    identity_rows: List[Dict[str, Any]] = []
    tuition_rows: List[Dict[str, Any]] = []
    majors_rows: List[Dict[str, Any]] = []
    program_rows: List[Dict[str, Any]] = []
    stale_original = 0
    stale_cleared = 0
    for candidate in candidates_list:
        candidate_id = candidate["candidate_university_id"]
        original = stage3_universities[candidate_id]
        base, identity = _overlay_base(candidate, original, aliases.get(candidate_id), hd_by_name)
        original_programs = stage3_programs[candidate_id]["top_5_programs_for_demo"]
        final_programs, added = _supplement_programs(original_programs, observations.get(candidate_id, []))
        original_reason = original.get("top_5_gap_reason")
        actual_gap = None if len(final_programs) == 5 else "fewer_than_five_official_undergraduate_demo_programs_available_after_stage3b"
        if original_reason and len(original_programs) == 5:
            stale_original += 1
            if actual_gap is None:
                stale_cleared += 1
        universities.append({
            **base, "top_5_programs_for_demo": final_programs, "top_5_gap_reason": actual_gap,
            "stage3b_overlay_note": "Derived overlay; Stage 3 input artifact remains unchanged.",
        })
        ratio_rows.append(_ratio_row(base, scorecard))
        if identity["original_identity_gap"]:
            identity_rows.append(identity)
            tuition = _tuition_records(base, tuition_by_unitid, _exact_hd_row(aliases[candidate_id], hd_by_name) if identity["unitid"] else None)
            majors = _major_rows(base.get("unitid"), completions, cip_titles)
            tuition_rows.append({"candidate_id": candidate_id, "canonical_id": base["canonical_id"], "display_name": base["display_name"], "original_gap": True, "resolved": bool(base.get("unitid")), "tuition_records": tuition})
            majors_rows.append({"candidate_id": candidate_id, "canonical_id": base["canonical_id"], "display_name": base["display_name"], "original_gap": True, "resolved": bool(majors), "all_undergraduate_majors": majors, "null_reason": None if majors else "official_undergraduate_areas_of_study_not_available_after_identity_resolution"})
        if len(original_programs) < 5:
            program_rows.append({"candidate_id": candidate_id, "canonical_id": base["canonical_id"], "display_name": base["display_name"], "original_gap": True, "original_program_count": len(original_programs), "added_demo_programs": added, "final_program_count": len(final_programs), "resolved": len(final_programs) == 5, "top_5_gap_reason": actual_gap})

    ratio_resolved = sum(row["student_faculty_ratio"] is not None for row in ratio_rows)
    identity_resolved = sum(row["resolution_status"] == "resolved" for row in identity_rows)
    tuition_resolved = sum(row["resolved"] for row in tuition_rows)
    majors_resolved = sum(row["resolved"] for row in majors_rows)
    program_resolved = sum(row["resolved"] for row in program_rows)
    stage3_summary = _read_json(stage3_dir / "program-mvp-summary.json")
    # Preserve the Stage 3 score's four dimensions: five demo programs,
    # student-faculty ratio, usable undergraduate tuition, and a majors/areas
    # list.  Stage 3B fills only the 11 original identity-derived tuition and
    # major gaps, so those fills must be added back to the 51 existing rows.
    tuition_coverage_after = (len(universities) - len(tuition_rows)) + tuition_resolved
    majors_coverage_after = (len(universities) - len(majors_rows)) + majors_resolved
    readiness_after = round((
        sum(len(row["top_5_programs_for_demo"]) == 5 for row in universities)
        + ratio_resolved + tuition_coverage_after + majors_coverage_after
    ) / (4 * len(universities)), 3)
    summary = {
        "record_type": "stage3b_demo_critical_gap_fill_summary", "total_universities": len(universities),
        "student_faculty_ratio_resolved_count": ratio_resolved, "student_faculty_ratio_unresolved_count": len(universities) - ratio_resolved,
        "identity_gap_original_count": len(identity_rows), "identity_gap_resolved_count": identity_resolved, "identity_gap_remaining_count": len(identity_rows) - identity_resolved,
        "tuition_gap_resolved_count": tuition_resolved, "tuition_gap_remaining_count": len(tuition_rows) - tuition_resolved,
        "majors_gap_resolved_count": majors_resolved, "majors_gap_remaining_count": len(majors_rows) - majors_resolved,
        "demo_program_gap_original_count": len(program_rows), "demo_program_gap_resolved_count": program_resolved, "demo_program_gap_remaining_count": len(program_rows) - program_resolved,
        "stale_top5_gap_reason_original_count": stale_original, "stale_top5_gap_reason_cleared_in_overlay_count": stale_cleared,
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "demo_readiness_before": stage3_summary.get("demo_readiness_score"), "demo_readiness_after": readiness_after,
        "remaining_blockers_before_frontend": [
            "Candidate v2 and Stage 3B remain source-limited and not final.",
            "Any remaining demo-program gap requires an official undergraduate source.",
        ], **STAGE3B_FLAGS,
    }
    disclosure = {
        "record_type": "stage3b_demo_critical_gap_disclosure", "stage3_artifacts_modified": False,
        "program_gap_derivation": "Stage 3B clears stale gap reasons only when the inherited program list already contains five rows; actual fewer-than-five gaps remain explicit.",
        "ratio_definition": "College Scorecard STUFACR is used as a direct federal field; no local ratio formula is applied.",
        "identity_mapping_policy": "Only reviewed alias mappings that resolve to exactly one declared IPEDS INSTNM may assign a UNITID.",
        "source_manifest": [
            {"source_id": "source_college_scorecard_institution_2025_05_19", "source_type": "official_federal_detail_dataset", "source_reference": SCORECARD_DOWNLOAD_URL, "documentation": SCORECARD_REFERENCE_URL, "field": "STUFACR"},
            {"source_id": "source_ipeds_hd2024", "source_type": "official_federal_detail_dataset", "source_reference": IPEDS_URL, "fields": ["UNITID", "INSTNM", "CITY", "STABBR", "LATITUDE", "LONGITUD"]},
        ],
        "remaining_program_gap_candidate_ids": [row["candidate_id"] for row in program_rows if not row["resolved"]],
        **STAGE3B_FLAGS,
    }
    return {
        "stage3b-mvp-universities.json": {"metadata": {"record_type": "stage3b_mvp_universities", **STAGE3B_FLAGS}, "universities": universities},
        "stage3b-student-faculty.json": {"metadata": {"record_type": "stage3b_student_faculty", **STAGE3B_FLAGS}, "universities": ratio_rows},
        "stage3b-identity-gap-fill.json": {"metadata": {"record_type": "stage3b_identity_gap_fill", **STAGE3B_FLAGS}, "universities": identity_rows},
        "stage3b-tuition-gap-fill.json": {"metadata": {"record_type": "stage3b_tuition_gap_fill", **STAGE3B_FLAGS}, "universities": tuition_rows},
        "stage3b-majors-gap-fill.json": {"metadata": {"record_type": "stage3b_majors_gap_fill", **STAGE3B_FLAGS}, "universities": majors_rows},
        "stage3b-program-gap-fill.json": {"metadata": {"record_type": "stage3b_program_gap_fill", **STAGE3B_FLAGS}, "universities": program_rows},
        "stage3b-gap-disclosure.json": disclosure,
        "stage3b-summary.json": summary,
    }


def validate_stage3b_gap_fill(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3_dir: Path, ipeds_cache: Path,
    official_cache: Path, alias_mappings_path: Path, program_observations_path: Path,
) -> Dict[str, Any]:
    """Fail closed unless a bundle exactly matches deterministic regeneration."""
    expected = build_stage3b_gap_fill(
        candidate_path=candidate_path, stage3_dir=stage3_dir, ipeds_cache=ipeds_cache, official_cache=official_cache,
        alias_mappings_path=alias_mappings_path, program_observations_path=program_observations_path,
    )
    if artifacts != expected:
        _fail("Stage 3B artifacts must match deterministic regeneration")
    summary = artifacts["stage3b-summary.json"]
    if summary["total_universities"] != 62 or summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0 or not _flags_valid(summary):
        _fail("Stage 3B summary violates scope, source-policy, or final-output boundaries")
    universities = artifacts["stage3b-mvp-universities.json"]["universities"]
    if {row["candidate_id"] for row in universities} != {row["candidate_university_id"] for row in _candidate_rows(candidate_path)}:
        _fail("Stage 3B university scope must equal Candidate v2")
    for row in universities:
        if len(row["top_5_programs_for_demo"]) == 5 and row.get("top_5_gap_reason") is not None:
            _fail("Full demo-program rows may not retain a stale top_5_gap_reason")
        if len(row["top_5_programs_for_demo"]) < 5 and not row.get("top_5_gap_reason"):
            _fail("Incomplete demo-program rows require an explicit gap reason")
        for program in row["top_5_programs_for_demo"]:
            if program.get("source_basis") != "usnews_program_ranking" and (program.get("usnews_category") is not None or program.get("usnews_rank") is not None):
                _fail("Detail source cannot populate or overwrite U.S. News ranking fields")
    for row in artifacts["stage3b-student-faculty.json"]["universities"]:
        if row["student_faculty_ratio"] is None:
            if not row.get("null_reason"):
                _fail("Unresolved student-faculty ratio requires null reason")
        elif not all(row.get(field) for field in ("source_id", "source_reference", "evidence_anchor", "definition_notes")):
            _fail("Resolved student-faculty ratio requires official field provenance")
        if row.get("derived_ratio") and not (row.get("derivation_formula") and row.get("derivation_variable_sources")):
            _fail("Derived student-faculty ratio requires formula and variable sources")
    mappings = _mapping_rows(alias_mappings_path, {row["candidate_university_id"]: row for row in _candidate_rows(candidate_path)})
    for row in artifacts["stage3b-identity-gap-fill.json"]["universities"]:
        if row.get("unitid") is not None:
            mapping = mappings.get(row["candidate_id"])
            if mapping is None or row.get("match_method") != "reviewed_alias_exact_ipeds_instnm" or row.get("mapping_id") != mapping["mapping_id"]:
                _fail("New UNITID requires an explicit reviewed alias mapping and exact IPEDS match")
    for row in artifacts["stage3b-tuition-gap-fill.json"]["universities"]:
        for tuition in row["tuition_records"]:
            try:
                validate_undergraduate_tuition_record(tuition)
            except Stage3ProgramMvpValidationError as error:
                _fail(str(error))
    for row in artifacts["stage3b-program-gap-fill.json"]["universities"]:
        for program in row["added_demo_programs"]:
            if program.get("source_type") != "official_institutional" or program.get("undergraduate_status") != "undergraduate":
                _fail("Stage 3B added program must be an official undergraduate observation")
    return {"record_type": "stage3b_demo_critical_gap_fill_validation_result", "result": "passed", "total_universities": 62, "source_policy_violations": 0, "ranking_field_contamination": 0, **STAGE3B_FLAGS}


def write_stage3b_gap_fill(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3b-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
