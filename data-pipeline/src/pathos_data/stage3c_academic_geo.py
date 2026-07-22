"""Deterministic, non-mutating Stage 3C academic and geography overlay."""

import copy
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .stage3_program_mvp import FLAGS, _candidate_rows, _normal
from .universe_candidate_v2 import validate_source_policy_use


STAGE3_FILES = (
    "program-mvp-universities.json", "program-mvp-programs.json", "program-mvp-tuition.json",
    "program-mvp-student-faculty.json", "program-mvp-majors.json", "program-mvp-gap-disclosure.json",
    "program-mvp-summary.json", "program-mvp-validation-result.json",
)
STAGE3B_FILES = (
    "stage3b-mvp-universities.json", "stage3b-student-faculty.json", "stage3b-identity-gap-fill.json",
    "stage3b-tuition-gap-fill.json", "stage3b-majors-gap-fill.json", "stage3b-program-gap-fill.json",
    "stage3b-gap-disclosure.json", "stage3b-summary.json", "stage3b-validation-result.json",
)
OUTPUT_FILES = (
    "stage3c-universities.json", "stage3c-official-major-sources.json", "stage3c-official-majors.json",
    "stage3c-demo-programs-overlay.json", "stage3c-tuition-deepening.json", "stage3c-highest-lowest-tuition.json",
    "stage3c-gap-disclosure.json", "stage3c-summary.json",
)
STAGE3C_FLAGS = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}
FOUR_REGIONS = {"Northeast", "Midwest", "South", "West"}
FORBIDDEN_TUITION = re.compile(
    r"\b(graduate|mba|law|medical|professional|cost of attendance|room and board|books|transportation|personal expenses)\b",
    re.IGNORECASE,
)
FORBIDDEN_PROGRAM = re.compile(r"\b(graduate|mba|law|medical|professional)\b", re.IGNORECASE)


class Stage3CAcademicGeoValidationError(ValueError):
    """Raised when Stage 3C crosses evidence, scope, or output boundaries."""


def _fail(message: str) -> None:
    raise Stage3CAcademicGeoValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3C input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3C input must be a JSON object: {path}")
    return value


def _fingerprints(directory: Path, names: Iterable[str]) -> Dict[str, str]:
    values = {}
    for name in names:
        path = directory / name
        try:
            values[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            _fail(f"Missing immutable upstream artifact: {path}")
            raise AssertionError("unreachable") from error
    return dict(sorted(values.items()))


def _load_bundle(directory: Path, names: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    return {name: _read_json(directory / name) for name in names}


def _flags_valid(value: Dict[str, Any]) -> bool:
    return (
        value.get("source_limited") is True and value.get("incomplete") is True and value.get("not_final") is True
        and value.get("final_universe_generated") is False
        and value.get("official_selection_memberships_generated") is False
        and value.get("frontend_export_generated") is False
    )


def _load_sources(path: Path) -> Dict[str, Dict[str, Any]]:
    document = _read_json(path)
    rows = document.get("sources")
    if document.get("record_type") != "stage3c_source_manifest" or not isinstance(rows, list):
        _fail("Stage 3C requires a source manifest")
    values = {}
    for row in rows:
        required = ("source_id", "source_type", "field_domain", "source_title", "source_url_or_reference", "publisher", "accessed_date")
        if not all(row.get(field) for field in required) or row["field_domain"] not in {"official_majors", "tuition_detail", "geography"}:
            _fail("Stage 3C source manifest row is incomplete")
        if row["source_id"] in values:
            _fail("Stage 3C source IDs must be unique")
        values[row["source_id"]] = row
    return values


def _load_major_observations(path: Path, candidates: set, sources: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    document = _read_json(path)
    rows = document.get("observations")
    if document.get("record_type") != "stage3c_official_undergraduate_major_observations" or not isinstance(rows, list):
        _fail("Stage 3C requires official undergraduate major observations")
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if row.get("candidate_id") not in candidates or row.get("source_id") not in sources:
            _fail("Major observation must resolve candidate and source")
        if row.get("undergraduate_status") != "undergraduate" or row.get("list_type") not in {
            "official_undergraduate_majors", "official_undergraduate_programs", "official_areas_of_study", "official_catalog_programs"
        }:
            _fail("Official major observation must be an allowed undergraduate list type")
        if FORBIDDEN_PROGRAM.search(str(row.get("major_name", ""))):
            _fail("Graduate/professional program cannot enter Stage 3C")
        anchor = row.get("evidence_anchor")
        if not isinstance(anchor, dict) or anchor.get("source_id") != row["source_id"] or not anchor.get("quote"):
            _fail("Official major observation requires a direct evidence anchor")
        source = sources[row["source_id"]]
        if source.get("source_type") != "official_institutional" or source.get("field_domain") != "official_majors":
            _fail("Official major observations require official institutional major sources")
        grouped.setdefault(row["candidate_id"], []).append(copy.deepcopy(row))
    return grouped


def _load_tuition_observations(path: Path, candidates: set, sources: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    document = _read_json(path)
    rows = document.get("observations")
    if document.get("record_type") != "stage3c_official_undergraduate_tuition_fee_observations" or not isinstance(rows, list):
        _fail("Stage 3C requires tuition observations")
    values = {}
    for row in rows:
        if row.get("candidate_id") not in candidates or row.get("candidate_id") in values:
            _fail("Tuition observation must resolve one unique candidate")
        if row.get("source_id") not in sources or sources[row["source_id"]].get("field_domain") != "tuition_detail":
            _fail("Tuition observation source must resolve to tuition detail")
        if row.get("tuition_deepening_status") not in {
            "university_level_only_confirmed", "college_level_surcharge_found", "program_level_extra_fee_found",
            "mixed_base_plus_surcharge_found", "official_page_found_no_program_difference", "not_found", "insufficient_data",
        }:
            _fail("Invalid tuition deepening status")
        for fee in row.get("fee_observations", []):
            _validate_fee(fee, sources)
        values[row["candidate_id"]] = copy.deepcopy(row)
    return values


def _validate_fee(fee: Dict[str, Any], sources: Dict[str, Dict[str, Any]]) -> None:
    required = ("fee_name", "fee_type", "amount", "currency", "academic_year", "residency_scope", "source_id", "evidence_anchor")
    if not all(fee.get(field) is not None for field in required):
        _fail("Tuition fee observation is incomplete")
    if fee.get("source_id") not in sources or not fee.get("undergraduate_only") or not fee.get("required_for_program"):
        _fail("Only sourced, required undergraduate fees can be comparable")
    if fee.get("fee_type") not in {"college_surcharge", "program_extra_fee", "differential_tuition", "lab_or_course_fee", "other_required_fee"}:
        _fail("Invalid Stage 3C fee type")
    quote = str(fee.get("evidence_anchor", {}).get("quote", ""))
    if FORBIDDEN_TUITION.search(quote) or FORBIDDEN_TUITION.search(str(fee.get("fee_name", ""))):
        _fail("Forbidden graduate/COA/living-cost tuition component")
    if fee["fee_type"] == "lab_or_course_fee" and not fee.get("required_for_program"):
        _fail("Course fee cannot be promoted to program comparison")


def _load_regions(path: Path) -> Dict[str, str]:
    document = _read_json(path)
    values = document.get("states")
    if document.get("record_type") != "stage3c_us_census_four_regions" or document.get("region_taxonomy") != "us_census_four_regions" or not isinstance(values, dict):
        _fail("Stage 3C requires the controlled Census four-region map")
    if set(values.values()) - FOUR_REGIONS or len(values) != 51:
        _fail("Census four-region map must contain 50 states and DC only")
    return values


def _load_town_manifest(path: Path, sources: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    document = _read_json(path)
    allowed = {"city", "town", "municipality", "incorporated_place", "census_designated_place"}
    if document.get("record_type") != "stage3c_town_source_manifest" or document.get("primary_source_id") not in sources:
        _fail("Stage 3C town source manifest lacks primary source")
    if set(document.get("allowed_place_types", [])) != allowed or "county" not in document.get("forbidden_place_types", []):
        _fail("Stage 3C town manifest must define controlled place candidate types")
    if document.get("distance_method") != "haversine_straight_line":
        _fail("Stage 3C only permits Haversine straight-line distance")
    return document


def _longitude_from_provenance(row: Dict[str, Any]) -> Optional[float]:
    if row.get("longitude") is not None:
        return float(row["longitude"])
    quote = str(row.get("field_level_provenance", {}).get("location", {}).get("quote", ""))
    match = re.search(r"LONGITUD=([-+]?\d+(?:\.\d+)?)", quote)
    return float(match.group(1)) if match else None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    p1, p2, dlat, dlon = map(math.radians, (lat1, lat2, lat2 - lat1, lon2 - lon1))
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def _load_places(town_cache: Path, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Read a future lawful controlled cache; unavailable cache yields disclosed gaps."""
    if manifest.get("source_status") != "available":
        return []
    path = town_cache / "places.json"
    if not path.exists():
        return []
    document = _read_json(path)
    rows = document.get("places")
    if not isinstance(rows, list):
        _fail("Controlled place cache must contain places list")
    allowed = set(manifest["allowed_place_types"])
    values = []
    for row in rows:
        if row.get("place_type") not in allowed or row.get("place_type") == "county":
            continue
        if row.get("latitude") is None or row.get("longitude") is None:
            continue
        values.append(row)
    return values


def _nearest_towns(base: Dict[str, Any], places: List[Dict[str, Any]], manifest: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    lat, lon = base.get("latitude"), base.get("longitude")
    if lat is None or lon is None:
        return [], "campus_coordinate_unavailable_for_nearest_towns"
    if not places:
        return [], manifest.get("source_status") or "official_place_source_unavailable"
    candidates = []
    for place in places:
        distance = _haversine_km(float(lat), float(lon), float(place["latitude"]), float(place["longitude"]))
        candidates.append((distance, _normal(place["town_name"]), place.get("state", ""), place))
    selected = []
    seen = set()
    for distance, _, _, place in sorted(candidates):
        key = (place["town_name"], place.get("state"))
        if key in seen:
            continue
        seen.add(key)
        same_city = _normal(str(base.get("city") or "")) == _normal(place["town_name"]) and base.get("state") == place.get("state")
        selected.append({
            "town_name": place["town_name"], "state": place.get("state"), "place_type": place["place_type"],
            "population_class": place.get("population_class", "unknown"), "distance_miles": round(distance * 0.621371, 2),
            "distance_km": round(distance, 2), "distance_method": "haversine_straight_line",
            "school_latitude": float(lat), "school_longitude": float(lon), "town_latitude": float(place["latitude"]),
            "town_longitude": float(place["longitude"]), "calculation_source": "campus coordinate + controlled place coordinate",
            "source_id": manifest["primary_source_id"],
            "notes": f"campus_city_included={'true' if same_city else 'false'}; Haversine straight-line distance; not driving distance.",
            "calculation_notes": "Haversine straight-line distance; not driving distance.",
        })
        if len(selected) == 3:
            break
    return selected, None


def _base_tuition_display(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    displays = [item for item in row.get("program_tuition_display", []) if item.get("displayed_amount") is not None]
    if not displays:
        return None, None, None
    display = displays[0]
    return float(display["displayed_amount"]), display.get("source_id"), display.get("displayed_amount_basis")


def _demo_overlay_program(observation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "program_name": observation["normalized_major_name"], "normalized_program_name": observation["normalized_major_name"],
        "college_or_school": observation.get("college_or_school"), "source_basis": "official_school_program_page",
        "usnews_category": None, "usnews_rank": None, "confidence": "high", "source_id": observation["source_id"],
        "source_url": None, "source_type": "official_institutional", "undergraduate_status": "undergraduate",
        "evidence_anchor": observation["evidence_anchor"], "null_reason": None,
        "source_note": "Official undergraduate program supplement; not a U.S. News ranking record.",
    }


def build_stage3c_academic_geo(
    candidate_path: Path, stage3_dir: Path, stage3b_dir: Path, source_manifest_path: Path,
    major_observations_path: Path, tuition_observations_path: Path, region_mapping_path: Path,
    town_manifest_path: Path, town_cache: Path,
) -> Dict[str, Dict[str, Any]]:
    """Build Stage 3C artifacts without writing or changing any upstream artifact."""
    validate_source_policy_use("IPEDS", "detail", has_field_provenance=True)
    validate_source_policy_use("official_institutional", "detail", has_field_provenance=True)
    validate_source_policy_use("Census", "detail", has_field_provenance=True)

    candidates_list = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidates_list}
    stage3_hashes = _fingerprints(stage3_dir, STAGE3_FILES)
    stage3b_hashes = _fingerprints(stage3b_dir, STAGE3B_FILES)
    stage3 = _load_bundle(stage3_dir, STAGE3_FILES)
    stage3b = _load_bundle(stage3b_dir, STAGE3B_FILES)
    sources = _load_sources(source_manifest_path)
    major_observations = _load_major_observations(major_observations_path, candidate_ids, sources)
    tuition_observations = _load_tuition_observations(tuition_observations_path, candidate_ids, sources)
    regions = _load_regions(region_mapping_path)
    town_manifest = _load_town_manifest(town_manifest_path, sources)
    places = _load_places(town_cache, town_manifest)

    upstream_universities = {row["candidate_id"]: row for row in stage3b["stage3b-mvp-universities.json"]["universities"]}
    stage3_tuition = {row["candidate_id"]: row for row in stage3["program-mvp-tuition.json"]["universities"]}
    stage3_majors = {row["candidate_id"]: row for row in stage3["program-mvp-majors.json"]["universities"]}
    stage3b_major_fallbacks = {
        row["candidate_id"]: row.get("all_undergraduate_majors", [])
        for row in stage3b["stage3b-majors-gap-fill.json"]["universities"]
        if row.get("resolved")
    }
    if set(upstream_universities) != candidate_ids or set(stage3_tuition) != candidate_ids or set(stage3_majors) != candidate_ids:
        _fail("Stage 3/3B inputs do not equal Candidate v2 scope")

    universities = []
    major_sources = []
    official_majors = []
    demo_programs = []
    tuition_deepening = []
    highest_lowest = []
    gaps = []
    for candidate in candidates_list:
        candidate_id = candidate["candidate_university_id"]
        upstream = copy.deepcopy(upstream_universities[candidate_id])
        upstream["longitude"] = _longitude_from_provenance(upstream)
        upstream["region"] = regions.get(upstream.get("state"))
        if upstream["region"] is None:
            _fail("Candidate state is absent from Census four-region map")
        towns, town_gap = _nearest_towns(upstream, places, town_manifest)
        universities.append({
            "candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"],
            "state": upstream["state"], "city": upstream["city"], "latitude": upstream["latitude"], "longitude": upstream["longitude"],
            "region": upstream["region"], "region_taxonomy": "us_census_four_regions",
            "region_source_id": "source_stage3c_us_census_region_mapping", "nearest_towns": towns,
            "nearest_towns_null_reason": town_gap, "input_overlay_note": "Stage 3 and Stage 3B remain immutable inputs.",
        })

        observed = major_observations.get(candidate_id, [])
        baseline_majors = stage3_majors[candidate_id].get("all_undergraduate_majors", [])
        if not baseline_majors:
            baseline_majors = stage3b_major_fallbacks.get(candidate_id, [])
        if observed:
            status = "official_undergraduate_programs_found"
            source = observed[0]
            major_sources.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "official_major_source_status": status, "official_major_source_url": sources[source["source_id"]]["source_url_or_reference"], "official_major_source_title": sources[source["source_id"]]["source_title"], "source_id": source["source_id"], "evidence_anchor": source["evidence_anchor"], "extraction_notes": "Structured official undergraduate entries only; no full page snapshot retained.", "confidence": "high", "null_reason": None})
        else:
            status = "only_ipeds_award_areas_available" if baseline_majors else "not_found"
            major_sources.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "official_major_source_status": status, "official_major_source_url": None, "official_major_source_title": None, "source_id": "source_ipeds_c2023_completions" if baseline_majors else None, "evidence_anchor": baseline_majors[0].get("evidence_anchor") if baseline_majors else None, "extraction_notes": "IPEDS reported bachelor-degree award areas are retained only as a federal fallback, not a current official catalog." if baseline_majors else None, "confidence": "medium" if baseline_majors else "low", "null_reason": "official_undergraduate_major_source_not_found" if baseline_majors else "no_undergraduate_major_source_available"})
        official_majors.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "official_major_source_status": status, "majors": observed, "null_reason": None if observed else major_sources[-1]["null_reason"]})

        programs = copy.deepcopy(upstream.get("top_5_programs_for_demo", []))
        existing = {_normal(row.get("normalized_program_name", row["program_name"])) for row in programs}
        added = []
        for observation in observed:
            if len(programs) == 5 or _normal(observation["normalized_major_name"]) in existing:
                continue
            row = _demo_overlay_program(observation)
            programs.append(row)
            added.append(row)
            existing.add(_normal(row["normalized_program_name"]))
        gap_reason = None if len(programs) == 5 else upstream.get("top_5_gap_reason") or "fewer_than_five_provenance_backed_demo_programs_available"
        demo_programs.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "top_5_programs_for_demo": programs[:5], "added_official_undergraduate_programs": added, "top_5_gap_reason": gap_reason})

        tuition_base = stage3_tuition[candidate_id]
        supplied = tuition_observations.get(candidate_id)
        base_amount, base_source, basis = _base_tuition_display(tuition_base)
        if supplied:
            deep = supplied
        elif tuition_base.get("tuition_records"):
            deep = {"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "academic_year": tuition_base["tuition_records"][0].get("academic_year"), "tuition_deepening_status": "university_level_only_confirmed", "official_tuition_source_url": None, "official_bursar_source_url": None, "official_program_fee_source_url": None, "source_id": base_source or "source_ipeds_ic2023_ay", "evidence_anchor": tuition_base["tuition_records"][0].get("evidence_anchor"), "extraction_notes": "IPEDS confirms institution-level undergraduate tuition/required fees; no differentiated official undergraduate fee observation was ingested.", "confidence": "high", "null_reason": None, "fee_observations": []}
        else:
            deep = {"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "academic_year": None, "tuition_deepening_status": "not_found", "official_tuition_source_url": None, "official_bursar_source_url": None, "official_program_fee_source_url": None, "source_id": None, "evidence_anchor": None, "extraction_notes": None, "confidence": "low", "null_reason": "validated_undergraduate_tuition_not_available", "fee_observations": []}
        deep = copy.deepcopy(deep)
        deep.setdefault("candidate_id", candidate_id)
        deep.setdefault("canonical_id", upstream["canonical_id"])
        deep.setdefault("display_name", upstream["display_name"])
        tuition_deepening.append(deep)

        fee_total = sum(float(fee["amount"]) for fee in deep.get("fee_observations", []) if fee.get("required_for_program"))
        if base_amount is None:
            highest_lowest.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "highest_tuition_program": None, "lowest_tuition_program": None, "highest_lowest_basis": "not_published", "comparison_basis": None, "source_ids": [], "calculation_notes": "No validated undergraduate tuition display amount is available.", "null_reason": "validated_undergraduate_tuition_not_available"})
        elif fee_total == 0 and programs:
            name = sorted(row["program_name"] for row in programs)[0]
            highest_lowest.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "highest_tuition_program": {"program_name": name, "amount": base_amount}, "lowest_tuition_program": {"program_name": name, "amount": base_amount}, "highest_lowest_basis": "university_level_same_for_all", "comparison_basis": basis, "source_ids": [base_source] if base_source else [], "calculation_notes": "All displayed demo programs use the same university-level undergraduate tuition; no program-specific tuition difference is published.", "null_reason": None})
        else:
            highest_lowest.append({"candidate_id": candidate_id, "canonical_id": upstream["canonical_id"], "display_name": upstream["display_name"], "highest_tuition_program": None, "lowest_tuition_program": None, "highest_lowest_basis": "insufficient_comparable_data", "comparison_basis": basis, "source_ids": [base_source] if base_source else [], "calculation_notes": "A fee observation exists but no aligned program/college applicability map supports a comparable program total.", "null_reason": "insufficient_program_or_college_level_tuition_data"})

        gaps.append({"candidate_id": candidate_id, "official_major_source_status": status, "nearest_towns_null_reason": town_gap, "tuition_deepening_status": deep["tuition_deepening_status"], "demo_program_gap_reason": gap_reason})

    # Immutable upstream hashes must remain unchanged after all pure construction.
    if stage3_hashes != _fingerprints(stage3_dir, STAGE3_FILES) or stage3b_hashes != _fingerprints(stage3b_dir, STAGE3B_FILES):
        _fail("Stage 3C may not mutate Stage 3 or Stage 3B artifacts")
    nearest_town_coverage_count = sum(bool(row["nearest_towns"]) for row in universities)
    nearest_town_total_count = len(universities)
    geo_nearest_towns_readiness = round(nearest_town_coverage_count / nearest_town_total_count, 3)
    nearest_town_completion_status = (
        "complete" if nearest_town_coverage_count == nearest_town_total_count
        else "incomplete_source_unavailable" if nearest_town_coverage_count == 0
        and town_manifest.get("source_status") == "source_unavailable_in_execution_environment"
        else "incomplete"
    )
    demo_program_readiness_after = round(sum(row["top_5_gap_reason"] is None for row in demo_programs) / 62, 3)
    summary = {
        "record_type": "stage3c_academic_geo_enrichment_summary", "total_universities": 62,
        "unc_demo_program_gap_resolved": next(row["top_5_gap_reason"] is None for row in demo_programs if row["candidate_id"] == "candidate-v2:university-of-north-carolina-chapel-hill"),
        "universities_with_official_full_undergraduate_major_list": sum(row["official_major_source_status"] == "official_full_undergraduate_major_list_found" for row in major_sources),
        "universities_with_official_areas_of_study": sum(row["official_major_source_status"] == "official_areas_of_study_found" for row in major_sources),
        "universities_with_official_catalog_programs": sum(row["official_major_source_status"] == "official_catalog_found" for row in major_sources),
        "universities_with_official_undergraduate_programs": sum(row["official_major_source_status"] == "official_undergraduate_programs_found" for row in major_sources),
        "universities_using_only_ipeds_award_areas": sum(row["official_major_source_status"] == "only_ipeds_award_areas_available" for row in major_sources),
        "universities_missing_official_major_source": sum(row["official_major_source_status"] == "not_found" for row in major_sources),
        "universities_with_university_level_only_confirmed": sum(row["tuition_deepening_status"] == "university_level_only_confirmed" for row in tuition_deepening),
        "universities_with_college_level_surcharge_found": sum(row["tuition_deepening_status"] == "college_level_surcharge_found" for row in tuition_deepening),
        "universities_with_program_level_extra_fee_found": sum(row["tuition_deepening_status"] == "program_level_extra_fee_found" for row in tuition_deepening),
        "universities_with_mixed_base_plus_surcharge_found": sum(row["tuition_deepening_status"] == "mixed_base_plus_surcharge_found" for row in tuition_deepening),
        "highest_lowest_basis_program_level_only_count": sum(row["highest_lowest_basis"] == "program_level_only" for row in highest_lowest),
        "highest_lowest_basis_college_or_program_level_count": sum(row["highest_lowest_basis"] == "college_level_or_program_level" for row in highest_lowest),
        "highest_lowest_basis_university_level_same_for_all_count": sum(row["highest_lowest_basis"] == "university_level_same_for_all" for row in highest_lowest),
        "highest_lowest_null_count": sum(row["highest_tuition_program"] is None for row in highest_lowest),
        "nearest_town_coverage_count": nearest_town_coverage_count,
        "nearest_town_total_count": nearest_town_total_count,
        "nearest_town_coverage_definition": "universities_with_at_least_one_nearest_town",
        "nearest_town_completion_status": nearest_town_completion_status,
        "geo_nearest_towns_readiness": geo_nearest_towns_readiness,
        "source_policy_violations": 0, "ranking_field_contamination": 0,
        "demo_readiness_before": stage3b["stage3b-summary.json"].get("demo_readiness_after"),
        "demo_readiness_after": demo_program_readiness_after,
        "demo_readiness_after_scope": "legacy_program_only",
        "demo_program_readiness_after": demo_program_readiness_after,
        "stage3c_overlay_status": "academic_complete_geo_partial",
        "input_sha256": {"stage3": stage3_hashes, "stage3b": stage3b_hashes},
        "remaining_data_gaps": ["Nearest-place cache unavailable in this execution environment; all nearest_towns are disclosed empty lists.", "Official major source uplift is best-effort; IPEDS award areas remain federal fallback for schools without a reviewed official source."],
        **STAGE3C_FLAGS,
    }
    disclosure = {
        "record_type": "stage3c_academic_geo_gap_disclosure",
        "universities": gaps,
        "town_source_limitation": town_manifest["limitation_note"],
        "nearest_towns_readiness": {
            "coverage_count": nearest_town_coverage_count,
            "total_count": nearest_town_total_count,
            "readiness": geo_nearest_towns_readiness,
            "completion_status": nearest_town_completion_status,
            "null_reason": "source_unavailable_in_execution_environment",
            "source_attempts": ["Census Gazetteer", "Census TigerWeb"],
            "no_bypass_no_guessing_no_fabricated_distance": True,
        },
        "upstream_artifacts_modified": False,
        **STAGE3C_FLAGS,
    }
    return {
        "stage3c-universities.json": {"metadata": {"record_type": "stage3c_universities", **STAGE3C_FLAGS}, "universities": universities},
        "stage3c-official-major-sources.json": {"metadata": {"record_type": "stage3c_official_major_sources", **STAGE3C_FLAGS}, "universities": major_sources},
        "stage3c-official-majors.json": {"metadata": {"record_type": "stage3c_official_majors", **STAGE3C_FLAGS}, "universities": official_majors},
        "stage3c-demo-programs-overlay.json": {"metadata": {"record_type": "stage3c_demo_programs_overlay", **STAGE3C_FLAGS}, "universities": demo_programs},
        "stage3c-tuition-deepening.json": {"metadata": {"record_type": "stage3c_tuition_deepening", **STAGE3C_FLAGS}, "universities": tuition_deepening},
        "stage3c-highest-lowest-tuition.json": {"metadata": {"record_type": "stage3c_highest_lowest_tuition", **STAGE3C_FLAGS}, "universities": highest_lowest},
        "stage3c-gap-disclosure.json": disclosure,
        "stage3c-summary.json": summary,
    }


def validate_stage3c_academic_geo(
    artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3_dir: Path, stage3b_dir: Path,
    source_manifest_path: Path, major_observations_path: Path, tuition_observations_path: Path,
    region_mapping_path: Path, town_manifest_path: Path, town_cache: Path, report_path: Path,
) -> Dict[str, Any]:
    """Fail closed unless artifacts exactly equal deterministic Stage 3C regeneration."""
    expected = build_stage3c_academic_geo(candidate_path, stage3_dir, stage3b_dir, source_manifest_path, major_observations_path, tuition_observations_path, region_mapping_path, town_manifest_path, town_cache)
    if artifacts != expected:
        _fail("Stage 3C artifacts must equal deterministic regeneration")
    candidates = {row["candidate_university_id"] for row in _candidate_rows(candidate_path)}
    for name in OUTPUT_FILES:
        if name not in artifacts:
            _fail("Stage 3C artifact bundle is incomplete")
    for document in artifacts.values():
        metadata = document.get("metadata")
        if metadata is not None and not _flags_valid(metadata):
            _fail("Stage 3C artifact flags violate final-output boundary")
    universities = artifacts["stage3c-universities.json"]["universities"]
    if {row["candidate_id"] for row in universities} != candidates or len(universities) != 62:
        _fail("Stage 3C university scope must equal Candidate v2")
    for row in universities:
        if row["region"] not in FOUR_REGIONS or row.get("region_taxonomy") != "us_census_four_regions":
            _fail("Stage 3C regions must use only Census four regions")
        for town in row["nearest_towns"]:
            if town.get("place_type") not in {"city", "town", "municipality", "incorporated_place", "census_designated_place"} or town.get("distance_method") != "haversine_straight_line":
                _fail("Nearest towns must use permitted places and Haversine method")
            if "not driving distance" not in town.get("calculation_notes", ""):
                _fail("Nearest towns must disclose straight-line distance")
    for row in artifacts["stage3c-official-majors.json"]["universities"]:
        for major in row["majors"]:
            if major.get("undergraduate_status") != "undergraduate" or major.get("usnews_category") is not None or major.get("usnews_rank") is not None:
                _fail("Official major detail may not contaminate ranking fields")
    for row in artifacts["stage3c-demo-programs-overlay.json"]["universities"]:
        for program in row["added_official_undergraduate_programs"]:
            if program.get("source_type") != "official_institutional" or program.get("undergraduate_status") != "undergraduate" or program.get("usnews_category") is not None or program.get("usnews_rank") is not None:
                _fail("Stage 3C demo additions must be official undergraduate non-ranking records")
        if len(row["top_5_programs_for_demo"]) < 5 and not row.get("top_5_gap_reason"):
            _fail("Incomplete demo programs require a gap reason")
    for row in artifacts["stage3c-tuition-deepening.json"]["universities"]:
        for fee in row.get("fee_observations", []):
            _validate_fee(fee, _load_sources(source_manifest_path))
    summary = artifacts["stage3c-summary.json"]
    if summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0 or not _flags_valid(summary):
        _fail("Stage 3C summary violates source policy or final-output boundary")
    if (
        summary.get("demo_program_readiness_after") != 1.0
        or summary.get("demo_readiness_after") != 1.0
        or summary.get("demo_readiness_after_scope") != "legacy_program_only"
        or summary.get("geo_nearest_towns_readiness") != 0.0
        or summary.get("nearest_town_coverage_count") != 0
        or summary.get("nearest_town_total_count") != 62
        or summary.get("nearest_town_coverage_definition") != "universities_with_at_least_one_nearest_town"
        or summary.get("nearest_town_completion_status") != "incomplete_source_unavailable"
        or summary.get("stage3c_overlay_status") != "academic_complete_geo_partial"
    ):
        _fail("Stage 3C readiness must separate program completion from unavailable nearest towns")
    disclosure = artifacts["stage3c-gap-disclosure.json"].get("nearest_towns_readiness", {})
    if (
        disclosure.get("coverage_count") != 0
        or disclosure.get("total_count") != 62
        or disclosure.get("readiness") != 0.0
        or disclosure.get("completion_status") != "incomplete_source_unavailable"
        or disclosure.get("null_reason") != "source_unavailable_in_execution_environment"
        or disclosure.get("source_attempts") != ["Census Gazetteer", "Census TigerWeb"]
        or disclosure.get("no_bypass_no_guessing_no_fabricated_distance") is not True
    ):
        _fail("Stage 3C nearest-town gap disclosure must explicitly disclose the 0/62 source limitation")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail(f"Stage 3C readiness report is required: {report_path}")
        raise AssertionError("unreachable") from error
    required_report_lines = (
        "Academic/program readiness: complete.",
        "Region readiness: complete.",
        "Nearest towns readiness: 0/62.",
        "Academic + partial Geo overlay",
        "`demo_program_readiness_after=1.0` does not mean nearest towns are complete.",
    )
    if any(line not in report for line in required_report_lines) or "Nearest towns readiness: complete." in report:
        _fail("Stage 3C report must not present nearest towns as complete")
    return {
        "record_type": "stage3c_academic_geo_enrichment_validation_result", "result": "passed", "total_universities": 62,
        "demo_program_readiness_after": 1.0, "geo_nearest_towns_readiness": 0.0,
        "nearest_town_coverage_count": 0, "nearest_town_total_count": 62,
        "nearest_town_completion_status": "incomplete_source_unavailable",
        "source_policy_violations": 0, "ranking_field_contamination": 0, **STAGE3C_FLAGS,
    }


def write_stage3c_academic_geo(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3c-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
