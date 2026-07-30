"""Fail-closed crime/safety readiness without subjective safety claims."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import fail


def build_crime_safety_metrics(
    geography_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    output = []
    for geography in geography_rows:
        primary = geography["primary_region_for_map"]
        record = {
            "candidate_id": geography["candidate_id"],
            "canonical_id": geography["canonical_id"],
            "university_display_name": geography["university_display_name"],
            "raw_crime": {
                "metric": "violent_and_property_crime_rate",
                "value": None,
                "unit": "incidents_per_1000_population",
                "count": None,
                "population_denominator": None,
                "reporting_jurisdiction": None,
                "geography_type": primary["geography_type"],
                "geography_id": primary["geography_id"],
                "reference_year": None,
                "source_ids": [],
                "availability_status": "deferred",
                "null_reason": (
                    "no_uniform_official_reporting_jurisdiction_and_year_for_62_schools"
                ),
            },
            "safety_index": {
                "value": None,
                "unit": "derived_index",
                "formula": None,
                "derived": True,
                "availability_status": "deferred",
                "null_reason": "uniform_comparable_raw_crime_inputs_not_available",
                "missing_crime_is_safe": False,
            },
        }
        validate_crime_safety_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_crime_safety_record(record: Dict[str, Any]) -> None:
    raw = record.get("raw_crime", {})
    if raw.get("availability_status") == "verified":
        required = (
            raw.get("value"),
            raw.get("count"),
            raw.get("population_denominator"),
            raw.get("reporting_jurisdiction"),
            raw.get("geography_type"),
            raw.get("reference_year"),
            raw.get("source_ids"),
        )
        if any(value in (None, "", []) for value in required):
            fail("Verified crime metric lacks jurisdiction/denominator/source/year")
        expected = raw["count"] / raw["population_denominator"] * 1000
        if abs(raw["value"] - expected) > 1e-9:
            fail("Crime rate does not match count and population denominator")
    safety = record.get("safety_index", {})
    if safety.get("availability_status") == "verified":
        if raw.get("availability_status") != "verified":
            fail("Missing crime cannot imply a verified safety index")
        if not safety.get("derived") or not safety.get("formula"):
            fail("Safety index requires a transparent derived formula")
        if safety.get("missing_crime_is_safe") is not False:
            fail("Missing crime must never be interpreted as safety")
    elif safety.get("value") is not None:
        fail("Unverified safety index cannot carry a value")
