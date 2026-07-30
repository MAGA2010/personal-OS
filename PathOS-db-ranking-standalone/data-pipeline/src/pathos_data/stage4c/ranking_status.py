"""Explicit null semantics for schools outside the frozen national ranking scope."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import fail


def build_ranking_status(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for candidate_id, marker in sorted(context["marker_by_id"].items()):
        rank = marker["national_rank"]["value"]
        if rank is None:
            status = "not_in_current_national_scope"
            label = "Not in selected national ranking scope"
            behavior = "exclude_from_numeric_range"
            sources = []
        else:
            status = "ranked_in_selected_national_family"
            label = f"#{rank}"
            behavior = "include_as_ranked"
            sources = marker["national_rank"]["source_ids"]
        row = {
            "candidate_id": candidate_id,
            "national_rank": rank,
            "ranking_status": status,
            "membership_basis": "frozen_stage2_national_top50_membership",
            "display_label": label,
            "filter_behavior": behavior,
            "source_ids": sources,
            "reason": (
                "verified frozen national rank"
                if rank is not None
                else "no membership in selected national top-50 family"
            ),
            "program_rank_used_as_national": False,
            "membership_modified": False,
        }
        validate_ranking_status_record(row)
        rows.append(row)
    return rows


def validate_ranking_status_record(row: Dict[str, Any]) -> None:
    if row["national_rank"] == 0:
        fail("Null national rank cannot be zero")
    if row["program_rank_used_as_national"]:
        fail("Program rank cannot become national rank")
    if row["membership_modified"]:
        fail("Stage 4C cannot modify ranking membership")
    if row["national_rank"] is None:
        if row["ranking_status"] not in {
            "not_in_current_national_scope", "program_only_membership",
            "special_focus_institution", "graduate_oriented_scope",
            "not_ranked_by_selected_family", "ranking_source_not_available",
            "pending_review",
        }:
            fail("Null national rank lacks an explicit semantic status")
        if row["filter_behavior"] not in {
            "exclude_from_numeric_range", "include_as_unranked", "not_applicable"
        }:
            fail("Null national rank lacks filter behavior")
