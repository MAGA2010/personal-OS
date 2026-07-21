"""Validation and staging contracts for Stage 2A ranking discovery metadata."""

from copy import deepcopy
from typing import Any, Dict, Iterable

from .schema_validation import SchemaValidationError, load_schema, validate_instance


class RankingDiscoveryValidationError(SchemaValidationError):
    """Raised when discovery metadata or a manual seed violates Stage 2A rules."""


ACCESSIBILITY_STATUSES = {
    "publicly_accessible", "partially_public", "login_required", "paywalled",
    "blocked", "unavailable", "needs_manual_seed",
}
INCLUSION_STATUSES = {"included", "excluded", "pending"}
EXCLUDED_FAMILIES = {"global_universities", "graduate_program"}
MANUAL_SEED_CUTOFFS = {"national_universities": 50, "undergraduate_program": 20}


def _schema_validate(document: Dict[str, Any], schema_name: str) -> None:
    try:
        validate_instance(document, load_schema(schema_name))
    except SchemaValidationError as error:
        raise RankingDiscoveryValidationError(str(error)) from error


def _required_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RankingDiscoveryValidationError(f"{field} must be a non-empty string")


def _unique(values: Iterable[str], label: str) -> None:
    materialized = list(values)
    if len(materialized) != len(set(materialized)):
        raise RankingDiscoveryValidationError(f"Duplicate {label}")


def _validate_source_ids(item: Dict[str, Any], label: str) -> None:
    source_ids = item.get("source_ids")
    if not isinstance(source_ids, list) or not source_ids or not all(isinstance(value, str) and value for value in source_ids):
        raise RankingDiscoveryValidationError(f"{label} requires at least one source_id")


def validate_ranking_family_inventory(document: Dict[str, Any]) -> None:
    """Validate family identity and enforce Global/Graduate exclusions."""
    _schema_validate(document, "ranking-family-inventory.json")
    families = document["families"]
    _unique((item["canonical_family_id"] for item in families), "ranking family id")
    for family in families:
        _required_string(family.get("edition"), "family edition")
        _validate_source_ids(family, "ranking family")
        if family.get("accessibility_status") not in ACCESSIBILITY_STATUSES:
            raise RankingDiscoveryValidationError("Unknown ranking family accessibility status")
        if family.get("inclusion_status") not in INCLUSION_STATUSES:
            raise RankingDiscoveryValidationError("Unknown ranking family inclusion status")
        if family.get("ranking_family") in EXCLUDED_FAMILIES and family["inclusion_status"] == "included":
            raise RankingDiscoveryValidationError("Global and Graduate ranking families are excluded from PathOS scope")


def validate_category_inventory(document: Dict[str, Any]) -> None:
    """Validate a versioned undergraduate category inventory and its lineage."""
    _schema_validate(document, "ranking-category-inventory.json")
    _required_string(document.get("inventory_id"), "inventory_id")
    _required_string(document.get("inventory_version"), "inventory_version")
    categories = document["categories"]
    _unique((item["canonical_category_id"] for item in categories), "category id")
    for category in categories:
        if category.get("ranking_family") != "undergraduate_program":
            raise RankingDiscoveryValidationError("Category inventory may only contain undergraduate_program categories")
        if category.get("edition") != document["edition"]:
            raise RankingDiscoveryValidationError("Category edition must match its inventory edition")
        if category.get("inclusion_status") not in INCLUSION_STATUSES:
            raise RankingDiscoveryValidationError("Unknown category inclusion status")
        if category.get("accessibility_status") not in ACCESSIBILITY_STATUSES:
            raise RankingDiscoveryValidationError("Unknown category accessibility status")
        _validate_source_ids(category, "ranking category")
        lineage = category.get("lineage")
        if not isinstance(lineage, dict) or lineage.get("change_type") not in {
            "new", "continued", "renamed", "split", "merged", "retired",
        }:
            raise RankingDiscoveryValidationError("Category lineage requires a valid change_type")
        previous = lineage.get("previous_category_ids")
        if not isinstance(previous, list):
            raise RankingDiscoveryValidationError("Category lineage requires previous_category_ids")
        if lineage["change_type"] == "new" and previous:
            raise RankingDiscoveryValidationError("New category cannot declare previous category ids")
        if lineage["change_type"] != "new" and not previous:
            raise RankingDiscoveryValidationError("Changed category requires previous category ids")


def validate_manual_seed_batch(document: Dict[str, Any]) -> None:
    """Validate manual seeds before they can enter staging; never write canonical data."""
    _schema_validate(document, "manual-ranking-seed-batch.json")
    records = document["records"]
    duplicate_keys = []
    for record in records:
        family = record.get("ranking_family")
        if family not in MANUAL_SEED_CUTOFFS:
            raise RankingDiscoveryValidationError("Manual seed ranking family is outside Stage 2B scope")
        rank = record.get("numeric_rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            raise RankingDiscoveryValidationError("Manual seed numeric_rank must be a positive integer")
        if rank > MANUAL_SEED_CUTOFFS[family]:
            raise RankingDiscoveryValidationError("Manual seed rank is outside PathOS selection cutoff")
        source = record.get("source")
        if not isinstance(source, dict):
            raise RankingDiscoveryValidationError("Manual seed requires source provenance")
        for field in ("source_id", "url", "accessed_at"):
            _required_string(source.get(field), f"manual seed source.{field}")
        for field in ("ranking_system", "category_id", "edition", "school_display_name", "displayed_rank", "entered_by", "entered_at", "verification_status"):
            _required_string(record.get(field), f"manual seed {field}")
        duplicate_keys.append((
            record["ranking_system"], family, record["category_id"], record["edition"],
            record["school_display_name"].strip().casefold(),
        ))
    if len(duplicate_keys) != len(set(duplicate_keys)):
        raise RankingDiscoveryValidationError("Duplicate manual seed record")


def stage_manual_seed_batch(document: Dict[str, Any]) -> Dict[str, Any]:
    """Return validated staging-only manual seed payload; canonical import remains separate."""
    validate_manual_seed_batch(document)
    staged = deepcopy(document)
    staged["record_type"] = "manual_ranking_seed_staging"
    staged["staging_status"] = "validated_manual_seed"
    return staged
