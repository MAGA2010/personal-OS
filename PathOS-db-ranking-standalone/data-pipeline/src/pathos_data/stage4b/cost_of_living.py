"""Cost-of-living readiness based on components rather than a fabricated index."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import fail


def build_cost_of_living_metrics(
    geography_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    output = []
    for geography in geography_rows:
        primary = geography["primary_region_for_map"]
        record = {
            "candidate_id": geography["candidate_id"],
            "canonical_id": geography["canonical_id"],
            "university_display_name": geography["university_display_name"],
            "geography_id": primary["geography_id"],
            "geography_type": primary["geography_type"],
            "component_fields": [
                "median_gross_rent",
                "median_household_income",
            ],
            "cost_of_living_index": {
                "value": None,
                "unit": "index",
                "formula": None,
                "reference_year": None,
                "source_ids": [],
                "availability_status": "deferred",
                "null_reason": (
                    "no_uniform_official_licensed_component_set_and_reference_year"
                ),
                "derived": True,
            },
            "comparison_policy": (
                "Expose verified rent and income components independently; "
                "do not substitute a synthetic total score."
            ),
        }
        validate_cost_of_living_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_cost_of_living_record(record: Dict[str, Any]) -> None:
    metric = record.get("cost_of_living_index", {})
    if metric.get("availability_status") == "verified":
        if (
            metric.get("value") is None
            or not metric.get("formula")
            or not metric.get("reference_year")
            or not metric.get("source_ids")
        ):
            fail("Verified cost-of-living index lacks formula/year/source")
    elif metric.get("value") is not None:
        fail("Deferred cost-of-living index cannot carry a value")
    if set(record.get("component_fields", [])) != {
        "median_gross_rent",
        "median_household_income",
    }:
        fail("Cost-of-living fallback must preserve rent and income components")
