"""Pure transforms for the raw → staging → normalization → canonical flow."""

from copy import deepcopy
from typing import Any, Dict

from .schema_validation import SchemaValidationError, load_schema, validate_instance


def _membership_reasons(selection_reason: str) -> list[str]:
    """Expand the display summary into atomic canonical selection facts."""
    if selection_reason == "both":
        return ["national_top_50", "program_top_20"]
    return [selection_reason]


def stage_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Make raw input explicit about its staging status without enrichment."""
    validate_instance(raw, load_schema("raw-university.json"))
    staged = deepcopy(raw)
    staged["record_type"] = "university_staging"
    staged["staging_status"] = "ready_for_normalization"
    return staged


def normalize_staged(staged: Dict[str, Any]) -> Dict[str, Any]:
    """Create a canonical-compatible read model; this does not write a database."""
    validate_instance(staged, load_schema("staging-university.json"))
    university = deepcopy(staged["university"])
    source = deepcopy(staged["source"])
    canonical = {
        "record_type": "canonical_university",
        "is_test_fixture": staged["is_test_fixture"],
        "university": university,
        "sources": [source],
        "university_sources": [{
            "university_id": university["internal_id"],
            "source_id": source["source_id"],
            "relation_type": "identity",
        }],
        "selection_memberships": [{
            "university_id": university["internal_id"],
            "selection_reason": reason,
            "source_id": source["source_id"],
        } for reason in _membership_reasons(university["selection_reason"])],
        "frontend_fields": deepcopy(staged["frontend_fields"]),
    }
    validate_instance(canonical, load_schema("canonical-university.json"))
    return canonical


def assert_formal_canonical(records: list[Dict[str, Any]]) -> None:
    """Reject test fixtures before they reach a real canonical dataset/export."""
    for record in records:
        validate_instance(record, load_schema("canonical-university.json"))
        if record["is_test_fixture"]:
            raise SchemaValidationError("Test fixtures cannot enter a formal canonical dataset")
