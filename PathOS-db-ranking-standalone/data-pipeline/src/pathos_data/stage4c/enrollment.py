"""Graduate and total enrollment completion from frozen College Scorecard fields."""

from __future__ import annotations

from typing import Any, Dict, List

from pathos_data.stage4b.source_intake import parse_int

from .config import fail


REFERENCE_YEAR = 2019
SOURCE_ID = "source_stage4b_college_scorecard_2025_05_19"


def build_enrollment_metrics(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    output = []
    for source in context["official_rows"]:
        candidate_id = source["candidate_id"]
        scorecard = source["scorecard"]
        undergraduate = parse_int(scorecard.get("UGDS"))
        graduate = parse_int(scorecard.get("GRADS"))
        graduate_status = "verified" if graduate is not None else "not_reported"
        total = undergraduate + graduate if graduate is not None else None
        total_status = "verified_derived_same_scope" if total is not None else "partial"
        row = {
            "candidate_id": candidate_id,
            "canonical_id": source["canonical_id"],
            "university_display_name": source["university_display_name"],
            "unitid": source["unitid"],
            "undergraduate": {
                "value": undergraduate,
                "status": "verified",
                "scope": "undergraduate_certificate_or_degree_seeking",
                "reference_year": REFERENCE_YEAR,
                "reporting_period": "fall",
                "source_ids": [SOURCE_ID],
                "supersedes_stage4b": False,
            },
            "graduate": {
                "value": graduate,
                "status": graduate_status,
                "scope": "graduate_students",
                "reference_year": REFERENCE_YEAR,
                "reporting_period": "fall",
                "source_ids": [SOURCE_ID] if graduate is not None else [],
                "null_reason": None if graduate is not None else "official_grads_not_reported",
            },
            "total": {
                "value": total,
                "status": total_status,
                "scope": "undergraduate_degree_seeking_plus_graduate_students",
                "reference_year": REFERENCE_YEAR,
                "reporting_period": "fall",
                "source_ids": [SOURCE_ID] if total is not None else [],
                "derived": total is not None,
                "formula": "UGDS + GRADS" if total is not None else None,
                "derivation": {
                    "undergraduate_reference_year": REFERENCE_YEAR,
                    "graduate_reference_year": REFERENCE_YEAR,
                    "same_dataset_release": True,
                    "inputs": ["UGDS", "GRADS"],
                },
                "null_reason": None if total is not None else "graduate_component_not_reported",
            },
            "warnings": [
                "reference year follows frozen Scorecard cohort map; values are not current-cycle counts"
            ],
        }
        validate_enrollment_record(row)
        output.append(row)
    return sorted(output, key=lambda row: row["candidate_id"])


def validate_enrollment_record(row: Dict[str, Any]) -> None:
    undergraduate, graduate, total = (
        row["undergraduate"], row["graduate"], row["total"]
    )
    if undergraduate["scope"] == graduate["scope"]:
        fail("Undergraduate and graduate enrollment scopes are conflated")
    if graduate["scope"] == "system_wide":
        fail("System-wide enrollment cannot enter a campus record")
    if graduate["value"] is None and graduate["status"] not in {
        "not_reported", "pending", "scope_ambiguous",
    }:
        fail("Missing graduate enrollment lacks an explicit status")
    if total["derived"]:
        derivation = total["derivation"]
        if (
            derivation["undergraduate_reference_year"]
            != derivation["graduate_reference_year"]
            or not derivation["same_dataset_release"]
            or total["value"] != undergraduate["value"] + graduate["value"]
        ):
            fail("Total enrollment derivation is not same-scope/same-year")
    if total["value"] == undergraduate["value"]:
        fail("Total enrollment cannot silently copy undergraduate enrollment")
