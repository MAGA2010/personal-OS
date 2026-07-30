"""Reviewed Chinese display aliases kept separate from canonical identity."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import fail, read_json


def build_chinese_display_names(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    path = (
        context["pipeline_root"]
        / "data/stage4c-mvp-critical-data-completion/"
        "stage4c-reviewed-chinese-name-mapping.json"
    )
    mapping = read_json(path)
    by_id = {row["candidate_id"]: row for row in mapping["names"]}
    rows = []
    for source in context["official_rows"]:
        candidate_id = source["candidate_id"]
        if candidate_id not in by_id:
            fail(f"Missing reviewed Chinese display name: {candidate_id}")
        reviewed = by_id[candidate_id]
        row = {
            "candidate_id": candidate_id,
            "canonical_id": source["canonical_id"],
            "canonical_name_en": source["university_display_name"],
            "display_name_zh": reviewed["display_name_zh"],
            "name_status": reviewed["name_status"],
            "source_ids": reviewed.get("source_ids", []),
            "ambiguity_notes": reviewed.get("ambiguity_notes", []),
            "manual_review_required": reviewed.get("manual_review_required", False),
            "identity_match_basis": "candidate_id_and_canonical_english_name",
            "canonical_identity_changed": False,
            "machine_translation_claimed_official": False,
        }
        validate_chinese_name_record(row)
        rows.append(row)
    return sorted(rows, key=lambda row: row["candidate_id"])


def validate_chinese_name_record(row: Dict[str, Any]) -> None:
    if row["name_status"] not in {
        "official", "reviewed_established", "reviewed_transliteration", "pending"
    }:
        fail("Invalid Chinese display-name status")
    if row["name_status"] != "pending" and not row["display_name_zh"]:
        fail("Reviewed Chinese display name is empty")
    if row["canonical_identity_changed"]:
        fail("Chinese display alias cannot change canonical identity")
    if row["identity_match_basis"] == "chinese_display_name":
        fail("Chinese display name cannot be an identity join key")
    if row["machine_translation_claimed_official"]:
        fail("Machine translation cannot be marked official")
