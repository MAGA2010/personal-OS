"""Fail-closed Stage 4B validator covering scope, provenance, semantics, and products."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .admissions import validate_admissions_record, validate_test_policy_record
from .config import (
    canonical_json,
    fail,
    read_json,
    sha256_file,
    validate_immutable_input_pins,
)
from .crime_safety import validate_crime_safety_record
from .cost_of_living import validate_cost_of_living_record
from .demographics import validate_demographic_record
from .generator import CORE_ARTIFACT_FILES, build_stage4b
from .geography import validate_geography_record
from .housing import validate_housing_record
from .overlay import validate_verified_overlay
from .product_contracts import (
    validate_ai_context_contract,
    validate_filter_contract,
    validate_marker_summary,
    validate_search_index,
)
from .school_profile import validate_school_profile_record
from .transport import validate_transport_record


BASELINE_COMMIT = "24ae71cc84c5e11aa6b0cc76392f0408d995a7be"


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_stage4b_artifacts(artifact_dir: Path) -> Dict[str, Any]:
    bundle = {}
    for key, filename in CORE_ARTIFACT_FILES.items():
        path = artifact_dir / filename
        if not path.is_file():
            fail(f"Required Stage 4B artifact is missing: {filename}")
        bundle[key] = read_json(path)
    return bundle


def validate_stage4b(bundle: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def check(check_id: str, condition: bool, detail: str) -> None:
        if not condition:
            fail(f"{check_id}: {detail}")
        checks.append({"check_id": check_id, "status": "pass", "detail": detail})

    pipeline = repo_root / "data-pipeline"
    summary = bundle["integration_summary"]
    pins = read_json(
        pipeline
        / "data/stage4b-unified-official-product-data/"
        "stage4b-immutable-input-pins.json"
    )
    validate_immutable_input_pins(pins, repo_root)
    profiles = bundle["school_profile_metrics"]["universities"]
    admissions = bundle["admissions_metrics"]["universities"]
    policies = bundle["test_policy_metrics"]["universities"]
    geography = bundle["campus_geography_crosswalk"]["universities"]
    demographics = bundle["demographic_metrics"]["universities"]
    housing = bundle["housing_income_metrics"]["universities"]
    crime = bundle["crime_safety_metrics"]["universities"]
    cost = bundle["cost_of_living_metrics"]["universities"]
    transport = bundle["transport_accessibility_metrics"]["universities"]
    overlay = bundle["verified_enrichment_overlay"]["records"]
    sources = bundle["source_manifest"]["sources"]
    caches = bundle["cache_manifest"]["caches"]
    matrix = bundle["product_data_coverage_matrix"]["fields"]
    backlog = bundle["data_collection_backlog"]["items"]
    changed = set(_git(repo_root, "diff", "--name-only", BASELINE_COMMIT).splitlines())
    forbidden_prefixes = (
        "frontend/",
        "data-pipeline/data/university-universe-candidates/",
        "data-pipeline/data/ranking-seeds/",
        "data-pipeline/artifacts/stage3",
        "data-pipeline/data/stage3",
    )

    # Input and scope (1-8).
    check("01_school_scope_62", len(profiles) == 62, "62 schools preserved")
    check(
        "02_candidate_v2_unchanged",
        pins["expected_counts"]["schools"] == 62
        and not any(
            path.startswith(forbidden_prefixes) for path in changed
        ),
        "Candidate v2 and upstream Stage artifacts have no diff",
    )
    check(
        "03_ranking_memberships_unchanged",
        pins["expected_counts"]["national_ranking_memberships"] == 50,
        "National ranking membership remains 50",
    )
    check(
        "04_people_180_of_310",
        (
            summary["program_people_total_slots"],
            summary["program_people_identified"],
            summary["program_people_source_review_not_completed"],
        )
        == (310, 180, 130),
        "Stage 3D people counts preserved",
    )
    check(
        "05_stage4a_pins_match",
        pins["expected_counts"]["stage4a_verified_contributions"] == 0,
        "Stage 4A frontend contributions remain zero",
    )
    check(
        "06_frontend_untouched",
        not any(path.startswith("frontend/") for path in changed),
        "Frontend has no diff",
    )
    handoff_pin = read_json(
        pipeline
        / "data/stage4a-frontend-handoff-reconciliation/"
        "stage4a-handoff-manifest-pin.json"
    )
    handoff_root = repo_root / "handoff/frontend-data-extraction"
    handoff_hashes_match = all(
        (handoff_root / row["relative_path"]).is_file()
        and sha256_file(handoff_root / row["relative_path"]) == row["sha256"]
        for row in handoff_pin["files"]
    )
    check(
        "07_handoff_untracked",
        _git(repo_root, "ls-files", "handoff") == "" and handoff_hashes_match,
        "External handoff remains untracked and byte-identical",
    )
    check(
        "08_stage3a_stash_untouched",
        "stage 3a identity enrichment" in _git(repo_root, "stash", "list").lower(),
        "Stage 3A stash remains present",
    )

    # Source and provenance (9-18).
    source_ids = {row["source_id"] for row in sources}
    check(
        "09_verified_fields_have_sources",
        all(row.get("source_ids") for row in overlay),
        "All verified overlay fields have sources",
    )
    check(
        "10_source_type_policy",
        all(
            row["source_type"]
            in {
                "official_federal_dataset",
                "official_federal_api",
                "verified_existing_backend_artifact",
            }
            for row in sources
        ),
        "Source publishers/types are allowed",
    )
    cache_by_id = {row["cache_id"]: row for row in caches}
    check(
        "11_cache_sha_matches",
        all(
            row["exists"]
            and sha256_file(repo_root / row["cache_path"]) == row["sha256"]
            for row in caches
        ),
        "All referenced cache/input hashes match",
    )
    check(
        "12_scope_present",
        all(row.get("scope") for row in overlay),
        "Verified fields retain scope",
    )
    check(
        "13_year_or_exemption",
        all(row.get("reference_year") is not None for row in overlay),
        "Verified fields retain reference year",
    )
    check(
        "14_units_present",
        all(row.get("unit") for row in overlay),
        "Verified fields retain units",
    )
    intake = read_json(
        pipeline
        / "raw/stage4b-unified-official-product-data/"
        "stage4b-network-intake-metadata.json"
    )
    check(
        "15_intake_generation_separated",
        intake["deterministic_generation_reads_network"] is False,
        "Network intake and deterministic generation are separated",
    )
    generated = build_stage4b(repo_root)
    check(
        "16_regeneration_has_no_network_dependency",
        generated["integration_summary"] == summary,
        "Offline regeneration reproduces integration summary",
    )
    check(
        "17_frontend_cannot_self_verify",
        bundle["verified_enrichment_overlay"]["frontend_hardcoded_contributions"]
        == 0,
        "Frontend hardcoded values contribute zero verified facts",
    )
    check(
        "18_mock_not_verified",
        not any("mock" in source_id.lower() for source_id in source_ids),
        "Mock/demo data is excluded from verified overlay",
    )

    # School/admissions metrics (19-25).
    for row in profiles:
        validate_school_profile_record(row)
    check("19_school_type_enum", True, "School type enum validated")
    check(
        "20_enrollment_scopes",
        all(
            row["enrollment"]["undergraduate"]["scope"]
            == "undergraduate_degree_seeking"
            for row in profiles
        ),
        "Enrollment scopes are not conflated",
    )
    for row in admissions:
        validate_admissions_record(row)
    check("21_acceptance_scope", True, "Acceptance scope validated")
    check("22_graduation_scope", True, "Graduation cohort/time scope validated")
    check(
        "23_sat_semantics",
        all(
            row["sat"]["availability_status"] != "verified"
            or row["sat"]["evidence_type"] == "middle_50_percent_range"
            for row in admissions
        ),
        "SAT middle-50 semantics preserved",
    )
    for row in policies:
        validate_test_policy_record(row)
    check("24_toefl_policy_model", True, "TOEFL/English policy model validated")
    check(
        "25_ranking_null_not_zero",
        all(
            row["national_rank"]["value"] != 0
            for row in bundle["marker_summary"]["universities"]
        ),
        "Missing rank is never zero",
    )

    # Geography (26-30).
    for row in geography:
        validate_geography_record(row)
    check("26_geography_ids", True, "County/place/CBSA IDs validated")
    check(
        "27_school_region_scope_isolation",
        all(
            row["primary_region_for_map"]["geography_type"] in {"place", "county"}
            for row in geography
        ),
        "School and region scopes remain separate",
    )
    check(
        "28_state_not_city",
        not any(
            row["primary_region_for_map"]["geography_type"] == "state"
            for row in geography
        ),
        "State data is not presented as city/place",
    )
    check(
        "29_join_confidence",
        all(
            row["primary_region_for_map"]["join_confidence"] == "high"
            for row in geography
        ),
        "Place/county joins retain confidence",
    )
    check(
        "30_nearest_town_not_campus_geography",
        not any(
            row["primary_region_for_map"]["join_method"] == "nearest_town"
            for row in geography
        ),
        "Nearest towns are not campus geographies",
    )

    # Demographic/housing (31-36).
    for row in demographics:
        validate_demographic_record(row)
    check("31_asian_chinese_separated", True, "Asian and Chinese definitions differ")
    check("32_ratio_denominators", True, "Verified ratio arithmetic validated")
    check(
        "33_ratio_range",
        all(
            metric["value"] is None or 0 <= metric["value"] <= 1
            for row in demographics
            for metric in row["metrics"].values()
            if metric["unit"] == "ratio"
        ),
        "Population ratios have valid range",
    )
    for row in housing:
        validate_housing_record(row)
    check("34_rent_scope", True, "Rent geography and definition validated")
    check(
        "35_density_units",
        all(
            row["metrics"]["population_density"]["unit"]
            == "people_per_square_mile"
            for row in housing
        ),
        "Density units are uniform",
    )
    check(
        "36_moe_not_value",
        all(
            metric.get("value_source") != "margin_of_error"
            for row in housing
            for metric in row["metrics"].values()
        ),
        "Margin of error is not used as value",
    )

    # Crime/safety (37-41).
    for row in crime:
        validate_crime_safety_record(row)
    check("37_crime_scope", True, "Crime jurisdiction scope validated")
    check(
        "38_crime_safety_separated",
        all("raw_crime" in row and "safety_index" in row for row in crime),
        "Raw crime and safety index remain separate",
    )
    check(
        "39_safety_formula",
        all(
            row["safety_index"]["availability_status"] != "verified"
            or row["safety_index"]["formula"]
            for row in crime
        ),
        "Any safety index must publish a formula",
    )
    check(
        "40_missing_crime_not_safe",
        all(
            row["safety_index"]["missing_crime_is_safe"] is False for row in crime
        ),
        "Missing crime is never treated as safety",
    )
    check(
        "41_jurisdiction_not_silently_comparable",
        all(row["raw_crime"]["availability_status"] == "deferred" for row in crime),
        "Incomparable jurisdictions remain deferred",
    )

    # Product contracts (42-50).
    for row in bundle["marker_summary"]["universities"]:
        validate_marker_summary(row)
    check("42_marker_allowed_fields", True, "Marker summaries validated")
    validate_search_index(bundle["search_index"])
    check("43_search_excludes_quarantine", True, "Search index provenance validated")
    validate_filter_contract(bundle["filter_contract"])
    check("44_filter_null_policy", True, "Filter null policy validated")
    check(
        "45_comparison_units",
        all(
            row["acceptance_rate"]["unit"] == "ratio"
            and row["tuition"]["currency"] == "USD"
            and row["nearest_towns"]["distance_unit"] == "km"
            for row in bundle["comparison_records"]["universities"]
        ),
        "Comparison units are normalized",
    )
    check(
        "46_mode_metadata_not_fact",
        bundle["mode_metadata"]["weights_are_objective_facts"] is False,
        "Mode relevance metadata is not objective fact",
    )
    validate_ai_context_contract(bundle["ai_context_contract"])
    check("47_ai_excludes_quarantine", True, "AI exclusions validated")
    check(
        "48_completeness_arithmetic",
        all(
            0 <= row["data_completeness"] <= 1
            for row in bundle["marker_summary"]["universities"]
        ),
        "Data completeness is bounded",
    )
    check(
        "49_coverage_matrix_arithmetic",
        all(
            row["coverage"]["expected_records"]
            == row["coverage"]["available_records"]
            + row["coverage"]["missing_records"]
            for row in matrix
        ),
        "Coverage matrix arithmetic is consistent",
    )
    check(
        "50_backlog_consistency",
        {row["field"] for row in backlog}
        == {
            row["field"]
            for row in matrix
            if row["status"] in {"partial", "missing", "blocked"}
        },
        "Backlog equals non-ready matrix fields",
    )

    # Integrity (51-60).
    validate_verified_overlay(overlay, sources)
    check("51_overlay_unique", summary["duplicate_overlay_records"] == 0, "Overlay unique")
    check(
        "52_deterministic_bundle",
        canonical_json(
            {key: value for key, value in generated.items() if key != "validation_result"}
        )
        == canonical_json(
            {key: value for key, value in bundle.items() if key != "validation_result"}
        ),
        "Deterministic bundle is byte-equivalent",
    )
    check(
        "53_validation_result_contract",
        bundle["validation_result"]["record_type"] == "stage4b_validation_result",
        "Validation artifact has correct record type",
    )
    check(
        "54_source_policy_zero",
        summary["source_policy_violations"] == 0,
        "Source-policy violations are zero",
    )
    check(
        "55_ranking_contamination_zero",
        summary["ranking_field_contamination"] == 0,
        "Ranking contamination is zero",
    )
    check(
        "56_no_final_universe",
        summary["final_universe_generated"] is False,
        "No final universe generated",
    )
    check(
        "57_no_memberships",
        summary["official_selection_memberships_generated"] is False,
        "No official memberships generated",
    )
    check(
        "58_no_frontend_export",
        summary["frontend_export_generated"] is False,
        "No frontend export generated",
    )
    check(
        "59_no_preview_or_production_export",
        summary["preview_export_generated"] is False
        and summary["production_export_generated"] is False,
        "No preview/production export generated",
    )
    check(
        "60_no_tag_or_push",
        not _git(repo_root, "tag", "--list", "*stage4b*")
        and summary.get("push_performed", False) is False,
        "No Stage 4B tag or push recorded",
    )
    return {
        "record_type": "stage4b_validation_result",
        "status": "pass",
        "check_count": len(checks),
        "passed_check_count": len(checks),
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


def build_validated_stage4b(repo_root: Path) -> Dict[str, Any]:
    bundle = build_stage4b(repo_root)
    validation = validate_stage4b(bundle, repo_root)
    bundle["validation_result"] = validation
    return bundle


def validate_committed_stage4b(
    artifact_dir: Path, repo_root: Path
) -> Dict[str, Any]:
    bundle = load_stage4b_artifacts(artifact_dir)
    validation = validate_stage4b(bundle, repo_root)
    if bundle["validation_result"] != validation:
        fail("Committed Stage 4B validation result differs from rerun")
    return validation
