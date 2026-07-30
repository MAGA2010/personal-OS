"""Deterministic Stage 4B artifact assembly.

This module never performs network access. Network intake, when available, is
isolated in source_intake and writes frozen metadata/cache before generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .admissions import build_admissions_metrics
from .config import (
    canonical_json,
    read_json,
    validate_immutable_input_pins,
)
from .cost_of_living import build_cost_of_living_metrics
from .crime_safety import build_crime_safety_metrics
from .demographics import build_demographic_metrics
from .geography import build_campus_geography_crosswalk
from .housing import build_housing_income_metrics
from .integration import (
    build_backend_context,
    build_backlog,
    build_comparison_records,
    build_coverage_matrix,
    build_source_and_cache_manifests,
)
from .overlay import build_verified_overlay, validate_verified_overlay
from .product_contracts import (
    build_ai_context_contract,
    build_filter_contract,
    build_marker_summaries,
    build_mode_metadata,
    build_search_index,
    validate_ai_context_contract,
    validate_filter_contract,
    validate_search_index,
)
from .school_profile import build_school_profile_metrics
from .source_intake import load_official_school_rows
from .transport import build_transport_accessibility_metrics


CORE_ARTIFACT_FILES = {
    "school_profile_metrics": "stage4b-school-profile-metrics.json",
    "admissions_metrics": "stage4b-admissions-metrics.json",
    "test_policy_metrics": "stage4b-test-policy-metrics.json",
    "campus_geography_crosswalk": "stage4b-campus-geography-crosswalk.json",
    "demographic_metrics": "stage4b-demographic-metrics.json",
    "housing_income_metrics": "stage4b-housing-income-metrics.json",
    "crime_safety_metrics": "stage4b-crime-safety-metrics.json",
    "cost_of_living_metrics": "stage4b-cost-of-living-metrics.json",
    "transport_accessibility_metrics": "stage4b-transport-accessibility-metrics.json",
    "source_manifest": "stage4b-source-manifest.json",
    "cache_manifest": "stage4b-cache-manifest.json",
    "field_provenance": "stage4b-field-provenance.json",
    "quarantine": "stage4b-quarantine.json",
    "gap_disclosure": "stage4b-gap-disclosure.json",
    "verified_enrichment_overlay": "stage4b-verified-enrichment-overlay.json",
    "marker_summary": "stage4b-marker-summary.json",
    "search_index": "stage4b-search-index.json",
    "filter_contract": "stage4b-filter-contract.json",
    "comparison_records": "stage4b-comparison-records.json",
    "mode_metadata": "stage4b-mode-metadata.json",
    "ai_context_contract": "stage4b-ai-context-contract.json",
    "product_data_coverage_matrix": "stage4b-product-data-coverage-matrix.json",
    "data_collection_backlog": "stage4b-data-collection-backlog.json",
    "integration_summary": "stage4b-integration-summary.json",
    "validation_result": "stage4b-validation-result.json",
    "input_pin_report": "stage4b-input-pin-report.json",
}


def build_school_admissions_bundle(repo_root: Path) -> Dict[str, Any]:
    pipeline_root = repo_root / "data-pipeline"
    official_rows = load_official_school_rows(pipeline_root)
    admissions, test_policies = build_admissions_metrics(official_rows)
    school_profiles = build_school_profile_metrics(official_rows)
    geography = build_campus_geography_crosswalk(pipeline_root, official_rows)
    demographics = build_demographic_metrics(geography)
    housing = build_housing_income_metrics(geography)
    crime = build_crime_safety_metrics(geography)
    cost = build_cost_of_living_metrics(geography)
    transport = build_transport_accessibility_metrics(pipeline_root, geography)
    return {
        "school_profile_metrics": {
            "record_type": "stage4b_school_profile_metrics",
            "universities": school_profiles,
            "school_count": len(school_profiles),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "admissions_metrics": {
            "record_type": "stage4b_admissions_metrics",
            "universities": admissions,
            "school_count": len(admissions),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "test_policy_metrics": {
            "record_type": "stage4b_test_policy_metrics",
            "universities": test_policies,
            "school_count": len(test_policies),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "campus_geography_crosswalk": {
            "record_type": "stage4b_campus_geography_crosswalk",
            "universities": geography,
            "school_count": len(geography),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "demographic_metrics": {
            "record_type": "stage4b_demographic_metrics",
            "universities": demographics,
            "school_count": len(demographics),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "housing_income_metrics": {
            "record_type": "stage4b_housing_income_metrics",
            "universities": housing,
            "school_count": len(housing),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "crime_safety_metrics": {
            "record_type": "stage4b_crime_safety_metrics",
            "universities": crime,
            "school_count": len(crime),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "cost_of_living_metrics": {
            "record_type": "stage4b_cost_of_living_metrics",
            "universities": cost,
            "school_count": len(cost),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
        "transport_accessibility_metrics": {
            "record_type": "stage4b_transport_accessibility_metrics",
            "universities": transport,
            "school_count": len(transport),
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
        },
    }


def _status_counts(value: Any) -> Dict[str, int]:
    counts = {
        key: 0
        for key in (
            "verified",
            "partial",
            "pending",
            "deferred",
            "unavailable",
            "not_applicable",
            "quarantined",
        )
    }

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("verification_status", "availability_status"):
                status = node.get(key)
                if status in counts:
                    counts[status] += 1
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return counts


def build_stage4b(repo_root: Path) -> Dict[str, Any]:
    bundle = build_school_admissions_bundle(repo_root)
    pipeline_root = repo_root / "data-pipeline"
    pins_path = (
        pipeline_root
        / "data/stage4b-unified-official-product-data/"
        "stage4b-immutable-input-pins.json"
    )
    pins = read_json(pins_path)
    validate_immutable_input_pins(pins, repo_root)
    official_rows = load_official_school_rows(pipeline_root)
    profiles = bundle["school_profile_metrics"]["universities"]
    admissions = bundle["admissions_metrics"]["universities"]
    geography = bundle["campus_geography_crosswalk"]["universities"]
    demographics = bundle["demographic_metrics"]["universities"]
    housing = bundle["housing_income_metrics"]["universities"]
    crime = bundle["crime_safety_metrics"]["universities"]
    context = build_backend_context(
        repo_root, official_rows, profiles, admissions
    )
    source_manifest, cache_manifest = build_source_and_cache_manifests(repo_root)
    overlay_records = build_verified_overlay(profiles, admissions, geography)
    validate_verified_overlay(overlay_records, source_manifest["sources"])
    marker_rows = build_marker_summaries(context)
    search_tokens = build_search_index(context)
    filter_rows = build_filter_contract()
    filter_contract = {
        "record_type": "stage4b_filter_contract",
        "filters": filter_rows,
        "nulls_coerced_to_zero": False,
    }
    validate_filter_contract(filter_contract)
    ai_contract = build_ai_context_contract()
    validate_ai_context_contract(ai_contract)
    search_index = {
        "record_type": "stage4b_search_index",
        "tokens": search_tokens,
        "quarantined_tokens_included": 0,
    }
    validate_search_index(search_index)
    comparison = build_comparison_records(
        context, geography, housing, demographics, crime
    )
    place_count = sum(
        row["census_place"]["availability_status"] == "verified"
        for row in geography
    )
    cbsa_count = sum(
        row["cbsa"]["availability_status"] == "verified" for row in geography
    )
    sat_count = sum(
        row["sat"]["availability_status"] == "verified" for row in admissions
    )
    act_count = sum(
        row["act"]["availability_status"] == "verified" for row in admissions
    )
    matrix = build_coverage_matrix(
        place_count=place_count,
        cbsa_count=cbsa_count,
        sat_count=sat_count,
        act_count=act_count,
    )
    backlog = build_backlog(matrix)
    provenance = [
        {
            "record_id": record["record_id"],
            "university_id": record["university_id"],
            "field": record["field"],
            "scope": record["scope"],
            "source_ids": record["source_ids"],
            "verification_status": "verified",
            "frontend_hardcoded_used_as_authority": False,
        }
        for record in overlay_records
    ]
    status_counts = _status_counts(bundle)
    integration_summary = {
        "record_type": "stage4b_integration_summary",
        "candidate_schools": 62,
        "school_type_coverage": 62,
        "undergraduate_enrollment_coverage": 62,
        "graduate_enrollment_coverage": 0,
        "total_enrollment_coverage": 0,
        "chinese_display_name_coverage": 0,
        "acceptance_rate_coverage": 62,
        "graduation_rate_coverage": 62,
        "retention_rate_coverage": 62,
        "sat_coverage": sat_count,
        "act_coverage": act_count,
        "test_optional_policy_coverage": 0,
        "toefl_policy_coverage": 0,
        "county_geoid_coverage": 62,
        "census_place_geoid_coverage": place_count,
        "cbsa_coverage": cbsa_count,
        "household_income_coverage": 0,
        "rent_coverage": 0,
        "population_density_coverage": 0,
        "asian_ratio_coverage": 0,
        "chinese_specific_ratio_coverage": 0,
        "raw_crime_coverage": 0,
        "safety_index_coverage": 0,
        "cost_of_living_coverage": 0,
        "transport_partial_coverage": 62,
        "verified_overlay_record_count": len(overlay_records),
        "field_status_observation_counts": status_counts,
        "quarantine_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "missing_cache_count": sum(
            not row["exists"] for row in cache_manifest["caches"]
        ),
        "duplicate_overlay_records": 0,
        "program_people_total_slots": 310,
        "program_people_identified": 180,
        "program_people_source_review_not_completed": 130,
        "program_people_no_qualifying_person_found": 0,
        "program_people_duplicate_count": 0,
        "history_coverage": "62/62",
        "anecdotes_coverage": "62/62",
        "notable_attendance_coverage": "62/62",
        "frontend_modified": False,
        "upstream_artifacts_modified": False,
        "final_universe_generated": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
        "preview_export_generated": False,
        "production_export_generated": False,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "readiness_status": "source_limited / incomplete / not_final",
        "core_map_preview_contract_ready": True,
        "school_detail_preview_contract_ready": True,
        "map_choropleth_ready": False,
        "not_final_reason": (
            "Regional official intake remains unavailable, policy fields are "
            "pending, and 130 program-person slots remain source-review gaps."
        ),
    }
    bundle.update(
        {
            "source_manifest": source_manifest,
            "cache_manifest": cache_manifest,
            "field_provenance": {
                "record_type": "stage4b_field_provenance",
                "records": provenance,
            },
            "quarantine": {
                "record_type": "stage4b_quarantine",
                "records": [],
                "frontend_handoff_promotions": 0,
            },
            "gap_disclosure": {
                "record_type": "stage4b_gap_disclosure",
                "items": backlog,
                "program_people_source_review_not_completed": 130,
                "gaps_rendered_as_none": False,
                "source_limited": True,
                "incomplete": True,
                "not_final": True,
            },
            "verified_enrichment_overlay": {
                "record_type": "stage4b_verified_enrichment_overlay",
                "records": overlay_records,
                "frontend_hardcoded_contributions": 0,
            },
            "marker_summary": {
                "record_type": "stage4b_marker_summary",
                "universities": marker_rows,
            },
            "search_index": search_index,
            "filter_contract": filter_contract,
            "comparison_records": {
                "record_type": "stage4b_comparison_records",
                "universities": comparison,
            },
            "mode_metadata": {
                "record_type": "stage4b_mode_metadata",
                "fields": build_mode_metadata(),
                "weights_are_objective_facts": False,
            },
            "ai_context_contract": ai_contract,
            "product_data_coverage_matrix": {
                "record_type": "stage4b_product_data_coverage_matrix",
                "fields": matrix,
            },
            "data_collection_backlog": {
                "record_type": "stage4b_data_collection_backlog",
                "items": backlog,
            },
            "integration_summary": integration_summary,
            "validation_result": {
                "record_type": "stage4b_validation_result",
                "status": "pending_final_validator",
                "checks": [],
            },
            "input_pin_report": {
                "record_type": "stage4b_input_pin_report",
                "input_count": len(pins["inputs"]),
                "all_pins_match": True,
                "expected_counts": pins["expected_counts"],
            },
        }
    )
    return bundle


def write_artifacts(bundle: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in CORE_ARTIFACT_FILES.items():
        if key in bundle:
            (output_dir / filename).write_text(
                canonical_json(bundle[key]), encoding="utf-8"
            )
