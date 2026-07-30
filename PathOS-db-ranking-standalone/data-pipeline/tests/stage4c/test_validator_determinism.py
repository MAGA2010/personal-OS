"""TDD contracts for the fail-closed Stage 4C validator and generator."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pathos_data.__main__ import main
from pathos_data.stage4c.config import Stage4CValidationError, canonical_json
from pathos_data.stage4c.generator import ARTIFACT_FILES, write_artifacts
from pathos_data.stage4c.validator import (
    build_validated_stage4c,
    validate_committed_stage4c,
    validate_stage4c,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class Stage4CValidatorDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_validated_stage4c(REPO_ROOT)

    def test_validator_passes_86_checks(self):
        result = self.bundle["validation_result"]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["check_count"], 86)
        self.assertEqual(result["passed_check_count"], 86)

    def test_all_28_artifacts_are_declared(self):
        self.assertEqual(len(ARTIFACT_FILES), 28)

    def test_program_people_and_gaps_fail_closed(self):
        invalid = deepcopy(self.bundle)
        invalid["integration_summary"]["program_people_identified"] = 181
        with self.assertRaises(Stage4CValidationError):
            validate_stage4c(invalid, REPO_ROOT)

    def test_frontend_export_flags_fail_closed(self):
        for field in (
            "frontend_modified", "final_universe_generated",
            "official_memberships_generated", "frontend_export_generated",
            "preview_export_generated", "production_export_generated",
        ):
            invalid = deepcopy(self.bundle)
            invalid["integration_summary"][field] = True
            with self.assertRaises(Stage4CValidationError):
                validate_stage4c(invalid, REPO_ROOT)

    def test_cache_sha_mismatch_fails_closed(self):
        invalid = deepcopy(self.bundle)
        invalid["cache_manifest"]["caches"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage4CValidationError):
            validate_stage4c(invalid, REPO_ROOT)

    def test_unverified_record_cannot_enter_overlay(self):
        invalid = deepcopy(self.bundle)
        invalid["verified_enrichment_overlay"]["records"][0][
            "verification_status"
        ] = "pending"
        with self.assertRaises(Stage4CValidationError):
            validate_stage4c(invalid, REPO_ROOT)

    def test_network_disabled_generation_is_deterministic(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            regenerated = build_validated_stage4c(REPO_ROOT)
        self.assertEqual(canonical_json(regenerated), canonical_json(self.bundle))

    def test_committed_result_matches_rerun(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            write_artifacts(self.bundle, output)
            result = validate_committed_stage4c(output, REPO_ROOT)
            self.assertEqual(result["status"], "pass")
            invalid = json.loads(
                (output / ARTIFACT_FILES["validation_result"]).read_text()
            )
            invalid["status"] = "conditional"
            (output / ARTIFACT_FILES["validation_result"]).write_text(
                canonical_json(invalid), encoding="utf-8"
            )
            with self.assertRaises(Stage4CValidationError):
                validate_committed_stage4c(output, REPO_ROOT)

    def test_gap_and_preview_semantics_are_preserved(self):
        self.assertFalse(self.bundle["gap_disclosure"]["gaps_rendered_as_none"])
        contract = self.bundle["preview_readiness_contract"]
        self.assertFalse(contract["preview_export_generated"])
        self.assertFalse(contract["production_export_generated"])
        self.assertTrue(self.bundle["integration_summary"]["source_limited"])
        self.assertTrue(self.bundle["integration_summary"]["incomplete"])
        self.assertTrue(self.bundle["integration_summary"]["not_final"])

    def test_additive_cli_generates_and_validates(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            reports = root / "reports"
            result = root / "validation.json"
            with patch(
                "sys.argv",
                [
                    "pathos_data",
                    "stage4c-mvp-critical-data-completion",
                    "--mode",
                    "generate",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--output",
                    str(artifacts),
                    "--report-output",
                    str(reports),
                ],
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(len(list(artifacts.glob("*.json"))), 28)
            self.assertEqual(len(list(reports.glob("*.md"))), 3)
            with patch(
                "sys.argv",
                [
                    "pathos_data",
                    "stage4c-mvp-critical-data-completion",
                    "--mode",
                    "validate",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--artifact-dir",
                    str(artifacts),
                    "--result-output",
                    str(result),
                ],
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(json.loads(result.read_text())["status"], "pass")


if __name__ == "__main__":
    unittest.main()
