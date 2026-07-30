"""Official ACS metric model with honest pending-external-access fallbacks."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import fail
from .geography import build_census_place_resolution


METRICS = {
    "median_household_income": ("USD_2023_inflation_adjusted", "B19013_001"),
    "median_gross_rent": ("USD_per_month", "B25064_001"),
    "total_population": ("people", "B01003_001"),
    "population_density": ("people_per_square_mile", "derived_population_land_area"),
    "asian_population_ratio": ("ratio", "B02001_005/B01003_001"),
    "chinese_specific_population_ratio": ("ratio", "B02015_chinese/B01003_001"),
}


def _metric(name: str) -> Dict[str, Any]:
    unit, definition = METRICS[name]
    return {
        "value": None,
        "numerator": None,
        "denominator": None,
        "unit": unit,
        "reference_year": 2023,
        "estimate_period": "ACS_5_year",
        "margin_of_error": None,
        "source_ids": [],
        "status": "pending_external_access",
        "definition": definition,
        "value_source": None,
        "null_reason": "api_key_required_and_official_bulk_gateway_forbidden",
    }


def build_regional_metrics(
    context: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    geography = {
        row["candidate_id"]: row
        for row in build_census_place_resolution(context)
    }
    rows = []
    for candidate_id, geo in sorted(geography.items()):
        preferred_place = geo["place_geoid"]
        fallback = geo["fallback_geography"]
        row = {
            "candidate_id": candidate_id,
            "geography_id": preferred_place or fallback["geoid"],
            "geography_type": "place" if preferred_place else "county",
            "fallback_used": preferred_place is None,
            "comparability_status": (
                "preferred_place_pending_data"
                if preferred_place
                else "county_fallback_pending_data"
            ),
            "status": "pending_external_access",
            "metrics": {name: _metric(name) for name in METRICS},
        }
        validate_regional_record(row)
        rows.append(row)
    failures = [
        {
            "metric": name,
            "attempted_methods": [
                "Census ACS API 2023 5-year",
                "Census table-based summary-file bulk download",
            ],
            "failure_classifications": ["missing_api_key", "bulk_download_http_403"],
            "affected_schools": 62,
            "retry_plan": "retry official bulk/API intake outside restricted gateway",
            "status": "pending_external_access",
        }
        for name in METRICS
    ]
    return rows, failures


def validate_regional_record(row: Dict[str, Any]) -> None:
    metrics = row["metrics"]
    if (
        metrics["asian_population_ratio"]["definition"]
        == metrics["chinese_specific_population_ratio"]["definition"]
    ):
        fail("Asian and Chinese-specific metrics are conflated")
    for name, metric in metrics.items():
        value = metric["value"]
        if metric.get("value_source") == "margin_of_error":
            fail("Margin of error cannot be promoted to a metric value")
        if value is not None and metric["unit"] == "ratio" and not 0 <= value <= 1:
            fail("Regional population ratio is outside [0,1]")
        if value is not None and not metric["source_ids"]:
            fail("Verified regional metric lacks an official source")
        if metric["reference_year"] is None:
            fail("Regional metric lacks a reference year")
    if row["fallback_used"] and row["geography_type"] != "county":
        fail("County fallback geography is mislabeled")
