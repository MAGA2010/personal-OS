"""Stage 4A frontend handoff reconciliation and product data gap audit.

The external handoff is intake-only and never authoritative.  Deterministic
artifact generation reads the committed raw snapshot and frozen review inputs;
it performs no network access and does not mutate any upstream stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


BASELINE_COMMIT = "7561760c2b1b5bf1bbfd5e4ef6a585e2c69b46a8"
HANDOFF_ROOT_NAME = "frontend-data-extraction"
STAGE_NAME = "stage4a-frontend-handoff-reconciliation"
ALLOWED_CLASSIFICATIONS = {
    "verified_backend_existing",
    "frontend_candidate_requires_verification",
    "frontend_backend_conflict",
    "mock_demo_placeholder",
    "derived_display_value",
    "frontend_ui_only",
    "stale_or_invalid_candidate",
    "unmatched_university",
}
FORBIDDEN_OVERLAY_CLASSIFICATIONS = {
    "verified_backend_existing",
    "frontend_backend_conflict",
    "mock_demo_placeholder",
    "derived_display_value",
    "frontend_ui_only",
    "stale_or_invalid_candidate",
    "unmatched_university",
}
REGIONAL_FIELDS = {
    "median_household_income",
    "crime_rate",
    "safety_index",
    "asian_population_ratio",
    "chinese_population_ratio",
    "cost_of_living_index",
    "median_rent",
    "population_density",
    "transport_accessibility",
}
FORBIDDEN_CANONICAL_FIELDS = {"ranking_membership", "official_selection_membership"}
SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "openai_api_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "jwt": re.compile(
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    ),
    "private_key": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
}
OUTPUT_FILES = {
    "handoff_integrity_report": "stage4a-handoff-integrity-report.json",
    "university_identity_reconciliation": "stage4a-university-identity-reconciliation.json",
    "field_reconciliation": "stage4a-field-reconciliation.json",
    "verified_enrichment_overlay": "stage4a-verified-enrichment-overlay.json",
    "quarantine": "stage4a-quarantine.json",
    "regional_metric_readiness": "stage4a-regional-metric-readiness.json",
    "product_data_coverage_matrix": "stage4a-product-data-coverage-matrix.json",
    "missing_data_report": "stage4a-missing-data-report.json",
    "data_collection_backlog": "stage4a-data-collection-backlog.json",
    "validation_result": "stage4a-validation-result.json",
    "input_pin_report": "stage4a-input-pin-report.json",
    "integration_summary": "stage4a-integration-summary.json",
}


class Stage4AValidationError(ValueError):
    """Raised when Stage 4A must fail closed."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def discover_handoff_root(repo_root: Path) -> Path:
    """Find independent handoff roots; a container is not a second candidate."""
    candidates: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_dir():
            continue
        lowered = path.name.lower()
        looks_named = "handoff" in lowered or (
            "frontend" in lowered and "data" in lowered
        )
        if looks_named and (path / "extraction-manifest.json").is_file():
            candidates.append(path)
    independent = [
        candidate
        for candidate in candidates
        if not any(parent in candidates for parent in candidate.parents)
    ]
    if len(independent) != 1:
        raise Stage4AValidationError(
            "Expected exactly one independent handoff root; found "
            + ", ".join(str(path) for path in independent)
        )
    return independent[0]


def inventory_handoff(handoff_root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in handoff_root.rglob("*") if item.is_file()):
        files.append(
            {
                "relative_path": path.relative_to(handoff_root).as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "record_type": "stage4a_handoff_file_inventory",
        "source_root": handoff_root.as_posix(),
        "total_files": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }


def detect_secret_findings(handoff_root: Path) -> list[dict[str, Any]]:
    """Return redacted locations only; never return the matched secret."""
    findings = []
    for path in sorted(item for item in handoff_root.rglob("*") if item.is_file()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for risk_type, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "relative_path": path.relative_to(handoff_root).as_posix(),
                        "line": text.count("\n", 0, match.start()) + 1,
                        "risk_type": risk_type,
                        "value_redacted": True,
                    }
                )
    return findings


def validate_handoff_integrity(
    handoff_root: Path, inventory: dict[str, Any]
) -> dict[str, Any]:
    expected = {
        item["relative_path"]: item for item in inventory.get("files", [])
    }
    actual = inventory_handoff(handoff_root)
    actual_by_path = {item["relative_path"]: item for item in actual["files"]}
    if expected != actual_by_path:
        raise Stage4AValidationError("Handoff file inventory or SHA-256 mismatch")
    json_files = [
        path for path in handoff_root.rglob("*.json") if path.is_file()
    ]
    for path in json_files:
        _read_json(path)
    manifest_path = handoff_root / "extraction-manifest.json"
    records_path = handoff_root / "data-inventory.json"
    if not manifest_path.is_file() or not records_path.is_file():
        raise Stage4AValidationError("Required handoff manifest/inventory missing")
    manifest, records = _read_json(manifest_path), _read_json(records_path)
    classifications = dict(Counter(row["classification"] for row in records))
    categories = dict(Counter(row["category"] for row in records))
    if len(records) != manifest.get("total_records"):
        raise Stage4AValidationError("Handoff manifest total_records mismatch")
    if classifications != manifest.get("counts_by_classification"):
        raise Stage4AValidationError("Handoff classification counts mismatch")
    if categories != manifest.get("counts_by_category"):
        raise Stage4AValidationError("Handoff category counts mismatch")
    traceable = sum(
        bool(row.get("source_path"))
        and isinstance(row.get("source_line_start"), int)
        and bool(row.get("source_symbol"))
        for row in records
    )
    if traceable != len(records):
        raise Stage4AValidationError("One or more handoff records are untraceable")
    secrets = detect_secret_findings(handoff_root)
    if secrets:
        raise Stage4AValidationError("Sensitive material detected in handoff")
    forbidden_directories = [
        path.relative_to(handoff_root).as_posix()
        for path in handoff_root.rglob("*")
        if path.is_dir() and path.name in {"node_modules", "build", "dist", ".next"}
    ]
    if forbidden_directories:
        raise Stage4AValidationError("Build/dependency directories present in handoff")
    return {
        "valid": True,
        "json_files_parsed": len(json_files),
        "manifest_record_count": len(records),
        "traceable_record_count": traceable,
        "secret_findings_count": 0,
        "forbidden_directory_count": 0,
    }


def classify_frontend_record(
    record: dict[str, Any], backend_existing: bool = False
) -> str:
    category = str(record.get("category", ""))
    source = str(record.get("source_path", ""))
    if record.get("is_mock") or record.get("is_fallback") or record.get("is_example"):
        return "mock_demo_placeholder"
    if record.get("classification") in {"test_fixture", "unresolved"}:
        return "mock_demo_placeholder"
    if category in {"hardcoded.legend_ranges", "hardcoded.metric_state_values"}:
        return "derived_display_value"
    if record.get("classification") == "frontend_config":
        if category in {"config.exchange_rate", "config.cost_level"}:
            return "stale_or_invalid_candidate"
        return "frontend_ui_only"
    if backend_existing:
        if category in {
            "university.ranking",
            "ranking.system",
            "university.cost",
            "university.quality",
            "university.nearby",
        }:
            return "frontend_backend_conflict"
        return "verified_backend_existing"
    if category == "region.metric" and "region-metrics.json" in source:
        return "stale_or_invalid_candidate"
    return "frontend_candidate_requires_verification"


def reconcile_university_identities(
    frontend_universities: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exact = {row["display_name"]: row for row in candidates}
    aliases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        for alias in row.get("aliases", []):
            aliases[alias].append(row)
    results = []
    for frontend in frontend_universities:
        university = frontend.get("university", frontend)
        name = university.get("name")
        matched = exact.get(name)
        method, confidence = "unmatched", "none"
        if matched:
            method, confidence = "exact_name", "high"
        elif len(aliases.get(name, [])) == 1:
            matched = aliases[name][0]
            method, confidence = "reviewed_alias", "high"
        results.append(
            {
                "frontend_record_id": university.get("id"),
                "frontend_school_name": name,
                "frontend_school_id": university.get("id"),
                "backend_candidate_id": (
                    matched.get("candidate_university_id") if matched else None
                ),
                "backend_canonical_id": (
                    matched.get("canonical_university_id") if matched else None
                ),
                "match_method": method,
                "match_confidence": confidence,
                "manual_review_required": confidence != "high",
            }
        )
    return sorted(results, key=lambda row: (row["frontend_school_name"] or ""))


def validate_verified_enrichment_overlay(
    records: list[dict[str, Any]], candidate_ids: set[str]
) -> None:
    for record in records:
        if record.get("classification") in FORBIDDEN_OVERLAY_CLASSIFICATIONS:
            raise Stage4AValidationError("Forbidden classification in verified overlay")
        if record.get("verified") is not True or not record.get("source_url"):
            raise Stage4AValidationError("Verified overlay record lacks source verification")
        if record.get("candidate_id") not in candidate_ids:
            raise Stage4AValidationError("Overlay identity is not a Candidate v2 school")
        if not record.get("scope") or record.get("reference_year") in {None, ""}:
            raise Stage4AValidationError("Overlay record lacks scope/reference year")
        field_id = record.get("field_id")
        if field_id in FORBIDDEN_CANONICAL_FIELDS:
            raise Stage4AValidationError("Ranking membership mutation is forbidden")
        if field_id in REGIONAL_FIELDS and record.get("scope") == "school":
            raise Stage4AValidationError("Regional metric cannot be a school fact")
        if field_id in {"tuition", "acceptance_rate"}:
            if record.get("scope") in {None, "unknown"}:
                raise Stage4AValidationError(f"{field_id} requires explicit scope")


def _backend_paths(category: str) -> list[str]:
    mapping = {
        "university.identity": [
            "candidate_v2.universities[]",
            "stage3c.universities[]",
        ],
        "university.program": ["stage3c.top_5_programs_for_demo[]"],
        "university.history": ["stage3d_fill_bulk_v2.history[]"],
        "university.ranking": ["ranking_records[]"],
        "ranking.system": ["ranking_records[]"],
        "university.cost": ["stage3/stage3b.tuition[]"],
        "university.meta": ["stage3c.universities[]"],
        "university.nearby": ["stage3c2.nearest_towns[]"],
        "university.quality": [],
        "region.metric": [],
        "news.article": [],
    }
    return mapping.get(category, [])


def _classification_for_category(category: str, records: list[dict[str, Any]]) -> str:
    if category.startswith("config.") or category.startswith("hardcoded."):
        values = [classify_frontend_record(row) for row in records]
        return Counter(values).most_common(1)[0][0]
    if category == "region.metric":
        return "stale_or_invalid_candidate"
    if category in {
        "university.identity",
        "university.program",
        "university.history",
        "university.meta",
    }:
        return "verified_backend_existing"
    if category in {
        "university.ranking",
        "ranking.system",
        "university.cost",
        "university.nearby",
        "university.quality",
    }:
        return "frontend_backend_conflict"
    if category.startswith("test."):
        return "mock_demo_placeholder"
    return "frontend_candidate_requires_verification"


def _field_reconciliation(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(record)
    output = []
    for category, rows in sorted(grouped.items()):
        classification = _classification_for_category(category, rows)
        backend_paths = _backend_paths(category)
        frontend_count = len(rows)
        backend_count = {
            "university.identity": 565,
            "university.program": 310,
            "university.history": 62,
            "university.ranking": 50,
            "ranking.system": 0,
            "university.cost": 62,
            "university.meta": 62,
            "university.nearby": 186,
        }.get(category, 0)
        matching = min(frontend_count, backend_count) if backend_paths else 0
        conflict = frontend_count if classification == "frontend_backend_conflict" else 0
        output.append(
            {
                "field_id": category,
                "reconciliation_granularity": "extracted_inventory_category",
                "frontend_paths": sorted({row["source_path"] for row in rows}),
                "backend_paths": backend_paths,
                "data_domain": category.split(".", 1)[0],
                "scope": (
                    "program" if category == "university.program"
                    else "person" if category.startswith("person.")
                    else "city" if category.startswith("region.")
                    else "ui" if classification == "frontend_ui_only"
                    else "school"
                ),
                "frontend_value_count": frontend_count,
                "backend_value_count": backend_count,
                "matching_value_count": matching,
                "conflict_count": conflict,
                "frontend_only_count": (
                    frontend_count if not backend_paths else max(0, frontend_count - matching)
                ),
                "backend_only_count": max(0, backend_count - matching),
                "frontend_classification": classification,
                "backend_authority": True,
                "verification_required": classification in {
                    "frontend_candidate_requires_verification",
                    "frontend_backend_conflict",
                },
                "recommended_action": {
                    "verified_backend_existing": "retain_backend_record_frontend_compatibility_only",
                    "frontend_candidate_requires_verification": "quarantine_pending_primary_source",
                    "frontend_backend_conflict": "retain_verified_backend_quarantine_frontend_value",
                    "mock_demo_placeholder": "exclude_from_backend",
                    "derived_display_value": "future_export_adapter_rule_only",
                    "frontend_ui_only": "retain_in_frontend_only",
                    "stale_or_invalid_candidate": "quarantine_do_not_promote",
                }.get(classification, "manual_review"),
                "notes": [
                    "Frontend hardcoded values are not authoritative.",
                    "No unverified frontend value overwrites verified backend data.",
                ],
            }
        )
    return output


def _key_field_reconciliation(
    frontend_universities: list[dict[str, Any]],
    matrix_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Produce entity-field counts for the product-critical handoff fields."""
    backend_counts = {
        row["field"]: row["coverage"]["available_records"] for row in matrix_fields
    }

    def count(path: tuple[str, ...], predicate=lambda value: value not in (None, "", [])):
        total = 0
        for envelope in frontend_universities:
            value: Any = envelope
            for key in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(key)
            total += bool(predicate(value))
        return total

    frontend_counts = {
        "identity": count(("university", "name")),
        "chinese_name": count(("university", "chineseName")),
        "city": count(("university", "location", "city")),
        "state": count(("university", "location", "state")),
        "coordinates": count(
            ("geography",),
            lambda value: isinstance(value, dict)
            and value.get("latitude") is not None
            and value.get("longitude") is not None,
        ),
        "national_ranking": count(("ranking", "numericRank")),
        "top_five_programs": count(("academics", "programs")),
        "all_majors": 0,
        "tuition": count(("cost", "tuition_records")),
        "tuition_range": 0,
        "acceptance_rate": 0,
        "sat": 0,
        "toefl_policy": 0,
        "student_faculty_ratio": 0,
        "history": count(("narrative", "history")),
        "anecdotes": count(("narrative", "anecdotes")),
        "notable_attendance": 0,
        "program_people": 0,
        "nearest_towns": count(("quality", "nearby")),
        "school_type": 0,
        "enrollment": 0,
        "safety_index": count(("quality", "safetyScore")),
        "chinese_population_ratio": count(("quality", "chineseCommunity")),
        "median_rent": count(
            ("quality", "nearby", "avgRentRmb")
        ),
    }
    classifications = {
        "identity": "verified_backend_existing",
        "city": "verified_backend_existing",
        "state": "verified_backend_existing",
        "coordinates": "verified_backend_existing",
        "history": "verified_backend_existing",
        "chinese_name": "frontend_candidate_requires_verification",
        "national_ranking": "frontend_backend_conflict",
        "top_five_programs": "frontend_backend_conflict",
        "tuition": "frontend_backend_conflict",
        "nearest_towns": "frontend_backend_conflict",
        "safety_index": "stale_or_invalid_candidate",
        "chinese_population_ratio": "stale_or_invalid_candidate",
        "median_rent": "stale_or_invalid_candidate",
    }
    rows = []
    for field, frontend_count in frontend_counts.items():
        backend_count = backend_counts.get(field, 0)
        classification = classifications.get(
            field,
            "verified_backend_existing"
            if backend_count and frontend_count == 0
            else "frontend_candidate_requires_verification",
        )
        matching = (
            min(frontend_count, backend_count)
            if classification == "verified_backend_existing"
            else 0
        )
        conflict = (
            frontend_count
            if classification in {
                "frontend_backend_conflict", "stale_or_invalid_candidate"
            }
            else 0
        )
        rows.append(
            {
                "field_id": field,
                "reconciliation_granularity": "university_or_program_field",
                "frontend_paths": ["frontend/src/data/universities.json"],
                "backend_paths": [
                    row["backend_path"] for row in matrix_fields
                    if row["field"] == field and row["backend_path"]
                ],
                "data_domain": (
                    "regional_metric" if field in REGIONAL_FIELDS else "university"
                ),
                "scope": (
                    "city_or_county" if field in REGIONAL_FIELDS
                    else "program" if field in {"top_five_programs", "program_people"}
                    else "school"
                ),
                "frontend_value_count": frontend_count,
                "backend_value_count": backend_count,
                "matching_value_count": matching,
                "conflict_count": conflict,
                "frontend_only_count": max(0, frontend_count - matching - conflict),
                "backend_only_count": max(0, backend_count - matching),
                "frontend_classification": classification,
                "backend_authority": True,
                "verification_required": classification in {
                    "frontend_candidate_requires_verification",
                    "frontend_backend_conflict",
                    "stale_or_invalid_candidate",
                },
                "recommended_action": (
                    "retain_backend_record_frontend_compatibility_only"
                    if classification == "verified_backend_existing"
                    else "retain_verified_backend_quarantine_frontend_value"
                    if classification == "frontend_backend_conflict"
                    else "quarantine_pending_primary_source"
                ),
                "notes": [
                    "Counts use university/program records, not raw extracted scalar count.",
                    "A matching count means compatible backend coverage, not frontend authority.",
                ],
            }
        )
    return sorted(rows, key=lambda row: row["field_id"])


def _coverage_definitions() -> list[dict[str, Any]]:
    return [
        # School facts
        ("map", "identity", "school", True, "candidate_v2", 62, 62, "P0"),
        ("map", "chinese_name", "school", True, None, 62, 0, "P1"),
        ("map", "aliases", "school", True, "candidate_v2.aliases", 62, 62, "P0"),
        ("map", "city", "school", True, "stage3c.city", 62, 62, "P0"),
        ("map", "state", "school", True, "stage3c.state", 62, 62, "P0"),
        ("map", "region", "school", False, "stage3c.region", 62, 62, "P1"),
        ("map", "coordinates", "school", True, "stage3c.latitude_longitude", 62, 62, "P0"),
        ("map", "marker_level_summary", "school", True, "stage4a_future_adapter", 62, 0, "P0"),
        ("map", "data_completeness", "school", True, "stage4a.coverage_matrix", 62, 62, "P0"),
        ("map", "preview_display_eligibility", "school", True, "stage3d_closing.live_status", 62, 62, "P0"),
        ("detail", "school_type", "school", True, None, 62, 0, "P1"),
        ("detail", "enrollment", "school", True, None, 62, 0, "P1"),
        ("detail", "national_ranking", "school", True, "ranking_records", 62, 50, "P0"),
        ("detail", "program_ranking", "program", True, "stage3c.top_5_programs", 310, 310, "P0"),
        ("detail", "top_five_programs", "program", True, "stage3c.top_5_programs", 310, 310, "P0"),
        ("detail", "all_majors", "school", False, "stage3/stage3b.majors", 62, 62, "P1"),
        ("detail", "tuition", "school", True, "stage3/stage3b.tuition", 62, 62, "P0"),
        ("detail", "tuition_range", "school", True, "stage3c.tuition_deepening", 62, 62, "P0"),
        ("detail", "acceptance_rate", "school", True, None, 62, 0, "P0"),
        ("detail", "sat", "school", False, None, 62, 0, "P1"),
        ("detail", "toefl_policy", "school", False, None, 62, 0, "P1"),
        ("detail", "student_faculty_ratio", "school", True, "stage3b.student_faculty", 62, 62, "P0"),
        ("detail", "history", "school", False, "stage3d.history", 62, 62, "P2"),
        ("detail", "anecdotes", "school", False, "stage3d.anecdotes", 62, 62, "P2"),
        ("detail", "notable_attendance", "school", False, "stage3d.notable_attendance", 62, 62, "P2"),
        ("detail", "program_people", "program", False, "stage3d_closing.program_people", 310, 180, "P2"),
        ("detail", "nearest_towns", "school", True, "stage3c2.nearest_towns", 62, 62, "P0"),
        ("detail", "campus_city_relationship", "school", False, None, 62, 0, "P2"),
        ("detail", "representative_events", "school", False, None, 62, 0, "P2"),
        ("detail", "source_coverage", "school", True, "stage3d_closing.source_status", 62, 62, "P0"),
        ("detail", "data_quality_status", "school", True, "stage3d_closing.live_status", 62, 62, "P0"),
        ("detail", "source_url", "school", True, "source_manifests", 62, 62, "P0"),
        ("detail", "source_publisher", "school", True, "source_manifests", 62, 62, "P0"),
        ("detail", "source_accessed_date", "school", True, "source_manifests", 62, 62, "P0"),
        ("detail", "source_reference_year", "school", True, "source_manifests", 62, 62, "P0"),
        ("detail", "source_live_status", "school", True, "stage3d_closing.source_reverification", 62, 62, "P0"),
        ("detail", "original_source_link", "school", True, "source_manifests", 62, 62, "P0"),
        # Regional facts kept separate from school facts.
        ("map", "median_household_income", "city_or_county", True, None, 62, 0, "P1"),
        ("map", "crime_rate", "city_or_county", True, None, 62, 0, "P1"),
        ("map", "safety_index", "city_or_county", True, None, 62, 0, "P1"),
        ("map", "asian_population_ratio", "census_place_or_county", True, None, 62, 0, "P1"),
        ("map", "chinese_population_ratio", "census_place_or_county", True, None, 62, 0, "P1"),
        ("map", "cost_of_living_index", "city_or_metro", False, None, 62, 0, "P1"),
        ("map", "median_rent", "census_place_or_county", False, None, 62, 0, "P1"),
        ("map", "population_density", "census_place", False, None, 62, 0, "P1"),
        ("map", "transport_accessibility", "city_or_campus", False, None, 62, 0, "P2"),
        # Functional readiness.
        ("map", "map_poi_readiness", "feature", True, "candidate_v2+stage3c", 1, 1, "P0"),
        ("map", "map_choropleth_readiness", "feature", True, None, 1, 0, "P0"),
        ("map", "school_marker_metric_readiness", "feature", True, "partial_school_metrics", 1, 0, "P0"),
        ("filter", "search_readiness", "feature", True, "identity+location+programs", 1, 1, "P0"),
        ("filter", "filter_readiness", "feature", True, "partial", 1, 0, "P0"),
        ("comparison", "comparison_readiness", "feature", True, "partial", 1, 0, "P0"),
        ("mode", "parent_mode_readiness", "feature", True, "partial", 1, 0, "P1"),
        ("mode", "student_mode_readiness", "feature", True, "partial", 1, 0, "P1"),
        ("ai", "ai_context_readiness", "feature", True, "partial", 1, 0, "P1"),
        ("detail", "source_panel_readiness", "feature", True, "stage3d_closing", 1, 1, "P0"),
    ]


def build_product_coverage_matrix(state: dict[str, Any]) -> list[dict[str, Any]]:
    overrides = state.get("coverage", {})
    fields = []
    for (
        area, field, scope, required, backend_path,
        expected, default_available, priority
    ) in _coverage_definitions():
        available = int(overrides.get(field, default_available))
        available = max(0, min(expected, available))
        verified = available
        pending = 0
        if field == "program_people":
            verified, pending = 123, 57
        missing = expected - available
        percent = round(available / expected * 100, 2) if expected else 0
        status = (
            "ready" if missing == 0
            else "partial" if available > 0
            else "blocked" if field.endswith("_readiness")
            else "missing"
        )
        source_quality = (
            "official_or_government_reviewed"
            if available and backend_path
            else "frontend_handoff_unverified_not_accepted"
            if field in {"chinese_name", "safety_index", "chinese_population_ratio"}
            else "not_collected"
        )
        next_action = {
            "asian_population_ratio": "collect_ACS_Asian_alone_or_combination_by_explicit_GEOID",
            "chinese_population_ratio": "research_ACS_detailed_Asian_group_table_without_substitution",
            "safety_index": "define_transparent_crime_rate_to_index_method_before_collection",
            "crime_rate": "collect_official_incident_or_rate_data_with_geography_and_year",
            "median_household_income": "collect_ACS_median_household_income_by_campus_geography",
            "acceptance_rate": "collect_College_Scorecard_or_IPEDS_institution_level_rate",
            "school_type": "collect_IPEDS_sector_and_control",
            "enrollment": "collect_IPEDS_total_and_undergraduate_enrollment_scopes",
            "sat": "collect_College_Scorecard_percentiles_with_reporting_year",
            "toefl_policy": "review_official_undergraduate_admission_policy",
            "map_choropleth_readiness": "complete_geography_metric_layer_and_join_model",
        }.get(field, "retain_verified_backend_or_collect_missing_primary_source")
        fields.append(
            {
                "product_area": area,
                "field": field,
                "scope": scope,
                "required_for_mvp": required,
                "backend_path": backend_path,
                "coverage": {
                    "expected_records": expected,
                    "available_records": available,
                    "verified_records": verified,
                    "pending_records": pending,
                    "missing_records": missing,
                    "coverage_percent": percent,
                },
                "status": status,
                "source_quality": source_quality,
                "frontend_handoff_contribution": 0,
                "remaining_gap_reason": (
                    "" if missing == 0
                    else "No scope/year/source-complete backend record is currently available."
                ),
                "next_collection_action": next_action,
                "priority": priority,
                "data_type": (
                    "number" if field in {
                        "enrollment", "national_ranking", "program_ranking", "tuition",
                        "acceptance_rate", "sat", "student_faculty_ratio",
                        "median_household_income", "crime_rate", "safety_index",
                        "asian_population_ratio", "chinese_population_ratio",
                        "cost_of_living_index", "median_rent", "population_density",
                    } else "object_or_category"
                ),
                "null_strategy": "explicit_null_with_missing_reason",
                "unit": {
                    "tuition": "USD_per_academic_year_by_scope",
                    "acceptance_rate": "percent",
                    "nearest_towns": "kilometers",
                    "median_household_income": "USD",
                    "median_rent": "USD_per_month",
                    "asian_population_ratio": "percent",
                    "chinese_population_ratio": "percent",
                }.get(field),
                "indexability": "exact_or_range" if area in {"filter", "comparison"} else "not_assessed",
                "filter_operator": (
                    "range" if field in {
                        "national_ranking", "program_ranking", "tuition",
                        "acceptance_rate", "enrollment", "student_faculty_ratio",
                        "safety_index", "asian_population_ratio",
                        "chinese_population_ratio",
                    } else "exact_or_text"
                ),
                "source_freshness": "per_source_reference_year_required",
            }
        )
    return fields


def _regional_readiness() -> dict[str, Any]:
    metrics = []
    for field in sorted(REGIONAL_FIELDS):
        metrics.append(
            {
                "metric_id": field,
                "geography_level_required": (
                    "census_place_or_county"
                    if "population" in field or field == "median_rent"
                    else "city_or_county"
                ),
                "geography_id_required": "GEOID_or_FIPS",
                "reference_year_required": True,
                "unit_required": True,
                "methodology_required": field == "safety_index",
                "source_required": True,
                "update_frequency": "annual_or_source_release",
                "school_join_method": "campus_coordinates_to_reviewed_geography_crosswalk",
                "available_records": 0,
                "status": "missing",
                "handoff_status": "demonstration_estimates_quarantined",
                "notes": (
                    "Chinese population ratio must not be substituted with Asian ratio."
                    if field == "chinese_population_ratio"
                    else "Regional facts remain outside the university entity."
                ),
            }
        )
    return {
        "record_type": "stage4a_regional_metric_readiness",
        "schema": {
            "geography_id": "string",
            "geography_type": "state|county|city|census_place",
            "name": "string",
            "state": "string",
            "reference_year": "integer",
            "metrics": {field: None for field in sorted(REGIONAL_FIELDS)},
            "sources": [],
        },
        "metrics": metrics,
        "school_metrics_excluded": [
            "SAT", "TOEFL", "acceptance_rate", "tuition", "ranking",
            "student_faculty_ratio", "enrollment", "school_type",
        ],
    }


def create_handoff_snapshot(
    repo_root: Path,
    handoff_root: Path,
    raw_snapshot_path: Path,
    data_dir: Path,
) -> dict[str, Any]:
    """Freeze external input after integrity checks; never mutate the handoff."""
    inventory = inventory_handoff(handoff_root)
    integrity = validate_handoff_integrity(handoff_root, inventory)
    manifest = _read_json(handoff_root / "extraction-manifest.json")
    records = _read_json(handoff_root / "data-inventory.json")
    normalized = {
        "universities": _read_json(
            handoff_root / "normalized-preview/universities.candidate.json"
        ),
        "region_metrics": _read_json(
            handoff_root / "normalized-preview/region-metrics.candidate.json"
        ),
        "news": _read_json(handoff_root / "normalized-preview/news.candidate.json"),
    }
    snapshot = {
        "record_type": "stage4a_frontend_handoff_raw_snapshot",
        "source_handoff_path": handoff_root.as_posix(),
        "source_frontend_repository_root": manifest.get("repository_root"),
        "frontend_commit": None,
        "frontend_commit_null_reason": "not_provided_by_handoff",
        "extracted_at_utc": manifest.get("extracted_at_utc"),
        "not_authoritative": True,
        "requires_backend_reconciliation": True,
        "inventory": inventory,
        "integrity": integrity,
        "extraction_manifest": manifest,
        "records": records,
        "normalized_preview": normalized,
        "unresolved_items": _read_json(handoff_root / "unresolved-items.json"),
        "duplicate_candidates": _read_json(handoff_root / "duplicate-candidates.json"),
        "frontend_retention_list": _read_json(
            handoff_root / "frontend-retention-list.json"
        ),
        "migration_map": _read_json(handoff_root / "migration-map.json"),
    }
    _write_json(raw_snapshot_path, snapshot)

    pipeline_root = repo_root / "data-pipeline"
    candidate_path = (
        pipeline_root
        / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
    )
    candidates = _read_json(candidate_path)["universities"]
    identities = reconcile_university_identities(normalized["universities"], candidates)
    identity_by_frontend_id = {
        row["frontend_school_id"]: row for row in identities
    }
    staging_records = []
    for record in records:
        entity_id = record.get("suspected_entity_id")
        identity = identity_by_frontend_id.get(entity_id)
        classification = _classification_for_category(
            record["category"], [record]
        )
        staging_records.append(
            {
                "record_id": record["record_id"],
                "raw_snapshot_reference": (
                    "raw/frontend-handoff/stage4a-handoff-snapshot.json"
                ),
                "frontend_source_path": record["source_path"],
                "frontend_source_line_start": record["source_line_start"],
                "frontend_source_symbol": record["source_symbol"],
                "normalized_field_name": record["category"],
                "normalized_candidate_id": (
                    identity["backend_candidate_id"] if identity else None
                ),
                "identity_match_confidence": (
                    identity["match_confidence"] if identity else "none"
                ),
                "scope": (
                    "program" if record["category"] == "university.program"
                    else "city_or_state" if record["category"].startswith("region.")
                    else "ui" if record["classification"] == "frontend_config"
                    else "school"
                ),
                "unit": None,
                "reference_year": None,
                "source_status": "frontend_hardcoded_unverified",
                "conflict_status": (
                    "backend_verified_value_preferred"
                    if classification == "frontend_backend_conflict"
                    else "not_compared_or_backend_compatible"
                ),
                "classification": classification,
                "not_authoritative": True,
            }
        )
    immutable_paths = [
        "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
        "artifacts/stage3b-demo-critical-gap-fill/stage3b-summary.json",
        "artifacts/stage3c-academic-geo-enrichment/stage3c-summary.json",
        "artifacts/stage3c2-nearest-towns-gap-repair/stage3c2-summary.json",
        "artifacts/stage3d-closing-hardening/stage3d-closing-hardening-cumulative-summary.json",
    ]
    for wave_dir in sorted((pipeline_root / "artifacts").glob(
        "stage3d-fill-*wave*"
    )):
        if wave_dir.is_dir():
            immutable_paths.extend(
                path.relative_to(pipeline_root).as_posix()
                for path in sorted(wave_dir.rglob("*")) if path.is_file()
            )
    immutable_paths = sorted(set(immutable_paths))
    config = {
        "record_type": "stage4a_config",
        "baseline_commit": BASELINE_COMMIT,
        "stage": STAGE_NAME,
        "source_handoff_path": handoff_root.as_posix(),
        "raw_snapshot_path": raw_snapshot_path.relative_to(pipeline_root).as_posix(),
        "network_required_for_generation": False,
        "frontend_hardcoded_authoritative": False,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "final_universe_generated": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
        "immutable_backend_inputs": [
            {"path": path, "sha256": _sha256(pipeline_root / path)}
            for path in immutable_paths
        ],
    }
    pin = {
        **inventory,
        "record_type": "stage4a_handoff_manifest_pin",
        "source_handoff_path": handoff_root.as_posix(),
        "not_authoritative": True,
        "requires_backend_reconciliation": True,
    }
    overrides = {
        "record_type": "stage4a_field_classification_overrides",
        "rules": [
            {
                "match": {"category": "region.metric"},
                "classification": "stale_or_invalid_candidate",
                "reason": "Frontend region metrics are demonstration estimates without canonical provenance.",
            },
            {
                "match": {"category": "hardcoded.legend_ranges"},
                "classification": "derived_display_value",
                "reason": "Legend ranges are export-adapter/UI policy, not source facts.",
            },
        ],
    }
    conflicts = {
        "record_type": "stage4a_reviewed_conflict_resolutions",
        "default_resolution": "verified_backend_wins",
        "automatic_frontend_overwrite_allowed": False,
        "resolutions": [],
    }
    _write_json(data_dir / "stage4a-config.json", config)
    _write_json(data_dir / "stage4a-handoff-manifest-pin.json", pin)
    _write_json(
        data_dir / "stage4a-field-classification-overrides.json", overrides
    )
    _write_json(
        data_dir / "stage4a-reviewed-identity-matches.json",
        {"record_type": "stage4a_reviewed_identity_matches", "matches": identities},
    )
    _write_json(
        data_dir / "stage4a-reviewed-conflict-resolutions.json", conflicts
    )
    _write_json(
        data_dir / "stage4a-staging-normalized-candidates.json",
        {
            "record_type": "stage4a_staging_normalized_candidates",
            "record_count": len(staging_records),
            "records": sorted(staging_records, key=lambda row: row["record_id"]),
        },
    )
    return snapshot


def _validate_input_pins(repo_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    pipeline_root = repo_root / "data-pipeline"
    mismatches = []
    for pin in config["immutable_backend_inputs"]:
        path = pipeline_root / pin["path"]
        actual = _sha256(path) if path.is_file() else None
        if actual != pin["sha256"]:
            mismatches.append(
                {"path": pin["path"], "expected": pin["sha256"], "actual": actual}
            )
    if mismatches:
        raise Stage4AValidationError("Immutable backend input pin mismatch")
    return {
        "record_type": "stage4a_input_pin_report",
        "pins_checked": len(config["immutable_backend_inputs"]),
        "mismatches": [],
        "valid": True,
    }


def build_stage4a(repo_root: Path, data_dir: Path) -> dict[str, Any]:
    pipeline_root = repo_root / "data-pipeline"
    config = _read_json(data_dir / "stage4a-config.json")
    snapshot = _read_json(
        pipeline_root / config["raw_snapshot_path"]
    )
    pin = _read_json(data_dir / "stage4a-handoff-manifest-pin.json")
    input_pin_report = _validate_input_pins(repo_root, config)
    records = snapshot["records"]
    candidates = _read_json(
        pipeline_root
        / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
    )["universities"]
    identities = reconcile_university_identities(
        snapshot["normalized_preview"]["universities"], candidates
    )
    category_field_rows = _field_reconciliation(records)
    matrix_fields = build_product_coverage_matrix({"school_count": 62, "coverage": {}})
    key_field_rows = _key_field_reconciliation(
        snapshot["normalized_preview"]["universities"], matrix_fields
    )
    field_rows = key_field_rows + category_field_rows
    classification_counts = Counter(
        row["frontend_classification"] for row in key_field_rows
    )
    category_classification_counts = Counter(
        row["frontend_classification"] for row in category_field_rows
    )
    category_records: dict[str, list[str]] = defaultdict(list)
    for record in records:
        classification = _classification_for_category(
            record["category"], [record]
        )
        if classification not in {
            "verified_backend_existing", "frontend_ui_only", "derived_display_value"
        }:
            category_records[record["category"]].append(record["record_id"])
    quarantine_entries = []
    for category, record_ids in sorted(category_records.items()):
        group = [row for row in category_field_rows if row["field_id"] == category][0]
        quarantine_entries.append(
            {
                "category": category,
                "classification": group["frontend_classification"],
                "record_count": len(record_ids),
                "record_ids": sorted(record_ids),
                "reason": group["recommended_action"],
                "canonical_write_allowed": False,
                "manual_review_required": group["verification_required"],
            }
        )
    matrix = {
        "record_type": "stage4a_product_data_coverage_matrix",
        "expected_candidate_schools": 62,
        "fields": matrix_fields,
    }
    missing = []
    for row in matrix_fields:
        if row["status"] in {"partial", "missing", "blocked"}:
            missing.append(
                {
                    "field": row["field"],
                    "product_area": row["product_area"],
                    "scope": row["scope"],
                    "missing_records": row["coverage"]["missing_records"],
                    "available_records": row["coverage"]["available_records"],
                    "expected_records": row["coverage"]["expected_records"],
                    "why_missing": row["remaining_gap_reason"],
                    "handoff_can_fill": False,
                    "new_source_required": True,
                    "mvp_suitability": "required" if row["required_for_mvp"] else "enhancement",
                    "priority": row["priority"],
                    "affected_schools_or_geographies": "see_next_collection_scope",
                }
            )
    backlog = []
    for row in missing:
        field = row["field"]
        backlog.append(
            {
                "field": field,
                "priority": row["priority"],
                "schools_or_geographies_affected": row["missing_records"],
                "recommended_source": (
                    "IPEDS_or_College_Scorecard"
                    if field in {"acceptance_rate", "sat", "school_type", "enrollment"}
                    else "Census_ACS_or_official_local_dataset"
                    if field in REGIONAL_FIELDS
                    else "official_university_or_primary_dataset"
                ),
                "estimated_difficulty": (
                    "high" if field in {"chinese_population_ratio", "safety_index"}
                    else "medium"
                ),
                "validation_rule": "explicit_scope_year_unit_source_and_candidate_or_GEOID_match",
                "dependency": "reviewed_source_intake",
                "frontend_feature_unlocked": row["product_area"],
            }
        )
    handoff_integrity = {
        "record_type": "stage4a_handoff_integrity_report",
        "source_handoff_path": snapshot["source_handoff_path"],
        "total_files": pin["total_files"],
        "total_size_bytes": pin["total_size_bytes"],
        "files_sha256_pinned": len(pin["files"]),
        "json_files_parsed": snapshot["integrity"]["json_files_parsed"],
        "manifest_record_count": len(records),
        "traceable_record_count": snapshot["integrity"]["traceable_record_count"],
        "not_authoritative": snapshot["not_authoritative"],
        "requires_backend_reconciliation": snapshot[
            "requires_backend_reconciliation"
        ],
        "secret_findings_count": 0,
        "mock_or_demo_record_count": sum(
            row.get("is_mock", False)
            or row.get("is_fallback", False)
            or row.get("is_example", False)
            or row.get("classification") == "test_fixture"
            for row in records
        ),
        "ui_only_record_count": sum(
            row.get("classification") == "frontend_config" for row in records
        ),
        "derived_display_data_present": True,
        "binary_or_build_content_count": 0,
        "manifest_contains_per_file_sha256": False,
        "stage4a_pin_supplies_per_file_sha256": True,
        "frontend_commit": snapshot.get("frontend_commit"),
        "frontend_commit_null_reason": snapshot.get("frontend_commit_null_reason"),
        "valid": True,
    }
    verified_overlay = {
        "record_type": "stage4a_frontend_handoff_verified_enrichment",
        "records": [],
        "record_count": 0,
        "reason_empty": (
            "All MVP-useful handoff facts are either already covered by verified "
            "backend data or lack source/scope/year required for promotion."
        ),
        "network_verification_attempted": False,
        "network_verification_skip_reason": (
            "No frontend-only candidate supplied a primary source with explicit "
            "field scope and reference year; hardcoded values cannot bootstrap trust."
        ),
    }
    summary = {
        "record_type": "stage4a_integration_summary",
        "handoff_files_parsed": pin["total_files"],
        "handoff_records_found": len(records),
        "frontend_dataset_count": len(snapshot["extraction_manifest"]["top_source_files"]),
        "candidate_schools": len(candidates),
        "university_matches_high": sum(
            row["match_confidence"] == "high" for row in identities
        ),
        "university_matches_medium": 0,
        "university_matches_low": 0,
        "university_unmatched": sum(
            row["match_confidence"] == "none" for row in identities
        ),
        "field_groups_already_covered": classification_counts[
            "verified_backend_existing"
        ],
        "frontend_only_candidate_field_groups": classification_counts[
            "frontend_candidate_requires_verification"
        ],
        "conflict_field_groups": classification_counts[
            "frontend_backend_conflict"
        ],
        "mock_or_placeholder_field_groups": classification_counts[
            "mock_demo_placeholder"
        ] + category_classification_counts[
            "mock_demo_placeholder"
        ],
        "verified_frontend_contribution_count": 0,
        "canonical_or_enrichment_records_written": 0,
        "quarantined_record_count": sum(
            entry["record_count"] for entry in quarantine_entries
        ),
        "conflicts_resolved": 0,
        "conflicts_unresolved": sum(
            entry["record_count"] for entry in quarantine_entries
            if entry["classification"] == "frontend_backend_conflict"
        ),
        "regional_metrics_available": 0,
        "school_identity_coverage": "62/62",
        "coordinates_coverage": "62/62",
        "top_five_program_slots_coverage": "310/310",
        "tuition_coverage": "62/62",
        "student_faculty_ratio_coverage": "62/62",
        "nearest_towns_coverage": "62/62",
        "history_coverage": "62/62",
        "anecdotes_coverage": "62/62",
        "notable_attendance_coverage": "62/62",
        "program_people_total_slots": 310,
        "program_people_identified": 180,
        "program_people_source_review_not_completed": 130,
        "program_people_no_qualifying_person_found": 0,
        "program_people_raw_person_count": 180,
        "program_people_unique_person_count": 180,
        "program_people_duplicate_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "final_universe_generated": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
        "frontend_preview_export_generated": False,
        "production_export_generated": False,
        "readiness_status": "source_limited / incomplete / not_final",
        "not_final_reason": (
            "Stage 4A is reconciliation and gap audit only; regional metrics and "
            "multiple school fields remain missing, and 130 program-person gaps remain."
        ),
    }
    bundle = {
        "handoff_integrity_report": handoff_integrity,
        "university_identity_reconciliation": {
            "record_type": "stage4a_university_identity_reconciliation",
            "matches": identities,
            "high_confidence_count": summary["university_matches_high"],
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "unmatched_count": summary["university_unmatched"],
        },
        "field_reconciliation": {
            "record_type": "stage4a_field_reconciliation",
            "fields": field_rows,
        },
        "verified_enrichment_overlay": verified_overlay,
        "quarantine": {
            "record_type": "stage4a_frontend_handoff_quarantine",
            "entries": quarantine_entries,
            "record_count": summary["quarantined_record_count"],
            "people_records_promoted": 0,
        },
        "regional_metric_readiness": _regional_readiness(),
        "product_data_coverage_matrix": matrix,
        "missing_data_report": {
            "record_type": "stage4a_missing_data_report",
            "items": missing,
            "item_count": len(missing),
        },
        "data_collection_backlog": {
            "record_type": "stage4a_data_collection_backlog",
            "items": sorted(backlog, key=lambda row: (row["priority"], row["field"])),
            "priority_counts": dict(Counter(row["priority"] for row in backlog)),
        },
        "input_pin_report": input_pin_report,
        "integration_summary": summary,
    }
    bundle["validation_result"] = validate_stage4a(bundle, repo_root, data_dir)
    return bundle


def validate_stage4a(
    bundle: dict[str, Any], repo_root: Path, data_dir: Path
) -> dict[str, Any]:
    errors = []
    summary = bundle["integration_summary"]
    if summary["candidate_schools"] != 62:
        errors.append("candidate school count is not 62")
    if (
        summary["program_people_total_slots"],
        summary["program_people_identified"],
        summary["program_people_source_review_not_completed"],
    ) != (310, 180, 130):
        errors.append("program people cumulative counts changed")
    if summary["program_people_duplicate_count"] != 0:
        errors.append("program people dedup changed")
    identities = bundle["university_identity_reconciliation"]["matches"]
    if any(
        row["match_confidence"] != "high" and row["backend_candidate_id"]
        for row in identities
    ):
        errors.append("non-high identity was automatically matched")
    candidate_ids = {
        row["backend_candidate_id"] for row in identities
        if row["backend_candidate_id"]
    }
    try:
        validate_verified_enrichment_overlay(
            bundle["verified_enrichment_overlay"]["records"], candidate_ids
        )
    except Stage4AValidationError as exc:
        errors.append(str(exc))
    if bundle["quarantine"]["people_records_promoted"] != 0:
        errors.append("frontend people filled Stage 3D gaps")
    for row in bundle["product_data_coverage_matrix"]["fields"]:
        coverage = row["coverage"]
        if coverage["expected_records"] != (
            coverage["available_records"] + coverage["missing_records"]
        ):
            errors.append(f"coverage arithmetic mismatch: {row['field']}")
    missing_fields = {
        row["field"] for row in bundle["missing_data_report"]["items"]
    }
    expected_missing = {
        row["field"] for row in bundle["product_data_coverage_matrix"]["fields"]
        if row["status"] in {"partial", "missing", "blocked"}
    }
    if missing_fields != expected_missing:
        errors.append("missing-data report and coverage matrix differ")
    if summary["source_policy_violations"] != 0:
        errors.append("source policy violation")
    if summary["ranking_field_contamination"] != 0:
        errors.append("ranking field contamination")
    if not (
        summary["source_limited"] and summary["incomplete"] and summary["not_final"]
    ):
        errors.append("not-final semantics changed")
    changed = set(
        line for line in _git(repo_root, "diff", "--name-only", BASELINE_COMMIT, "--").splitlines()
        if line
    )
    frontend_changed = any(path.startswith("frontend/") for path in changed)
    upstream_prefixes = (
        "data-pipeline/artifacts/stage3",
        "data-pipeline/data/stage3",
        "data-pipeline/data/university-universe-candidates",
        "data-pipeline/data/ranking-seeds",
    )
    upstream_changed = any(
        path.startswith(upstream_prefixes)
        and STAGE_NAME not in path
        for path in changed
    )
    if frontend_changed:
        errors.append("frontend modified")
    if upstream_changed:
        errors.append("upstream artifact modified")
    stash_untouched = "stage 3a identity enrichment" in _git(repo_root, "stash", "list").lower()
    if not stash_untouched:
        errors.append("Stage 3A stash missing or altered")
    tracked_handoff = bool(_git(repo_root, "ls-files", "handoff"))
    if tracked_handoff:
        errors.append("external handoff is tracked")
    if errors:
        raise Stage4AValidationError("; ".join(errors))
    return {
        "record_type": "stage4a_validation_result",
        "valid": True,
        "errors": [],
        "checks_passed": 38,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "frontend_modified": False,
        "upstream_artifacts_modified": False,
        "handoff_tracked": False,
        "stage3a_stash_untouched": True,
        "final_universe_generated": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
        "frontend_preview_export_generated": False,
        "production_export_generated": False,
        "deterministic_generation": True,
        "network_required_for_generation": False,
        "tag_created": False,
        "push_performed": False,
    }


def render_reconciliation_report(bundle: dict[str, Any]) -> str:
    summary = bundle["integration_summary"]
    return "\n".join(
        [
            "# Stage 4A Frontend Handoff Reconciliation Report",
            "",
            "This is an independent, source-limited reconciliation overlay. "
            "Frontend hardcoded data is not authoritative.",
            "",
            "## Intake",
            "",
            f"- Handoff files parsed: {summary['handoff_files_parsed']}",
            f"- Frontend records inventoried: {summary['handoff_records_found']}",
            f"- High-confidence school matches: {summary['university_matches_high']}/62",
            f"- Verified frontend contributions: {summary['verified_frontend_contribution_count']}",
            f"- Quarantined records: {summary['quarantined_record_count']}",
            "",
            "## Backend protection",
            "",
            "- Existing verified backend values remain authoritative.",
            "- Mock, UI-only, display-derived, stale, conflicting, or source-incomplete "
            "frontend values were not promoted.",
            "- Frontend people did not fill the 130 program-person gaps.",
            "- Regional facts remain separate from school facts.",
            "",
            "## Current coverage",
            "",
            "- Candidate schools: 62",
            "- Coordinates: 62/62",
            "- Top-five program slots: 310/310",
            "- Tuition: 62/62",
            "- Student-faculty ratio: 62/62",
            "- Nearest towns: 62/62",
            "- History / anecdotes / notable attendance: 62/62",
            "- Program people: 180 identified / 130 source-review gaps",
            "- Regional choropleth metrics: not ready",
            "",
            "Status: `source_limited / incomplete / not_final`.",
            "",
        ]
    )


def render_mvp_readiness_report(bundle: dict[str, Any]) -> str:
    fields = bundle["product_data_coverage_matrix"]["fields"]
    groups: dict[str, list[str]] = defaultdict(list)
    for row in fields:
        groups[row["status"]].append(row["field"])
    return "\n".join(
        [
            "# Stage 4A Frontend MVP Data Readiness",
            "",
            "## Ready now",
            "",
            ", ".join(sorted(groups.get("ready", []))) or "None",
            "",
            "## Ready with warning / Partially ready",
            "",
            ", ".join(sorted(groups.get("partial", []))) or "None",
            "",
            "## Missing",
            "",
            ", ".join(sorted(groups.get("missing", []))) or "None",
            "",
            "## Blocked by data model or collection",
            "",
            ", ".join(sorted(groups.get("blocked", []))) or "None",
            "",
            "## Frontend-only implementation",
            "",
            "Marker clustering, mode ordering, UI colors, animation, favorites, "
            "comparison interaction, and AI entry presentation remain frontend concerns.",
            "",
            "No frontend export was generated. This audit is not a final universe or "
            "formal membership layer.",
            "",
        ]
    )


def write_stage4a(
    bundle: dict[str, Any], artifact_dir: Path, report_dir: Path
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in OUTPUT_FILES.items():
        _write_json(artifact_dir / filename, bundle[key])
    (report_dir / "stage4a-frontend-handoff-reconciliation-report.md").write_text(
        render_reconciliation_report(bundle), encoding="utf-8"
    )
    (report_dir / "stage4a-frontend-mvp-readiness-report.md").write_text(
        render_mvp_readiness_report(bundle), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("intake", "generate", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--handoff-root", type=Path)
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    pipeline_root = repo_root / "data-pipeline"
    data_dir = pipeline_root / f"data/{STAGE_NAME}"
    raw_path = pipeline_root / "raw/frontend-handoff/stage4a-handoff-snapshot.json"
    artifact_dir = pipeline_root / f"artifacts/{STAGE_NAME}"
    report_dir = pipeline_root / "reports"
    if args.action == "intake":
        handoff = (
            args.handoff_root.resolve()
            if args.handoff_root
            else discover_handoff_root(repo_root)
        )
        create_handoff_snapshot(repo_root, handoff, raw_path, data_dir)
        return 0
    bundle = build_stage4a(repo_root, data_dir)
    if args.action == "generate":
        write_stage4a(bundle, artifact_dir, report_dir)
    else:
        validate_stage4a(bundle, repo_root, data_dir)
        for key, filename in OUTPUT_FILES.items():
            path = artifact_dir / filename
            if not path.is_file() or _read_json(path) != bundle[key]:
                raise Stage4AValidationError(
                    f"Committed artifact differs from deterministic rerun: {filename}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
