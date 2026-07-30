"""Build campus geography crosswalks from official IPEDS and reviewed Census links."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from .config import fail, read_json
from .source_intake import (
    IPEDS_HD_SOURCE_ID,
    IPEDS_REFERENCE_YEAR,
    parse_float,
)


CENSUS_GAZETTEER_SOURCE_ID = "source_stage4b_census_2024_places_gazetteer"
COUNTY_RE = re.compile(r"^\d{5}$")
PLACE_RE = re.compile(r"^\d{7}$")
CBSA_RE = re.compile(r"^\d{5}$")


def _clean_code(value: Any, width: int) -> Any:
    if value in (None, "", "NA", "NULL", "PrivacySuppressed"):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(width)


def build_campus_geography_crosswalk(
    pipeline_root: Any, official_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    nearest_path = (
        pipeline_root
        / "artifacts/stage3c2-nearest-towns-gap-repair/stage3c2-nearest-towns.json"
    )
    nearest_rows = read_json(nearest_path).get("universities")
    if not isinstance(nearest_rows, list) or len(nearest_rows) != 62:
        fail("Stage 4B geography requires 62 reviewed nearest-town rows")
    nearest = {row["candidate_id"]: row for row in nearest_rows}
    output: List[Dict[str, Any]] = []
    for row in official_rows:
        hd = row["ipeds_hd"]
        county_geoid = _clean_code(hd.get("COUNTYCD"), 5)
        state_fips = _clean_code(hd.get("FIPS"), 2)
        cbsa_geoid = _clean_code(hd.get("CBSA"), 5)
        if county_geoid is None:
            fail(f"IPEDS county GEOID missing for {row['candidate_id']}")
        campus_place_candidates = [
            town
            for town in nearest[row["candidate_id"]].get("nearest_towns", [])
            if town.get("campus_city_included") is True
        ]
        if len(campus_place_candidates) > 1:
            fail(f"Multiple reviewed campus places for {row['candidate_id']}")
        campus_place = campus_place_candidates[0] if campus_place_candidates else None
        place_geoid = (
            _clean_code(campus_place.get("source_geoid"), 7)
            if campus_place
            else None
        )
        place_verified = bool(campus_place and PLACE_RE.fullmatch(place_geoid or ""))
        primary = (
            {
                "geography_type": "place",
                "geography_id": place_geoid,
                "join_method": "reviewed_campus_city_census_place_link",
                "join_confidence": "high",
            }
            if place_verified
            else {
                "geography_type": "county",
                "geography_id": county_geoid,
                "join_method": "ipeds_reported_county",
                "join_confidence": "high",
            }
        )
        record = {
            "candidate_id": row["candidate_id"],
            "canonical_id": row["canonical_id"],
            "university_display_name": row["university_display_name"],
            "campus_coordinates": {
                "latitude": parse_float(hd.get("LATITUDE")),
                "longitude": parse_float(hd.get("LONGITUD")),
                "reference_year": IPEDS_REFERENCE_YEAR,
                "source_ids": [IPEDS_HD_SOURCE_ID],
            },
            "state": {
                "abbreviation": hd.get("STABBR"),
                "fips": state_fips,
                "source_ids": [IPEDS_HD_SOURCE_ID],
                "availability_status": "verified",
            },
            "county": {
                "name": hd.get("COUNTYNM"),
                "geoid": county_geoid,
                "geography_type": "county",
                "join_method": "ipeds_reported_county",
                "join_confidence": "high",
                "reference_year": IPEDS_REFERENCE_YEAR,
                "source_ids": [IPEDS_HD_SOURCE_ID],
                "availability_status": "verified",
            },
            "census_place": {
                "name": campus_place.get("town_name") if campus_place else None,
                "geoid": place_geoid if place_verified else None,
                "geography_type": "place",
                "join_method": (
                    "reviewed_campus_city_census_place_link"
                    if place_verified
                    else "not_resolved"
                ),
                "join_confidence": "high" if place_verified else "none",
                "reference_year": 2024 if place_verified else None,
                "source_ids": (
                    [CENSUS_GAZETTEER_SOURCE_ID] if place_verified else []
                ),
                "availability_status": "verified" if place_verified else "pending",
                "null_reason": (
                    None
                    if place_verified
                    else "campus_city_not_safely_linked_to_census_place"
                ),
            },
            "cbsa": {
                "geoid": cbsa_geoid if CBSA_RE.fullmatch(cbsa_geoid or "") else None,
                "geography_type": "cbsa",
                "join_method": "ipeds_reported_cbsa",
                "join_confidence": (
                    "high" if CBSA_RE.fullmatch(cbsa_geoid or "") else "none"
                ),
                "reference_year": IPEDS_REFERENCE_YEAR,
                "source_ids": [IPEDS_HD_SOURCE_ID] if cbsa_geoid else [],
                "availability_status": (
                    "verified" if CBSA_RE.fullmatch(cbsa_geoid or "") else "unavailable"
                ),
                "null_reason": None if cbsa_geoid else "ipeds_cbsa_not_available",
            },
            "primary_region_for_map": primary,
            "fallback_region": {
                "geography_type": "state",
                "geography_id": state_fips,
                "join_method": "ipeds_reported_state",
                "join_confidence": "high",
            },
            "geography_scope_notes": (
                "Primary region is a reviewed campus Census place when an exact "
                "campus-city link exists; otherwise the directly reported IPEDS "
                "county is used. Nearest non-campus towns are never substituted."
            ),
        }
        validate_geography_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_geography_record(record: Dict[str, Any]) -> None:
    county = record.get("county", {})
    if (
        county.get("availability_status") != "verified"
        or not COUNTY_RE.fullmatch(str(county.get("geoid") or ""))
        or county.get("join_confidence") not in {"high", "medium"}
    ):
        fail("Stage 4B county geography is invalid")
    place = record.get("census_place", {})
    if place.get("availability_status") == "verified":
        if (
            not PLACE_RE.fullmatch(str(place.get("geoid") or ""))
            or place.get("join_method")
            != "reviewed_campus_city_census_place_link"
            or place.get("join_confidence") != "high"
        ):
            fail("Stage 4B verified Census place join is invalid")
    elif place.get("geoid") is not None:
        fail("Unverified Census place cannot carry a GEOID")
    primary = record.get("primary_region_for_map", {})
    if primary.get("geography_type") == "place":
        if primary.get("geography_id") != place.get("geoid"):
            fail("Primary place geography does not match reviewed Census place")
    elif primary.get("geography_type") == "county":
        if primary.get("geography_id") != county.get("geoid"):
            fail("Primary county geography does not match IPEDS county")
    else:
        fail("Primary campus region must be a verified place or county")
    if primary.get("join_method") == "nearest_town":
        fail("Nearest town cannot become campus geography")
    fallback = record.get("fallback_region", {})
    if (
        fallback.get("geography_type") != "state"
        or not re.fullmatch(r"\d{2}", str(fallback.get("geography_id") or ""))
    ):
        fail("Stage 4B fallback state geography is invalid")
