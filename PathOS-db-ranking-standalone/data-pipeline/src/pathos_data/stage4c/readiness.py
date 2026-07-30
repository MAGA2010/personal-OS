"""Preview-adapter readiness contract without creating any export."""

from __future__ import annotations

from typing import Any, Dict, List


def build_preview_readiness(
    context: Dict[str, Any], overlay: List[Dict[str, Any]]
) -> Dict[str, Any]:
    areas = {
        "core_map": ("ready", ["identity", "coordinates", "marker_summary"]),
        "marker_summary": ("ready", ["school_type", "undergraduate_enrollment"]),
        "school_detail": (
            "ready_with_warning",
            ["school_profile", "admissions", "stories", "localization"],
        ),
        "admissions_section": (
            "ready_with_warning",
            ["acceptance_rate", "graduation_rate", "sat", "act", "test_policy"],
        ),
        "international_applicant_section": (
            "partial", ["english_proficiency_policy"]
        ),
        "search": ("ready", ["identity", "aliases", "programs"]),
        "filters": ("ready_with_warning", ["school_metrics", "null_strategy"]),
        "comparison": ("ready_with_warning", ["normalized_units", "scope_warnings"]),
        "student_mode": ("ready", ["programs", "stories", "admissions"]),
        "parent_mode": ("partial", ["tuition", "regional_metrics"]),
        "ai_context": ("partial", ["verified_facts", "missing_disclosure"]),
        "source_panel": ("ready", ["source_ids", "source_status"]),
        "choropleth": ("blocked", ["official_regional_metrics"]),
    }
    return {
        "record_type": "stage4c_preview_readiness_contract",
        "areas": [
            {
                "product_area": name,
                "status": status,
                "required_backend_fields": fields,
                "current_coverage": "see_stage4c_product_data_coverage_matrix",
                "missing_fields": (
                    ["official_regional_metrics"]
                    if name == "choropleth"
                    else []
                ),
                "allowed_warnings": [
                    "source_limited", "pending_external_access", "null_not_zero"
                ],
                "null_strategy": "preserve_null_with_status_and_warning",
                "source_status_strategy": "expose_verification_and_source_ids",
                "quarantine_exclusions": True,
                "preview_eligibility": status in {"ready", "ready_with_warning"},
                "production_eligibility": False,
            }
            for name, (status, fields) in areas.items()
        ],
        "stage4c_verified_record_count": len(overlay),
        "preview_export_generated": False,
        "production_export_generated": False,
        "frontend_export_generated": False,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }
