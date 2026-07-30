"""Deterministic Stage 5 Preview Bundle builder and writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .config import canonical_json, sha256_text
from .loader import load_stage5_inputs
from .transform import build_preview_contract
from .validator import validate_preview_bundle


ARTIFACT_FILES = {
    "manifest": "manifest.json",
    "universities": "universities.json",
    "region_metrics": "region-metrics.json",
    "source_index": "source-index.json",
    "status_dictionary": "status-dictionary.json",
    "feature_readiness": "feature-readiness.json",
    "integration_diagnostics": "integration-diagnostics.json",
    "contract_mapping_matrix": "contract-mapping-matrix.json",
    "validation_result": "validation-result.json",
}


def build_validated_preview_bundle(repo_root: Path) -> Dict[str, Any]:
    bundle = build_preview_contract(load_stage5_inputs(Path(repo_root)))
    validation = validate_preview_bundle(bundle)
    bundle["validation_result"] = validation
    if validation["status"] != "pass":
        failed = [row["label"] for row in validation["checks"] if row["status"] == "fail"]
        raise ValueError("Stage 5 Preview validation failed: {}".format(", ".join(failed)))
    artifact_hashes = {
        ARTIFACT_FILES[key]: sha256_text(canonical_json(value))
        for key, value in bundle.items()
        if key in ARTIFACT_FILES and key != "manifest"
    }
    artifact_hashes.update(
        {
            "university-details/{}.json".format(university_id): sha256_text(canonical_json(detail))
            for university_id, detail in bundle["university_details"].items()
        }
    )
    bundle["manifest"]["artifactHashes"] = dict(sorted(artifact_hashes.items()))
    return bundle


def write_preview_bundle(bundle: Dict[str, Any], output_root: Path) -> None:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for key, relative_path in ARTIFACT_FILES.items():
        (output_root / relative_path).write_text(
            canonical_json(bundle[key]), encoding="utf-8"
        )
    detail_root = output_root / "university-details"
    detail_root.mkdir(parents=True, exist_ok=True)
    for university_id, detail in sorted(bundle["university_details"].items()):
        (detail_root / "{}.json".format(university_id)).write_text(
            canonical_json(detail), encoding="utf-8"
        )
