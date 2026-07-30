"""TDD hardening for the fail-closed Stage 4B validator."""

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pathos_data.stage4b.config import Stage4BValidationError, canonical_json
from pathos_data.stage4b.generator import CORE_ARTIFACT_FILES, write_artifacts
from pathos_data.stage4b.validator import (
    build_validated_stage4b,
    load_stage4b_artifacts,
    validate_committed_stage4b,
    validate_stage4b,
)
from pathos_data.__main__ import main


REPO_ROOT = Path(__file__).resolve().parents[3]


class Stage4BValidatorDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_validated_stage4b(REPO_ROOT)

    def test_validator_passes_all_60_checks(self):
        result = self.bundle["validation_result"]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["check_count"], 60)
        self.assertEqual(result["passed_check_count"], 60)
        self.assertEqual(result["failed_check_count"], 0)

    def test_cache_sha_mismatch_fails_closed(self):
        invalid = deepcopy(self.bundle)
        invalid["cache_manifest"]["caches"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage4BValidationError):
            validate_stage4b(invalid, REPO_ROOT)

    def test_frontend_hardcoded_source_cannot_enter_overlay(self):
        invalid = deepcopy(self.bundle)
        invalid["verified_enrichment_overlay"]["records"][0]["source_ids"] = [
            "frontend-hardcoded"
        ]
        with self.assertRaises(Stage4BValidationError):
            validate_stage4b(invalid, REPO_ROOT)

    def test_people_counts_and_gaps_cannot_change(self):
        invalid = deepcopy(self.bundle)
        invalid["integration_summary"]["program_people_identified"] = 181
        with self.assertRaises(Stage4BValidationError):
            validate_stage4b(invalid, REPO_ROOT)

    def test_no_export_flags_fail_closed(self):
        for field in (
            "final_universe_generated",
            "official_selection_memberships_generated",
            "frontend_export_generated",
            "preview_export_generated",
            "production_export_generated",
        ):
            invalid = deepcopy(self.bundle)
            invalid["integration_summary"][field] = True
            with self.assertRaises(Stage4BValidationError, msg=field):
                validate_stage4b(invalid, REPO_ROOT)

    def test_artifact_round_trip_and_committed_result_match(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            write_artifacts(self.bundle, output)
            loaded = load_stage4b_artifacts(output)
            self.assertEqual(
                canonical_json(loaded),
                canonical_json(self.bundle),
            )
            result = validate_committed_stage4b(output, REPO_ROOT)
            self.assertEqual(result["status"], "pass")

    def test_validation_result_mismatch_rejected(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            invalid = deepcopy(self.bundle)
            invalid["validation_result"]["status"] = "conditional"
            write_artifacts(invalid, output)
            with self.assertRaises(Stage4BValidationError):
                validate_committed_stage4b(output, REPO_ROOT)

    def test_network_disabled_validated_generation(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            regenerated = build_validated_stage4b(REPO_ROOT)
        self.assertEqual(
            canonical_json(regenerated),
            canonical_json(self.bundle),
        )

    def test_all_required_artifact_names_are_declared(self):
        self.assertEqual(len(CORE_ARTIFACT_FILES), 26)
        self.assertIn("validation_result", CORE_ARTIFACT_FILES)
        self.assertIn("input_pin_report", CORE_ARTIFACT_FILES)

    def test_coverage_and_reports_use_source_limited_not_final_semantics(self):
        summary = self.bundle["integration_summary"]
        self.assertTrue(summary["source_limited"])
        self.assertTrue(summary["incomplete"])
        self.assertTrue(summary["not_final"])
        self.assertFalse(summary["map_choropleth_ready"])
        self.assertEqual(
            self.bundle["gap_disclosure"][
                "program_people_source_review_not_completed"
            ],
            130,
        )
        self.assertFalse(self.bundle["gap_disclosure"]["gaps_rendered_as_none"])

    def test_additive_cli_generates_and_validates_offline(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact_dir = root / "artifacts"
            report_dir = root / "reports"
            result_path = root / "validation.json"
            generate_args = [
                "pathos_data",
                "stage4b-unified-official-product-data",
                "--mode",
                "generate",
                "--repo-root",
                str(REPO_ROOT),
                "--output",
                str(artifact_dir),
                "--report-output",
                str(report_dir),
            ]
            with patch.object(sys, "argv", generate_args), patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("network forbidden"),
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(len(list(artifact_dir.glob("*.json"))), 26)
            self.assertEqual(len(list(report_dir.glob("*.md"))), 3)

            validate_args = [
                "pathos_data",
                "stage4b-unified-official-product-data",
                "--mode",
                "validate",
                "--repo-root",
                str(REPO_ROOT),
                "--artifact-dir",
                str(artifact_dir),
                "--result-output",
                str(result_path),
            ]
            with patch.object(sys, "argv", validate_args), patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("network forbidden"),
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(
                json.loads(result_path.read_text(encoding="utf-8"))["status"],
                "pass",
            )


if __name__ == "__main__":
    unittest.main()
