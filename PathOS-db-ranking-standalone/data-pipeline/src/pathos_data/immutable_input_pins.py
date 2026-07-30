"""Manifest-driven SHA-256 pins for immutable data-pipeline inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


DATA_PIPELINE_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_and_verify_input_pins(
    manifest_path: Path,
    *,
    expected_record_type: str,
    fail: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load a versioned pin manifest and fail closed on path or digest drift."""
    reject = fail or (lambda message: (_ for _ in ()).throw(ValueError(message)))
    try:
        document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        reject(f"Cannot read immutable input pin manifest: {error}")
        raise AssertionError("unreachable")
    if document.get("record_type") != expected_record_type:
        reject("Immutable input pin manifest has an invalid record type")
    rows = document.get("pins")
    if not isinstance(rows, list) or not rows:
        reject("Immutable input pin manifest must contain pins")
    pins: dict[str, dict[str, Any]] = {}
    for original in rows:
        row = dict(original)
        pin_id = row.get("pin_id")
        if not isinstance(pin_id, str) or not pin_id or pin_id in pins:
            reject("Immutable input pin IDs must be non-empty and unique")
        if row.get("immutable") is not True:
            reject(f"Immutable input pin {pin_id} must declare immutable=true")
        raw_path = row.get("path")
        digest = row.get("sha256")
        if not isinstance(raw_path, str) or not raw_path or not isinstance(digest, str) or len(digest) != 64:
            reject(f"Immutable input pin {pin_id} is incomplete")
        path = Path(raw_path)
        resolved = path if path.is_absolute() else DATA_PIPELINE_ROOT / path
        if not resolved.is_file() or _sha256(resolved) != digest:
            reject(f"Immutable input pin {pin_id} failed SHA-256 verification")
        row["resolved_path"] = str(resolved)
        pins[pin_id] = row
    return document, pins
