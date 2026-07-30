"""TDD contracts for Stage 4B crime, cost, and transport readiness."""

import unittest
from copy import deepcopy
from pathlib import Path

from pathos_data.stage4b.config import Stage4BValidationError
from pathos_data.stage4b.cost_of_living import (
    build_cost_of_living_metrics,
    validate_cost_of_living_record,
)
from pathos_data.stage4b.crime_safety import (
    build_crime_safety_metrics,
    validate_crime_safety_record,
)
from pathos_data.stage4b.geography import build_campus_geography_crosswalk
from pathos_data.stage4b.source_intake import load_official_school_rows
from pathos_data.stage4b.transport import (
    build_transport_accessibility_metrics,
    validate_transport_record,
)


PIPELINE_ROOT = Path(__file__).resolve().parents[2]


class Stage4BLivingReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = load_official_school_rows(PIPELINE_ROOT)
        geography = build_campus_geography_crosswalk(PIPELINE_ROOT, rows)
        cls.crime = build_crime_safety_metrics(geography)
        cls.cost = build_cost_of_living_metrics(geography)
        cls.transport = build_transport_accessibility_metrics(
            PIPELINE_ROOT, geography
        )

    def test_crime_attempted_for_all_schools_without_fake_values(self):
        self.assertEqual(len(self.crime), 62)
        for record in self.crime:
            self.assertEqual(record["raw_crime"]["availability_status"], "deferred")
            self.assertIsNone(record["raw_crime"]["value"])
            self.assertEqual(record["safety_index"]["availability_status"], "deferred")
            self.assertIsNone(record["safety_index"]["value"])
            validate_crime_safety_record(record)

    def test_verified_crime_requires_jurisdiction_and_denominator(self):
        invalid = deepcopy(self.crime[0])
        invalid["raw_crime"].update(
            {
                "availability_status": "verified",
                "value": 10.0,
                "count": 100,
                "population_denominator": None,
                "reporting_jurisdiction": None,
            }
        )
        with self.assertRaises(Stage4BValidationError):
            validate_crime_safety_record(invalid)

    def test_missing_crime_cannot_imply_safe(self):
        invalid = deepcopy(self.crime[0])
        invalid["safety_index"].update(
            {
                "availability_status": "verified",
                "value": 100,
                "formula": "missing crime means safe",
            }
        )
        with self.assertRaises(Stage4BValidationError):
            validate_crime_safety_record(invalid)

    def test_safety_formula_must_be_transparent_if_derived(self):
        invalid = deepcopy(self.crime[0])
        invalid["raw_crime"].update(
            {
                "availability_status": "verified",
                "value": 5.0,
                "count": 50,
                "population_denominator": 1000,
                "reporting_jurisdiction": "Example Police Department",
                "geography_type": "reporting_agency_jurisdiction",
                "reference_year": 2024,
                "source_ids": ["official"],
            }
        )
        invalid["safety_index"].update(
            {
                "availability_status": "verified",
                "value": 95.0,
                "formula": None,
                "derived": True,
            }
        )
        with self.assertRaises(Stage4BValidationError):
            validate_crime_safety_record(invalid)

    def test_cost_index_falls_back_to_components_not_fake_score(self):
        self.assertEqual(len(self.cost), 62)
        for record in self.cost:
            self.assertIsNone(record["cost_of_living_index"]["value"])
            self.assertEqual(
                record["cost_of_living_index"]["availability_status"], "deferred"
            )
            self.assertIn("median_gross_rent", record["component_fields"])
            self.assertIn("median_household_income", record["component_fields"])
            validate_cost_of_living_record(record)

    def test_cost_index_requires_formula_and_uniform_scope(self):
        invalid = deepcopy(self.cost[0])
        invalid["cost_of_living_index"].update(
            {"value": 88, "availability_status": "verified", "formula": None}
        )
        with self.assertRaises(Stage4BValidationError):
            validate_cost_of_living_record(invalid)

    def test_transport_schema_is_partial_and_never_subjective(self):
        self.assertEqual(len(self.transport), 62)
        for record in self.transport:
            self.assertEqual(record["availability_status"], "partial")
            self.assertEqual(record["nearest_towns"]["count"], 3)
            self.assertNotIn("convenient", str(record).lower())
            self.assertIsNone(record["nearest_airport"]["distance_km"])
            self.assertIsNone(record["nearest_intercity_rail"]["distance_km"])
            validate_transport_record(record)

    def test_transport_distance_must_be_nonnegative_and_method_explicit(self):
        invalid = deepcopy(self.transport[0])
        invalid["nearest_airport"].update(
            {
                "distance_km": -1,
                "availability_status": "verified",
                "distance_method": None,
                "source_ids": ["official"],
            }
        )
        with self.assertRaises(Stage4BValidationError):
            validate_transport_record(invalid)


if __name__ == "__main__":
    unittest.main()
