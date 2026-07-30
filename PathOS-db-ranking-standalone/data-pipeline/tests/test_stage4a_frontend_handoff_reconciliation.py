"""TDD contracts for Stage 4A frontend handoff reconciliation."""

import json
import shutil
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

try:
    from pathos_data.stage4a_frontend_handoff_reconciliation import (
        Stage4AValidationError,
        build_product_coverage_matrix,
        build_stage4a,
        classify_frontend_record,
        detect_secret_findings,
        discover_handoff_root,
        inventory_handoff,
        reconcile_university_identities,
        validate_handoff_integrity,
        validate_stage4a,
        validate_verified_enrichment_overlay,
        write_stage4a,
    )
except ImportError:
    Stage4AValidationError = ValueError
    build_product_coverage_matrix = None
    build_stage4a = None
    classify_frontend_record = None
    detect_secret_findings = None
    discover_handoff_root = None
    inventory_handoff = None
    reconcile_university_identities = None
    validate_handoff_integrity = None
    validate_stage4a = None
    validate_verified_enrichment_overlay = None
    write_stage4a = None


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
HANDOFF = REPO_ROOT / "handoff/frontend-data-extraction"
DATA_DIR = ROOT / "data/stage4a-frontend-handoff-reconciliation"


class Stage4AFrontendHandoffReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_handoff_discovery_finds_nested_official_root(self):
        container = self.temp / "handoff"
        official = container / "frontend-data-extraction"
        official.mkdir(parents=True)
        (official / "extraction-manifest.json").write_text("{}\n")
        self.assertEqual(discover_handoff_root(self.temp), official)

    def test_multiple_independent_handoff_directories_fail_closed(self):
        for name in ("frontend-data-handoff", "imported-handoff"):
            directory = self.temp / name
            directory.mkdir()
            (directory / "extraction-manifest.json").write_text("{}\n")
        with self.assertRaises(Stage4AValidationError):
            discover_handoff_root(self.temp)

    def test_handoff_inventory_and_manifest_sha_mismatch_rejection(self):
        root = self.temp / "handoff/frontend-data-extraction"
        root.mkdir(parents=True)
        (root / "extraction-manifest.json").write_text(
            '{"total_records":1,"counts_by_classification":{"backend_candidate":1},'
            '"counts_by_category":{"university.identity":1}}\n'
        )
        record = {
            "record_id": "r1", "category": "university.identity",
            "classification": "backend_candidate", "source_path": "frontend/x.json",
            "source_line_start": 1, "source_symbol": "x", "raw_value": "Example",
        }
        (root / "data-inventory.json").write_text(json.dumps([record]) + "\n")
        inventory = inventory_handoff(root)
        self.assertEqual(inventory["total_files"], 2)
        validate_handoff_integrity(root, inventory)
        invalid = deepcopy(inventory)
        invalid["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage4AValidationError):
            validate_handoff_integrity(root, invalid)

    def test_secret_detection_reports_location_without_secret_value(self):
        root = self.temp / "handoff"
        root.mkdir()
        (root / "candidate.txt").write_text("api_key=sk-" + "A" * 32)
        findings = detect_secret_findings(root)
        self.assertEqual(findings[0]["risk_type"], "openai_api_key")
        self.assertNotIn("A" * 16, json.dumps(findings))

    def test_business_mock_and_ui_classification(self):
        business = {"classification": "backend_candidate", "category": "university.cost"}
        mock = {**business, "is_mock": True}
        ui = {"classification": "frontend_config", "category": "config.default_filters"}
        self.assertEqual(
            classify_frontend_record(business), "frontend_candidate_requires_verification"
        )
        self.assertEqual(classify_frontend_record(mock), "mock_demo_placeholder")
        self.assertEqual(classify_frontend_record(ui), "frontend_ui_only")

    def test_backend_verified_wins_conflict_and_mock_cannot_enter_overlay(self):
        records = [{
            "record_id": "r1", "classification": "frontend_backend_conflict",
            "verified": False, "source_url": None, "candidate_id": "candidate-v2:test",
        }]
        with self.assertRaises(Stage4AValidationError):
            validate_verified_enrichment_overlay(records, {"candidate-v2:test"})
        mock = [{
            "record_id": "r2", "classification": "mock_demo_placeholder",
            "verified": True, "source_url": "https://example.edu",
            "candidate_id": "candidate-v2:test", "scope": "school", "reference_year": 2025,
        }]
        with self.assertRaises(Stage4AValidationError):
            validate_verified_enrichment_overlay(mock, {"candidate-v2:test"})

    def test_identity_reconciliation_requires_high_confidence_candidate_match(self):
        candidates = [{
            "candidate_university_id": "candidate-v2:example-university",
            "canonical_university_id": "institution:example-university",
            "display_name": "Example University", "aliases": ["Example U."],
        }]
        front = [
            {"university": {"id": "example", "name": "Example University"}},
            {"university": {"id": "unknown", "name": "Unknown College"}},
        ]
        rows = reconcile_university_identities(front, candidates)
        self.assertEqual(rows[0]["match_method"], "exact_name")
        self.assertEqual(rows[0]["match_confidence"], "high")
        self.assertEqual(rows[1]["match_method"], "unmatched")
        self.assertTrue(rows[1]["manual_review_required"])

    def test_low_confidence_or_unmatched_identity_cannot_enter_overlay(self):
        record = {
            "record_id": "r", "classification": "frontend_candidate_requires_verification",
            "verified": True, "source_url": "https://example.edu/fact",
            "candidate_id": None, "scope": "school", "reference_year": 2025,
        }
        with self.assertRaises(Stage4AValidationError):
            validate_verified_enrichment_overlay([record], {"candidate-v2:example"})

    def test_tuition_and_acceptance_rate_require_scope_and_year(self):
        for field in ("tuition", "acceptance_rate"):
            record = {
                "record_id": field, "classification": "frontend_candidate_requires_verification",
                "verified": True, "source_url": "https://example.edu/fact",
                "candidate_id": "candidate-v2:example", "field_id": field,
                "scope": None, "reference_year": None,
            }
            with self.assertRaises(Stage4AValidationError):
                validate_verified_enrichment_overlay([record], {"candidate-v2:example"})

    def test_ranking_membership_and_school_region_separation(self):
        forbidden = [{
            "record_id": "rank", "classification": "frontend_candidate_requires_verification",
            "verified": True, "source_url": "https://example.edu",
            "candidate_id": "candidate-v2:example", "field_id": "ranking_membership",
            "scope": "school", "reference_year": 2026,
        }]
        with self.assertRaises(Stage4AValidationError):
            validate_verified_enrichment_overlay(forbidden, {"candidate-v2:example"})
        region_as_school = deepcopy(forbidden)
        region_as_school[0]["field_id"] = "median_household_income"
        with self.assertRaises(Stage4AValidationError):
            validate_verified_enrichment_overlay(region_as_school, {"candidate-v2:example"})

    def test_chinese_and_asian_population_ratios_are_not_interchangeable(self):
        rows = build_product_coverage_matrix({
            "school_count": 62, "coverage": {
                "asian_population_ratio": 0, "chinese_population_ratio": 0
            }
        })
        fields = {row["field"]: row for row in rows}
        self.assertIn("asian_population_ratio", fields)
        self.assertIn("chinese_population_ratio", fields)
        self.assertNotEqual(
            fields["asian_population_ratio"]["next_collection_action"],
            fields["chinese_population_ratio"]["next_collection_action"],
        )

    def test_closing_people_policy_and_gaps_are_preserved(self):
        bundle = build_stage4a(REPO_ROOT, DATA_DIR)
        summary = bundle["integration_summary"]
        self.assertEqual(summary["program_people_identified"], 180)
        self.assertEqual(summary["program_people_source_review_not_completed"], 130)
        self.assertEqual(summary["program_people_no_qualifying_person_found"], 0)
        self.assertEqual(summary["program_people_raw_person_count"], 180)
        self.assertEqual(summary["program_people_unique_person_count"], 180)
        self.assertEqual(summary["program_people_duplicate_count"], 0)
        self.assertEqual(bundle["verified_enrichment_overlay"]["records"], [])

    def test_coverage_arithmetic_and_missing_report_consistency(self):
        bundle = build_stage4a(REPO_ROOT, DATA_DIR)
        for row in bundle["product_data_coverage_matrix"]["fields"]:
            coverage = row["coverage"]
            self.assertEqual(
                coverage["expected_records"],
                coverage["available_records"] + coverage["missing_records"],
            )
            self.assertGreaterEqual(coverage["available_records"], coverage["verified_records"])
        report_fields = {
            row["field"] for row in bundle["missing_data_report"]["items"]
        }
        matrix_missing = {
            row["field"] for row in bundle["product_data_coverage_matrix"]["fields"]
            if row["status"] in {"partial", "missing", "blocked"}
        }
        self.assertEqual(report_fields, matrix_missing)

    def test_deterministic_regeneration_uses_no_network(self):
        first = build_stage4a(REPO_ROOT, DATA_DIR)
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            second = build_stage4a(REPO_ROOT, DATA_DIR)
        self.assertEqual(first, second)
        out1, out2 = self.temp / "one", self.temp / "two"
        write_stage4a(first, out1, self.temp / "report-one")
        write_stage4a(second, out2, self.temp / "report-two")
        self.assertEqual(
            {p.name: p.read_bytes() for p in out1.iterdir()},
            {p.name: p.read_bytes() for p in out2.iterdir()},
        )

    def test_validator_preserves_frontend_and_upstream_immutability(self):
        bundle = build_stage4a(REPO_ROOT, DATA_DIR)
        result = validate_stage4a(bundle, REPO_ROOT, DATA_DIR)
        self.assertTrue(result["valid"])
        self.assertEqual(result["source_policy_violations"], 0)
        self.assertEqual(result["ranking_field_contamination"], 0)
        self.assertFalse(result["frontend_modified"])
        self.assertFalse(result["upstream_artifacts_modified"])
        self.assertFalse(result["final_universe_generated"])
        self.assertFalse(result["official_selection_memberships_generated"])
        self.assertFalse(result["frontend_export_generated"])


if __name__ == "__main__":
    unittest.main()
