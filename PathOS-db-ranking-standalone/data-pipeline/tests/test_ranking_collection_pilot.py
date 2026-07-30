"""Stage 2B1 verified-only ranking-record and identity-staging behavior."""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.ranking_collection import (
    RankingCollectionValidationError,
    build_identity_index,
    stage_verified_pilot_stream,
    validate_pilot_artifacts,
    validate_pilot_stream,
)
from pathos_data.__main__ import main


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ranking-collection"
PILOT = ROOT / "data" / "ranking-seeds" / "2026-best-colleges" / "pilot"
BATCH_01 = ROOT / "data" / "ranking-seeds" / "2026-best-colleges" / "batch-01"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RankingCollectionPilotTests(unittest.TestCase):
    def test_verified_record_with_full_evidence_enters_formal_staging(self) -> None:
        staged = stage_verified_pilot_stream(
            load_fixture("verified-seed-batch.json"),
            load_fixture("identity-mappings.json"),
        )
        self.assertEqual(staged["records"][0]["verification_status"], "verified")

    def test_partially_verified_record_cannot_enter_formal_ranking_staging(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["verification_status"] = "partially_verified"
        with self.assertRaises(RankingCollectionValidationError):
            stage_verified_pilot_stream(batch, load_fixture("identity-mappings.json"))

    def test_verified_record_requires_full_direct_evidence(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["evidence"]["directly_supported_fields"].remove("edition")
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_verified_record_missing_evidence_anchors_is_rejected(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        del batch["records"][0]["evidence_anchors"]
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_evidence_anchor_field_must_be_directly_supported(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["evidence_anchors"][0]["field"] = "unverified_field"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_evidence_anchor_empty_quote_is_rejected(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["evidence_anchors"][0]["quote"] = ""
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_inferred_edition_cannot_be_declared_directly_supported(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["edition_evidence"] = "edition_inferred_from_release_cycle"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_seed_record_requires_a_source(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        del batch["records"][0]["source"]
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_unresolved_identity_does_not_create_a_canonical_university(self) -> None:
        mappings = load_fixture("identity-mappings.json")
        mappings["mappings"][0]["resolution_status"] = "unresolved"
        mappings["mappings"][0]["canonical_identity_id"] = None
        mappings["mappings"][0]["official_institution_name"] = None
        staged = stage_verified_pilot_stream(load_fixture("verified-seed-batch.json"), mappings)
        record = staged["records"][0]
        self.assertIsNone(record["canonical_university_id"])
        self.assertNotIn("created_canonical_university", record)

    def test_source_display_name_and_tied_rank_are_preserved(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["records"][0]["displayed_rank"] = "#6 (tie)"
        batch["records"][0]["tied"] = True
        staged = stage_verified_pilot_stream(batch, load_fixture("identity-mappings.json"))
        record = staged["records"][0]
        self.assertEqual(record["source_display_name"], "Tepper School of Business")
        self.assertEqual(record["displayed_rank"], "#6 (tie)")
        self.assertTrue(record["tied"])

    def test_cutoff_rank_with_tie_is_accepted_without_rank_rewrite(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        batch["stream"]["ranking_family"] = "national_universities"
        batch["stream"]["category_id"] = "national-universities"
        batch["stream"]["expected_cutoff"] = 50
        batch["records"][0]["ranking_family"] = "national_universities"
        batch["records"][0]["category_id"] = "national-universities"
        batch["records"][0]["numeric_rank"] = 50
        batch["records"][0]["displayed_rank"] = "#50 (tie)"
        batch["records"][0]["tied"] = True
        validate_pilot_stream(batch)

    def test_edition_and_category_mismatch_are_rejected(self) -> None:
        edition_mismatch = load_fixture("verified-seed-batch.json")
        edition_mismatch["records"][0]["edition"] = "2025 Best Colleges"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(edition_mismatch)
        category_mismatch = load_fixture("verified-seed-batch.json")
        category_mismatch["records"][0]["category_id"] = "business-accounting"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(category_mismatch)

    def test_duplicate_pilot_seed_record_is_rejected(self) -> None:
        batch = load_fixture("verified-seed-batch.json")
        duplicate = copy.deepcopy(batch["records"][0])
        duplicate["record_id"] = "duplicate-tepper-business"
        batch["records"].append(duplicate)
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_stream(batch)

    def test_duplicate_school_aliases_share_one_canonical_identity(self) -> None:
        mappings = load_fixture("identity-mappings.json")
        mappings["mappings"].append({
            "record_id": "alias-record",
            "source_display_name": "Carnegie Mellon University",
            "normalized_display_name": "Carnegie Mellon University",
            "official_institution_name": "Carnegie Mellon University",
            "aliases": ["Tepper School of Business"],
            "unitid": None,
            "identity_confidence": "high",
            "identity_source": {"source_id": "test-source", "url": "https://example.invalid/identity"},
            "resolution_status": "resolved",
            "canonical_identity_id": "institution:carnegie-mellon-university"
        })
        index = build_identity_index(mappings)
        self.assertEqual(len(index), 1)

    def test_committed_pilot_batches_are_verified_and_stageable(self) -> None:
        identities = json.loads((PILOT / "identity-mappings.json").read_text(encoding="utf-8"))
        for name in (
            "national-universities.json",
            "undergraduate-business-programs.json",
            "engineering-aerospace.json",
        ):
            batch = json.loads((PILOT / name).read_text(encoding="utf-8"))
            staged = stage_verified_pilot_stream(batch, identities)
            self.assertTrue(all(record["verification_status"] == "verified" for record in staged["records"]))

    def test_partially_verified_candidate_is_excluded_from_pilot_staging(self) -> None:
        result = validate_pilot_artifacts(
            [load_pilot("national-universities.json"), load_pilot("undergraduate-business-programs.json"), load_pilot("engineering-aerospace.json")],
            load_pilot("identity-mappings.json"),
            load_pilot("candidate-observations.json"),
            load_pilot("coverage-matrix.json"),
            load_pilot("source-manifest.json"),
        )
        self.assertEqual(result["verified_records_stageable"], 6)
        self.assertEqual(result["partially_verified_records_excluded_from_staging"], 2)

    def test_tepper_without_direct_edition_evidence_is_a_partial_candidate(self) -> None:
        business_batch = load_pilot("undergraduate-business-programs.json")
        candidates = load_pilot("candidate-observations.json")
        self.assertNotIn("pilot-business-tepper", {record["record_id"] for record in business_batch["records"]})
        tepper = next(item for item in candidates["observations"] if item["candidate_id"] == "pilot-business-tepper-partial")
        self.assertEqual(tepper["verification_status"], "partially_verified")
        self.assertEqual(tepper["edition_evidence"], "edition_inferred_from_release_cycle")
        self.assertNotIn("edition", tepper["directly_supported_fields"])

    def test_cornell_2025_26_edition_remains_partial(self) -> None:
        candidates = load_pilot("candidate-observations.json")
        cornell = next(item for item in candidates["observations"] if item["candidate_id"] == "pilot-business-cornell-partial")
        self.assertEqual(cornell["verification_status"], "partially_verified")
        self.assertEqual(cornell["edition_evidence"], "edition_ambiguous")

    def test_verified_candidate_observation_is_rejected(self) -> None:
        candidates = load_pilot("candidate-observations.json")
        candidates["observations"][0]["verification_status"] = "verified"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_artifacts(
                [load_pilot("national-universities.json"), load_pilot("undergraduate-business-programs.json"), load_pilot("engineering-aerospace.json")],
                load_pilot("identity-mappings.json"), candidates,
                load_pilot("coverage-matrix.json"), load_pilot("source-manifest.json"),
            )

    def test_coverage_matrix_count_mismatch_is_rejected(self) -> None:
        coverage = load_pilot("coverage-matrix.json")
        coverage["streams"][0]["verified_records"] = 50
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_artifacts(
                [load_pilot("national-universities.json"), load_pilot("undergraduate-business-programs.json"), load_pilot("engineering-aerospace.json")],
                load_pilot("identity-mappings.json"), load_pilot("candidate-observations.json"),
                coverage, load_pilot("source-manifest.json"),
            )

    def test_zero_verified_stream_is_allowed_only_with_a_no_verified_reason(self) -> None:
        coverage = load_pilot("coverage-matrix.json")
        zero = copy.deepcopy(coverage["streams"][0])
        zero.update({"stream_id": "unverified-sweep-stream", "discovered_records": 0, "verified_records": 0, "partially_verified_records": 0, "unresolved_records": 0, "ties_observed": 0, "source_count": 0, "official_source_count": 0, "university_official_cross_source_count": 0, "identity_resolved_count": 0, "identity_unresolved_count": 0, "no_verified_reason": "No lawful direct Top-20 evidence found."})
        coverage["streams"].append(zero)
        result = validate_pilot_artifacts(
            [load_pilot("national-universities.json"), load_pilot("undergraduate-business-programs.json"), load_pilot("engineering-aerospace.json")],
            load_pilot("identity-mappings.json"), load_pilot("candidate-observations.json"), coverage,
            load_pilot("source-manifest.json"),
        )
        self.assertEqual(result["verified_records_stageable"], 6)

    def test_evidence_anchor_source_must_exist_in_source_manifest(self) -> None:
        batches = [load_pilot(name) for name in (
            "national-universities.json", "undergraduate-business-programs.json", "engineering-aerospace.json",
        )]
        batches[0]["records"][0]["evidence_anchors"][0]["source_id"] = "missing-source"
        with self.assertRaises(RankingCollectionValidationError):
            validate_pilot_artifacts(
                batches, load_pilot("identity-mappings.json"), load_pilot("candidate-observations.json"),
                load_pilot("coverage-matrix.json"), load_pilot("source-manifest.json"),
            )

    def test_formal_cli_rejects_missing_source_manifest(self) -> None:
        with patch.object(sys, "argv", [
            "pathos_data", "validate-ranking-pilot", "--seed-batch", str(PILOT / "national-universities.json"),
            "--identity-mappings", str(PILOT / "identity-mappings.json"),
        ]):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)

    def test_formal_cli_rejects_missing_coverage_matrix(self) -> None:
        with patch.object(sys, "argv", [
            "pathos_data", "validate-ranking-pilot", "--seed-batch", str(PILOT / "national-universities.json"),
            "--identity-mappings", str(PILOT / "identity-mappings.json"),
            "--source-manifest", str(PILOT / "source-manifest.json"),
            "--candidate-observations", str(PILOT / "candidate-observations.json"),
            "--result-output", str(PILOT / "validation-result.json"),
        ]):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)

    def test_formal_cli_rejects_missing_candidate_observations(self) -> None:
        with patch.object(sys, "argv", [
            "pathos_data", "validate-ranking-pilot", "--seed-batch", str(PILOT / "national-universities.json"),
            "--identity-mappings", str(PILOT / "identity-mappings.json"),
            "--source-manifest", str(PILOT / "source-manifest.json"),
            "--coverage-matrix", str(PILOT / "coverage-matrix.json"),
            "--result-output", str(PILOT / "validation-result.json"),
        ]):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)

    def test_committed_batch_01_artifacts_validate_full_path(self) -> None:
        names = (
            "business-accounting.json", "business-analytics.json",
            "business-management-information-systems.json",
            "business-production-operations-management.json", "business-management.json",
            "business-supply-chain-management-logistics.json", "business-real-estate.json",
        )
        result = validate_pilot_artifacts(
            [json.loads((BATCH_01 / name).read_text(encoding="utf-8")) for name in names],
            json.loads((BATCH_01 / "identity-mappings.json").read_text(encoding="utf-8")),
            json.loads((BATCH_01 / "candidate-observations.json").read_text(encoding="utf-8")),
            json.loads((BATCH_01 / "coverage-matrix.json").read_text(encoding="utf-8")),
            json.loads((BATCH_01 / "source-manifest.json").read_text(encoding="utf-8")),
        )
        self.assertEqual(result["verified_records_stageable"], 7)
        self.assertEqual(result["partially_verified_records_excluded_from_staging"], 0)


def load_pilot(name: str) -> dict:
    return json.loads((PILOT / name).read_text(encoding="utf-8"))
