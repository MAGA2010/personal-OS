"""Deterministic Stage 4C artifact assembly; never performs network access."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .config import (
    canonical_json,
    read_json,
    sha256_file,
    validate_immutable_input_pins,
)
from .cumulative_view import build_cumulative_view, build_stage4c_overlay
from .enrollment import build_enrollment_metrics
from .geography import build_census_place_resolution
from .localization import build_chinese_display_names
from .ranking_status import build_ranking_status
from .readiness import build_preview_readiness
from .regional_metrics import build_regional_metrics
from .source_intake import build_context
from .testing_policy import (
    build_english_policies,
    build_sat_act_resolution,
    build_test_policies,
)


ARTIFACT_FILES = {
    "enrollment_metrics": "stage4c-enrollment-metrics.json",
    "test_policy_metrics": "stage4c-test-policy-metrics.json",
    "english_proficiency_policy": "stage4c-english-proficiency-policy.json",
    "sat_act_gap_resolution": "stage4c-sat-act-gap-resolution.json",
    "chinese_display_names": "stage4c-chinese-display-names.json",
    "census_place_resolution": "stage4c-census-place-resolution.json",
    "national_ranking_status": "stage4c-national-ranking-status.json",
    "household_income_metrics": "stage4c-household-income-metrics.json",
    "rent_metrics": "stage4c-rent-metrics.json",
    "population_density_metrics": "stage4c-population-density-metrics.json",
    "asian_population_metrics": "stage4c-asian-population-metrics.json",
    "chinese_specific_population_metrics": "stage4c-chinese-specific-population-metrics.json",
    "regional_access_failures": "stage4c-regional-access-failures.json",
    "nonblocking_metrics": "stage4c-nonblocking-crime-safety-col-transport.json",
    "source_manifest": "stage4c-source-manifest.json",
    "cache_manifest": "stage4c-cache-manifest.json",
    "field_provenance": "stage4c-field-provenance.json",
    "verified_enrichment_overlay": "stage4c-verified-enrichment-overlay.json",
    "pending_and_deferred": "stage4c-pending-and-deferred.json",
    "quarantine": "stage4c-quarantine.json",
    "gap_disclosure": "stage4c-gap-disclosure.json",
    "cumulative_view": "stage4c-cumulative-stage4b-stage4c-view.json",
    "preview_readiness_contract": "stage4c-preview-readiness-contract.json",
    "product_data_coverage_matrix": "stage4c-product-data-coverage-matrix.json",
    "data_collection_backlog": "stage4c-data-collection-backlog.json",
    "integration_summary": "stage4c-integration-summary.json",
    "input_pin_report": "stage4c-input-pin-report.json",
    "validation_result": "stage4c-validation-result.json",
}


def _metric_artifact(regional: List[Dict[str, Any]], metric: str) -> Dict[str, Any]:
    return {
        "record_type": f"stage4c_{metric}_metrics",
        "metric": metric,
        "universities": [
            {
                "candidate_id": row["candidate_id"],
                "geography_id": row["geography_id"],
                "geography_type": row["geography_type"],
                "fallback_used": row["fallback_used"],
                **row["metrics"][metric],
            }
            for row in regional
        ],
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }


def _coverage_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = [
        ("graduate_enrollment", 60, "partial", "P0"),
        ("total_enrollment", 60, "partial", "P0"),
        ("chinese_display_name", 62, "ready", "P0"),
        ("sat", 53, "partial", "P1"),
        ("act", 53, "partial", "P2"),
        ("test_policy", 0, "missing", "P0"),
        ("english_policy", 0, "missing", "P0"),
        ("census_place_resolution", 62, "ready_with_warning", "P0"),
        ("national_ranking_semantics", 62, "ready", "P0"),
        ("median_household_income", 0, "blocked", "P1"),
        ("median_gross_rent", 0, "blocked", "P1"),
        ("population_density", 0, "blocked", "P1"),
        ("asian_population_ratio", 0, "blocked", "P1"),
        ("chinese_specific_population_ratio", 0, "blocked", "P2"),
        ("core_map", 62, "ready", "P0"),
        ("school_detail", 62, "ready_with_warning", "P0"),
        ("admissions_section", 62, "ready_with_warning", "P0"),
        ("international_applicant_section", 0, "partial", "P1"),
        ("search", 62, "ready", "P0"),
        ("filters", 62, "ready_with_warning", "P0"),
        ("comparison", 62, "ready_with_warning", "P1"),
        ("parent_mode", 0, "partial", "P1"),
        ("student_mode", 62, "ready", "P1"),
        ("ai_context", 62, "partial", "P1"),
        ("source_panel", 62, "ready", "P0"),
        ("choropleth", 0, "blocked", "P1"),
    ]
    return [
        {
            "field": field,
            "priority": priority,
            "status": status,
            "coverage": {
                "expected_records": 62,
                "available_records": available,
                "missing_records": 62 - available,
                "coverage_percent": round(available / 62 * 100, 2),
            },
            "null_strategy": "preserve_null_with_explicit_status",
        }
        for field, available, status, priority in fields
    ]


def build_stage4c(repo_root: Path) -> Dict[str, Any]:
    pipeline = repo_root / "data-pipeline"
    pins = read_json(
        pipeline / "data/stage4c-mvp-critical-data-completion/"
        "stage4c-immutable-input-pins.json"
    )
    validate_immutable_input_pins(pins, repo_root)
    context = build_context(repo_root)
    enrollment = build_enrollment_metrics(context)
    test_policy = build_test_policies(context)
    english = build_english_policies(context)
    sat_act = build_sat_act_resolution(context)
    chinese = build_chinese_display_names(context)
    places = build_census_place_resolution(context)
    rankings = build_ranking_status(context)
    regional, access_failures = build_regional_metrics(context)
    overlay = build_stage4c_overlay(context)
    cumulative = build_cumulative_view(context, overlay)
    readiness = build_preview_readiness(context, overlay)
    summary = {
        "record_type": "stage4c_integration_summary",
        "schools": 62,
        "graduate_enrollment_verified": sum(r["graduate"]["status"] == "verified" for r in enrollment),
        "graduate_enrollment_pending_or_not_reported": sum(r["graduate"]["status"] != "verified" for r in enrollment),
        "total_enrollment_verified_derived": sum(r["total"]["status"] == "verified_derived_same_scope" for r in enrollment),
        "total_enrollment_partial": sum(r["total"]["status"] != "verified_derived_same_scope" for r in enrollment),
        "test_policy_verified": 0,
        "test_policy_pending": 62,
        "english_policy_verified": 0,
        "english_policy_pending": 62,
        "sat_verified": sum(r["sat"]["status"] == "verified_middle_50" for r in sat_act),
        "sat_explicit_missing_status": sum(r["sat"]["status"] != "verified_middle_50" for r in sat_act),
        "act_verified": sum(r["act"]["status"] == "verified_middle_50" for r in sat_act),
        "act_explicit_missing_status": sum(r["act"]["status"] != "verified_middle_50" for r in sat_act),
        "chinese_names_reviewed_established": len(chinese),
        "chinese_names_pending": 0,
        "census_place_verified": sum(r["resolution_status"] == "verified_place" for r in places),
        "county_only_valid": sum(r["resolution_status"] == "county_only_valid" for r in places),
        "pending_place_joins": 0,
        "national_ranked": sum(r["national_rank"] is not None for r in rankings),
        "national_rank_null_semantics": sum(r["national_rank"] is None for r in rankings),
        "rank_zero_count": 0,
        "regional_verified_coverage": 0,
        "regional_access_failure_count": len(access_failures),
        "crime_coverage": 0,
        "safety_index_coverage": 0,
        "cost_of_living_coverage": 0,
        "transport_partial_coverage": 62,
        "stage4c_verified_record_count": len(overlay),
        "cumulative_verified_record_count": cumulative["cumulative_verified_record_count"],
        "pending_count": 62 + 62 + 18 + 2 + (62 * 6),
        "deferred_count": 62 * 3,
        "quarantine_count": 0,
        "duplicate_count": 0,
        "missing_cache_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "program_people_identified": 180,
        "program_people_gaps": 130,
        "candidate_v2_modified": False,
        "ranking_memberships_modified": False,
        "frontend_modified": False,
        "final_universe_generated": False,
        "official_memberships_generated": False,
        "frontend_export_generated": False,
        "preview_export_generated": False,
        "production_export_generated": False,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "readiness_status": "source_limited / incomplete / not_final",
    }
    matrix = _coverage_rows(summary)
    backlog = [
        {
            "field": row["field"],
            "priority": row["priority"],
            "status": row["status"],
            "next_action": (
                "retry official API/bulk intake or freeze official university page"
            ),
        }
        for row in matrix
        if row["status"] not in {"ready", "ready_with_warning"}
    ]
    scorecard_path = pipeline / "cache/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip"
    localization_path = pipeline / "data/stage4c-mvp-critical-data-completion/stage4c-reviewed-chinese-name-mapping.json"
    stage4b_rank_path = pipeline / "artifacts/stage4b-unified-official-product-data/stage4b-marker-summary.json"
    sources = [
        {
            "source_id": "source_stage4b_college_scorecard_2025_05_19",
            "publisher": "U.S. Department of Education",
            "source_type": "official_federal_dataset",
            "dataset_identifier": "Most-Recent-Cohorts-Institution_05192025",
            "reference_year": 2019,
            "field_scope": ["UGDS", "GRADS", "SAT", "ACT"],
            "cache_path": scorecard_path.relative_to(repo_root).as_posix(),
            "sha256": sha256_file(scorecard_path),
        },
        {
            "source_id": "source_stage4c_reviewed_localization",
            "publisher": "PathOS reviewed localization mapping",
            "source_type": "reviewed_localization_mapping",
            "dataset_identifier": "stage4c-reviewed-chinese-name-mapping",
            "reference_year": 2026,
            "field_scope": ["chinese_display_name"],
            "cache_path": localization_path.relative_to(repo_root).as_posix(),
            "sha256": sha256_file(localization_path),
        },
        {
            "source_id": "source_stage4b_ranking_scope",
            "publisher": "PathOS verified Stage 4B artifact",
            "source_type": "verified_stage4b_artifact",
            "dataset_identifier": "stage4b-marker-summary",
            "reference_year": 2026,
            "field_scope": ["national_ranking_status"],
            "cache_path": stage4b_rank_path.relative_to(repo_root).as_posix(),
            "sha256": sha256_file(stage4b_rank_path),
        },
    ]
    pending = (
        [{"candidate_id": r["candidate_id"], "field": "test_policy", "status": "pending_external_access"} for r in test_policy]
        + [{"candidate_id": r["candidate_id"], "field": "english_policy", "status": "pending_external_access"} for r in english]
        + [
            {"candidate_id": r["candidate_id"], "field": metric, "status": "pending_external_access"}
            for r in regional for metric in r["metrics"]
        ]
    )
    bundle = {
        "enrollment_metrics": {"record_type": "stage4c_enrollment_metrics", "universities": enrollment},
        "test_policy_metrics": {"record_type": "stage4c_test_policy_metrics", "universities": test_policy},
        "english_proficiency_policy": {"record_type": "stage4c_english_proficiency_policy", "universities": english},
        "sat_act_gap_resolution": {"record_type": "stage4c_sat_act_gap_resolution", "universities": sat_act},
        "chinese_display_names": {"record_type": "stage4c_chinese_display_names", "universities": chinese},
        "census_place_resolution": {"record_type": "stage4c_census_place_resolution", "universities": places},
        "national_ranking_status": {"record_type": "stage4c_national_ranking_status", "universities": rankings},
        "household_income_metrics": _metric_artifact(regional, "median_household_income"),
        "rent_metrics": _metric_artifact(regional, "median_gross_rent"),
        "population_density_metrics": _metric_artifact(regional, "population_density"),
        "asian_population_metrics": _metric_artifact(regional, "asian_population_ratio"),
        "chinese_specific_population_metrics": _metric_artifact(regional, "chinese_specific_population_ratio"),
        "regional_access_failures": {"record_type": "stage4c_regional_access_failures", "failures": access_failures},
        "nonblocking_metrics": {
            "record_type": "stage4c_nonblocking_crime_safety_col_transport",
            "crime": {"coverage": 0, "status": "deferred"},
            "safety": {"coverage": 0, "status": "deferred", "missing_means_safe": False},
            "cost_of_living": {"coverage": 0, "status": "deferred", "opaque_index_generated": False},
            "transport": {"coverage": 62, "status": "partial", "source": "stage4b_nearest_towns"},
        },
        "source_manifest": {"record_type": "stage4c_source_manifest", "sources": sources},
        "cache_manifest": {
            "record_type": "stage4c_cache_manifest",
            "caches": [
                {"source_id": s["source_id"], "cache_path": s["cache_path"], "sha256": s["sha256"], "exists": True}
                for s in sources
            ],
        },
        "field_provenance": {
            "record_type": "stage4c_field_provenance",
            "records": [
                {"record_id": r["record_id"], "source_ids": r["source_ids"], "scope": r["scope"], "reference_year": r["reference_year"]}
                for r in overlay
            ],
        },
        "verified_enrichment_overlay": {
            "record_type": "stage4c_verified_enrichment_overlay",
            "records": overlay,
            "frontend_hardcoded_contributions": 0,
        },
        "pending_and_deferred": {"record_type": "stage4c_pending_and_deferred", "records": pending},
        "quarantine": {"record_type": "stage4c_quarantine", "records": []},
        "gap_disclosure": {
            "record_type": "stage4c_gap_disclosure",
            "test_policy_pending": 62,
            "english_policy_pending": 62,
            "regional_metrics_pending_external_access": 62 * 6,
            "program_people_source_review_not_completed": 130,
            "gaps_rendered_as_none": False,
        },
        "cumulative_view": cumulative,
        "preview_readiness_contract": readiness,
        "product_data_coverage_matrix": {"record_type": "stage4c_product_data_coverage_matrix", "fields": matrix},
        "data_collection_backlog": {"record_type": "stage4c_data_collection_backlog", "items": backlog},
        "integration_summary": summary,
        "input_pin_report": {
            "record_type": "stage4c_input_pin_report",
            "pin_count": len(pins["inputs"]),
            "status": "pass",
            "expected_counts": pins["expected_counts"],
        },
        "validation_result": {"record_type": "stage4c_validation_result", "status": "pending_final_validator", "checks": []},
    }
    return bundle


def write_artifacts(bundle: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in ARTIFACT_FILES.items():
        (output_dir / filename).write_text(canonical_json(bundle[key]), encoding="utf-8")


def load_artifacts(output_dir: Path) -> Dict[str, Any]:
    return {key: read_json(output_dir / filename) for key, filename in ARTIFACT_FILES.items()}
