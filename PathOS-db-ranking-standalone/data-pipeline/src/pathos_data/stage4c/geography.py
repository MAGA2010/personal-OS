"""Resolve Stage 4B place gaps to explicit place or valid county fallback states."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import fail


def build_census_place_resolution(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for candidate_id, geography in sorted(context["geography_by_id"].items()):
        place = geography["census_place"]
        verified = place["geoid"] is not None
        row = {
            "candidate_id": candidate_id,
            "campus_coordinates": geography["campus_coordinates"],
            "address": geography.get("official_location"),
            "county_geoid": geography["county"]["geoid"],
            "place_geoid": place["geoid"],
            "place_name": place.get("name"),
            "place_type": place.get("place_type") if verified else None,
            "resolution_status": "verified_place" if verified else "county_only_valid",
            "join_method": place["join_method"] if verified else "reviewed_county_fallback",
            "confidence": "high",
            "fallback_geography": None if verified else {
                "geography_type": "county",
                "geoid": geography["county"]["geoid"],
                "name": geography["county"]["name"],
            },
            "reason": (
                "reviewed_stage3c2_campus_place_link"
                if verified
                else "no_safe_place_join_in_frozen_official_inputs"
            ),
            "reviewed_exception": not verified,
            "nearest_town_used": False,
            "postal_city_assumed_place": False,
        }
        validate_place_resolution(row)
        rows.append(row)
    return rows


def validate_place_resolution(row: Dict[str, Any]) -> None:
    allowed = {
        "verified_place", "verified_cdp", "verified_city", "county_only_valid",
        "unincorporated_area", "multi_place_campus", "special_campus_geography",
        "pending", "not_applicable",
    }
    if row["resolution_status"] not in allowed:
        fail("Invalid Census place resolution status")
    if row["nearest_town_used"] or row["join_method"] == "nearest_town":
        fail("Nearest town cannot define campus geography")
    if row["resolution_status"] == "county_only_valid":
        if row["place_geoid"] is not None or not row["fallback_geography"]:
            fail("County fallback must be explicit and place must stay null")
    elif row["resolution_status"].startswith("verified") and not row["place_geoid"]:
        fail("Verified place resolution lacks a GEOID")
    if row["postal_city_assumed_place"]:
        fail("Postal city cannot be silently treated as Census place")
