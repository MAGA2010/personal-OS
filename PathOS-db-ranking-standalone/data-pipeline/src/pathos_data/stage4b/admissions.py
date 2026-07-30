"""Build official admissions/result metrics and explicit test-policy gaps."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .config import fail
from .source_intake import (
    SCORECARD_RELEASE_YEAR,
    SCORECARD_SOURCE_ID,
    parse_float,
    parse_int,
)


TOEFL_POLICY_ENUM = {
    "required",
    "conditionally_required",
    "waiver_available",
    "not_required",
    "program_specific",
    "not_found",
}


def _ratio(
    value: Any,
    *,
    scope: str,
    source_field: str,
    extra: Any = None,
) -> Dict[str, Any]:
    return {
        "value": value,
        "unit": "ratio",
        "scope": scope,
        "reference_year": SCORECARD_RELEASE_YEAR,
        "reference_year_semantics": "dataset_release_year",
        "source_ids": [SCORECARD_SOURCE_ID],
        "source_field": source_field,
        "verification_status": "verified" if value is not None else "unavailable",
        "null_reason": None if value is not None else "official_field_not_available",
        "warnings": [
            "uniform source-variable cohort year is not available in the "
            "frozen 2025 release metadata"
        ],
        **(extra or {}),
    }


def _score_range(
    scorecard: Dict[str, str],
    prefix: str,
    evidence_type: str,
) -> Dict[str, Any]:
    if prefix == "SAT":
        reading_25 = parse_int(scorecard.get("SATVR25"))
        reading_75 = parse_int(scorecard.get("SATVR75"))
        math_25 = parse_int(scorecard.get("SATMT25"))
        math_75 = parse_int(scorecard.get("SATMT75"))
        available = all(
            value is not None
            for value in (reading_25, reading_75, math_25, math_75)
        )
        return {
            "availability_status": "verified" if available else "unavailable",
            "evidence_type": evidence_type,
            "reporting_population": "enrolled_students_who_submitted_scores",
            "reading_writing": {
                "percentile_25": reading_25,
                "percentile_75": reading_75,
            },
            "math": {
                "percentile_25": math_25,
                "percentile_75": math_75,
            },
            "average": parse_int(scorecard.get("SAT_AVG")),
            "unit": "score",
            "reference_year": SCORECARD_RELEASE_YEAR,
            "reference_year_semantics": "dataset_release_year",
            "source_ids": [SCORECARD_SOURCE_ID],
            "null_reason": None if available else "official_sat_range_not_available",
            "warnings": [
                "score reporting does not establish a current test-optional policy"
            ],
        }
    p25 = parse_int(scorecard.get("ACTCM25"))
    p75 = parse_int(scorecard.get("ACTCM75"))
    available = p25 is not None and p75 is not None
    return {
        "availability_status": "verified" if available else "unavailable",
        "evidence_type": evidence_type,
        "reporting_population": "enrolled_students_who_submitted_scores",
        "composite": {"percentile_25": p25, "percentile_75": p75},
        "unit": "score",
        "reference_year": SCORECARD_RELEASE_YEAR,
        "reference_year_semantics": "dataset_release_year",
        "source_ids": [SCORECARD_SOURCE_ID],
        "null_reason": None if available else "official_act_range_not_available",
    }


def build_admissions_metrics(
    official_rows: Iterable[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    admissions: List[Dict[str, Any]] = []
    policies: List[Dict[str, Any]] = []
    for row in official_rows:
        scorecard = row["scorecard"]
        admission = {
            "candidate_id": row["candidate_id"],
            "canonical_id": row["canonical_id"],
            "university_display_name": row["university_display_name"],
            "unitid": row["unitid"],
            "acceptance_rate": _ratio(
                parse_float(scorecard.get("ADM_RATE")),
                scope="institution_undergraduate_admissions",
                source_field="ADM_RATE",
                extra={"numerator": None, "denominator": None},
            ),
            "graduation_rate": _ratio(
                parse_float(scorecard.get("C150_4")),
                scope="institution",
                source_field="C150_4",
                extra={
                    "time_horizon": "150_percent_of_normal_time",
                    "cohort_scope": "first_time_full_time_degree_seeking",
                    "credential_scope": "four_year_institution",
                },
            ),
            "retention_rate": _ratio(
                parse_float(scorecard.get("RET_FT4")),
                scope="four_year_institution",
                source_field="RET_FT4",
                extra={
                    "time_horizon": "one_year",
                    "cohort_scope": "first_time_full_time_bachelors_seeking",
                },
            ),
            "sat": _score_range(
                scorecard, "SAT", "middle_50_percent_range"
            ),
            "act": _score_range(
                scorecard, "ACT", "middle_50_percent_range"
            ),
            "evidence_anchors": {
                "acceptance_rate": (
                    f"UNITID={row['unitid']}; ADM_RATE={scorecard.get('ADM_RATE')}"
                ),
                "graduation_rate": (
                    f"UNITID={row['unitid']}; C150_4={scorecard.get('C150_4')}"
                ),
                "retention_rate": (
                    f"UNITID={row['unitid']}; RET_FT4={scorecard.get('RET_FT4')}"
                ),
                "sat": (
                    f"UNITID={row['unitid']}; SATVR25={scorecard.get('SATVR25')}; "
                    f"SATVR75={scorecard.get('SATVR75')}; "
                    f"SATMT25={scorecard.get('SATMT25')}; "
                    f"SATMT75={scorecard.get('SATMT75')}"
                ),
                "act": (
                    f"UNITID={row['unitid']}; ACTCM25={scorecard.get('ACTCM25')}; "
                    f"ACTCM75={scorecard.get('ACTCM75')}"
                ),
            },
        }
        policy = {
            "candidate_id": row["candidate_id"],
            "canonical_id": row["canonical_id"],
            "university_display_name": row["university_display_name"],
            "test_optional_policy": {
                "policy_status": "not_found",
                "applicant_scope": "undergraduate_first_year",
                "reference_year": None,
                "source_ids": [],
                "verification_status": "pending",
                "null_reason": "current_official_policy_review_not_completed",
            },
            "english_proficiency_policy": {
                "policy_status": "not_found",
                "minimum_score": None,
                "test_type": None,
                "applicant_scope": "undergraduate_international",
                "reference_year": None,
                "source_ids": [],
                "verification_status": "pending",
                "null_reason": "official_undergraduate_policy_review_not_completed",
            },
        }
        validate_admissions_record(admission)
        validate_test_policy_record(policy)
        admissions.append(admission)
        policies.append(policy)
    return (
        sorted(admissions, key=lambda item: item["candidate_id"]),
        sorted(policies, key=lambda item: item["candidate_id"]),
    )


def validate_admissions_record(record: Dict[str, Any]) -> None:
    acceptance = record.get("acceptance_rate", {})
    if acceptance.get("scope") != "institution_undergraduate_admissions":
        fail("Acceptance rate cannot use a program/college/early-decision scope")
    for field in ("acceptance_rate", "graduation_rate", "retention_rate"):
        metric = record.get(field, {})
        value = metric.get("value")
        if value is not None and not (0 <= value <= 1):
            fail(f"Stage 4B {field} must be a ratio from zero to one")
        if not metric.get("source_ids") or not metric.get("reference_year"):
            fail(f"Stage 4B verified {field} lacks source/year")
    graduation = record.get("graduation_rate", {})
    if (
        graduation.get("time_horizon") != "150_percent_of_normal_time"
        or graduation.get("cohort_scope")
        != "first_time_full_time_degree_seeking"
        or graduation.get("credential_scope") != "four_year_institution"
    ):
        fail("Stage 4B graduation rate semantics are incomplete")
    sat = record.get("sat", {})
    if sat.get("availability_status") == "verified":
        if sat.get("evidence_type") != "middle_50_percent_range":
            fail("SAT range must retain middle-50 semantics")
        if "minimum_score" in sat:
            fail("SAT middle-50 evidence cannot be represented as a cutoff")
    act = record.get("act", {})
    if (
        act.get("availability_status") == "verified"
        and act.get("evidence_type") != "middle_50_percent_range"
    ):
        fail("ACT range must retain middle-50 semantics")


def validate_test_policy_record(record: Dict[str, Any]) -> None:
    test_policy = record.get("test_optional_policy", {})
    if test_policy.get("policy_status") not in {
        "required",
        "optional",
        "test_blind",
        "not_found",
    }:
        fail("Stage 4B test-optional policy enum is invalid")
    english = record.get("english_proficiency_policy", {})
    if english.get("policy_status") not in TOEFL_POLICY_ENUM:
        fail("Stage 4B English-proficiency policy enum is invalid")
    if english.get("applicant_scope") != "undergraduate_international":
        fail("Stage 4B English-proficiency policy scope is invalid")
    if (
        english.get("policy_status") == "not_found"
        and english.get("minimum_score") is not None
    ):
        fail("Missing English-proficiency policy cannot carry a forced score")
