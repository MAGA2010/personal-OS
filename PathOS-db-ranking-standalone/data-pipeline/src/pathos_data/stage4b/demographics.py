"""Represent Census demographic intake with strict population-definition semantics."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import fail


ACS_DEFERRED_SOURCE_ID = "source_stage4b_acs5_2023_intake_deferred"


def _deferred_metric(
    *,
    definition: str,
    geography_type: str,
    geography_id: str,
    unit: str,
) -> Dict[str, Any]:
    return {
        "value": None,
        "unit": unit,
        "numerator": None,
        "denominator": None,
        "reference_year": 2023,
        "estimate_type": "ACS_5_year_estimate",
        "margin_of_error": None,
        "geography_type": geography_type,
        "geography_id": geography_id,
        "population_definition": definition,
        "source_ids": [ACS_DEFERRED_SOURCE_ID],
        "availability_status": "deferred",
        "null_reason": "official_acs_api_requires_unavailable_credential",
    }


def build_demographic_metrics(
    geography_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    output = []
    for geography in geography_rows:
        primary = geography["primary_region_for_map"]
        gtype = primary["geography_type"]
        geoid = primary["geography_id"]
        metrics = {
            "total_population": _deferred_metric(
                definition="total_resident_population",
                geography_type=gtype,
                geography_id=geoid,
                unit="people",
            ),
            "asian_population_ratio": _deferred_metric(
                definition="asian_alone_resident_population",
                geography_type=gtype,
                geography_id=geoid,
                unit="ratio",
            ),
            "chinese_population_ratio": _deferred_metric(
                definition="chinese_alone_or_in_any_combination_resident_population",
                geography_type=gtype,
                geography_id=geoid,
                unit="ratio",
            ),
            "poverty_rate": _deferred_metric(
                definition="population_for_whom_poverty_status_is_determined",
                geography_type=gtype,
                geography_id=geoid,
                unit="ratio",
            ),
        }
        record = {
            "candidate_id": geography["candidate_id"],
            "canonical_id": geography["canonical_id"],
            "university_display_name": geography["university_display_name"],
            "geography_id": geoid,
            "geography_type": gtype,
            "metrics": metrics,
        }
        validate_demographic_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_demographic_record(record: Dict[str, Any]) -> None:
    metrics = record.get("metrics", {})
    asian = metrics.get("asian_population_ratio", {})
    chinese = metrics.get("chinese_population_ratio", {})
    if asian.get("population_definition") == chinese.get("population_definition"):
        fail("Asian and Chinese population definitions cannot be interchangeable")
    for name, metric in metrics.items():
        if metric.get("geography_type") not in {"place", "county"}:
            fail("Regional demographic metric has invalid geography scope")
        status = metric.get("availability_status")
        if status not in {"verified", "partial", "pending", "deferred", "unavailable"}:
            fail("Regional demographic availability status is invalid")
        if status == "verified":
            value = metric.get("value")
            if value is None or not metric.get("source_ids"):
                fail("Verified demographic metric lacks value/source")
            if metric.get("unit") == "ratio":
                numerator = metric.get("numerator")
                denominator = metric.get("denominator")
                if denominator in (None, 0) or numerator is None:
                    fail("Verified demographic ratio lacks numerator/denominator")
                if abs(value - numerator / denominator) > 1e-9:
                    fail("Demographic ratio does not match numerator/denominator")
                if not (0 <= value <= 1):
                    fail("Demographic ratio must be between zero and one")
