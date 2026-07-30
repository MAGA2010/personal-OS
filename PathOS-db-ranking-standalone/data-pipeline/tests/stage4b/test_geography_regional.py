"""TDD contracts for Stage 4B campus geography and regional metrics."""

import unittest
from copy import deepcopy
from pathlib import Path

from pathos_data.stage4b.config import Stage4BValidationError
from pathos_data.stage4b.demographics import (
    build_demographic_metrics,
    validate_demographic_record,
)
from pathos_data.stage4b.geography import (
    build_campus_geography_crosswalk,
    validate_geography_record,
)
from pathos_data.stage4b.housing import (
    build_housing_income_metrics,
    validate_housing_record,
)
from pathos_data.stage4b.source_intake import load_official_school_rows


PIPELINE_ROOT = Path(__file__).resolve().parents[2]


class Stage4BGeographyRegionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = load_official_school_rows(PIPELINE_ROOT)
        cls.geography = build_campus_geography_crosswalk(PIPELINE_ROOT, rows)
        cls.demographics = build_demographic_metrics(cls.geography)
        cls.housing = build_housing_income_metrics(cls.geography)

    def test_all_schools_have_official_county_geoid(self):
        self.assertEqual(len(self.geography), 62)
        self.assertEqual(
            sum(row["county"]["availability_status"] == "verified" for row in self.geography),
            62,
        )
        for row in self.geography:
            self.assertEqual(len(row["county"]["geoid"]), 5)
            validate_geography_record(row)

    def test_reviewed_census_place_links_are_not_guessed(self):
        verified = [
            row for row in self.geography
            if row["census_place"]["availability_status"] == "verified"
        ]
        pending = [
            row for row in self.geography
            if row["census_place"]["availability_status"] == "pending"
        ]
        self.assertEqual(len(verified), 46)
        self.assertEqual(len(pending), 16)
        self.assertTrue(
            all(
                row["census_place"]["join_method"]
                == "reviewed_campus_city_census_place_link"
                for row in verified
            )
        )
        self.assertTrue(all(row["census_place"]["geoid"] is None for row in pending))

    def test_nearest_noncampus_town_cannot_be_primary_geography(self):
        for row in self.geography:
            if row["census_place"]["availability_status"] != "verified":
                self.assertEqual(row["primary_region_for_map"]["geography_type"], "county")
                self.assertNotEqual(
                    row["primary_region_for_map"]["join_method"], "nearest_town"
                )

    def test_county_and_place_ids_fail_closed(self):
        invalid = deepcopy(self.geography[0])
        invalid["county"]["geoid"] = "bad"
        with self.assertRaises(Stage4BValidationError):
            validate_geography_record(invalid)
        place = next(
            row for row in self.geography
            if row["census_place"]["availability_status"] == "verified"
        )
        invalid = deepcopy(place)
        invalid["census_place"]["geoid"] = "123"
        with self.assertRaises(Stage4BValidationError):
            validate_geography_record(invalid)

    def test_state_data_cannot_masquerade_as_city_or_place(self):
        invalid = deepcopy(self.geography[0])
        invalid["primary_region_for_map"]["geography_type"] = "state"
        invalid["primary_region_for_map"]["geography_id"] = invalid["county"]["geoid"]
        with self.assertRaises(Stage4BValidationError):
            validate_geography_record(invalid)

    def test_cbsa_is_explicit_and_partial_not_fabricated(self):
        verified = sum(
            row["cbsa"]["availability_status"] == "verified" for row in self.geography
        )
        self.assertGreaterEqual(verified, 55)
        for row in self.geography:
            if row["cbsa"]["availability_status"] != "verified":
                self.assertIsNone(row["cbsa"]["geoid"])

    def test_demographic_fields_are_attempted_with_explicit_status(self):
        self.assertEqual(len(self.demographics), 62)
        for row in self.demographics:
            self.assertIn("asian_population_ratio", row["metrics"])
            self.assertIn("chinese_population_ratio", row["metrics"])
            self.assertNotEqual(
                row["metrics"]["asian_population_ratio"]["population_definition"],
                row["metrics"]["chinese_population_ratio"]["population_definition"],
            )
            validate_demographic_record(row)

    def test_asian_ratio_cannot_substitute_for_chinese_ratio(self):
        invalid = deepcopy(self.demographics[0])
        invalid["metrics"]["chinese_population_ratio"] = deepcopy(
            invalid["metrics"]["asian_population_ratio"]
        )
        with self.assertRaises(Stage4BValidationError):
            validate_demographic_record(invalid)

    def test_ratio_denominator_validation(self):
        invalid = deepcopy(self.demographics[0])
        metric = invalid["metrics"]["asian_population_ratio"]
        metric.update(
            {
                "availability_status": "verified",
                "value": 0.3,
                "numerator": 30,
                "denominator": 50,
            }
        )
        with self.assertRaises(Stage4BValidationError):
            validate_demographic_record(invalid)

    def test_housing_rent_scope_and_density_units_are_explicit(self):
        self.assertEqual(len(self.housing), 62)
        for row in self.housing:
            rent = row["metrics"]["median_gross_rent"]
            self.assertEqual(rent["metric_definition"], "median_gross_rent")
            self.assertIn(rent["geography_type"], {"place", "county"})
            density = row["metrics"]["population_density"]
            self.assertEqual(density["unit"], "people_per_square_mile")
            validate_housing_record(row)

    def test_margin_of_error_is_not_used_as_value(self):
        invalid = deepcopy(self.housing[0])
        metric = invalid["metrics"]["median_household_income"]
        metric["availability_status"] = "verified"
        metric["value"] = 100
        metric["margin_of_error"] = 100
        metric["value_source"] = "margin_of_error"
        with self.assertRaises(Stage4BValidationError):
            validate_housing_record(invalid)


if __name__ == "__main__":
    unittest.main()
