"""Shared deterministic configuration and immutable-input helpers for Stage 4B."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class Stage4BValidationError(ValueError):
    """Raised when Stage 4B would violate scope, provenance, or product semantics."""


def fail(message: str) -> None:
    raise Stage4BValidationError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Unable to read deterministic Stage 4B input: {path}: {error}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        fail(f"Unable to hash Stage 4B input: {path}: {error}")
    return digest.hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _record_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in (
            "universities",
            "memberships",
            "records",
            "fields",
            "items",
            "sources",
            "inputs",
        ):
            rows = value.get(key)
            if isinstance(rows, list):
                return len(rows)
        return 1
    return 1


PIN_INPUTS = (
    (
        "data-pipeline/data/university-universe-candidates/v2-source-limited/"
        "candidate-memberships.json",
        "candidate_v2",
        "candidate_scope",
    ),
    (
        "data-pipeline/data/ranking-seeds/2026-best-colleges/completion-national/"
        "national-universities-top-50.json",
        "stage2_ranking",
        "ranking_membership_read_only",
    ),
    (
        "data-pipeline/artifacts/stage3b-demo-critical-gap-fill/"
        "stage3b-mvp-universities.json",
        "stage3b",
        "official_identity_programs_and_unitid",
    ),
    (
        "data-pipeline/artifacts/stage3c-academic-geo-enrichment/"
        "stage3c-universities.json",
        "stage3c",
        "canonical_coordinates_and_region",
    ),
    (
        "data-pipeline/artifacts/stage3c2-nearest-towns-gap-repair/"
        "stage3c2-nearest-towns.json",
        "stage3c2",
        "nearest_towns_and_reviewed_place_links",
    ),
    (
        "data-pipeline/artifacts/stage3d-closing-hardening/"
        "stage3d-closing-hardening-cumulative-summary.json",
        "stage3d_closing",
        "people_narrative_closing_counts",
    ),
    (
        "data-pipeline/artifacts/stage4a-frontend-handoff-reconciliation/"
        "stage4a-integration-summary.json",
        "stage4a",
        "reconciliation_counts",
    ),
    (
        "data-pipeline/artifacts/stage4a-frontend-handoff-reconciliation/"
        "stage4a-product-data-coverage-matrix.json",
        "stage4a",
        "product_coverage_baseline",
    ),
    (
        "data-pipeline/artifacts/stage4a-frontend-handoff-reconciliation/"
        "stage4a-data-collection-backlog.json",
        "stage4a",
        "data_collection_backlog",
    ),
    (
        "data-pipeline/data/stage4a-frontend-handoff-reconciliation/"
        "stage4a-handoff-manifest-pin.json",
        "stage4a",
        "external_handoff_integrity",
    ),
    (
        "data-pipeline/cache/stage3b-official/"
        "Most-Recent-Cohorts-Institution_05192025.zip",
        "official_federal_cache",
        "college_scorecard_institution_release",
    ),
    (
        "data-pipeline/cache/stage3b-official/CollegeScorecardDataDictionary.xlsx",
        "official_federal_cache",
        "college_scorecard_dictionary",
    ),
    (
        "data-pipeline/cache/stage3-ipeds/HD2024.zip",
        "official_federal_cache",
        "ipeds_institutional_characteristics",
    ),
    (
        "data-pipeline/cache/stage3c2-geography/2024_Gaz_place_national.zip",
        "official_federal_cache",
        "census_places_gazetteer",
    ),
)


def _schema_and_migration_paths(repo_root: Path) -> Iterable[Path]:
    yield from sorted((repo_root / "data-pipeline/schemas/v1").glob("*.json"))
    yield from sorted((repo_root / "data-pipeline/migrations").glob("*.sql"))


def build_immutable_input_pins(repo_root: Path) -> Dict[str, Any]:
    inputs: List[Dict[str, Any]] = []
    declared_paths = [
        (repo_root / relative, source_stage, role)
        for relative, source_stage, role in PIN_INPUTS
    ]
    declared_paths.extend(
        (path, "schema_or_migration", "validation_contract")
        for path in _schema_and_migration_paths(repo_root)
    )
    for path, source_stage, role in declared_paths:
        if not path.is_file():
            fail(f"Required immutable Stage 4B input is missing: {path}")
        try:
            parsed = read_json(path) if path.suffix == ".json" else None
        except Stage4BValidationError:
            parsed = None
        inputs.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": sha256_file(path),
                "git_blob_sha": git_blob_sha(path),
                "record_count": _record_count(parsed) if parsed is not None else 1,
                "source_stage": source_stage,
                "expected_role": role,
            }
        )
    return {
        "record_type": "stage4b_immutable_input_pins",
        "inputs": inputs,
        "expected_counts": {
            "schools": 62,
            "program_slots": 310,
            "program_people_identified": 180,
            "program_people_gaps": 130,
            "program_people_no_qualifying": 0,
            "duplicate_people": 0,
            "stage4a_verified_contributions": 0,
            "national_ranking_memberships": 50,
        },
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }


def validate_immutable_input_pins(pins: Dict[str, Any], repo_root: Path) -> None:
    if pins.get("record_type") != "stage4b_immutable_input_pins":
        fail("Stage 4B immutable pin record type is invalid")
    expected = pins.get("expected_counts", {})
    required_counts = {
        "schools": 62,
        "program_slots": 310,
        "program_people_identified": 180,
        "program_people_gaps": 130,
        "program_people_no_qualifying": 0,
        "duplicate_people": 0,
        "stage4a_verified_contributions": 0,
        "national_ranking_memberships": 50,
    }
    if any(expected.get(key) != value for key, value in required_counts.items()):
        fail("Stage 4B frozen cumulative counts do not match the approved baseline")
    inputs = pins.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        fail("Stage 4B immutable pin manifest is empty")
    for row in inputs:
        path = repo_root / row.get("path", "")
        if not path.is_file():
            fail(f"Pinned Stage 4B input is missing: {path}")
        if sha256_file(path) != row.get("sha256"):
            fail(f"Pinned Stage 4B SHA-256 mismatch: {path}")
        if git_blob_sha(path) != row.get("git_blob_sha"):
            fail(f"Pinned Stage 4B git blob mismatch: {path}")
    stage4a = read_json(
        repo_root
        / "data-pipeline/artifacts/stage4a-frontend-handoff-reconciliation/"
        "stage4a-integration-summary.json"
    )
    closing = read_json(
        repo_root
        / "data-pipeline/artifacts/stage3d-closing-hardening/"
        "stage3d-closing-hardening-cumulative-summary.json"
    )
    if stage4a.get("candidate_schools") != 62:
        fail("Stage 4A candidate scope changed")
    if stage4a.get("verified_frontend_contribution_count") != 0:
        fail("Stage 4A frontend hardcoded data cannot become Stage 4B authority")
    if (
        closing.get("program_people_total_slots"),
        closing.get("program_people_identified"),
        closing.get("program_people_source_review_not_completed"),
        closing.get("duplicate_count"),
    ) != (310, 180, 130, 0):
        fail("Stage 3D people baseline changed before Stage 4B")
