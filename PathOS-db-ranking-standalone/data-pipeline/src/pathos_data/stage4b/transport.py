"""Partial transport availability built only from verified distance facts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import fail, read_json


NEAREST_TOWNS_SOURCE_ID = "source_stage4b_stage3c2_nearest_towns"


def _pending_transport(kind: str) -> Dict[str, Any]:
    return {
        "kind": kind,
        "name": None,
        "distance_km": None,
        "distance_method": None,
        "source_ids": [],
        "availability_status": "deferred",
        "null_reason": "uniform_official_transport_intake_not_available",
    }


def build_transport_accessibility_metrics(
    pipeline_root: Path, geography_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    nearest_path = (
        pipeline_root
        / "artifacts/stage3c2-nearest-towns-gap-repair/stage3c2-nearest-towns.json"
    )
    rows = read_json(nearest_path).get("universities")
    nearest = {row["candidate_id"]: row for row in rows}
    output = []
    for geography in geography_rows:
        towns = nearest[geography["candidate_id"]]["nearest_towns"]
        distances = [town.get("distance_km") for town in towns]
        record = {
            "candidate_id": geography["candidate_id"],
            "canonical_id": geography["canonical_id"],
            "university_display_name": geography["university_display_name"],
            "availability_status": "partial",
            "nearest_towns": {
                "count": len(towns),
                "minimum_distance_km": min(distances) if distances else None,
                "distance_method": "haversine_straight_line",
                "source_ids": [NEAREST_TOWNS_SOURCE_ID],
                "availability_status": "verified",
            },
            "campus_city_relationship": {
                "campus_place_resolved": (
                    geography["census_place"]["availability_status"] == "verified"
                ),
                "availability_status": (
                    "verified"
                    if geography["census_place"]["availability_status"] == "verified"
                    else "pending"
                ),
                "source_ids": (
                    geography["census_place"]["source_ids"]
                    if geography["census_place"]["availability_status"] == "verified"
                    else []
                ),
            },
            "nearest_airport": _pending_transport("airport"),
            "nearest_intercity_rail": _pending_transport("intercity_rail"),
            "public_transit_availability": {
                "value": None,
                "source_ids": [],
                "availability_status": "deferred",
                "null_reason": "uniform_official_transit_agency_intake_not_available",
            },
        }
        validate_transport_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_transport_record(record: Dict[str, Any]) -> None:
    if record.get("availability_status") not in {"partial", "verified", "deferred"}:
        fail("Transport availability status is invalid")
    towns = record.get("nearest_towns", {})
    if towns.get("availability_status") == "verified":
        if (
            towns.get("count") != 3
            or towns.get("distance_method") != "haversine_straight_line"
            or not towns.get("source_ids")
        ):
            fail("Verified nearest-town transport context is incomplete")
    for field in ("nearest_airport", "nearest_intercity_rail"):
        item = record.get(field, {})
        if item.get("availability_status") == "verified":
            distance = item.get("distance_km")
            if (
                not isinstance(distance, (int, float))
                or distance < 0
                or not item.get("distance_method")
                or not item.get("source_ids")
            ):
                fail("Verified transport distance lacks method/source or is negative")
        elif item.get("distance_km") is not None:
            fail("Unverified transport distance cannot carry a value")
