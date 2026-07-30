"""Stage 2H Top-20 completion-attempt safeguards."""

import json
import copy
import unittest
from pathlib import Path

from pathos_data.program_top20_completion import (
    ProgramTop20CompletionValidationError,
    validate_program_top20_completion_attempt_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = (
    ROOT
    / "data"
    / "ranking-seeds"
    / "2026-best-colleges"
    / "completion-programs-top20-attempt"
)


class ProgramTop20CompletionAttemptTests(unittest.TestCase):
    def test_attempt_bundle_has_a_readiness_summary_for_every_stream(self) -> None:
        """A completion attempt cannot silently omit an in-scope stream."""
        summary_path = ATTEMPT / "completion-readiness-summary.json"
        self.assertTrue(summary_path.exists())
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["streams_assessed"], 28)
        self.assertFalse(summary["program_top20_completion_ready"])

    def load(self, name: str) -> dict:
        return json.loads((ATTEMPT / name).read_text(encoding="utf-8"))

    def validate(self) -> dict:
        return validate_program_top20_completion_attempt_artifacts(
            self.load("accepted-seed-batches.json"), self.load("identity-mappings.json"),
            self.load("candidate-observations.json"), self.load("coverage-matrix.json"),
            self.load("source-manifest.json"), self.load("gap-report.json"),
            self.load("duplicate-dedupe-report.json"), self.load("manual-seed-needed-report.json"),
            self.load("completion-readiness-summary.json"),
            ROOT / "data" / "ranking-seeds" / "2026-best-colleges",
        )

    def test_committed_attempt_represents_existing_corpus_without_fake_additions(self) -> None:
        result = self.validate()
        self.assertEqual(result["accepted_program_records_considered"], 80)
        self.assertEqual(result["new_verified_records_stageable"], 0)
        self.assertEqual(result["incomplete_stream_count"], 27)
        self.assertEqual(result["manual_seed_needed_stream_count"], 1)

    def test_incomplete_stream_cannot_be_promoted_to_complete_without_boundary_proof(self) -> None:
        coverage = copy.deepcopy(self.load("coverage-matrix.json"))
        coverage["streams"][0]["stream_status"] = "complete"
        with self.assertRaises(ProgramTop20CompletionValidationError):
            validate_program_top20_completion_attempt_artifacts(
                self.load("accepted-seed-batches.json"), self.load("identity-mappings.json"),
                self.load("candidate-observations.json"), coverage, self.load("source-manifest.json"),
                self.load("gap-report.json"), self.load("duplicate-dedupe-report.json"),
                self.load("manual-seed-needed-report.json"), self.load("completion-readiness-summary.json"),
                ROOT / "data" / "ranking-seeds" / "2026-best-colleges",
            )

    def test_manual_seed_needed_economics_is_allowed_without_fake_seed(self) -> None:
        coverage = {row["stream_id"]: row for row in self.load("coverage-matrix.json")["streams"]}
        self.assertEqual(coverage["undergraduate-economics"]["accepted_record_count"], 0)
        self.assertEqual(coverage["undergraduate-economics"]["stream_status"], "manual_seed_needed")
        self.assertEqual(self.load("accepted-seed-batches.json")["batches"], [])

    def test_unvalidated_new_seed_or_duplicate_report_is_rejected(self) -> None:
        seeds = copy.deepcopy(self.load("accepted-seed-batches.json"))
        seeds["batches"].append({"records": [{"record_id": "invented"}]})
        with self.assertRaises(ProgramTop20CompletionValidationError):
            validate_program_top20_completion_attempt_artifacts(
                seeds, self.load("identity-mappings.json"), self.load("candidate-observations.json"),
                self.load("coverage-matrix.json"), self.load("source-manifest.json"), self.load("gap-report.json"),
                self.load("duplicate-dedupe-report.json"), self.load("manual-seed-needed-report.json"),
                self.load("completion-readiness-summary.json"), ROOT / "data" / "ranking-seeds" / "2026-best-colleges",
            )
        dedupe = copy.deepcopy(self.load("duplicate-dedupe-report.json"))
        dedupe["duplicate_accepted_records_found"] = 1
        with self.assertRaises(ProgramTop20CompletionValidationError):
            validate_program_top20_completion_attempt_artifacts(
                self.load("accepted-seed-batches.json"), self.load("identity-mappings.json"), self.load("candidate-observations.json"),
                self.load("coverage-matrix.json"), self.load("source-manifest.json"), self.load("gap-report.json"), dedupe,
                self.load("manual-seed-needed-report.json"), self.load("completion-readiness-summary.json"), ROOT / "data" / "ranking-seeds" / "2026-best-colleges",
            )

    def test_final_universe_or_frontend_flags_are_rejected(self) -> None:
        summary = copy.deepcopy(self.load("completion-readiness-summary.json"))
        summary["frontend_export_created"] = True
        with self.assertRaises(ProgramTop20CompletionValidationError):
            validate_program_top20_completion_attempt_artifacts(
                self.load("accepted-seed-batches.json"), self.load("identity-mappings.json"), self.load("candidate-observations.json"),
                self.load("coverage-matrix.json"), self.load("source-manifest.json"), self.load("gap-report.json"), self.load("duplicate-dedupe-report.json"),
                self.load("manual-seed-needed-report.json"), summary, ROOT / "data" / "ranking-seeds" / "2026-best-colleges",
            )
