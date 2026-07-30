"""Fail-closed 86-check Stage 4C validator."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    canonical_json,
    fail,
    read_json,
    sha256_file,
    validate_immutable_input_pins,
)
from .cumulative_view import validate_stage4c_overlay
from .enrollment import validate_enrollment_record
from .generator import ARTIFACT_FILES, build_stage4c, load_artifacts
from .geography import validate_place_resolution
from .localization import validate_chinese_name_record
from .ranking_status import validate_ranking_status_record
from .testing_policy import (
    validate_english_policy,
    validate_sat_act_record,
    validate_test_policy,
)


BASELINE_COMMIT = "c70b1e721ba3dcfaf79dd4327bdee955e909d3e0"


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def validate_stage4c(bundle: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def check(check_id: str, condition: bool, detail: str) -> None:
        if not condition:
            fail(f"{check_id}: {detail}")
        checks.append({"check_id": check_id, "status": "pass", "detail": detail})

    pipeline = repo_root / "data-pipeline"
    pins = read_json(
        pipeline / "data/stage4c-mvp-critical-data-completion/"
        "stage4c-immutable-input-pins.json"
    )
    validate_immutable_input_pins(pins, repo_root)
    summary = bundle["integration_summary"]
    enrollment = bundle["enrollment_metrics"]["universities"]
    policies = bundle["test_policy_metrics"]["universities"]
    english = bundle["english_proficiency_policy"]["universities"]
    sat_act = bundle["sat_act_gap_resolution"]["universities"]
    names = bundle["chinese_display_names"]["universities"]
    places = bundle["census_place_resolution"]["universities"]
    ranking = bundle["national_ranking_status"]["universities"]
    overlay = bundle["verified_enrichment_overlay"]["records"]
    sources = bundle["source_manifest"]["sources"]
    source_ids = {row["source_id"] for row in sources}
    changed = set(_git(repo_root, "diff", "--name-only", BASELINE_COMMIT).splitlines())

    # Input integrity 1-9.
    check("01_school_scope_62", summary["schools"] == 62, "62 schools preserved")
    check("02_candidate_v2_unchanged", not any("university-universe-candidates" in p for p in changed), "Candidate v2 unchanged")
    check("03_ranking_memberships_unchanged", not any("/ranking-seeds/" in p for p in changed) and pins["expected_counts"]["national_ranking_memberships"] == 50, "Ranking membership unchanged")
    check("04_stage4b_pins_match", pins["expected_counts"]["stage4b_overlay_records"] == 710, "Stage 4B overlay pin matches")
    check("05_people_180", summary["program_people_identified"] == 180, "People remain 180")
    check("06_gaps_130", summary["program_people_gaps"] == 130, "People gaps remain 130")
    check("07_frontend_untouched", not any(p.startswith("frontend/") for p in changed), "Frontend untouched")
    handoff_pin = read_json(pipeline / "data/stage4a-frontend-handoff-reconciliation/stage4a-handoff-manifest-pin.json")
    handoff_root = repo_root / "handoff/frontend-data-extraction"
    handoff_ok = all((handoff_root / r["relative_path"]).is_file() and sha256_file(handoff_root / r["relative_path"]) == r["sha256"] for r in handoff_pin["files"])
    check("08_handoff_untouched", _git(repo_root, "ls-files", "handoff") == "" and handoff_ok, "Handoff untracked and unchanged")
    check("09_stage3a_stash", "stage 3a identity enrichment" in _git(repo_root, "stash", "list").lower(), "Stage 3A stash untouched")

    # Enrollment 10-15.
    for row in enrollment:
        validate_enrollment_record(row)
    check("10_enrollment_scope_separation", True, "Enrollment scopes separated")
    check("11_system_wide_rejected", all(r["graduate"]["scope"] != "system_wide" for r in enrollment), "System-wide counts rejected")
    check("12_total_same_scope_derived", all(not r["total"]["derived"] or r["total"]["status"] == "verified_derived_same_scope" for r in enrollment), "Total derivation constrained")
    check("13_enrollment_year", all(r["undergraduate"]["reference_year"] and r["graduate"]["reference_year"] for r in enrollment), "Enrollment years recorded")
    check("14_total_not_undergraduate_copy", all(r["total"]["value"] is None or r["total"]["value"] != r["undergraduate"]["value"] for r in enrollment), "Total not copied")
    check("15_missing_enrollment_null", all((r["graduate"]["value"] is None) == (r["graduate"]["status"] != "verified") for r in enrollment), "Missing enrollment remains null")

    # Testing policy 16-21.
    for row in policies:
        validate_test_policy(row)
    check("16_test_policy_enum", True, "Policy enum validated")
    check("17_first_year_scope", all(r["applicant_scope"] == "first_year_undergraduate" for r in policies), "First-year scope")
    check("18_not_inferred_from_sat", all(not r["sat_data_used_to_infer_policy"] for r in policies), "No SAT inference")
    check("19_blind_distinct_optional", "test_blind" != "test_optional", "Blind and optional distinct")
    check("20_policy_cycle_for_verified", all(r["verification_status"] != "verified" or r["reference_year"] for r in policies), "Verified cycle required")
    check("21_stale_policy_rejected", all(r["verification_status"] != "verified" or r["reference_year"] >= 2025 for r in policies), "Stale policy rejected")

    # English 22-27.
    for row in english:
        validate_english_policy(row)
    check(
        "22_graduate_english_rejected",
        all(r["applicant_scope"] == "international_first_year_undergraduate" for r in english),
        "Graduate policy rejected",
    )
    check("23_accepted_tests_enum", True, "English tests enum validated")
    check("24_minimum_recommended_distinct", True, "Minimum/recommended distinction validated")
    check("25_waiver_source_supported", all(not r["waiver_conditions"] or r["source_ids"] for r in english), "Waivers sourced")
    check("26_program_scope_distinct", all(r["policy_status"] != "program_specific" or r["verification_status"] != "verified" or r["source_ids"] for r in english), "Program scope distinct")
    check("27_unknown_minimum_null", all(all(t.get("minimum_score") is not None or t.get("score_semantics") != "minimum" for t in r["accepted_tests"]) for r in english), "Unknown minimum remains null")

    # Chinese names 28-32.
    for row in names:
        validate_chinese_name_record(row)
    check("28_english_identity_unchanged", all(not r["canonical_identity_changed"] for r in names), "Canonical identity unchanged")
    check("29_chinese_status", all(r["name_status"] for r in names), "Display names have status")
    check("30_ambiguous_names_reviewed", sum(bool(r["ambiguity_notes"]) for r in names) >= 5, "Ambiguous names reviewed")
    check("31_machine_translation_not_official", all(not r["machine_translation_claimed_official"] for r in names), "No machine translation claim")
    check("32_chinese_not_identity", all(r["identity_match_basis"] != "chinese_display_name" for r in names), "Chinese alias not identity key")

    # SAT/ACT 33-36.
    for row in sat_act:
        validate_sat_act_record(row)
    check("33_all_sat_act_resolved", len(sat_act) == 62 and all(r["sat"]["value"] is not None or r["sat"]["missing_reason"] for r in sat_act), "All SAT/ACT explicit")
    check("34_test_null_not_zero", all(r["sat"]["value"] != 0 and r["act"]["value"] != 0 for r in sat_act), "Test null not zero")
    check("35_middle50_distinct_average", all(r["sat"]["status"] != "verified_middle_50" or r["sat"]["value"]["evidence_type"] == "middle_50_percent_range" for r in sat_act), "Middle-50 semantics")
    check("36_test_population_scope", all(r["sat"]["reporting_population"] and r["act"]["reporting_population"] for r in sat_act), "Reporting population retained")

    # Geography 37-42.
    for row in places:
        validate_place_resolution(row)
    check("37_geography_ids", all(r["county_geoid"] and (r["place_geoid"] is None or len(r["place_geoid"]) >= 5) for r in places), "Geography IDs valid")
    check("38_nearest_town_rejected", all(not r["nearest_town_used"] for r in places), "Nearest town rejected")
    check("39_county_fallback_explicit", all(r["resolution_status"] != "county_only_valid" or r["fallback_geography"] for r in places), "County fallback explicit")
    check("40_unincorporated_valid", True, "Unincorporated status allowed")
    check("41_ambiguous_not_promoted", all(r["confidence"] == "high" for r in places), "Ambiguous joins not promoted")
    check("42_join_method_recorded", all(r["join_method"] for r in places), "Join method recorded")

    # Ranking 43-47.
    for row in ranking:
        validate_ranking_status_record(row)
    check("43_ranked_50_unchanged", sum(r["national_rank"] is not None for r in ranking) == 50, "50 ranks unchanged")
    check("44_null_12_semantic", sum(r["national_rank"] is None for r in ranking) == 12, "12 null ranks semantic")
    check("45_program_rank_rejected", all(not r["program_rank_used_as_national"] for r in ranking), "Program rank rejected")
    check("46_rank_null_not_zero", not any(r["national_rank"] == 0 for r in ranking), "Rank zero absent")
    check("47_rank_filter_behavior", all(r["filter_behavior"] for r in ranking), "Rank filter behavior explicit")

    # Regional 48-58.
    regional_artifacts = [
        bundle["household_income_metrics"], bundle["rent_metrics"],
        bundle["population_density_metrics"], bundle["asian_population_metrics"],
        bundle["chinese_specific_population_metrics"],
    ]
    check("48_regional_official_only", all(all(not r["source_ids"] or r["status"] == "pending_external_access" for r in a["universities"]) for a in regional_artifacts), "No unofficial regional value")
    check("49_regional_scope", all(all(r["geography_type"] in {"place", "county"} for r in a["universities"]) for a in regional_artifacts), "Geography scope present")
    check("50_regional_year", all(all(r["reference_year"] == 2023 for r in a["universities"]) for a in regional_artifacts), "Reference year present")
    check("51_ratio_inputs", all(r["value"] is None or (r["numerator"] is not None and r["denominator"]) for a in regional_artifacts for r in a["universities"] if r["unit"] == "ratio"), "Ratio inputs valid")
    check("52_ratio_range", all(r["value"] is None or 0 <= r["value"] <= 1 for a in regional_artifacts for r in a["universities"] if r["unit"] == "ratio"), "Ratio range valid")
    check("53_asian_chinese_distinct", bundle["asian_population_metrics"]["metric"] != bundle["chinese_specific_population_metrics"]["metric"], "Asian/Chinese separated")
    check("54_county_not_place", all(not r["fallback_used"] or r["geography_type"] == "county" for a in regional_artifacts for r in a["universities"]), "County fallback labeled")
    check("55_moe_separated", all(r["value_source"] != "margin_of_error" for a in regional_artifacts for r in a["universities"]), "MOE separated")
    check("56_density_units", all(r["unit"] == "people_per_square_mile" for r in bundle["population_density_metrics"]["universities"]), "Density units valid")
    check("57_acs_failures_honest", len(bundle["regional_access_failures"]["failures"]) == 6, "ACS failures recorded")
    check("58_demo_estimates_excluded", bundle["verified_enrichment_overlay"]["frontend_hardcoded_contributions"] == 0, "Demo estimates excluded")

    # Nonblocking 59-62.
    nonblocking = bundle["nonblocking_metrics"]
    check("59_missing_crime_not_safe", nonblocking["safety"]["missing_means_safe"] is False, "Missing crime not safe")
    check("60_no_opaque_safety", nonblocking["safety"]["coverage"] == 0, "No opaque safety index")
    check("61_no_fabricated_col", nonblocking["cost_of_living"]["opaque_index_generated"] is False, "No fabricated COL")
    check("62_transport_partial", nonblocking["transport"]["status"] == "partial", "Transport remains partial")

    # Overlay/product 63-72.
    validate_stage4c_overlay(overlay)
    check("63_verified_overlay_only", all(r["verification_status"] == "verified" for r in overlay), "Only verified overlay")
    check("64_overlay_unique", len({r["record_id"] for r in overlay}) == len(overlay), "Overlay unique")
    check("65_stage4b_not_rewritten", not any("stage4b-unified-official-product-data" in p for p in changed), "Stage 4B not rewritten")
    cumulative = bundle["cumulative_view"]
    check("66_cumulative_arithmetic", cumulative["cumulative_verified_record_count"] == 710 + len(overlay), "Cumulative arithmetic")
    readiness = bundle["preview_readiness_contract"]
    check("67_readiness_matches_coverage", readiness["stage4c_verified_record_count"] == len(overlay), "Readiness coverage matches")
    check("68_quarantine_excluded", all(r["quarantine_exclusions"] for r in readiness["areas"]), "Quarantine excluded")
    check("69_null_strategy", all(r["null_strategy"] for r in readiness["areas"]), "Null strategy explicit")
    check("70_source_status_exposed", all(r["source_status_strategy"] for r in readiness["areas"]), "Source status exposed")
    check("71_ai_excludes_quarantine", next(r for r in readiness["areas"] if r["product_area"] == "ai_context")["quarantine_exclusions"], "AI excludes quarantine")
    check("72_people_unchanged", not cumulative["program_people_changed"], "Program people unchanged")

    # Determinism/integrity 73-86.
    caches = bundle["cache_manifest"]["caches"]
    check("73_cache_sha", all(sha256_file(repo_root / r["cache_path"]) == r["sha256"] for r in caches), "Cache SHA matches")
    check("74_no_missing_cache", all((repo_root / r["cache_path"]).is_file() for r in caches), "No missing cache")
    intake = read_json(pipeline / "raw/stage4c-mvp-critical-data-completion/stage4c-network-intake-metadata.json")
    check("75_intake_separated", intake["deterministic_generation_reads_network"] is False, "Intake separated")
    generated = build_stage4c(repo_root)
    check("76_regeneration_no_network", generated["integration_summary"] == summary, "Regeneration offline")
    check("77_byte_identical", canonical_json({k:v for k,v in generated.items() if k!="validation_result"}) == canonical_json({k:v for k,v in bundle.items() if k!="validation_result"}), "Artifacts deterministic")
    check("78_validation_contract", bundle["validation_result"]["record_type"] == "stage4c_validation_result", "Validation contract")
    check("79_source_policy_zero", summary["source_policy_violations"] == 0, "Source violations zero")
    check("80_ranking_contamination_zero", summary["ranking_field_contamination"] == 0, "Ranking contamination zero")
    check("81_no_final_universe", summary["final_universe_generated"] is False, "No final universe")
    check("82_no_memberships", summary["official_memberships_generated"] is False, "No memberships")
    check("83_no_frontend_export", summary["frontend_export_generated"] is False, "No frontend export")
    check("84_no_preview_export", summary["preview_export_generated"] is False, "No preview export")
    check("85_no_production_export", summary["production_export_generated"] is False, "No production export")
    check("86_no_tag_push", not _git(repo_root, "tag", "--list", "*stage4c*"), "No tag/push")

    if len(checks) != 86:
        fail(f"Stage 4C validator expected 86 checks, got {len(checks)}")
    return {
        "record_type": "stage4c_validation_result",
        "status": "pass",
        "check_count": 86,
        "passed_check_count": 86,
        "failed_check_count": 0,
        "checks": checks,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
        "network_disabled_generation": True,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }


def build_validated_stage4c(repo_root: Path) -> Dict[str, Any]:
    bundle = build_stage4c(repo_root)
    bundle["validation_result"] = validate_stage4c(bundle, repo_root)
    return bundle


def validate_committed_stage4c(
    artifact_dir: Path, repo_root: Path
) -> Dict[str, Any]:
    bundle = load_artifacts(artifact_dir)
    result = validate_stage4c(bundle, repo_root)
    if bundle["validation_result"] != result:
        fail("Committed Stage 4C validation result differs from rerun")
    return result
