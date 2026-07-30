"""Regression tests for the independent Stage 3C2 nearest-towns overlay."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3c2_nearest_towns import (
        ALLOWED_PLACE_TYPES,
        Stage3C2NearestTownsValidationError,
        build_stage3c2_nearest_towns,
        haversine_km,
        render_stage3c2_report,
        validate_stage3c2_nearest_towns,
    )
except ImportError:
    build_stage3c2_nearest_towns = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3C2NearestTownsTests(unittest.TestCase):
    def inputs(self) -> dict:
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "place_manifest_path": ROOT / "data/stage3c2/place-source-manifest.json",
            "cache_dir": ROOT / "cache/stage3c2-geography",
        }

    def test_generator_builds_three_census_places_for_each_candidate(self):
        self.assertIsNotNone(build_stage3c2_nearest_towns)
        artifacts = build_stage3c2_nearest_towns(**self.inputs())
        universities = artifacts["stage3c2-nearest-towns.json"]["universities"]

        self.assertEqual(len(universities), 62)
        self.assertTrue(all(len(row["nearest_towns"]) == 3 for row in universities))
        for university in universities:
            self.assertIsNotNone(university["school_latitude"])
            self.assertIsNotNone(university["school_longitude"])
            for town in university["nearest_towns"]:
                self.assertIn(town["place_type"], ALLOWED_PLACE_TYPES)
                self.assertEqual(town["distance_method"], "haversine_straight_line")
                self.assertIn("not driving distance", town["calculation_notes"])
                self.assertIn("not travel time", town["calculation_notes"])
                distance = haversine_km(
                    university["school_latitude"], university["school_longitude"],
                    town["town_latitude"], town["town_longitude"],
                )
                self.assertEqual(round(distance, 2), town["distance_km"])

    def test_validator_rejects_forbidden_place_type_and_accepts_reviewed_cache_artifacts(self):
        artifacts = build_stage3c2_nearest_towns(**self.inputs())
        with TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "stage3c2-report.md"
            report_path.write_text(render_stage3c2_report(artifacts), encoding="utf-8")
            result = validate_stage3c2_nearest_towns(artifacts, **self.inputs(), report_path=report_path)
            self.assertEqual(result["result"], "passed")
            self.assertTrue(artifacts["stage3c2-place-source-manifest.json"]["cache_gitignored"])
            artifacts["stage3c2-nearest-towns.json"]["universities"][0]["nearest_towns"][0]["place_type"] = "county"
            with self.assertRaises(Stage3C2NearestTownsValidationError):
                validate_stage3c2_nearest_towns(artifacts, **self.inputs(), report_path=report_path)

    def test_campus_city_flag_normalizes_state_abbreviations_and_rejects_other_places(self):
        artifacts = build_stage3c2_nearest_towns(**self.inputs())
        summary = artifacts["stage3c2-summary.json"]
        self.assertEqual(summary.get("campus_city_included_university_count"), 46)
        self.assertEqual(summary.get("campus_city_included_place_count"), 46)
        universities = {
            row["display_name"]: row
            for row in artifacts["stage3c2-nearest-towns.json"]["universities"]
        }

        for university_name, city, state in (
            ("Arizona State University", "Tempe", "Arizona"),
            ("Harvard University", "Cambridge", "Massachusetts"),
            ("Brown University", "Providence", "Rhode Island"),
        ):
            university = universities[university_name]
            campus_city = next(
                town for town in university["nearest_towns"]
                if town["town_name"] == city and town["state"] == state
            )
            self.assertTrue(campus_city["campus_city_included"])
            self.assertTrue(all(
                town["campus_city_included"] is False
                for town in university["nearest_towns"]
                if town is not campus_city
            ))


if __name__ == "__main__":
    unittest.main()
