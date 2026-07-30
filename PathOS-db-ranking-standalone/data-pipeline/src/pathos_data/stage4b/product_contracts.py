"""Assemble map, search, filter, comparison, mode, and AI product contracts."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List

from .config import fail


def normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def enrollment_size_band(value: int) -> str:
    if value < 5000:
        return "small"
    if value < 15000:
        return "medium"
    if value < 30000:
        return "large"
    return "very_large"


def build_marker_summaries(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    output = []
    for candidate_id, university in context["universities"].items():
        profile = context["profiles"][candidate_id]
        admission = context["admissions"][candidate_id]
        rank = context["rankings"].get(candidate_id)
        tuition = context["tuition"][candidate_id]
        ratio = context["ratios"][candidate_id]
        available = sum(
            value is not None
            for value in (
                university.get("city"),
                university.get("state"),
                university.get("latitude"),
                university.get("longitude"),
                profile["school_type"]["value"],
                profile["enrollment"]["undergraduate"]["value"],
                admission["acceptance_rate"]["value"],
                ratio.get("student_faculty_ratio"),
            )
        )
        warnings = []
        if rank is None:
            warnings.append("not_in_verified_national_top50_scope")
        if not tuition["values"]:
            warnings.append("tuition_value_unavailable")
        record = {
            "university_id": candidate_id,
            "name": university["university_display_name"],
            "city": university["city"],
            "state": university["state"],
            "coordinates": {
                "latitude": university["latitude"],
                "longitude": university["longitude"],
            },
            "national_rank": {
                "value": rank["numeric_rank"] if rank else None,
                "status": (
                    "verified"
                    if rank
                    else "explicit_not_applicable_or_not_in_national_scope"
                ),
                "edition": rank["edition"] if rank else None,
                "source_ids": (
                    [rank["source"]["source_id"]] if rank else []
                ),
            },
            "top_program_count": len(university["top_5_programs_for_demo"]),
            "tuition_summary": tuition,
            "acceptance_rate": admission["acceptance_rate"]["value"],
            "undergraduate_enrollment": profile["enrollment"]["undergraduate"]["value"],
            "enrollment_size_band": enrollment_size_band(
                profile["enrollment"]["undergraduate"]["value"]
            ),
            "student_faculty_ratio": ratio.get("student_faculty_ratio"),
            "school_type": profile["school_type"]["value"],
            "data_completeness": round(available / 8, 4),
            "source_coverage": len(
                {
                    *profile["school_type"]["source_ids"],
                    *profile["enrollment"]["undergraduate"]["source_ids"],
                    *admission["acceptance_rate"]["source_ids"],
                    ratio.get("source_id"),
                }
                - {None}
            ),
            "warning_count": len(warnings),
            "warnings": warnings,
            "marker_channels": {
                "color": {
                    "metric": "acceptance_rate",
                    "null_fallback": "not_encoded",
                },
                "size": {
                    "metric": "undergraduate_enrollment",
                    "null_fallback": "default_neutral_size",
                },
                "border": {
                    "metric": "data_quality_status",
                    "null_fallback": "warning_border",
                },
            },
            "derived": True,
            "derivation_version": "stage4b-marker-v1",
            "input_fields": [
                "stage3c.coordinates",
                "stage2.national_ranking",
                "stage3b.top_5_programs",
                "stage3b.tuition",
                "stage3b.student_faculty_ratio",
                "stage4b.school_type",
                "stage4b.undergraduate_enrollment",
                "stage4b.acceptance_rate",
            ],
        }
        validate_marker_summary(record)
        output.append(record)
    return sorted(output, key=lambda row: row["university_id"])


def validate_marker_summary(record: Dict[str, Any]) -> None:
    if record.get("derived") is not True or not record.get("input_fields"):
        fail("Marker summary must be a traceable derived record")
    if not {"color", "size", "border"}.issubset(record.get("marker_channels", {})):
        fail("Marker summary does not distinguish visual channels")
    if record.get("national_rank", {}).get("value") == 0:
        fail("Missing national rank cannot be represented as zero")
    if record.get("data_completeness") is None:
        fail("Marker summary lacks deterministic completeness")


def build_search_index(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    tokens: List[Dict[str, Any]] = []
    seen = set()
    for candidate_id, university in context["universities"].items():
        source_values = [
            (university["university_display_name"], "canonical_name", "stage3b.identity"),
            *[
                (value, "alias", "candidate_v2.reviewed_alias")
                for value in university.get("known_aliases", [])
            ],
            (university["city"], "city", "stage3c.location"),
            (university["state"], "state", "stage3c.location"),
            (university["region"], "region", "stage3c.region"),
            *[
                (
                    program["program_name"],
                    "top_program",
                    f"stage3b.top_program:{program.get('source_id')}",
                )
                for program in university["top_5_programs_for_demo"]
            ],
            *[
                (major, "major", "stage3c.reviewed_official_major")
                for major in context["majors"][candidate_id]
            ],
        ]
        for display, field_type, provenance in source_values:
            if not isinstance(display, str) or not display.strip():
                continue
            key = (candidate_id, field_type, normalize_token(display))
            if key in seen:
                continue
            seen.add(key)
            tokens.append(
                {
                    "university_id": candidate_id,
                    "normalized_token": key[2],
                    "original_display": display,
                    "field_type": field_type,
                    "backend_provenance": provenance,
                    "verification_status": "verified",
                }
            )
    return sorted(
        tokens,
        key=lambda row: (
            row["university_id"],
            row["field_type"],
            row["normalized_token"],
        ),
    )


def validate_search_index(index: Dict[str, Any]) -> None:
    for token in index.get("tokens", []):
        if (
            not token.get("normalized_token")
            or not token.get("backend_provenance")
            or token.get("verification_status") != "verified"
        ):
            fail("Search token lacks verified backend provenance")
        if "quarantin" in token.get("backend_provenance", "").lower():
            fail("Search index cannot include quarantined text")


FILTER_DEFINITIONS = (
    ("national_ranking", "range", "rank", 50),
    ("program_ranking", "range", "rank", 62),
    ("tuition", "range", "USD", 62),
    ("acceptance_rate", "range", "ratio", 62),
    ("undergraduate_enrollment", "range", "students", 62),
    ("enrollment_size_band", "category", "enum", 62),
    ("school_type", "category", "enum", 62),
    ("student_faculty_ratio", "range", "students_per_faculty", 62),
    ("state", "multiselect", "state_code", 62),
    ("region", "multiselect", "enum", 62),
    ("program", "multiselect", "text", 62),
    ("median_household_income", "range", "USD", 0),
    ("median_gross_rent", "range", "USD_per_month", 0),
    ("asian_population_ratio", "range", "ratio", 0),
    ("chinese_population_ratio", "range", "ratio", 0),
    ("crime_rate", "range", "incidents_per_1000", 0),
    ("safety_index", "range", "derived_index", 0),
)


def build_filter_contract() -> List[Dict[str, Any]]:
    return [
        {
            "field": field,
            "backend_path": f"stage4b.product.{field}",
            "type": kind,
            "unit": unit,
            "null_behavior": "exclude_from_numeric_comparison_and_show_unknown",
            "range_or_category_semantics": (
                "inclusive_range" if kind == "range" else "exact_verified_category"
            ),
            "coverage_count": coverage,
            "expected_count": 62,
            "sort_behavior": "nulls_last_without_numeric_coercion",
            "reference_year_policy": "display_and_warn_when_different",
        }
        for field, kind, unit, coverage in FILTER_DEFINITIONS
    ]


def validate_filter_contract(contract: Dict[str, Any]) -> None:
    for item in contract.get("filters", []):
        if (
            item.get("null_behavior")
            != "exclude_from_numeric_comparison_and_show_unknown"
            or item.get("sort_behavior") != "nulls_last_without_numeric_coercion"
        ):
            fail("Filter contract has unsafe null semantics")


def build_mode_metadata() -> List[Dict[str, Any]]:
    definitions = {
        "tuition": ("financial", "high", "medium"),
        "crime_safety": ("living_environment", "high", "medium"),
        "income_rent": ("living_environment", "high", "medium"),
        "source_trust": ("data_quality", "high", "medium"),
        "program_quality": ("academic", "high", "high"),
        "transport": ("accessibility", "medium", "medium"),
        "community_indicators": ("community", "high", "medium"),
        "school_stories": ("narrative", "low", "high"),
        "enrollment": ("school_context", "medium", "high"),
        "admissions": ("admissions", "medium", "high"),
    }
    missing = {"crime_safety", "income_rent", "community_indicators"}
    partial = {"transport"}
    return [
        {
            "field": field,
            "field_category": category,
            "parent_relevance_tag": parent,
            "student_relevance_tag": student,
            "availability": (
                "missing" if field in missing else "partial" if field in partial else "ready"
            ),
            "confidence": "high",
            "source_status": "verified_or_explicit_gap",
            "warning_status": field in missing | partial,
            "objective_fact": False,
            "metadata_type": "product_relevance_metadata",
        }
        for field, (category, parent, student) in definitions.items()
    ]


def build_ai_context_contract() -> Dict[str, Any]:
    return {
        "record_type": "stage4b_ai_context_contract",
        "request_context_fields": [
            "selected_university_ids",
            "comparison_university_ids",
            "active_filters",
            "map_metric",
            "mode",
        ],
        "fact_groups": [
            "verified_school_facts",
            "verified_regional_facts",
            "derived_metrics",
            "source_ids",
            "warnings",
            "missing_fields",
            "reference_years",
            "geography_scopes",
        ],
        "allowed_fact_statuses": [
            "verified",
            "normalized_verified",
            "cache_verified_pending",
            "derived",
            "partial",
            "missing",
        ],
        "excluded_fact_classes": [
            "quarantined",
            "frontend_demonstration_estimates",
            "unresolved_handoff_conflicts",
            "quarantined_people",
            "source_review_not_completed_program_people",
            "unsourced_recommendation_facts",
        ],
        "missing_field_disclosure_required": True,
        "source_id_required_for_verified_facts": True,
    }


def validate_ai_context_contract(contract: Dict[str, Any]) -> None:
    required_exclusions = {
        "quarantined",
        "frontend_demonstration_estimates",
        "unresolved_handoff_conflicts",
        "quarantined_people",
        "source_review_not_completed_program_people",
        "unsourced_recommendation_facts",
    }
    if not required_exclusions.issubset(
        set(contract.get("excluded_fact_classes", []))
    ):
        fail("AI context does not exclude quarantined/unverified facts")
    if not contract.get("missing_field_disclosure_required"):
        fail("AI context must disclose missing fields")
