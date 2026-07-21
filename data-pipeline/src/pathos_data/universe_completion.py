"""Validate a non-collecting plan to complete the ranking universe."""

from typing import Any, Dict

from .schema_validation import SchemaValidationError, load_schema, validate_instance


class UniverseCompletionPlanValidationError(SchemaValidationError):
    """Raised when a completion plan is inconsistent with the current corpus."""


def _fail(message: str) -> None:
    raise UniverseCompletionPlanValidationError(message)


def validate_universe_completion_plan(
    plan: Dict[str, Any], inventory: Dict[str, Any], corpus: Dict[str, Any]
) -> None:
    """Bind a planning artifact to current inventory/corpus without collecting data."""
    try:
        validate_instance(plan, load_schema("universe-completion-plan.json"))
    except SchemaValidationError as error:
        raise UniverseCompletionPlanValidationError(str(error)) from error

    included = {
        item["canonical_category_id"]
        for item in inventory.get("categories", [])
        if item.get("inclusion_status") == "included"
    }
    baseline = plan["baseline"]
    expected_baseline = {
        "total_scope_streams": len(included) + 1,
        "verified_records": corpus["counts"]["verified_records"],
        "source_limited_candidate_count": 7,
        "incomplete_streams": corpus["gaps"]["incomplete_stream_count"],
        "no_verified_streams": corpus["counts"]["no_verified_stream_count"],
        "national_current_coverage_max_rank": 3,
    }
    for field, value in expected_baseline.items():
        if baseline.get(field) != value:
            _fail(f"Plan baseline {field} does not match current corpus")

    phases = plan["phases"]
    if [phase.get("phase_id") for phase in phases] != ["A", "B", "C"]:
        _fail("Plan phases must be A, B, C in order")
    national = phases[0]
    if national.get("stream_id") != "national-universities" or national.get("target_numeric_rank") != 50:
        _fail("Phase A must complete National Universities through numeric rank 50")
    if national.get("include_all_ties") is not True:
        _fail("Phase A must include all ties at the cutoff")

    priority = phases[1].get("priority_streams")
    if not isinstance(priority, list) or not 8 <= len(priority) <= 12:
        _fail("Phase B must contain 8 to 12 priority streams")
    if len(priority) != len(set(priority)) or not set(priority).issubset(included):
        _fail("Phase B streams must be unique included categories")

    remaining = phases[2].get("remaining_streams")
    expected_remaining = included - set(priority)
    if not isinstance(remaining, list) or set(remaining) != expected_remaining:
        _fail("Phase C must cover every remaining included category exactly once")
    if len(remaining) != len(set(remaining)):
        _fail("Phase C contains duplicate stream")

    boundaries = plan["output_boundaries"]
    for field in (
        "final_universe_generated",
        "selection_memberships_generated",
        "frontend_export_generated",
        "new_ranking_records_collected_in_stage_2e",
    ):
        if boundaries.get(field) is not False:
            _fail(f"Plan boundary {field} must be false")
    if plan.get("completed_candidate_is_final") is not False:
        _fail("Completed candidate must not be declared final")
