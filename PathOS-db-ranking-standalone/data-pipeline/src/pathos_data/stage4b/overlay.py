"""Build and validate the Stage 4B verified enrichment overlay."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import fail


def _overlay_record(
    university: Dict[str, Any],
    *,
    field: str,
    value: Any,
    unit: Any,
    scope: str,
    reference_year: Any,
    source_ids: List[str],
    geography_id: Any = None,
    warnings: Any = None,
) -> Dict[str, Any]:
    return {
        "record_id": f"{university['candidate_id']}:{field}:{scope}",
        "university_id": university["candidate_id"],
        "canonical_id": university["canonical_id"],
        "field": field,
        "value": value,
        "unit": unit,
        "scope": scope,
        "reference_year": reference_year,
        "source_ids": source_ids,
        "verification_status": "verified",
        "confidence": "high",
        "geography_id": geography_id,
        "warnings": warnings or [],
        "derived": False,
    }


def build_verified_overlay(
    school_profiles: Iterable[Dict[str, Any]],
    admissions: Iterable[Dict[str, Any]],
    geography: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    admissions_by_id = {row["candidate_id"]: row for row in admissions}
    geography_by_id = {row["candidate_id"]: row for row in geography}
    for profile in school_profiles:
        candidate_id = profile["candidate_id"]
        school_fields = {
            "school_type": profile["school_type"],
            "public_private_control": profile["public_private_control"],
            "undergraduate_enrollment": profile["enrollment"]["undergraduate"],
            "campus_setting": profile["campus_setting"],
        }
        for field, metric in school_fields.items():
            if metric.get("verification_status") != "verified":
                continue
            output.append(
                _overlay_record(
                    profile,
                    field=field,
                    value=metric["value"],
                    unit=metric["unit"],
                    scope=metric["scope"],
                    reference_year=metric["reference_year"],
                    source_ids=metric["source_ids"],
                    warnings=metric.get("warnings"),
                )
            )
        admission = admissions_by_id[candidate_id]
        for field in ("acceptance_rate", "graduation_rate", "retention_rate"):
            metric = admission[field]
            if metric.get("verification_status") == "verified":
                output.append(
                    _overlay_record(
                        admission,
                        field=field,
                        value=metric["value"],
                        unit=metric["unit"],
                        scope=metric["scope"],
                        reference_year=metric["reference_year"],
                        source_ids=metric["source_ids"],
                        warnings=metric.get("warnings"),
                    )
                )
        for field in ("sat", "act"):
            metric = admission[field]
            if metric.get("availability_status") == "verified":
                output.append(
                    _overlay_record(
                        admission,
                        field=field,
                        value={
                            key: value
                            for key, value in metric.items()
                            if key
                            not in {
                                "source_ids",
                                "warnings",
                                "null_reason",
                                "availability_status",
                            }
                        },
                        unit=metric["unit"],
                        scope=metric["reporting_population"],
                        reference_year=metric["reference_year"],
                        source_ids=metric["source_ids"],
                        warnings=metric.get("warnings"),
                    )
                )
        geo = geography_by_id[candidate_id]
        for field, key in (
            ("county_geoid", "county"),
            ("census_place_geoid", "census_place"),
            ("cbsa_geoid", "cbsa"),
        ):
            metric = geo[key]
            if metric.get("availability_status") == "verified":
                output.append(
                    _overlay_record(
                        geo,
                        field=field,
                        value=metric["geoid"],
                        unit="geoid",
                        scope=metric["geography_type"],
                        reference_year=metric["reference_year"],
                        source_ids=metric["source_ids"],
                        geography_id=metric["geoid"],
                    )
                )
    return sorted(
        output, key=lambda row: (row["university_id"], row["field"], row["scope"])
    )


def validate_verified_overlay(
    records: Iterable[Dict[str, Any]], sources: Iterable[Dict[str, Any]]
) -> None:
    allowed_sources = {
        row["source_id"]
        for row in sources
        if row.get("availability_status") == "verified"
    }
    keys = set()
    for record in records:
        key = (
            record.get("university_id"),
            record.get("field"),
            record.get("scope"),
        )
        if key in keys:
            fail("Stage 4B verified overlay contains a duplicate field/scope")
        keys.add(key)
        if (
            record.get("verification_status") != "verified"
            or record.get("value") is None
            or not record.get("scope")
            or record.get("reference_year") is None
            or not record.get("unit")
            or record.get("derived") is not False
        ):
            fail("Stage 4B verified overlay record is incomplete")
        source_ids = record.get("source_ids")
        if (
            not isinstance(source_ids, list)
            or not source_ids
            or not set(source_ids).issubset(allowed_sources)
        ):
            fail("Stage 4B verified overlay references a disallowed source")
