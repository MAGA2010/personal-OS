"""Cross-batch notable-attendance deduplication for Bulk People v2."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .immutable_input_pins import load_and_verify_input_pins
from .stage3d_fill_bulk_people_v2 import ALLOWED_RELATIONSHIPS, FLAGS, _reject_ranking_fields


OUTPUT_FILES = (
    "stage3d-fill-bulk-people-v2-combined-notable-attendance.json",
    "stage3d-fill-bulk-people-v2-combined-duplicate-records.json",
    "stage3d-fill-bulk-people-v2-combined-summary.json",
)
VALIDATION_FILE = "stage3d-fill-bulk-people-v2-combined-validation-result.json"
STRICT_FIELDS = (
    "canonical_id",
    "university_display_name",
    "person_name",
    "attendance_relationship",
)
OPTIONAL_MERGE_FIELDS = (
    "degree_or_program",
    "major_or_program",
    "major_confidence",
)


class Stage3DFillBulkPeopleV2CombinedDedupValidationError(ValueError):
    """Raised when cross-batch person deduplication fails closed."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkPeopleV2CombinedDedupValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read combined-dedup input {path}: {error}")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def _one_file(directory: Path, suffix: str) -> Path:
    matches = sorted(Path(directory).glob(f"*{suffix}"))
    if len(matches) != 1:
        _fail(f"Combined dedup requires exactly one {suffix} in {directory}")
    return matches[0]


def _record_key(record: dict[str, Any]) -> tuple[str, str]:
    candidate_id = record.get("candidate_id")
    person_id = record.get("canonical_person_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        _fail("Combined attendance requires candidate_id")
    if not isinstance(person_id, str) or not person_id:
        _fail("Combined attendance requires canonical_person_id")
    return candidate_id, person_id


def _load_batch(
    directory: Path, expected_hashes: dict[str, str] | None = None,
) -> tuple[str, list[dict[str, Any]], dict[str, str]]:
    directory = Path(directory)
    batch_id = directory.name
    attendance_path = _one_file(directory, "-notable-attendance.json")
    summary_path = _one_file(directory, "-summary.json")
    hashes = {"attendance": _sha256(attendance_path), "summary": _sha256(summary_path)}
    if expected_hashes is not None and hashes != expected_hashes:
        _fail(f"Immutable {batch_id} SHA-256 protection failed")
    summary = _read(summary_path)
    for flag in (
        "final_universe_generated",
        "official_selection_memberships_generated",
        "frontend_export_generated",
    ):
        if summary.get(flag) is not False:
            _fail(f"{batch_id} violates the combined non-final boundary")
    if summary.get("source_policy_violations") != 0 or summary.get("ranking_field_contamination") != 0:
        _fail(f"{batch_id} cannot enter combined output with policy violations")
    records = _read(attendance_path).get("records", [])
    if not isinstance(records, list):
        _fail(f"{batch_id} attendance records must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for original in records:
        row = deepcopy(original)
        _reject_ranking_fields(row, f"combined_input.{batch_id}")
        key = _record_key(row)
        if key in seen:
            _fail(f"{batch_id} already contains duplicate notable attendance")
        seen.add(key)
        if row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail(f"{batch_id} contains a forbidden attendance relationship")
        anchor = row.get("evidence_anchor")
        if (
            not row.get("source_id")
            or not row.get("source_url")
            or not isinstance(anchor, dict)
            or anchor.get("source_id") != row.get("source_id")
            or row.get("quote_verification_method") != "local_cache_substring_check"
            or anchor.get("quote_verification_method") != "local_cache_substring_check"
        ):
            _fail(f"{batch_id} attendance provenance is incomplete")
        row["_origin_batch"] = batch_id
        normalized.append(row)
    return batch_id, normalized, hashes


def _merge_scalar(rows: list[dict[str, Any]], field: str) -> Any:
    values = [row.get(field) for row in rows if row.get(field) is not None]
    distinct: list[Any] = []
    for value in values:
        if value not in distinct:
            distinct.append(value)
    if len(distinct) > 1:
        _fail(f"Cross-batch duplicate has conflicting {field}")
    return distinct[0] if distinct else None


def _merge_group(key: tuple[str, str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted(rows, key=lambda row: (row["_origin_batch"], row["source_id"]))
    for field in STRICT_FIELDS:
        values = {row.get(field) for row in rows}
        if len(values) != 1:
            _fail(f"Cross-batch duplicate {key} has conflicting {field}")
    primary = deepcopy(rows[0])
    primary.pop("_origin_batch", None)
    for field in OPTIONAL_MERGE_FIELDS:
        primary[field] = _merge_scalar(rows, field)
    source_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_groups.setdefault(row["source_id"], []).append(row)
    source_records = []
    for source_id in sorted(source_groups):
        group = source_groups[source_id]
        first = group[0]
        source_records.append({
            "source_id": source_id,
            "source_url": first["source_url"],
            "publisher": first.get("publisher"),
            "evidence_anchor": first["evidence_anchor"],
            "quote_verification_method": first["quote_verification_method"],
            "origin_batches": sorted({row["_origin_batch"] for row in group}),
        })
    primary.update({
        "source_ids": sorted(source_groups),
        "source_records": source_records,
        "origin_batches": sorted({row["_origin_batch"] for row in rows}),
        "dedup_key": {"candidate_id": key[0], "canonical_person_id": key[1]},
    })
    return primary


def _post_merge_duplicate_count(records: list[dict[str, Any]]) -> int:
    keys = [_record_key(row) for row in records]
    return len(keys) - len(set(keys))


def build_stage3d_fill_bulk_people_v2_combined_dedup(
    batch_dirs: list[Path], pin_manifest_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Merge immutable batch attendance while preserving duplicate provenance."""
    if not isinstance(batch_dirs, list) or not batch_dirs:
        _fail("Combined dedup requires at least one batch directory")
    expected_by_batch: dict[str, dict[str, str]] = {}
    if pin_manifest_path is not None:
        pin_document, pins = load_and_verify_input_pins(
            pin_manifest_path,
            expected_record_type="stage3d_fill_bulk_completion_wave1_immutable_input_pin_manifest",
            fail=_fail,
        )
        for row in pin_document.get("combined_attendance_batches", []):
            attendance_pin = pins.get(row.get("attendance_pin_id"))
            summary_pin = pins.get(row.get("summary_pin_id"))
            if not attendance_pin or not summary_pin:
                _fail("Combined attendance batch manifest contains unresolved pins")
            expected_by_batch[row["batch_id"]] = {
                "attendance": attendance_pin["sha256"],
                "summary": summary_pin["sha256"],
            }
    loaded = [
        _load_batch(Path(directory), expected_by_batch.get(Path(directory).name))
        for directory in batch_dirs
    ]
    if pin_manifest_path is not None and set(expected_by_batch) != {item[0] for item in loaded}:
        _fail("Combined attendance batch directories do not match the input pin manifest")
    batch_ids = [batch_id for batch_id, _, _ in loaded]
    if len(batch_ids) != len(set(batch_ids)):
        _fail("Combined dedup batch IDs must be unique")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    input_hashes: dict[str, dict[str, str]] = {}
    for batch_id, records, hashes in loaded:
        input_hashes[batch_id] = hashes
        for row in records:
            grouped.setdefault(_record_key(row), []).append(row)
    combined = [_merge_group(key, rows) for key, rows in sorted(grouped.items())]
    duplicates = []
    for (candidate_id, person_id), rows in sorted(grouped.items()):
        if len(rows) <= 1:
            continue
        duplicates.append({
            "candidate_id": candidate_id,
            "canonical_person_id": person_id,
            "person_name": rows[0]["person_name"],
            "input_occurrence_count": len(rows),
            "origin_batches": sorted({row["_origin_batch"] for row in rows}),
            "source_ids": sorted({row["source_id"] for row in rows}),
            "resolution": "merged_to_one_logical_attendance_record_preserving_provenance",
        })
    post_merge_duplicates = _post_merge_duplicate_count(combined)
    if post_merge_duplicates != 0:
        _fail("Combined attendance retains duplicate person keys")
    summary = _flags(
        "stage3d_fill_bulk_people_v2_combined_summary",
        batch_count=len(batch_ids),
        batch_ids=batch_ids,
        input_record_count=sum(len(records) for _, records, _ in loaded),
        unique_person_count=len(combined),
        duplicate_person_count=len(duplicates),
        duplicate_records=duplicates,
        post_merge_duplicate_count=post_merge_duplicates,
        input_sha256=input_hashes,
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        dedup_key_fields=["candidate_id", "canonical_person_id"],
        not_final_reason="Combined dedup validates cumulative attendance only; People/Narrative remains source-limited and incomplete.",
    )
    return {
        "stage3d-fill-bulk-people-v2-combined-notable-attendance.json": _flags(
            "stage3d_fill_bulk_people_v2_combined_notable_attendance",
            dedup_key_fields=["candidate_id", "canonical_person_id"],
            records=combined,
        ),
        "stage3d-fill-bulk-people-v2-combined-duplicate-records.json": _flags(
            "stage3d_fill_bulk_people_v2_combined_duplicate_records",
            duplicate_records=duplicates,
        ),
        "stage3d-fill-bulk-people-v2-combined-summary.json": summary,
    }


def validate_stage3d_fill_bulk_people_v2_combined_dedup(
    artifacts: dict[str, dict[str, Any]], batch_dirs: list[Path], pin_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed if combined records retain duplicates or diverge from inputs."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Combined dedup artifact set is incomplete")
    records = artifacts["stage3d-fill-bulk-people-v2-combined-notable-attendance.json"].get("records", [])
    duplicate_count = _post_merge_duplicate_count(records)
    if duplicate_count != 0:
        _fail("Combined notable attendance contains duplicate candidate/person keys")
    expected = build_stage3d_fill_bulk_people_v2_combined_dedup(batch_dirs, pin_manifest_path)
    if artifacts != expected:
        _fail("Combined dedup artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]
    duplicate_records = artifacts["stage3d-fill-bulk-people-v2-combined-duplicate-records.json"]["duplicate_records"]
    if summary["unique_person_count"] != len(records):
        _fail("Combined unique-person summary is inconsistent")
    if summary["duplicate_person_count"] != len(duplicate_records):
        _fail("Combined duplicate-person summary is inconsistent")
    if summary["duplicate_records"] != duplicate_records:
        _fail("Combined duplicate audit is inconsistent across artifacts")
    if summary["post_merge_duplicate_count"] != 0:
        _fail("Combined post-merge duplicate count must be zero")
    if summary["source_policy_violations"] != 0 or summary["ranking_field_contamination"] != 0:
        _fail("Combined policy or ranking-contamination guard failed")
    return {
        "record_type": "stage3d_fill_bulk_people_v2_combined_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 15,
        "batch_count": summary["batch_count"],
        "input_record_count": summary["input_record_count"],
        "unique_person_count": summary["unique_person_count"],
        "duplicate_person_count": summary["duplicate_person_count"],
        "duplicate_records": summary["duplicate_records"],
        "post_merge_duplicate_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_people_v2_combined_dedup(
    artifacts: dict[str, dict[str, Any]], output_dir: Path, validation: dict[str, Any],
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        (output_dir / name).write_text(
            json.dumps(artifacts[name], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / VALIDATION_FILE).write_text(
        json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_stage3d_fill_bulk_people_v2_combined_dedup_report(
    artifacts: dict[str, dict[str, Any]],
) -> str:
    summary = artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]
    duplicate_names = ", ".join(row["person_name"] for row in summary["duplicate_records"]) or "none"
    return f"""# Stage 3D-Fill Bulk People v2 Cross-Batch Deduplication Report

## Combined result

- batches: **{summary['batch_count']}**
- input attendance records: **{summary['input_record_count']}**
- unique people after merge: **{summary['unique_person_count']}**
- duplicate person keys detected in immutable inputs: **{summary['duplicate_person_count']}**
- duplicate people: **{duplicate_names}**
- duplicates remaining after merge: **{summary['post_merge_duplicate_count']}**

The deduplication key is `(candidate_id, canonical_person_id)`. Duplicate input records are not deleted or rewritten. The combined layer emits one logical attendance record and preserves all origin batches and source provenance. Same names at different institutions are not merged.

## Boundaries

- source policy violations: **{summary['source_policy_violations']}**
- ranking field contamination: **{summary['ranking_field_contamination']}**
- final universe generated: **false**
- formal memberships generated: **false**
- frontend export generated: **false**

This combined layer remains `source_limited`, `incomplete`, and `not_final`.
"""
