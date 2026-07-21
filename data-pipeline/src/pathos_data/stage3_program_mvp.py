"""Build the source-limited, program-centric Stage 3 MVP detail pack.

The pack is intentionally conservative: IPEDS supplies only institution-level
tuition/fees and reported bachelor award areas. It never invents program-level
tuition, cost of attendance, or a student-faculty ratio.
"""

import csv
import html
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .official_program_sweep import STREAM_NAMES
from .universe_candidate_v2 import validate_source_policy_use


DETAIL_EDITION = "Stage 3 MVP / IPEDS 2023-24 and 2024"
IPEDS_URL = "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx"
CIP_URL = "https://nces.ed.gov/ipeds/cipcode/browse.aspx?y=56"
REGIONS = {
    "1": "New England", "2": "Mid East", "3": "Great Lakes", "4": "Plains",
    "5": "Southeast", "6": "Southwest", "7": "Rocky Mountains", "8": "Far West",
    "9": "Outlying Areas",
}
FLAGS = {
    "source_limited": True, "incomplete": True, "not_final": True,
    "final_universe_generated": False, "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3ProgramMvpValidationError(ValueError):
    """Raised when MVP fields leave their evidence and tuition boundaries."""


def _fail(message: str) -> None:
    raise Stage3ProgramMvpValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3 input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3 input must be a JSON object: {path}")
    return value


def _csv_from_zip(cache: Path, zip_name: str, csv_name: str) -> List[Dict[str, str]]:
    path = cache / zip_name
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open(csv_name) as raw:
                return list(csv.DictReader(line.decode("utf-8-sig") for line in raw))
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        _fail(f"Missing or unreadable official IPEDS cache input: {path}")
        raise AssertionError("unreachable") from error


def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _amount(value: Optional[str]) -> Optional[float]:
    if value is None or not value.strip() or value.strip() in {"-1", "-2", "-3"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number >= 0 else None


def _cip_titles(cache: Path) -> Dict[str, str]:
    path = cache / "cip2020-browse.html"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        _fail(f"Missing official CIP 2020 cache input: {path}")
        raise AssertionError("unreachable") from error
    titles: Dict[str, str] = {}
    for code, title in re.findall(r">(\d{2}\.\d{4})\)\s*(.*?)</a>", content):
        titles[code] = re.sub(r"\s+", " ", html.unescape(title)).strip().rstrip(".")
    if not titles:
        _fail("Official CIP cache did not contain any six-digit titles")
    return titles


def _program_records_by_id(ranking_root: Path) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    for path in sorted(ranking_root.rglob("*.json")):
        if "completion-programs-top20-attempt" in path.parts:
            continue
        document = _read_json(path)
        for record in document.get("records", []):
            if (
                isinstance(record, dict)
                and record.get("ranking_family") == "undergraduate_program"
                and record.get("verification_status") == "verified"
            ):
                records[record["record_id"]] = record
    return records


def _candidate_rows(candidate_path: Path) -> List[Dict[str, Any]]:
    document = _read_json(candidate_path)
    metadata = document.get("metadata", {})
    if metadata.get("record_type") != "university_universe_candidate_v2":
        _fail("Stage 3 requires Candidate v2")
    if metadata.get("source_limited") is not True or metadata.get("not_final") is not True:
        _fail("Stage 3 Candidate v2 source-limited flags are missing")
    candidates = document.get("universities")
    if not isinstance(candidates, list) or len(candidates) != 62:
        _fail("Stage 3 requires exactly 62 Candidate v2 universities")
    return sorted(candidates, key=lambda row: row["candidate_university_id"])


def _exact_ipeds_match(candidate: Dict[str, Any], by_name: Dict[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
    # Exact normalized equality across Candidate v2 display/source/known aliases,
    # not fuzzy matching or a campus/system name guess.
    names = [candidate["display_name"], *candidate.get("source_names", []), *candidate.get("aliases", [])]
    for name in names:
        row = by_name.get(_normal(name))
        if row:
            return row
    return None


def _source_anchor(source_id: str, text: str) -> Dict[str, str]:
    return {"source_id": source_id, "evidence_type": "dataset_row", "quote": text}


def _base_university(candidate: Dict[str, Any], hd: Optional[Dict[str, str]]) -> Dict[str, Any]:
    base = {
        "candidate_id": candidate["candidate_university_id"], "canonical_id": candidate["canonical_university_id"],
        "display_name": candidate["display_name"], "known_aliases": candidate.get("aliases", []),
        "country": "US", "official_homepage": None, "city": None, "state": None,
        "latitude": None, "longitude": None, "region": None, "unitid": None,
        "identity_source_id": None, "field_level_provenance": {}, "null_reason": None,
    }
    if hd is None:
        base["null_reason"] = "identity_ipeds_match_not_resolved"
        return base
    base.update({
        "official_homepage": hd.get("WEBADDR") or None, "city": hd.get("CITY") or None,
        "state": hd.get("STABBR") or None, "latitude": _amount(hd.get("LATITUDE")),
        "longitude": _amount(hd.get("LONGITUD")), "region": REGIONS.get(hd.get("OBEREG", "")),
        "unitid": hd["UNITID"], "identity_source_id": "source_ipeds_hd2024",
        "field_level_provenance": {
            "official_homepage": _source_anchor("source_ipeds_hd2024", f"WEBADDR={hd.get('WEBADDR') or ''}"),
            "location": _source_anchor("source_ipeds_hd2024", f"CITY={hd.get('CITY')}; STABBR={hd.get('STABBR')}; LATITUDE={hd.get('LATITUDE')}; LONGITUD={hd.get('LONGITUD')}"),
            "identity": _source_anchor("source_ipeds_hd2024", f"UNITID={hd['UNITID']}; INSTNM={hd['INSTNM']}"),
        },
    })
    if not all(base[field] is not None for field in ("official_homepage", "city", "state", "latitude", "longitude", "region")):
        base["null_reason"] = "ipeds_hd2024_missing_one_or_more_requested_identity_fields"
    return base


def _major_rows(unitid: Optional[str], completions: Dict[str, List[Dict[str, str]]], cip_titles: Dict[str, str]) -> List[Dict[str, Any]]:
    if not unitid:
        return []
    items = []
    for row in completions.get(unitid, []):
        if row.get("AWLEVEL") != "5":
            continue
        code = row.get("CIPCODE", "")
        if code not in cip_titles:
            continue
        count = _amount(row.get("CTOTALT")) or 0
        items.append((code, count, row))
    # C2023 awards can repeat a CIP under MAJORNUM. Aggregate without creating
    # a fictitious current catalog entry.
    grouped: Dict[str, Tuple[float, Dict[str, str]]] = {}
    for code, count, row in items:
        total, exemplar = grouped.get(code, (0, row))
        grouped[code] = (total + count, exemplar)
    majors = []
    for code, (count, row) in sorted(grouped.items(), key=lambda item: (-item[1][0], item[0])):
        majors.append({
            "major_name": cip_titles[code], "normalized_major_name": cip_titles[code],
            "degree_type": "bachelor_degree_award_area", "college_or_school": None,
            "list_type": "areas_of_study", "source_id": "source_ipeds_c2023_completions",
            "evidence_anchor": _source_anchor("source_ipeds_c2023_completions", f"UNITID={unitid}; CIPCODE={code}; AWLEVEL=5; CTOTALT={int(count)}"),
            "confidence": "medium", "null_reason": None,
            "data_limitation": "IPEDS reported bachelor-degree award area for 2022-23; not a current official catalog assertion.",
            "cip_code": code,
        })
    return majors


def _ranked_programs(candidate: Dict[str, Any], record_index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for record_id in candidate.get("supporting_ranking_record_ids", []):
        record = record_index.get(record_id)
        if record is None:
            continue
        category = record["category_id"]
        name = STREAM_NAMES.get(category, category)
        anchor = next((anchor for anchor in record.get("evidence_anchors", []) if anchor.get("field") == "numeric_rank"), None)
        rows.append({
            "program_name": name, "normalized_program_name": name, "college_or_school": None,
            "source_basis": "usnews_program_ranking", "usnews_category": category,
            "usnews_rank": record["numeric_rank"], "confidence": "high",
            "source_id": record["source"]["source_id"], "evidence_anchor": anchor,
            "null_reason": None, "source_record_id": record_id,
        })
    deduped: Dict[str, Dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: (item["usnews_rank"], item["program_name"], item["source_record_id"])):
        deduped.setdefault(row["normalized_program_name"], row)
    return list(deduped.values())


def _top_programs(candidate: Dict[str, Any], majors: List[Dict[str, Any]], record_index: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    programs = _ranked_programs(candidate, record_index)
    existing = {program["normalized_program_name"] for program in programs}
    for major in majors:
        if len(programs) == 5:
            break
        if major["normalized_major_name"] in existing:
            continue
        programs.append({
            "program_name": major["major_name"], "normalized_program_name": major["normalized_major_name"],
            # This is a conservative extension to the display taxonomy: an
            # IPEDS award area is authoritative reported data, but not a
            # school-maintained current major list.
            "college_or_school": major["college_or_school"], "source_basis": "ipeds_reported_award_area",
            "usnews_category": None, "usnews_rank": None, "confidence": "medium",
            "source_id": major["source_id"], "evidence_anchor": major["evidence_anchor"],
            "null_reason": None,
            "source_note": "IPEDS-reported bachelor award area is a demo program candidate, not a U.S. News ranking or current catalog assertion.",
        })
        existing.add(major["normalized_major_name"])
    gap = None if len(programs) == 5 else "fewer_than_five_provenance_backed_demo_programs_available"
    return programs[:5], gap


def _tuition_records(base: Dict[str, Any], tuition_by_unitid: Dict[str, Dict[str, str]], hd: Optional[Dict[str, str]]) -> List[Dict[str, Any]]:
    common = {
        "candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "display_name": base["display_name"],
        "academic_year": "2023-24", "currency": "USD", "tuition_source_type": "other_detail_source",
        "tuition_scope": "university_level", "college_surcharge_amount": None, "program_extra_fee_amount": None,
        "estimated_cost_of_attendance_amount": None, "source_id": "source_ipeds_ic2023_ay", "source_url": IPEDS_URL,
        "evidence_type": "dataset_row", "confidence": "high", "extraction_notes": "IPEDS IC2023_AY published undergraduate tuition and required-fee fields; cost of attendance is not used.",
    }
    if not base.get("unitid") or hd is None or base["unitid"] not in tuition_by_unitid:
        return [{**common, "tuition_charge_model": "not_published", "tuition_scope": "not_published", "residency_scope": "not_published", "base_tuition_amount": None, "mandatory_fees_amount": None, "total_tuition_and_required_fees": None, "evidence_anchor": None, "null_reason": "official_undergraduate_tuition_not_found_or_identity_not_resolved"}]
    row = tuition_by_unitid[base["unitid"]]
    control = hd.get("CONTROL")
    def item(residency: str, tuition_field: str, fee_field: str, model: str) -> Dict[str, Any]:
        tuition = _amount(row.get(tuition_field)); fee = _amount(row.get(fee_field))
        return {**common, "tuition_charge_model": model, "residency_scope": residency, "base_tuition_amount": tuition, "mandatory_fees_amount": fee, "total_tuition_and_required_fees": (tuition + fee) if tuition is not None and fee is not None else None, "evidence_anchor": _source_anchor("source_ipeds_ic2023_ay", f"UNITID={base['unitid']}; {tuition_field}={row.get(tuition_field)}; {fee_field}={row.get(fee_field)}"), "null_reason": None if tuition is not None else "official_undergraduate_tuition_not_published"}
    if control == "1":
        return [item("in_state", "TUITION2", "FEE2", "public_in_state_out_of_state"), item("out_of_state", "TUITION3", "FEE3", "public_in_state_out_of_state")]
    if control in {"2", "3"}:
        return [item("private_single_rate", "TUITION2", "FEE2", "private_single_rate")]
    return [{**common, "tuition_charge_model": "unknown", "tuition_scope": "not_published", "residency_scope": "unknown", "base_tuition_amount": None, "mandatory_fees_amount": None, "total_tuition_and_required_fees": None, "evidence_anchor": None, "null_reason": "institution_control_not_available_for_tuition_model"}]


def _program_tuition_display(programs: List[Dict[str, Any]], tuition: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records = {row["residency_scope"]: row for row in tuition}
    public = records.get("out_of_state")
    private = records.get("private_single_rate")
    if public and public.get("base_tuition_amount") is not None:
        in_state = records.get("in_state")
        displays = [{
            "program_name": item["program_name"], "normalized_program_name": item["normalized_program_name"], "college_or_school": item.get("college_or_school"), "academic_year": public["academic_year"],
            "tuition_display_type": "public_in_state_out_of_state_tuition", "tuition_charge_model": "public_in_state_out_of_state", "tuition_scope": "university_level",
            "in_state_base_tuition": in_state.get("base_tuition_amount") if in_state else None, "out_of_state_base_tuition": public["base_tuition_amount"], "private_single_rate_tuition": None,
            "mandatory_fees": public.get("mandatory_fees_amount"), "college_surcharge": None, "program_extra_fee": None,
            "calculated_in_state_total": in_state.get("total_tuition_and_required_fees") if in_state else None, "calculated_out_of_state_total": public.get("total_tuition_and_required_fees"), "calculated_private_total": None,
            "displayed_amount": public.get("total_tuition_and_required_fees"), "displayed_amount_basis": "out_of_state_total", "program_specific": False,
            "display_label": "Public university: in-state and out-of-state undergraduate tuition; university-level tuition applied to this program, not program-specific.",
            "source_id": public["source_id"], "evidence_anchor": public["evidence_anchor"], "calculation_notes": "Out-of-state tuition is used as the default comparison basis for demo display.", "null_reason": public.get("null_reason"), "confidence": public["confidence"],
        } for item in programs]
        basis = "university_level_same_for_all"
        notes = "All displayed demo programs use the same university-level undergraduate tuition; no program-specific tuition difference is published. Out-of-state tuition is used as the default comparison basis for demo display."
    elif private and private.get("base_tuition_amount") is not None:
        displays = [{
            "program_name": item["program_name"], "normalized_program_name": item["normalized_program_name"], "college_or_school": item.get("college_or_school"), "academic_year": private["academic_year"],
            "tuition_display_type": "private_single_rate_tuition", "tuition_charge_model": "private_single_rate", "tuition_scope": "university_level",
            "in_state_base_tuition": None, "out_of_state_base_tuition": None, "private_single_rate_tuition": private["base_tuition_amount"],
            "mandatory_fees": private.get("mandatory_fees_amount"), "college_surcharge": None, "program_extra_fee": None,
            "calculated_in_state_total": None, "calculated_out_of_state_total": None, "calculated_private_total": private.get("total_tuition_and_required_fees"),
            "displayed_amount": private.get("total_tuition_and_required_fees"), "displayed_amount_basis": "private_single_rate_total", "program_specific": False,
            "display_label": "University-wide private undergraduate tuition, not program-specific.",
            "source_id": private["source_id"], "evidence_anchor": private["evidence_anchor"], "calculation_notes": "Uniform undergraduate tuition is applied to every displayed demo program.", "null_reason": private.get("null_reason"), "confidence": private["confidence"],
        } for item in programs]
        basis = "university_level_same_for_all"
        notes = "All displayed demo programs use the same university-level undergraduate tuition; no program-specific tuition difference is published."
    else:
        reference = tuition[0]
        displays = [{
            "program_name": item["program_name"], "normalized_program_name": item["normalized_program_name"], "college_or_school": item.get("college_or_school"), "academic_year": reference["academic_year"],
            "tuition_display_type": "tuition_not_published", "tuition_charge_model": reference["tuition_charge_model"], "tuition_scope": reference["tuition_scope"], "in_state_base_tuition": None, "out_of_state_base_tuition": None, "private_single_rate_tuition": None, "mandatory_fees": None, "college_surcharge": None, "program_extra_fee": None, "calculated_in_state_total": None, "calculated_out_of_state_total": None, "calculated_private_total": None, "displayed_amount": None, "displayed_amount_basis": "not_available", "program_specific": False, "display_label": "Program-level tuition not published.", "source_id": reference["source_id"], "evidence_anchor": reference.get("evidence_anchor"), "calculation_notes": "No official undergraduate tuition amount is available for comparison.", "null_reason": reference["null_reason"], "confidence": reference["confidence"],
        } for item in programs]
        basis = "not_published" if programs else "insufficient_comparable_data"
        notes = "No official undergraduate tuition amount is available for comparison."
    comparable = [row for row in displays if row.get("displayed_amount") is not None]
    if comparable:
        ordered = sorted(comparable, key=lambda row: (row["displayed_amount"], row["program_name"]))
        comparison = {"highest_tuition_program": {"program_name": ordered[-1]["program_name"], "amount": ordered[-1]["displayed_amount"], "source_id": ordered[-1]["source_id"]}, "lowest_tuition_program": {"program_name": ordered[0]["program_name"], "amount": ordered[0]["displayed_amount"], "source_id": ordered[0]["source_id"]}, "highest_lowest_basis": basis, "calculation_notes": notes, "null_reason": None}
    else:
        comparison = {"highest_tuition_program": None, "lowest_tuition_program": None, "highest_lowest_basis": basis, "calculation_notes": notes, "null_reason": "insufficient_program_or_college_level_tuition_data" if basis == "insufficient_comparable_data" else "official_undergraduate_tuition_not_found"}
    return displays, comparison


def validate_undergraduate_tuition_record(record: Dict[str, Any]) -> None:
    """Reject COA and graduate/professional prices before display calculations."""
    if record.get("estimated_cost_of_attendance_amount") is not None:
        _fail("Estimated cost of attendance cannot be used as undergraduate tuition")
    evidence = record.get("evidence_anchor") or {}
    source_text = " ".join(str(record.get(field, "")) for field in ("extraction_notes", "source_reference", "source_url"))
    source_text += " " + str(evidence.get("quote", ""))
    # Word boundaries matter: "undergraduate tuition" is legitimate input and
    # must not be treated as the substring "graduate tuition".
    prohibited = (
        r"\bgraduate(?:\s+program)?\s+tuition\b",
        r"\bmba\s+tuition\b",
        r"\blaw\s+school\s+tuition\b",
        r"\bmedical\s+school\s+tuition\b",
        r"\bprofessional\s+school\s+tuition\b",
    )
    if any(re.search(pattern, source_text, flags=re.IGNORECASE) for pattern in prohibited):
        _fail("Graduate, MBA, law, medical, or professional tuition cannot enter undergraduate records")


def _ratio_record(base: Dict[str, Any]) -> Dict[str, Any]:
    return {"candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "display_name": base["display_name"], "student_faculty_ratio": None, "reporting_year": None, "source_type": "ipeds", "source_id": None, "evidence_anchor": None, "definition_notes": "No student-faculty ratio was calculated from the selected IPEDS inputs; the MVP does not infer ratios from unrelated enrollment or staff fields.", "confidence": "low", "null_reason": "official_student_faculty_ratio_not_collected_in_stage3_mvp"}


def build_stage3_program_mvp(candidate_path: Path, ranking_root: Path, cache: Path) -> Dict[str, Dict[str, Any]]:
    """Build every Stage 3 output deterministically from Candidate v2 and IPEDS cache."""
    validate_source_policy_use("IPEDS", "detail", has_field_provenance=True)
    candidates = _candidate_rows(candidate_path)
    hd_rows = _csv_from_zip(cache, "HD2024.zip", "HD2024.csv")
    tuition_rows = _csv_from_zip(cache, "IC2023_AY.zip", "ic2023_ay.csv")
    completion_rows = _csv_from_zip(cache, "C2023_A.zip", "C2023_a.csv")
    hd_by_name = {_normal(row["INSTNM"]): row for row in hd_rows}
    tuition_by_id = {row["UNITID"]: row for row in tuition_rows}
    completions: Dict[str, List[Dict[str, str]]] = {}
    for row in completion_rows:
        completions.setdefault(row["UNITID"], []).append(row)
    cip_titles = _cip_titles(cache)
    ranking_records = _program_records_by_id(ranking_root)

    universities = []; programs = []; tuition_output = []; ratios = []; majors_output = []; gaps = []
    for candidate in candidates:
        hd = _exact_ipeds_match(candidate, hd_by_name)
        base = _base_university(candidate, hd)
        majors = _major_rows(base.get("unitid"), completions, cip_titles)
        top5, top_gap = _top_programs(candidate, majors, ranking_records)
        tuition = _tuition_records(base, tuition_by_id, hd)
        displays, comparison = _program_tuition_display(top5, tuition)
        universities.append({**base, "top_5_programs_for_demo": top5, "top_5_gap_reason": top_gap, **comparison})
        programs.append({"candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "top_5_programs_for_demo": top5, "gap_reason": top_gap})
        tuition_output.append({"candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "display_name": base["display_name"], "tuition_records": tuition, "program_tuition_display": displays, **comparison})
        ratios.append(_ratio_record(base))
        majors_output.append({"candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "display_name": base["display_name"], "all_undergraduate_majors": majors, "major_list_gap_reason": None if majors else ("identity_ipeds_match_not_resolved" if not base.get("unitid") else "no_ipeds_bachelor_award_areas_reported")})
        if base["null_reason"] or top_gap or not majors:
            gaps.append({"candidate_id": base["candidate_id"], "canonical_id": base["canonical_id"], "identity_gap": base["null_reason"], "top_5_gap_reason": top_gap, "major_list_gap_reason": majors_output[-1]["major_list_gap_reason"], "student_faculty_ratio_gap_reason": ratios[-1]["null_reason"]})

    top5_count = sum(len(item["top_5_programs_for_demo"]) == 5 for item in programs)
    public = sum(any(record["tuition_charge_model"] == "public_in_state_out_of_state" and record["base_tuition_amount"] is not None for record in item["tuition_records"]) for item in tuition_output)
    private = sum(any(record["tuition_charge_model"] == "private_single_rate" and record["base_tuition_amount"] is not None for record in item["tuition_records"]) for item in tuition_output)
    not_published = sum(all(record["tuition_charge_model"] == "not_published" for record in item["tuition_records"]) for item in tuition_output)
    major_coverage = sum(bool(item["all_undergraduate_majors"]) for item in majors_output)
    summary = {
        "record_type": "stage3_program_mvp_summary", "total_universities": len(universities),
        "universities_with_5_demo_programs": top5_count, "universities_missing_5_demo_programs": len(universities) - top5_count,
        "universities_with_student_faculty_ratio": 0, "universities_missing_student_faculty_ratio": len(universities),
        "universities_with_public_in_state_out_of_state_tuition": public, "universities_with_private_single_rate_tuition": private,
        "universities_with_university_level_single_rate_tuition": public + private, "universities_with_college_level_surcharge": 0, "universities_with_program_level_extra_fee": 0,
        "universities_with_tuition_not_published": not_published,
        "top5_programs_using_university_level_tuition": sum(len(item["program_tuition_display"]) for item in tuition_output if item["highest_lowest_basis"] == "university_level_same_for_all"),
        "top5_programs_using_college_level_tuition": 0, "top5_programs_using_program_level_tuition": 0,
        "universities_with_all_undergraduate_majors_list": major_coverage, "universities_missing_major_list": len(universities) - major_coverage,
        "highest_lowest_basis_program_level_only_count": 0, "highest_lowest_basis_college_or_program_level_count": 0,
        "highest_lowest_basis_university_level_same_for_all_count": sum(item["highest_lowest_basis"] == "university_level_same_for_all" for item in tuition_output),
        "highest_lowest_null_count": sum(item["highest_tuition_program"] is None for item in tuition_output),
        "estimated_cost_of_attendance_excluded_from_tuition_count": 0, "graduate_tuition_rejected_count": 0,
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "demo_readiness_score": round((top5_count + public + private + major_coverage) / (4 * len(universities)), 3),
        **FLAGS,
    }
    gap_disclosure = {
        "record_type": "stage3_program_mvp_gap_disclosure",
        "candidate_v2_is_not_final_universe": True,
        "program_top20_complete_stream_count": 0,
        "program_top20_incomplete_stream_count": 27,
        "economics_manual_seed_needed": True,
        "identity_ipeds_exact_match_unresolved_count": len(universities) - sum(item["unitid"] is not None for item in universities),
        "student_faculty_ratio_gap_count": len(universities),
        "major_list_limitation": "IPEDS C2023_A bachelor award areas are used as structured areas of study, not current official catalogs.",
        "tuition_limitation": "IPEDS IC2023_AY supplies university-level tuition and required fees only; no program-level tuition is inferred.",
        "source_manifest": [
            {"source_id": "source_ipeds_hd2024", "publisher": "NCES IPEDS", "source_type": "federal_detail_dataset", "source_url": IPEDS_URL, "use": "candidate identity and map fields", "field_level_provenance_required": True},
            {"source_id": "source_ipeds_ic2023_ay", "publisher": "NCES IPEDS", "source_type": "federal_detail_dataset", "source_url": IPEDS_URL, "use": "institution-level undergraduate tuition and required fees only", "field_level_provenance_required": True},
            {"source_id": "source_ipeds_c2023_completions", "publisher": "NCES IPEDS", "source_type": "federal_detail_dataset", "source_url": IPEDS_URL, "use": "reported bachelor-degree award areas, not a current catalog", "field_level_provenance_required": True},
            {"source_id": "source_nces_cip2020", "publisher": "NCES", "source_type": "federal_reference", "source_url": CIP_URL, "use": "CIP title normalization", "field_level_provenance_required": True},
        ],
        "gaps": gaps,
        **FLAGS,
    }
    return {
        "program-mvp-universities.json": {"metadata": {"record_type": "stage3_program_mvp_universities", "detail_edition": DETAIL_EDITION, **FLAGS}, "universities": universities},
        "program-mvp-programs.json": {"metadata": {"record_type": "stage3_program_mvp_programs", **FLAGS}, "universities": programs},
        "program-mvp-tuition.json": {"metadata": {"record_type": "stage3_program_mvp_tuition", **FLAGS}, "universities": tuition_output},
        "program-mvp-student-faculty.json": {"metadata": {"record_type": "stage3_program_mvp_student_faculty", **FLAGS}, "universities": ratios},
        "program-mvp-majors.json": {"metadata": {"record_type": "stage3_program_mvp_majors", **FLAGS}, "universities": majors_output},
        "program-mvp-gap-disclosure.json": gap_disclosure,
        "program-mvp-summary.json": summary,
    }


def validate_stage3_program_mvp(artifacts: Dict[str, Dict[str, Any]], candidate_path: Path, ranking_root: Path, cache: Path) -> Dict[str, Any]:
    expected = build_stage3_program_mvp(candidate_path, ranking_root, cache)
    if set(artifacts) != set(expected) or artifacts != expected:
        _fail("Stage 3 artifacts must match deterministic regeneration")
    summary = artifacts["program-mvp-summary.json"]
    if summary["total_universities"] != 62 or summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Stage 3 summary violates coverage or source-policy contract")
    universities = artifacts["program-mvp-universities.json"]["universities"]
    tuition = artifacts["program-mvp-tuition.json"]["universities"]
    majors = artifacts["program-mvp-majors.json"]["universities"]
    ratios = artifacts["program-mvp-student-faculty.json"]["universities"]
    candidate_ids = {item["candidate_id"] for item in universities}
    if len(candidate_ids) != 62 or any({item["candidate_id"] for item in collection} != candidate_ids for collection in (tuition, majors, ratios)):
        _fail("Every Candidate v2 university must have every Stage 3 artifact row")
    for university in universities:
        programs = university["top_5_programs_for_demo"]
        if len(programs) > 5 or (len(programs) < 5 and not university.get("top_5_gap_reason")):
            _fail("Top five programs require provenance-backed rows or a gap reason")
        for program in programs:
            if not program.get("source_id") or not program.get("evidence_anchor"):
                _fail("Top demo programs require field-level provenance")
            if program["source_basis"] == "usnews_program_ranking" and program["source_id"].startswith("source_ipeds"):
                _fail("Detail source contaminated a U.S. News ranking field")
    for item in tuition:
        for record in item["tuition_records"]:
            validate_undergraduate_tuition_record(record)
            for field in ("tuition_charge_model", "tuition_scope", "residency_scope"):
                if not record.get(field):
                    _fail("Tuition record lacks pricing model metadata")
            if not record.get("source_id") and not record.get("null_reason"):
                _fail("Tuition record requires provenance or null reason")
            if record["tuition_scope"] == "program_level" and not (record.get("program_extra_fee_amount") is not None or record.get("base_tuition_amount") is not None):
                _fail("Program-level tuition requires a direct program amount")
            if record.get("estimated_cost_of_attendance_amount") is not None:
                _fail("Cost of attendance must not enter this MVP tuition dataset")
        for display in item["program_tuition_display"]:
            if display["program_specific"] is True and display["tuition_scope"] != "program_level":
                _fail("Program-specific display must have program-level tuition scope")
            if display["program_specific"] is True and not (display.get("program_extra_fee") is not None or display.get("displayed_amount") is not None):
                _fail("Program-specific display requires a direct program-level amount")
            if display["tuition_scope"] == "college_level" and (not display.get("college_or_school") or not (display.get("college_surcharge") is not None or display.get("displayed_amount") is not None)):
                _fail("College-level tuition display requires a college and a differential amount")
            if display["tuition_charge_model"] == "public_in_state_out_of_state" and display["out_of_state_base_tuition"] is None and not display.get("null_reason"):
                _fail("Public tuition display needs out-of-state value or null reason")
            if display["tuition_charge_model"] == "public_in_state_out_of_state" and display["in_state_base_tuition"] is None and not display.get("null_reason"):
                _fail("Public tuition display needs in-state value or null reason")
            if display["tuition_charge_model"] == "private_single_rate" and (display["in_state_base_tuition"] is not None or display["out_of_state_base_tuition"] is not None):
                _fail("Private single-rate display must not fabricate residency rates")
            if display["tuition_scope"] == "university_level" and display["program_specific"] is False and "not program-specific" not in display["display_label"].lower():
                _fail("University-level tuition display must disclose that it is not program-specific")
        if item["highest_lowest_basis"] == "university_level_same_for_all" and item["highest_tuition_program"] is not None and "same university-level" not in item["calculation_notes"].lower():
            _fail("Same-rate highest/lowest explanation is required")
    for item in ratios:
        if item["student_faculty_ratio"] is None and not item.get("null_reason"):
            _fail("Student-faculty ratio requires provenance or null reason")
    for item in majors:
        for major in item["all_undergraduate_majors"]:
            if not major.get("source_id") or not major.get("evidence_anchor"):
                _fail("Undergraduate major rows require provenance")
    return {"record_type": "stage3_program_mvp_validation_result", "total_universities": 62, "source_policy_violations": 0, "ranking_field_contamination": 0, "result": "passed", **FLAGS}


def write_stage3_program_mvp(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "program-mvp-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
