"""Build official school-profile metrics without conflating enrollment scopes."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .config import Stage4BValidationError, fail
from .source_intake import (
    IPEDS_HD_SOURCE_ID,
    IPEDS_REFERENCE_YEAR,
    SCORECARD_RELEASE_YEAR,
    SCORECARD_SOURCE_ID,
    parse_int,
)


SCHOOL_TYPE_ENUM = {
    "public",
    "private_nonprofit",
    "private_for_profit",
    "federal_service_academy",
    "special_focus",
    "unknown",
}
CONTROL_TO_TYPE = {
    1: "public",
    2: "private_nonprofit",
    3: "private_for_profit",
}
LOCALE_LABELS = {
    11: "city_large",
    12: "city_midsize",
    13: "city_small",
    21: "suburb_large",
    22: "suburb_midsize",
    23: "suburb_small",
    31: "town_fringe",
    32: "town_distant",
    33: "town_remote",
    41: "rural_fringe",
    42: "rural_distant",
    43: "rural_remote",
}


def _metric(
    value: Any,
    *,
    scope: str,
    unit: str,
    reference_year: int,
    source_ids: List[str],
    verification_status: str,
    null_reason: Any = None,
    warnings: Any = None,
) -> Dict[str, Any]:
    return {
        "value": value,
        "scope": scope,
        "unit": unit,
        "reference_year": reference_year,
        "source_ids": source_ids,
        "verification_status": verification_status,
        "null_reason": null_reason,
        "warnings": warnings or [],
    }


def build_school_profile_metrics(
    official_rows: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    output = []
    for row in official_rows:
        hd = row["ipeds_hd"]
        scorecard = row["scorecard"]
        control = parse_int(hd.get("CONTROL"))
        school_type = CONTROL_TO_TYPE.get(control, "unknown")
        undergraduate = parse_int(scorecard.get("UGDS"))
        locale_code = parse_int(hd.get("LOCALE"))
        record = {
            "candidate_id": row["candidate_id"],
            "canonical_id": row["canonical_id"],
            "university_display_name": row["university_display_name"],
            "unitid": row["unitid"],
            "school_type": _metric(
                school_type,
                scope="institution",
                unit="enum",
                reference_year=IPEDS_REFERENCE_YEAR,
                source_ids=[IPEDS_HD_SOURCE_ID],
                verification_status="verified",
            ),
            "public_private_control": _metric(
                control,
                scope="institution",
                unit="ipeds_control_code",
                reference_year=IPEDS_REFERENCE_YEAR,
                source_ids=[IPEDS_HD_SOURCE_ID],
                verification_status="verified",
            ),
            "enrollment": {
                "undergraduate": _metric(
                    undergraduate,
                    scope="undergraduate_degree_seeking",
                    unit="students",
                    reference_year=SCORECARD_RELEASE_YEAR,
                    source_ids=[SCORECARD_SOURCE_ID],
                    verification_status="verified",
                    warnings=[
                        "reference_year_is_dataset_release_year; "
                        "uniform cohort year is not published in the frozen release"
                    ],
                ),
                "graduate": _metric(
                    None,
                    scope="graduate",
                    unit="students",
                    reference_year=IPEDS_REFERENCE_YEAR,
                    source_ids=[IPEDS_HD_SOURCE_ID],
                    verification_status="deferred",
                    null_reason="official_graduate_enrollment_not_in_frozen_inputs",
                ),
                "total": _metric(
                    None,
                    scope="institution_total",
                    unit="students",
                    reference_year=IPEDS_REFERENCE_YEAR,
                    source_ids=[IPEDS_HD_SOURCE_ID],
                    verification_status="deferred",
                    null_reason="official_total_enrollment_not_in_frozen_inputs",
                ),
            },
            "campus_setting": _metric(
                LOCALE_LABELS.get(locale_code),
                scope="institution",
                unit="ipeds_locale_category",
                reference_year=IPEDS_REFERENCE_YEAR,
                source_ids=[IPEDS_HD_SOURCE_ID],
                verification_status=(
                    "verified" if locale_code in LOCALE_LABELS else "unavailable"
                ),
                null_reason=(
                    None
                    if locale_code in LOCALE_LABELS
                    else "ipeds_locale_not_available"
                ),
            ),
            "chinese_display_name": _metric(
                None,
                scope="display_alias",
                unit="text",
                reference_year=IPEDS_REFERENCE_YEAR,
                source_ids=[],
                verification_status="deferred",
                null_reason="no_reviewed_official_chinese_name_source",
            ),
            "evidence_anchors": {
                "school_type": (
                    f"UNITID={row['unitid']}; CONTROL={hd.get('CONTROL')}"
                ),
                "undergraduate_enrollment": (
                    f"UNITID={row['unitid']}; UGDS={scorecard.get('UGDS')}"
                ),
                "campus_setting": (
                    f"UNITID={row['unitid']}; LOCALE={hd.get('LOCALE')}"
                ),
            },
        }
        validate_school_profile_record(record)
        output.append(record)
    return sorted(output, key=lambda item: item["candidate_id"])


def validate_school_profile_record(record: Dict[str, Any]) -> None:
    if record.get("school_type", {}).get("value") not in SCHOOL_TYPE_ENUM:
        fail("Stage 4B school type is outside the controlled enum")
    control = record.get("public_private_control", {}).get("value")
    if control not in {1, 2, 3}:
        fail("Stage 4B public/private control must be an IPEDS control code")
    enrollment = record.get("enrollment", {})
    undergraduate = enrollment.get("undergraduate", {})
    if undergraduate.get("scope") != "undergraduate_degree_seeking":
        fail("Stage 4B undergraduate enrollment scope is invalid")
    if not isinstance(undergraduate.get("value"), int):
        fail("Stage 4B undergraduate enrollment requires a direct integer")
    graduate = enrollment.get("graduate", {})
    total = enrollment.get("total", {})
    if graduate.get("value") is not None and graduate.get("scope") != "graduate":
        fail("Stage 4B graduate enrollment scope is invalid")
    if total.get("value") is not None and total.get("scope") != "institution_total":
        fail("Stage 4B total enrollment scope is invalid")
    if total.get("value") == undergraduate.get("value") and total.get("value") is not None:
        fail("Undergraduate enrollment cannot be copied into total enrollment")
    if graduate.get("value") == undergraduate.get("value") and graduate.get("value") is not None:
        fail("Undergraduate enrollment cannot be copied into graduate enrollment")
