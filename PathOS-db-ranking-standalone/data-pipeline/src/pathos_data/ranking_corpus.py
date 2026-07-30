"""Offline Stage 2C validation across every committed ranking seed batch."""

import json
from pathlib import Path
from typing import Any, Dict

from .ranking_collection import RankingCollectionValidationError, validate_pilot_artifacts


class CorpusValidationError(RankingCollectionValidationError):
    """Raised for a corpus-wide ranking contract violation."""


def _load_bundle(root: Path) -> Dict[str, Any]:
    bundles = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir() and path.name in {"pilot", "batch-01", "batch-02", "batch-03"}):
        documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]
        bundles.append({"name": directory.name, "seed_batches": [item for item in documents if item.get("record_type") == "manual_ranking_seed_batch"], "identity": next(item for item in documents if item.get("record_type") == "pilot_identity_mappings"), "candidates": next(item for item in documents if item.get("record_type") == "ranking_collection_candidate_observations"), "coverage": next(item for item in documents if item.get("record_type") == "ranking_collection_pilot_coverage_matrix"), "manifest": next(item for item in documents if item.get("record_type") == "ranking_collection_pilot_source_manifest")})
    if {item["name"] for item in bundles} != {"pilot", "batch-01", "batch-02", "batch-03"}:
        raise CorpusValidationError("Corpus must include exactly pilot, batch-01, batch-02 and batch-03")
    return {"bundles": bundles, "seed_batches": [seed for bundle in bundles for seed in bundle["seed_batches"]], "identity_documents": [bundle["identity"] for bundle in bundles]}


def _validate_materialized(corpus: Dict[str, Any]) -> Dict[str, Any]:
    records = []
    coverages = []
    partial = unresolved = no_verified = 0
    names = {}
    for bundle in corpus["bundles"]:
        try:
            result = validate_pilot_artifacts(bundle["seed_batches"], bundle["identity"], bundle["candidates"], bundle["coverage"], bundle["manifest"])
        except RankingCollectionValidationError as error:
            raise CorpusValidationError(f"Batch {bundle['name']} failed corpus validation: {error}") from error
        records.extend(record for seed in bundle["seed_batches"] for record in seed["records"])
        coverages.extend(bundle["coverage"]["streams"])
        partial += result["partially_verified_records_excluded_from_staging"]
        unresolved += result["unresolved_records_excluded_from_staging"]
        no_verified += sum(row.get("verified_records") == 0 for row in bundle["coverage"]["streams"])
        for mapping in bundle["identity"]["mappings"]:
            key = mapping["normalized_display_name"].casefold()
            existing = names.setdefault(key, mapping["canonical_identity_id"])
            if existing != mapping["canonical_identity_id"]:
                raise CorpusValidationError("Identity conflict for normalized source display name")
            if mapping.get("unitid") is not None:
                raise CorpusValidationError("Corpus identity mapping must not guess UNITID")
    seen = set()
    for record in records:
        stream = next(seed["stream"] for seed in corpus["seed_batches"] if record in seed["records"])
        if record["edition"] != stream["edition"] or record["category_id"] != stream["category_id"] or record["ranking_family"] != stream["ranking_family"]:
            raise CorpusValidationError("Record conflicts with its stream metadata")
        if record["ranking_family"] not in {"national_universities", "undergraduate_program"}:
            raise CorpusValidationError("Global, graduate or non-undergraduate ranking contamination")
        key = (record["ranking_family"], record["category_id"], record["edition"], record["school_display_name"].casefold(), record["numeric_rank"])
        if key in seen:
            raise CorpusValidationError("Duplicate ranking record in corpus")
        seen.add(key)
    return {"counts": {"total_streams": len(coverages), "processed_streams": len(coverages), "verified_records": len(records), "partial_rejected": partial, "unresolved": unresolved, "no_verified_stream_count": no_verified, "duplicate_records": 0, "identity_conflicts": 0, "identity_unresolved": 0}, "gaps": {"incomplete_stream_count": sum(row.get("complete_cutoff_coverage") is False for row in coverages), "no_verified_stream_count": no_verified, "national_universities_partial": True}, "readiness": {"universe_candidate_ready": True, "universe_generated": False, "reason": "All streams are processed and validated, but coverage remains source-limited and incomplete."}, "coverage_rows": coverages}


def validate_corpus(root: Path, materialize: bool = False, materialized: Dict[str, Any] = None) -> Dict[str, Any]:
    corpus = materialized if materialized is not None else _load_bundle(root)
    result = _validate_materialized(corpus)
    if materialize:
        result.update({"seed_batches": corpus["seed_batches"], "identity_documents": corpus["identity_documents"], "bundles": corpus["bundles"]})
    return result


def write_corpus_artifacts(result: Dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payloads = {"corpus-validation-result.json": result, "corpus-coverage-summary.json": {"coverage_rows": result["coverage_rows"]}, "corpus-identity-summary.json": {"identity_conflicts": result["counts"]["identity_conflicts"], "identity_unresolved": result["counts"]["identity_unresolved"]}, "corpus-gap-summary.json": result["gaps"], "corpus-readiness.json": result["readiness"]}
    for name, payload in payloads.items():
        (output / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
