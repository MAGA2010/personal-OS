"""Represent official housing/income attempts without inventing a cost index."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import fail
from .demographics import ACS_DEFERRED_SOURCE_ID


def _deferred(
    *,
    definition: str,
    geography_type: str,
    geography_id: str,
    unit: str,
) -> Dict[str, Any]:
    return {
        "value": None,
        "unit": unit,
        "metric_definition": definition,
        "geography_type": geography_type,
        "geography_id": geography_id,
        "reference_year": 2023,
        "estimate_type": "ACS_5_year_estimate",
        "margin_of_error": None,
        "value_source": "estimate",
        "source_ids": [ACS_DEFERRED_SOURCE_ID],
        "availability_status": "deferred",
        "null_reason": "official_acs_api_requires_unavailable_credential",
    }


def build_housing_income_metrics(
    geography_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    output = []
    for geography in geography_rows:
        primary = geography["primary_region_for_map"]
        gtype = primary["geography_type"]
        geoid = primary["geography_id"]
        record = {
            "candidate_id": geography["candidate_id"],
            "canonical_id": geography["canonical_id"],
            "university_display_name": geography["university_display_name"],
            "geography_id": geoid,
            "geography_type": gtype,
            "metrics": {
                "median_household_income": _deferred(
                    definition="median_household_income",
                    geography_type=gtype,
                    geography_id=geoid,
                    unit="usd_current_year",
                ),
                "median_gross_rent": _deferred(
                    definition="median_gross_rent",
                    geography_type=gtype,
                    geography_id=geoid,
                    unit="usd_per_month",
                ),
                "population_density": _deferred(
                    definition="resident_population_density",
                    geography_type=gtype,
                    geography_id=geoid,
                    unit="people_per_square_mile",
                ),
            },
        }
        validate_housing_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_housing_record(record: Dict[str, Any]) -> None:
    for name, metric in record.get("metrics", {}).items():
        if metric.get("geography_type") not in {"place", "county"}:
            fail("Housing/income metric has invalid geography scope")
        if name == "median_gross_rent" and metric.get("metric_definition") != "median_gross_rent":
            fail("Rent metric must preserve median-gross-rent semantics")
        if name == "population_density" and metric.get("unit") != "people_per_square_mile":
            fail("Population density unit must be people per square mile")
        if metric.get("availability_status") == "verified":
            if metric.get("value") is None or not metric.get("source_ids"):
                fail("Verified housing metric lacks value/source")
            if metric.get("value_source") == "margin_of_error":
                fail("Margin of error cannot be used as a metric value")
