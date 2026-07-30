"""Undergraduate test/English policy attempts and SAT/ACT gap semantics."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import fail


TEST_POLICY_ENUM = {
    "required", "test_optional", "test_blind", "test_flexible",
    "conditionally_required", "program_specific", "policy_transition", "not_found",
}
ENGLISH_POLICY_ENUM = {
    "required", "conditionally_required", "waiver_available", "not_required",
    "program_specific", "not_found", "pending",
}


def build_test_policies(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for source in context["official_rows"]:
        row = {
            "candidate_id": source["candidate_id"],
            "university_display_name": source["university_display_name"],
            "policy_status": "not_found",
            "applicant_scope": "first_year_undergraduate",
            "entry_terms": [],
            "international_applicants_included": None,
            "exceptions": [],
            "supersedes_previous_policy": None,
            "effective_start": None,
            "effective_end": None,
            "reference_year": None,
            "source_ids": [],
            "last_checked_at": "2026-07-24",
            "verification_status": "pending_external_access",
            "reviewed_scope": [source["official_homepage"]],
            "gap_reason": "official_admissions_policy_bulk_unavailable_and_school_page_not_frozen",
            "sat_data_used_to_infer_policy": False,
        }
        validate_test_policy(row)
        rows.append(row)
    return rows


def validate_test_policy(row: Dict[str, Any]) -> None:
    if row["policy_status"] not in TEST_POLICY_ENUM:
        fail("Invalid undergraduate testing policy status")
    if row["applicant_scope"] != "first_year_undergraduate":
        fail("Testing policy scope is not first-year undergraduate")
    if row.get("sat_data_used_to_infer_policy"):
        fail("Testing policy cannot be inferred from SAT reporting")
    if row["verification_status"] == "verified":
        if not row["source_ids"] or not row["reference_year"]:
            fail("Verified testing policy lacks source or cycle")
        if row["reference_year"] < 2025:
            fail("Stale pandemic-era policy cannot become current")


def build_english_policies(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for source in context["official_rows"]:
        row = {
            "candidate_id": source["candidate_id"],
            "university_display_name": source["university_display_name"],
            "applicant_scope": "international_first_year_undergraduate",
            "policy_status": "pending",
            "accepted_tests": [],
            "waiver_available": None,
            "waiver_conditions": [],
            "reference_cycle": None,
            "source_ids": [],
            "verification_status": "pending_external_access",
            "reviewed_scope": [source["official_homepage"]],
            "gap_reason": "official_undergraduate_english_policy_pages_not_frozen",
        }
        validate_english_policy(row)
        rows.append(row)
    return rows


def validate_english_policy(row: Dict[str, Any]) -> None:
    if row["applicant_scope"] != "international_first_year_undergraduate":
        fail("Graduate or program policy cannot enter undergraduate English policy")
    if row["policy_status"] not in ENGLISH_POLICY_ENUM:
        fail("Invalid English policy status")
    allowed_tests = {"TOEFL_iBT", "IELTS", "Duolingo", "Cambridge", "PTE", "other"}
    for test in row["accepted_tests"]:
        if test["test_type"] not in allowed_tests:
            fail("Unsupported English test type")
        if test.get("minimum_score") is None and test.get("score_semantics") == "minimum":
            fail("Unknown minimum cannot be represented as a minimum")
    if row["waiver_conditions"] and not row["source_ids"]:
        fail("Waiver conditions require source support")


def build_sat_act_resolution(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for candidate_id, admission in sorted(context["admissions_by_id"].items()):
        tests = {}
        for key in ("sat", "act"):
            source = admission[key]
            verified = source["availability_status"] == "verified"
            tests[key] = {
                "status": "verified_middle_50" if verified else "not_reported",
                "value": source if verified else None,
                "reference_year": source["reference_year"],
                "reference_year_semantics": source["reference_year_semantics"],
                "reporting_population": source["reporting_population"],
                "percentage_submitting": None,
                "source_ids": source["source_ids"],
                "missing_reason": None if verified else source["null_reason"],
                "display_label": None if verified else "Not reported",
            }
        row = {"candidate_id": candidate_id, **tests}
        validate_sat_act_record(row)
        rows.append(row)
    return rows


def validate_sat_act_record(row: Dict[str, Any]) -> None:
    allowed = {
        "verified_middle_50", "verified_percentile_range", "not_reported",
        "insufficient_reporting_sample", "test_blind_not_applicable",
        "special_focus_not_applicable", "pending_source_access", "scope_ambiguous",
    }
    for key in ("sat", "act"):
        test = row[key]
        if test["status"] not in allowed:
            fail("Invalid SAT/ACT availability status")
        if test["value"] == 0:
            fail("Missing SAT/ACT cannot be zero")
        if test["value"] is None and not test["missing_reason"]:
            fail("Missing SAT/ACT requires a reason")
        if not test["reporting_population"]:
            fail("SAT/ACT population scope is missing")
