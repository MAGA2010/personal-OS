"""Deterministic Stage 3C2 repair for the Stage 3C nearest-town gap."""

import hashlib
import io
import json
import math
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .stage3_program_mvp import FLAGS, _candidate_rows, _normal
from .universe_candidate_v2 import validate_source_policy_use


STAGE3C_FILES = (
    "stage3c-universities.json", "stage3c-official-major-sources.json", "stage3c-official-majors.json",
    "stage3c-demo-programs-overlay.json", "stage3c-tuition-deepening.json", "stage3c-highest-lowest-tuition.json",
    "stage3c-gap-disclosure.json", "stage3c-summary.json", "stage3c-validation-result.json",
)
OUTPUT_FILES = (
    "stage3c2-nearest-towns.json", "stage3c2-place-source-manifest.json", "stage3c2-place-observations.json",
    "stage3c2-gap-disclosure.json", "stage3c2-summary.json",
)
FLAGS_3C2 = {
    **FLAGS,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}
ALLOWED_PLACE_TYPES = {"city", "town", "municipality", "incorporated_place", "census_designated_place"}
ZIP_NAME = "2024_Gaz_place_national.zip"
ZIP_MEMBER = "2024_Gaz_place_national.txt"
STATE_NAMES = {
    "AL": "Alabama", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


class Stage3C2NearestTownsValidationError(ValueError):
    """Raised for scope, provenance, place, or distance violations."""


def _fail(message: str) -> None:
    raise Stage3C2NearestTownsValidationError(message)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Unable to read Stage 3C2 input: {path}")
        raise AssertionError("unreachable") from error
    if not isinstance(value, dict):
        _fail(f"Stage 3C2 input must be a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprints(directory: Path, names: Iterable[str]) -> Dict[str, str]:
    values = {}
    for name in names:
        path = directory / name
        if not path.exists():
            _fail(f"Missing immutable Stage 3C input: {path}")
        values[str(path)] = _sha256(path)
    return dict(sorted(values.items()))


def _flags_valid(value: Dict[str, Any]) -> bool:
    return (
        value.get("source_limited") is True and value.get("incomplete") is True and value.get("not_final") is True
        and value.get("final_universe_generated") is False
        and value.get("official_selection_memberships_generated") is False
        and value.get("frontend_export_generated") is False
    )


def _load_manifest(path: Path, cache_dir: Path) -> Tuple[Dict[str, Any], Path]:
    manifest = _read_json(path)
    required = ("source_id", "source_type", "source_title", "source_url_or_reference", "publisher", "dataset_file", "cache_relative_path", "review_status")
    if manifest.get("record_type") != "stage3c2_place_source_manifest" or not all(manifest.get(key) for key in required):
        _fail("Stage 3C2 requires a complete reviewed place source manifest")
    if manifest.get("source_type") != "census_gazetteer" or manifest.get("dataset_file") != ZIP_NAME:
        _fail("Stage 3C2 only accepts the reviewed Census 2024 National Places Gazetteer")
    cache_file = cache_dir / manifest["dataset_file"]
    if not cache_file.exists() or _sha256(cache_file) != manifest.get("cache_sha256"):
        _fail("Reviewed Census place cache is missing or its checksum does not match the manifest")
    repo_root = cache_dir.resolve().parents[2]
    ignored = subprocess.run(["git", "-C", str(repo_root), "check-ignore", "-q", str(cache_file.resolve())], check=False).returncode == 0
    if not ignored:
        _fail("Reviewed place cache must be gitignored")
    return manifest, cache_file


def _place_type(lsad: str) -> str:
    if lsad == "57":
        return "census_designated_place"
    if lsad == "25":
        return "city"
    if lsad == "43":
        return "town"
    return "incorporated_place"


def _place_name(name: str) -> str:
    for suffix in (" city", " town", " village", " CDP", " municipality", " borough"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _normalized_state(value: Any) -> str:
    """Normalize either a postal abbreviation or Census full state name."""
    raw = str(value or "").strip()
    return _normal(STATE_NAMES.get(raw.upper(), raw))


def _is_campus_city(university: Dict[str, Any], place: Dict[str, Any]) -> bool:
    """Return whether a selected Census place is the university's campus city."""
    school_city = str(university.get("city") or university.get("school_city") or "").strip()
    school_state = str(university.get("state") or university.get("school_state") or "").strip()
    return bool(school_city and school_state) and (
        _normal(school_city) == _normal(str(place.get("town_name") or ""))
        and _normalized_state(school_state) == _normalized_state(place.get("state"))
    )


def _load_places(cache_file: Path) -> List[Dict[str, Any]]:
    try:
        archive = zipfile.ZipFile(cache_file)
        with archive.open(ZIP_MEMBER) as binary:
            rows = io.TextIOWrapper(binary, encoding="utf-8").read().splitlines()
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        _fail("Reviewed Census cache cannot be parsed")
        raise AssertionError("unreachable") from error
    header = [value.strip() for value in rows[0].split("\t")]
    required = {"USPS", "GEOID", "NAME", "LSAD", "INTPTLAT", "INTPTLONG"}
    if not required.issubset(set(header)):
        _fail("Census place cache has no required place coordinate columns")
    index = {name: position for position, name in enumerate(header)}
    places = []
    for line in rows[1:]:
        columns = line.split("\t")
        if len(columns) < len(header):
            continue
        state_code = columns[index["USPS"]].strip()
        if state_code not in STATE_NAMES:
            continue
        try:
            latitude = float(columns[index["INTPTLAT"]])
            longitude = float(columns[index["INTPTLONG"]])
        except ValueError:
            continue
        place_type = _place_type(columns[index["LSAD"]].strip())
        if place_type not in ALLOWED_PLACE_TYPES:
            continue
        source_name = columns[index["NAME"]].strip()
        places.append({
            "town_name": _place_name(source_name), "source_place_name": source_name,
            "state": STATE_NAMES[state_code], "place_type": place_type,
            "geoid": columns[index["GEOID"]].strip(), "town_latitude": latitude, "town_longitude": longitude,
        })
    if not places:
        _fail("Reviewed Census cache yielded no permitted places")
    return places


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance using the fixed WGS84 mean Earth radius."""
    radius_km = 6371.0088
    p1, p2, dlat, dlon = map(math.radians, (lat1, lat2, lat2 - lat1, lon2 - lon1))
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def _nearest_places(university: Dict[str, Any], places: List[Dict[str, Any]], manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    latitude, longitude = university.get("latitude"), university.get("longitude")
    if latitude is None or longitude is None:
        _fail("Stage 3C2 requires a source-backed school coordinate")
    candidates = []
    for place in places:
        distance_km = haversine_km(float(latitude), float(longitude), place["town_latitude"], place["town_longitude"])
        candidates.append((distance_km, _normal(place["town_name"]), place["state"], place["geoid"], place))
    selected, seen = [], set()
    for distance_km, _, _, _, place in sorted(candidates):
        key = (place["state"], _normal(place["town_name"]))
        if key in seen:
            continue
        seen.add(key)
        campus_city_included = _is_campus_city(university, place)
        selected.append({
            "town_name": place["town_name"], "state": place["state"], "place_type": place["place_type"],
            "population_class": None, "population_class_null_reason": "not_provided_by_census_2024_places_gazetteer",
            "town_latitude": place["town_latitude"], "town_longitude": place["town_longitude"],
            "distance_miles": round(distance_km * 0.621371, 2), "distance_km": round(distance_km, 2),
            "distance_method": "haversine_straight_line", "source_id": manifest["source_id"],
            "source_reference": manifest["source_url_or_reference"], "source_place_name": place["source_place_name"],
            "source_geoid": place["geoid"], "campus_city_included": campus_city_included,
            "calculation_notes": "Haversine straight-line distance; not driving distance; not travel time.",
            "null_reason": None,
        })
        if len(selected) == 3:
            break
    return selected


def build_stage3c2_nearest_towns(candidate_path: Path, stage3c_dir: Path, place_manifest_path: Path, cache_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Build Stage 3C2 only from Candidate v2, immutable Stage 3C, and reviewed Census cache."""
    validate_source_policy_use("Census", "detail", has_field_provenance=True)
    candidate_rows = _candidate_rows(candidate_path)
    candidate_ids = {row["candidate_university_id"] for row in candidate_rows}
    input_hashes = _fingerprints(stage3c_dir, STAGE3C_FILES)
    stage3c = _read_json(stage3c_dir / "stage3c-universities.json")
    rows = stage3c.get("universities")
    if not isinstance(rows, list) or {row.get("candidate_id") for row in rows} != candidate_ids or len(rows) != 62:
        _fail("Stage 3C2 scope must exactly match Candidate v2 and immutable Stage 3C")
    manifest, cache_file = _load_manifest(place_manifest_path, cache_dir)
    places = _load_places(cache_file)
    by_id = {row["candidate_id"]: row for row in rows}
    universities, observations, gaps = [], [], []
    for candidate in candidate_rows:
        candidate_id = candidate["candidate_university_id"]
        base = by_id[candidate_id]
        towns = _nearest_places(base, places, manifest)
        gap_reason = None if len(towns) == 3 else "fewer_than_three_permitted_census_places_available"
        university = {
            "candidate_id": candidate_id, "canonical_id": base["canonical_id"], "display_name": base["display_name"],
            "school_city": base["city"], "school_state": base["state"], "school_latitude": base["latitude"],
            "school_longitude": base["longitude"], "nearest_towns": towns, "nearest_towns_gap_reason": gap_reason,
        }
        universities.append(university)
        for town in towns:
            observations.append({"candidate_id": candidate_id, "canonical_id": base["canonical_id"], "display_name": base["display_name"], **town})
        if gap_reason:
            gaps.append({"candidate_id": candidate_id, "nearest_towns_gap_reason": gap_reason})
    if input_hashes != _fingerprints(stage3c_dir, STAGE3C_FILES):
        _fail("Stage 3C2 may not mutate Stage 3C inputs")
    resolved = sum(len(row["nearest_towns"]) == 3 for row in universities)
    campus_city_included_place_count = sum(
        town["campus_city_included"]
        for university in universities
        for town in university["nearest_towns"]
    )
    campus_city_included_university_count = sum(
        any(town["campus_city_included"] for town in university["nearest_towns"])
        for university in universities
    )
    source_artifact = {**manifest, "cache_sha256": _sha256(cache_file), "cache_committed": False, "cache_gitignored": True, **FLAGS_3C2}
    summary = {
        "record_type": "stage3c2_nearest_towns_summary", "total_universities": 62,
        "nearest_town_resolved_university_count": resolved, "nearest_town_unresolved_university_count": 62 - resolved,
        "total_nearest_town_records": len(observations), "geo_nearest_towns_readiness": round(resolved / 62, 3),
        "campus_city_included_university_count": campus_city_included_university_count,
        "campus_city_included_place_count": campus_city_included_place_count,
        "place_source_used": manifest["source_id"], "distance_method": "haversine_straight_line",
        "excluded_place_type_count": 0, "source_policy_violations": 0, "ranking_field_contamination": 0,
        "input_sha256": {"stage3c": input_hashes}, "cache_sha256": _sha256(cache_file), **FLAGS_3C2,
    }
    disclosure = {
        "record_type": "stage3c2_nearest_towns_gap_disclosure", "unresolved_universities": gaps,
        "source_limitations": "Reviewed Census 2024 National Places Gazetteer provides place coordinates but not population; population_class remains null.",
        "no_driving_distance_or_travel_time": True, "no_unreviewed_geo_source_used": True, **FLAGS_3C2,
    }
    return {
        "stage3c2-nearest-towns.json": {"metadata": {"record_type": "stage3c2_nearest_towns", **FLAGS_3C2}, "universities": universities},
        "stage3c2-place-source-manifest.json": source_artifact,
        "stage3c2-place-observations.json": {"metadata": {"record_type": "stage3c2_place_observations", **FLAGS_3C2}, "observations": observations},
        "stage3c2-gap-disclosure.json": disclosure,
        "stage3c2-summary.json": summary,
    }


def render_stage3c2_report(artifacts: Dict[str, Dict[str, Any]]) -> str:
    summary = artifacts["stage3c2-summary.json"]
    return "\n".join((
        "# Stage 3C2 — Nearest Towns Gap Repair Report", "",
        "## Scope and source", "",
        "Stage 3C2 is an independent, source-limited, not-final geography overlay for the fixed 62-university Candidate v2 scope. It does not modify Stage 3, Stage 3B, Candidate v2, frontend, ranking fields, final universe, official selection memberships, or frontend export.",
        "", "- Sole place source: reviewed U.S. Census 2024 National Places Gazetteer cache.",
        "- Only Census places are used. Counties, campuses, neighborhoods, school facilities, metro areas, and unclassified labels are excluded.",
        "- Distances are Haversine straight-line distances, not driving distance and not travel time.",
        "", "## Coverage", "",
        f"- Nearest towns readiness: {summary['nearest_town_resolved_university_count']}/62 ({summary['geo_nearest_towns_readiness']}).",
        f"- Total nearest-town records: {summary['total_nearest_town_records']}.",
        f"- Campus-city place included: {summary['campus_city_included_university_count']}/62 universities ({summary['campus_city_included_place_count']} places).",
        "- Each resolved university has exactly three allowed Census places, deterministically ordered by Haversine distance and source identifier.",
        "", "## Limitations and validation", "",
        "- Census Gazetteer does not provide population counts in this cache; population_class is null with an explicit source limitation.",
        "- source_policy_violations = 0; ranking_field_contamination = 0.",
        "- Cache is gitignored; only structured source metadata, selected observations, calculations, disclosure, and validation artifacts are version controlled.",
        "",
    ))


def validate_stage3c2_nearest_towns(artifacts: Dict[str, Dict[str, Any]], *, candidate_path: Path, stage3c_dir: Path, place_manifest_path: Path, cache_dir: Path, report_path: Path) -> Dict[str, Any]:
    """Fail closed on cache provenance, scope, place type, distance, or output-boundary violations."""
    expected = build_stage3c2_nearest_towns(candidate_path, stage3c_dir, place_manifest_path, cache_dir)
    if artifacts != expected:
        _fail("Stage 3C2 artifacts must equal deterministic regeneration")
    candidates = {row["candidate_university_id"] for row in _candidate_rows(candidate_path)}
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Stage 3C2 artifact bundle is incomplete")
    universities = artifacts["stage3c2-nearest-towns.json"].get("universities", [])
    if len(universities) != 62 or {row.get("candidate_id") for row in universities} != candidates:
        _fail("Stage 3C2 university scope must remain 62 Candidate v2 universities")
    for university in universities:
        towns = university.get("nearest_towns", [])
        if len(towns) != 3 or university.get("nearest_towns_gap_reason") is not None:
            _fail("Stage 3C2 requires exactly three resolved Census places per university")
        for town in towns:
            if town.get("place_type") not in ALLOWED_PLACE_TYPES or town.get("distance_method") != "haversine_straight_line":
                _fail("Nearest towns must use only allowed Census places and Haversine")
            notes = str(town.get("calculation_notes", "")).lower()
            non_disclaimer_notes = notes.replace("not driving distance", "").replace("not travel time", "")
            if not town.get("source_id") or "driving distance" in non_disclaimer_notes or "travel time" in non_disclaimer_notes:
                _fail("Nearest towns require source provenance and must not claim driving distance or travel time")
            distance = haversine_km(float(university["school_latitude"]), float(university["school_longitude"]), float(town["town_latitude"]), float(town["town_longitude"]))
            if abs(round(distance, 2) - town["distance_km"]) > 0.001 or abs(round(distance * 0.621371, 2) - town["distance_miles"]) > 0.001:
                _fail("Nearest-town distance must be deterministically reproducible")
            expected_campus_city = _is_campus_city({
                "school_city": university.get("school_city"), "school_state": university.get("school_state"),
            }, town)
            if town.get("campus_city_included") is not expected_campus_city:
                _fail("campus_city_included must match normalized school and Census place city/state")
    campus_city_included_place_count = sum(
        town["campus_city_included"]
        for university in universities
        for town in university["nearest_towns"]
    )
    campus_city_included_university_count = sum(
        any(town["campus_city_included"] for town in university["nearest_towns"])
        for university in universities
    )
    summary = artifacts["stage3c2-summary.json"]
    if (
        summary.get("nearest_town_resolved_university_count") != 62 or summary.get("nearest_town_unresolved_university_count") != 0
        or summary.get("total_nearest_town_records") != 186 or summary.get("geo_nearest_towns_readiness") != 1.0
        or summary.get("campus_city_included_university_count") != campus_city_included_university_count
        or summary.get("campus_city_included_place_count") != campus_city_included_place_count
        or summary.get("distance_method") != "haversine_straight_line" or summary.get("source_policy_violations") != 0
        or summary.get("ranking_field_contamination") != 0 or not _flags_valid(summary)
    ):
        _fail("Stage 3C2 summary does not honestly represent the resolved nearest-town overlay")
    source_manifest = artifacts["stage3c2-place-source-manifest.json"]
    if source_manifest.get("cache_committed") is not False or source_manifest.get("cache_gitignored") is not True:
        _fail("Stage 3C2 cache policy is violated")
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as error:
        _fail("Stage 3C2 report is required for formal validation")
        raise AssertionError("unreachable") from error
    required = (
        "Nearest towns readiness: 62/62 (1.0).",
        f"Campus-city place included: {campus_city_included_university_count}/62 universities ({campus_city_included_place_count} places).",
        "not driving distance and not travel time",
        "source_policy_violations = 0",
        "ranking_field_contamination = 0",
    )
    if any(value not in report for value in required):
        _fail("Stage 3C2 report omits required coverage or distance disclosures")
    return {"record_type": "stage3c2_nearest_towns_validation_result", "result": "passed", "total_universities": 62, "nearest_town_resolved_university_count": 62, "total_nearest_town_records": 186, "geo_nearest_towns_readiness": 1.0, "source_policy_violations": 0, "ranking_field_contamination": 0, **FLAGS_3C2}


def write_stage3c2_artifacts(artifacts: Dict[str, Dict[str, Any]], output: Path, validation: Dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {**artifacts, "stage3c2-validation-result.json": validation}.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
