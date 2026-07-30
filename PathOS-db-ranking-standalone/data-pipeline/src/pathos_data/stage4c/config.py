"""Shared deterministic helpers and immutable-input policy for Stage 4C."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class Stage4CValidationError(ValueError):
    """Raised when Stage 4C would weaken scope, provenance, or gap semantics."""


def fail(message: str) -> None:
    raise Stage4CValidationError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Unable to read Stage 4C input {path}: {error}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        fail(f"Unable to hash Stage 4C input {path}: {error}")
    return digest.hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def record_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in (
            "universities", "records", "fields", "items", "sources", "inputs",
            "areas", "memberships",
        ):
            if isinstance(value.get(key), list):
                return len(value[key])
    return 1


def _frozen_paths(repo_root: Path) -> Iterable[tuple[Path, str, str]]:
    pipeline = repo_root / "data-pipeline"
    fixed = (
        "data/university-universe-candidates/v2-source-limited/candidate-memberships.json",
        "data/ranking-seeds/2026-best-colleges/completion-national/national-universities-top-50.json",
        "artifacts/stage3d-closing-hardening/stage3d-closing-hardening-cumulative-summary.json",
    )
    for relative in fixed:
        yield pipeline / relative, "upstream_frozen", "scope_and_counts"
    for namespace in (
        pipeline / "data/stage4b-unified-official-product-data",
        pipeline / "artifacts/stage4b-unified-official-product-data",
    ):
        for path in sorted(namespace.glob("*.json")):
            yield path, "stage4b", "stage4b_read_only_input"
    for path in sorted((pipeline / "reports").glob("stage4b-*.md")):
        yield path, "stage4b", "stage4b_read_only_report"
    for path in (
        pipeline / "cache/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip",
        pipeline / "cache/stage3b-official/CollegeScorecardDataDictionary.xlsx",
        pipeline / "cache/stage3-ipeds/HD2024.zip",
        pipeline / "cache/stage3c2-geography/2024_Gaz_place_national.zip",
    ):
        yield path, "official_federal_cache", "official_frozen_source"
    for path in sorted((pipeline / "schemas/v1").glob("*.json")):
        yield path, "schema", "validation_contract"
    for path in sorted((pipeline / "migrations").glob("*.sql")):
        yield path, "migration", "validation_contract"


def build_immutable_input_pins(repo_root: Path) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for path, stage, role in _frozen_paths(repo_root):
        if not path.is_file():
            fail(f"Required Stage 4C input is missing: {path}")
        parsed = read_json(path) if path.suffix == ".json" else None
        rows.append({
            "path": path.relative_to(repo_root).as_posix(),
            "sha256": sha256_file(path),
            "git_blob_sha": git_blob_sha(path),
            "record_count": record_count(parsed) if parsed is not None else 1,
            "stage": stage,
            "role": role,
        })
    return {
        "record_type": "stage4c_immutable_input_pins",
        "inputs": rows,
        "expected_counts": {
            "schools": 62,
            "national_ranking_memberships": 50,
            "program_slots": 310,
            "identified_people": 180,
            "program_people_gaps": 130,
            "duplicates": 0,
            "stage4b_overlay_records": 710,
        },
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
    }


def validate_immutable_input_pins(pins: Dict[str, Any], repo_root: Path) -> None:
    expected = {
        "schools": 62,
        "national_ranking_memberships": 50,
        "program_slots": 310,
        "identified_people": 180,
        "program_people_gaps": 130,
        "duplicates": 0,
        "stage4b_overlay_records": 710,
    }
    if pins.get("record_type") != "stage4c_immutable_input_pins":
        fail("Stage 4C input-pin record type is invalid")
    if pins.get("expected_counts") != expected:
        fail("Stage 4C frozen counts differ from the approved baseline")
    if not pins.get("inputs"):
        fail("Stage 4C input pins are empty")
    for row in pins["inputs"]:
        path = repo_root / row["path"]
        if not path.is_file():
            fail(f"Pinned Stage 4C input is missing: {path}")
        if sha256_file(path) != row["sha256"] or git_blob_sha(path) != row["git_blob_sha"]:
            fail(f"Pinned Stage 4C input changed: {path}")
