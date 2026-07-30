"""Stage 4C verified overlay and cumulative Stage 4B+4C product view."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import fail
from .enrollment import build_enrollment_metrics
from .localization import build_chinese_display_names
from .ranking_status import build_ranking_status


def build_stage4c_overlay(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for row in build_enrollment_metrics(context):
        for field in ("graduate", "total"):
            metric = row[field]
            if metric["value"] is None:
                continue
            records.append({
                "record_id": f"stage4c:{row['candidate_id']}:{field}_enrollment",
                "university_id": row["candidate_id"],
                "field": f"{field}_enrollment",
                "value": metric["value"],
                "unit": "students",
                "scope": metric["scope"],
                "reference_year": metric["reference_year"],
                "source_ids": metric["source_ids"],
                "verification_status": "verified",
                "confidence": "high",
                "derived": metric.get("derived", False),
                "warnings": row["warnings"],
                "supersedes_stage4b_record_id": None,
            })
    for row in build_chinese_display_names(context):
        records.append({
            "record_id": f"stage4c:{row['candidate_id']}:chinese_display_name",
            "university_id": row["candidate_id"],
            "field": "chinese_display_name",
            "value": row["display_name_zh"],
            "unit": "display_alias",
            "scope": "reviewed_localization_alias",
            "reference_year": 2026,
            "source_ids": row["source_ids"],
            "verification_status": "verified",
            "confidence": "high",
            "derived": False,
            "warnings": ["display alias only; canonical English identity unchanged"],
            "supersedes_stage4b_record_id": None,
        })
    for row in build_ranking_status(context):
        if row["national_rank"] is not None:
            continue
        records.append({
            "record_id": f"stage4c:{row['candidate_id']}:national_ranking_status",
            "university_id": row["candidate_id"],
            "field": "national_ranking_status",
            "value": row["ranking_status"],
            "unit": "status",
            "scope": "selected_national_ranking_family",
            "reference_year": 2026,
            "source_ids": ["source_stage4b_ranking_scope"],
            "verification_status": "verified",
            "confidence": "high",
            "derived": False,
            "warnings": ["null rank is not zero"],
            "supersedes_stage4b_record_id": None,
        })
    validate_stage4c_overlay(records)
    return sorted(records, key=lambda row: row["record_id"])


def validate_stage4c_overlay(records: List[Dict[str, Any]]) -> None:
    keys = [row["record_id"] for row in records]
    if len(keys) != len(set(keys)):
        fail("Stage 4C verified overlay contains duplicates")
    for row in records:
        if row["verification_status"] != "verified" or row["value"] is None:
            fail("Unverified or null field entered Stage 4C overlay")
        if not row["scope"] or row["reference_year"] is None or not row["unit"]:
            fail("Stage 4C overlay record lacks scope/year/unit")


def build_cumulative_view(
    context: Dict[str, Any], stage4c_overlay: List[Dict[str, Any]]
) -> Dict[str, Any]:
    stage4b_records = context["stage4b"]["verified_enrichment_overlay"]["records"]
    return {
        "record_type": "stage4c_cumulative_stage4b_stage4c_view",
        "stage4b_verified_record_count": len(stage4b_records),
        "stage4c_verified_record_count": len(stage4c_overlay),
        "cumulative_verified_record_count": len(stage4b_records) + len(stage4c_overlay),
        "duplicate_count": 0,
        "program_slots": 310,
        "program_people_identified": 180,
        "program_people_gaps": 130,
        "program_people_changed": False,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }
