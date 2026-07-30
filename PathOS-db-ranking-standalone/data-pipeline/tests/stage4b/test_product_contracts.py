"""TDD contracts for Stage 4B unified overlay and product data contracts."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from pathos_data.stage4b.config import Stage4BValidationError
from pathos_data.stage4b.generator import build_stage4b
from pathos_data.stage4b.overlay import validate_verified_overlay
from pathos_data.stage4b.product_contracts import (
    validate_ai_context_contract,
    validate_filter_contract,
    validate_marker_summary,
    validate_search_index,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class Stage4BProductContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_stage4b(REPO_ROOT)

    def test_verified_overlay_is_unique_and_provenance_backed(self):
        overlay = self.bundle["verified_enrichment_overlay"]
        self.assertGreater(len(overlay["records"]), 500)
        validate_verified_overlay(
            overlay["records"], self.bundle["source_manifest"]["sources"]
        )
        keys = {
            (row["university_id"], row["field"], row.get("scope"))
            for row in overlay["records"]
        }
        self.assertEqual(len(keys), len(overlay["records"]))
        self.assertTrue(all(row["source_ids"] for row in overlay["records"]))

    def test_national_rank_has_50_values_and_12_explicit_non_scope_states(self):
        marker_rows = self.bundle["marker_summary"]["universities"]
        ranked = [row for row in marker_rows if row["national_rank"]["value"] is not None]
        unranked = [row for row in marker_rows if row["national_rank"]["value"] is None]
        self.assertEqual(len(ranked), 50)
        self.assertEqual(len(unranked), 12)
        self.assertTrue(
            all(
                row["national_rank"]["status"]
                == "explicit_not_applicable_or_not_in_national_scope"
                for row in unranked
            )
        )
        self.assertNotIn(0, [row["national_rank"]["value"] for row in marker_rows])

    def test_marker_summary_is_derived_and_never_fills_missing_with_zero(self):
        rows = self.bundle["marker_summary"]["universities"]
        self.assertEqual(len(rows), 62)
        for row in rows:
            self.assertTrue(row["derived"])
            self.assertTrue(row["input_fields"])
            self.assertIn("color", row["marker_channels"])
            self.assertIn("size", row["marker_channels"])
            self.assertIn("border", row["marker_channels"])
            validate_marker_summary(row)

    def test_search_index_uses_verified_backend_provenance(self):
        index = self.bundle["search_index"]
        self.assertGreater(len(index["tokens"]), 500)
        validate_search_index(index)
        self.assertTrue(
            all(token["verification_status"] == "verified" for token in index["tokens"])
        )
        self.assertNotIn("quarantined", json.dumps(index["tokens"]).lower())

    def test_filter_contract_uses_explicit_null_exclusion(self):
        contract = self.bundle["filter_contract"]
        validate_filter_contract(contract)
        for item in contract["filters"]:
            self.assertNotEqual(item["null_behavior"], "coerce_to_zero")
            self.assertIn(item["type"], {"range", "category", "multiselect"})

    def test_comparison_records_preserve_units_scope_year_and_warnings(self):
        records = self.bundle["comparison_records"]["universities"]
        self.assertEqual(len(records), 62)
        for record in records:
            self.assertEqual(record["acceptance_rate"]["unit"], "ratio")
            self.assertEqual(record["tuition"]["currency"], "USD")
            self.assertEqual(record["nearest_towns"]["distance_unit"], "km")
            self.assertIn("warnings", record)

    def test_mode_metadata_is_product_metadata_not_objective_fact(self):
        rows = self.bundle["mode_metadata"]["fields"]
        self.assertTrue(rows)
        for row in rows:
            self.assertFalse(row["objective_fact"])
            self.assertIn(row["availability"], {"ready", "partial", "missing"})

    def test_ai_context_contract_excludes_quarantine_and_people_gaps(self):
        contract = self.bundle["ai_context_contract"]
        validate_ai_context_contract(contract)
        excluded = set(contract["excluded_fact_classes"])
        self.assertIn("quarantined", excluded)
        self.assertIn("source_review_not_completed_program_people", excluded)
        self.assertIn("frontend_demonstration_estimates", excluded)

    def test_program_people_and_gap_counts_are_preserved(self):
        summary = self.bundle["integration_summary"]
        self.assertEqual(summary["program_people_total_slots"], 310)
        self.assertEqual(summary["program_people_identified"], 180)
        self.assertEqual(summary["program_people_source_review_not_completed"], 130)
        self.assertEqual(summary["program_people_duplicate_count"], 0)

    def test_coverage_matrix_arithmetic_and_backlog_consistency(self):
        matrix = self.bundle["product_data_coverage_matrix"]["fields"]
        for row in matrix:
            coverage = row["coverage"]
            self.assertEqual(
                coverage["expected_records"],
                coverage["available_records"] + coverage["missing_records"],
            )
            self.assertGreaterEqual(
                coverage["available_records"], coverage["verified_records"]
            )
        backlog_fields = {
            row["field"] for row in self.bundle["data_collection_backlog"]["items"]
        }
        expected = {
            row["field"] for row in matrix if row["status"] in {"partial", "missing", "blocked"}
        }
        self.assertEqual(backlog_fields, expected)

    def test_source_cache_manifest_sha_and_policy(self):
        sources = self.bundle["source_manifest"]["sources"]
        caches = self.bundle["cache_manifest"]["caches"]
        cache_ids = {row["cache_id"] for row in caches}
        self.assertTrue(sources)
        self.assertTrue(caches)
        for source in sources:
            if source["availability_status"] == "verified":
                self.assertIn(source["cache_id"], cache_ids)
                self.assertIn(
                    source["source_type"],
                    {
                        "official_federal_dataset",
                        "verified_existing_backend_artifact",
                    },
                )

    def test_invalid_overlay_source_rejected(self):
        record = deepcopy(self.bundle["verified_enrichment_overlay"]["records"][0])
        record["source_ids"] = ["frontend-hardcoded"]
        with self.assertRaises(Stage4BValidationError):
            validate_verified_overlay(
                [record], self.bundle["source_manifest"]["sources"]
            )

    def test_network_disabled_generation_is_deterministic(self):
        first = build_stage4b(REPO_ROOT)
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            second = build_stage4b(REPO_ROOT)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
