"""Stage 2G-A official-source incremental priority-program safeguards."""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.priority_program_batch import (
    PriorityProgramBatchValidationError,
    validate_priority_program_batch_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
BATCH = (
    ROOT
    / "data"
    / "ranking-seeds"
    / "2026-best-colleges"
    / "completion-programs-priority"
    / "batch-01"
)


def load(name: str) -> dict:
    return json.loads((BATCH / name).read_text(encoding="utf-8"))


def validate() -> dict:
    return validate_priority_program_batch_artifacts(
        [load("priority-programs-official-batch-01.json")],
        load("identity-mappings.json"),
        load("candidate-observations.json"),
        load("coverage-matrix.json"),
        load("source-manifest.json"),
        load("gap-report.json"),
    )


class PriorityProgramBatchTests(unittest.TestCase):
    def test_committed_official_records_validate_without_claiming_stream_completion(self) -> None:
        result = validate()
        self.assertEqual(result["verified_records_stageable"], 15)
        self.assertTrue(result["all_priority_streams_incomplete"])
        self.assertFalse(result["canonical_universe_created"])
        self.assertFalse(result["selection_memberships_created"])
        self.assertFalse(result["frontend_export_created"])

    def test_official_school_page_record_has_direct_evidence(self) -> None:
        batch = load("priority-programs-official-batch-01.json")
        record = next(item for item in batch["records"] if item["record_id"] == "priority01-iowa-nursing")
        self.assertEqual(record["verification_basis"], "official_school_or_college_page_direct")
        self.assertEqual(record["source_confidence"], "official_institutional")
        self.assertIn("edition", record["evidence"]["directly_supported_fields"])
        self.assertTrue(record["evidence_anchors"])

    def test_stream_with_fewer_than_top_twenty_records_remains_incomplete(self) -> None:
        coverage = load("coverage-matrix.json")
        business = next(item for item in coverage["streams"] if item["stream_id"] == "undergraduate-business-programs")
        self.assertLess(business["accepted_records"], 20)
        self.assertFalse(business["complete_top20_with_boundary_ties"])
        self.assertEqual(business["coverage_status"], "incomplete")

    def test_not_collected_streams_remain_in_coverage_matrix(self) -> None:
        coverage = load("coverage-matrix.json")
        rows = {item["stream_id"]: item for item in coverage["streams"]}
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows["undergraduate-computer-science"]["coverage_status"], "not_collected_in_batch")
        self.assertEqual(rows["undergraduate-economics"]["coverage_status"], "not_collected_in_batch")
        self.assertEqual(rows["undergraduate-psychology"]["coverage_status"], "not_collected_in_batch")

    def test_partial_program_record_cannot_enter_accepted_seed(self) -> None:
        batch = load("priority-programs-official-batch-01.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["verification_status"] = "partially_verified"
        with self.assertRaises(PriorityProgramBatchValidationError):
            validate_priority_program_batch_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"),
            )

    def test_missing_evidence_anchor_fails(self) -> None:
        batch = load("priority-programs-official-batch-01.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["evidence_anchors"] = []
        with self.assertRaises(PriorityProgramBatchValidationError):
            validate_priority_program_batch_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"),
            )

    def test_existing_canonical_identity_is_reused(self) -> None:
        mappings = {item["record_id"]: item["canonical_identity_id"] for item in load("identity-mappings.json")["mappings"]}
        self.assertEqual(mappings["priority01-berkeley-business"], "institution:university-of-california-berkeley")
        self.assertEqual(mappings["priority01-indiana-business"], "institution:indiana-university-bloomington")

    def test_national_record_cannot_enter_priority_program_batch(self) -> None:
        batch = load("priority-programs-official-batch-01.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["ranking_family"] = "national_universities"
        with self.assertRaises(PriorityProgramBatchValidationError):
            validate_priority_program_batch_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"),
            )

    def test_manual_source_cannot_be_confused_with_an_official_batch_source(self) -> None:
        manifest = load("source-manifest.json")
        mutated = copy.deepcopy(manifest)
        mutated["sources"][0]["manual_seed"] = True
        with self.assertRaises(PriorityProgramBatchValidationError):
            validate_priority_program_batch_artifacts(
                [load("priority-programs-official-batch-01.json")], load("identity-mappings.json"),
                load("candidate-observations.json"), load("coverage-matrix.json"), mutated, load("gap-report.json"),
            )

    def test_formal_cli_fails_closed_when_full_artifact_argument_is_missing(self) -> None:
        from pathos_data.__main__ import main

        with patch.object(sys, "argv", [
            "pathos_data", "validate-priority-program-batch",
            "--seed-batch", str(BATCH / "priority-programs-official-batch-01.json"),
            "--identity-mappings", str(BATCH / "identity-mappings.json"),
            "--candidate-observations", str(BATCH / "candidate-observations.json"),
            "--coverage-matrix", str(BATCH / "coverage-matrix.json"),
            "--gap-report", str(BATCH / "gap-report.json"),
            "--result-output", str(BATCH / "ignored-result.json"),
        ]):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
