"""TDD contracts for official regional gaps and preview readiness."""

import unittest
from copy import deepcopy
from pathlib import Path

from pathos_data.stage4c.config import Stage4CValidationError
from pathos_data.stage4c.cumulative_view import (
    build_cumulative_view,
    build_stage4c_overlay,
    validate_stage4c_overlay,
)
from pathos_data.stage4c.readiness import build_preview_readiness
from pathos_data.stage4c.regional_metrics import (
    build_regional_metrics,
    validate_regional_record,
)
from pathos_data.stage4c.source_intake import build_context


REPO_ROOT = Path(__file__).resolve().parents[3]


class Stage4CRegionalProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = build_context(REPO_ROOT)

    def test_acs_access_failure_is_honest_and_complete(self):
        metrics, failures = build_regional_metrics(self.context)
        self.assertEqual(len(metrics), 62)
        self.assertTrue(all(r["status"] == "pending_external_access" for r in metrics))
        self.assertEqual({r["metric"] for r in failures}, {
            "median_household_income", "median_gross_rent", "total_population",
            "population_density", "asian_population_ratio",
            "chinese_specific_population_ratio",
        })

    def test_asian_and_chinese_metrics_are_not_interchangeable(self):
        row = deepcopy(build_regional_metrics(self.context)[0][0])
        row["metrics"]["chinese_specific_population_ratio"] = deepcopy(
            row["metrics"]["asian_population_ratio"]
        )
        row["metrics"]["chinese_specific_population_ratio"]["definition"] = (
            row["metrics"]["asian_population_ratio"]["definition"]
        )
        with self.assertRaises(Stage4CValidationError):
            validate_regional_record(row)

    def test_margin_of_error_is_not_promoted_to_value(self):
        row = deepcopy(build_regional_metrics(self.context)[0][0])
        row["metrics"]["median_household_income"]["value"] = 10
        row["metrics"]["median_household_income"]["value_source"] = "margin_of_error"
        with self.assertRaises(Stage4CValidationError):
            validate_regional_record(row)

    def test_overlay_contains_only_verified_records_and_is_unique(self):
        records = build_stage4c_overlay(self.context)
        self.assertTrue(records)
        self.assertTrue(all(r["verification_status"] == "verified" for r in records))
        validate_stage4c_overlay(records)
        duplicate = records + [deepcopy(records[0])]
        with self.assertRaises(Stage4CValidationError):
            validate_stage4c_overlay(duplicate)

    def test_cumulative_view_preserves_stage4b_and_people(self):
        overlay = build_stage4c_overlay(self.context)
        cumulative = build_cumulative_view(self.context, overlay)
        self.assertEqual(cumulative["stage4b_verified_record_count"], 710)
        self.assertEqual(cumulative["program_people_identified"], 180)
        self.assertEqual(cumulative["program_people_gaps"], 130)
        self.assertEqual(
            cumulative["cumulative_verified_record_count"],
            710 + len(overlay),
        )

    def test_preview_contract_is_ready_without_export(self):
        contract = build_preview_readiness(self.context, build_stage4c_overlay(self.context))
        by_area = {r["product_area"]: r for r in contract["areas"]}
        self.assertEqual(by_area["core_map"]["status"], "ready")
        self.assertEqual(by_area["school_detail"]["status"], "ready_with_warning")
        self.assertEqual(by_area["choropleth"]["status"], "blocked")
        self.assertFalse(contract["preview_export_generated"])
        self.assertFalse(contract["production_export_generated"])


if __name__ == "__main__":
    unittest.main()
