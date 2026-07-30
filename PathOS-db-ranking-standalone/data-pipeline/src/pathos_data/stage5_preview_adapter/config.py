"""Frozen Stage 5 contract constants and canonical JSON helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


CONTRACT_VERSION = "pathos-preview-v1"
DATASET_VERSION = "stage5-preview-ec8c66e"
SOURCE_CHECKPOINT = "ec8c66e200b566dba4de35987aa5213960749a57"
SOURCE_CHECKPOINT_TIME = "2026-07-24T22:33:02+08:00"

ENABLED_FEATURES = (
    "core_map",
    "marker_summary",
    "school_detail",
    "admissions_section",
    "search",
    "filters",
    "comparison",
    "student_mode",
    "source_panel",
)
DISABLED_FEATURES = (
    "international_applicant_section",
    "parent_mode",
    "ai_context",
    "choropleth",
)

INPUT_PATHS = {
    "mapping_matrix": "data-pipeline/data/stage5-warning-aware-preview/contract-mapping-matrix.json",
    "candidate_identities": "data-pipeline/data/university-universe-candidates/v2-source-limited/candidate-universities.json",
    "stage3b_universities": "data-pipeline/artifacts/stage3b-demo-critical-gap-fill/stage3b-mvp-universities.json",
    "stage3b_program_sources": "data-pipeline/data/stage3b/official-program-observations.json",
    "stage3c_source_manifest": "data-pipeline/data/stage3c/source-manifest.json",
    "stage3c_all_majors": "data-pipeline/artifacts/stage3-program-mvp-detail-pack/program-mvp-majors.json",
    "narrative_history": "data-pipeline/artifacts/stage3d-fill-bulk-completion-v2/stage3d-fill-bulk-v2-history.json",
    "narrative_anecdotes": "data-pipeline/artifacts/stage3d-fill-bulk-completion-v2/stage3d-fill-bulk-v2-anecdotes.json",
    "narrative_notable": "data-pipeline/artifacts/stage3d-fill-bulk-completion-v2/stage3d-fill-bulk-v2-notable-attendance.json",
    "narrative_sources": "data-pipeline/artifacts/stage3d-fill-bulk-completion-v2/stage3d-fill-bulk-v2-source-manifest.json",
    "people_reverification": "data-pipeline/artifacts/stage3d-closing-hardening/stage3d-closing-hardening-source-reverification.json",
    "stage4b_marker": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-marker-summary.json",
    "stage4b_profiles": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-school-profile-metrics.json",
    "stage4b_admissions": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-admissions-metrics.json",
    "stage4b_geography": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-campus-geography-crosswalk.json",
    "stage4b_comparison": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-comparison-records.json",
    "stage4b_search": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-search-index.json",
    "stage4b_source_manifest": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-source-manifest.json",
    "stage4b_provenance": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-field-provenance.json",
    "stage4b_overlay": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-verified-enrichment-overlay.json",
    "stage4b_summary": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-integration-summary.json",
    "stage4b_validation": "data-pipeline/artifacts/stage4b-unified-official-product-data/stage4b-validation-result.json",
    "stage4c_enrollment": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-enrollment-metrics.json",
    "stage4c_test_policy": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-test-policy-metrics.json",
    "stage4c_english_policy": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-english-proficiency-policy.json",
    "stage4c_sat_act": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-sat-act-gap-resolution.json",
    "stage4c_chinese_names": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-chinese-display-names.json",
    "stage4c_places": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-census-place-resolution.json",
    "stage4c_rankings": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-national-ranking-status.json",
    "stage4c_source_manifest": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-source-manifest.json",
    "stage4c_provenance": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-field-provenance.json",
    "stage4c_overlay": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-verified-enrichment-overlay.json",
    "stage4c_pending": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-pending-and-deferred.json",
    "stage4c_cumulative": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-cumulative-stage4b-stage4c-view.json",
    "stage4c_readiness": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-preview-readiness-contract.json",
    "stage4c_summary": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-integration-summary.json",
    "stage4c_validation": "data-pipeline/artifacts/stage4c-mvp-critical-data-completion/stage4c-validation-result.json",
}


class Stage5ContractError(ValueError):
    """Raised when frozen inputs or Preview output violate the contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def index_by(rows: Any, key: str) -> Dict[str, Dict[str, Any]]:
    indexed = {row[key]: row for row in rows}
    if len(indexed) != len(rows):
        raise Stage5ContractError("Duplicate stable IDs in frozen input")
    return indexed
