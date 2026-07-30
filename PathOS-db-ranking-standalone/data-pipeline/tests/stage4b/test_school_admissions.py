"""TDD contracts for Stage 4B school-profile and admissions metrics."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from pathos_data.stage4b.admissions import (
    build_admissions_metrics,
    validate_admissions_record,
    validate_test_policy_record,
)
from pathos_data.stage4b.config import (
    Stage4BValidationError,
    build_immutable_input_pins,
    sha256_file,
    validate_immutable_input_pins,
)
from pathos_data.stage4b.school_profile import (
    SCHOOL_TYPE_ENUM,
    build_school_profile_metrics,
    validate_school_profile_record,
)
from pathos_data.stage4b.source_intake import load_official_school_rows


PIPELINE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PIPELINE_ROOT.parent


class Stage4BSchoolAdmissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_official_school_rows(PIPELINE_ROOT)
        cls.school_profiles = build_school_profile_metrics(cls.rows)
        cls.admissions, cls.test_policies = build_admissions_metrics(cls.rows)

    def test_official_identity_join_preserves_62_schools(self):
        self.assertEqual(len(self.rows), 62)
        self.assertEqual(len({row["candidate_id"] for row in self.rows}), 62)
        self.assertTrue(all(row["unitid"] for row in self.rows))

    def test_school_type_enum_and_control_mapping(self):
        self.assertEqual(len(self.school_profiles), 62)
        for record in self.school_profiles:
            self.assertIn(record["school_type"]["value"], SCHOOL_TYPE_ENUM)
            self.assertIn(record["public_private_control"]["value"], {1, 2, 3})
            validate_school_profile_record(record)

    def test_undergraduate_enrollment_is_not_total_or_graduate(self):
        for record in self.school_profiles:
            undergraduate = record["enrollment"]["undergraduate"]
            self.assertEqual(undergraduate["scope"], "undergraduate_degree_seeking")
            self.assertGreater(undergraduate["value"], 0)
            self.assertIsNone(record["enrollment"]["graduate"]["value"])
            self.assertIsNone(record["enrollment"]["total"]["value"])

    def test_enrollment_scope_confusion_fails_closed(self):
        invalid = deepcopy(self.school_profiles[0])
        invalid["enrollment"]["total"] = deepcopy(invalid["enrollment"]["undergraduate"])
        with self.assertRaises(Stage4BValidationError):
            validate_school_profile_record(invalid)

    def test_acceptance_rate_has_scope_year_unit_and_source(self):
        self.assertEqual(len(self.admissions), 62)
        for record in self.admissions:
            metric = record["acceptance_rate"]
            self.assertEqual(metric["scope"], "institution_undergraduate_admissions")
            self.assertEqual(metric["unit"], "ratio")
            self.assertGreaterEqual(metric["value"], 0)
            self.assertLessEqual(metric["value"], 1)
            self.assertIsInstance(metric["reference_year"], int)
            self.assertTrue(metric["source_ids"])
            validate_admissions_record(record)

    def test_acceptance_rate_wrong_scope_fails_closed(self):
        invalid = deepcopy(self.admissions[0])
        invalid["acceptance_rate"]["scope"] = "graduate_program"
        with self.assertRaises(Stage4BValidationError):
            validate_admissions_record(invalid)

    def test_graduation_rate_is_150_percent_six_year_cohort(self):
        for record in self.admissions:
            metric = record["graduation_rate"]
            self.assertEqual(metric["time_horizon"], "150_percent_of_normal_time")
            self.assertEqual(metric["cohort_scope"], "first_time_full_time_degree_seeking")
            self.assertEqual(metric["credential_scope"], "four_year_institution")

    def test_sat_middle_50_is_not_average_or_cutoff(self):
        available = [
            row for row in self.admissions
            if row["sat"]["availability_status"] == "verified"
        ]
        self.assertGreaterEqual(len(available), 50)
        for record in available:
            sat = record["sat"]
            self.assertEqual(sat["evidence_type"], "middle_50_percent_range")
            self.assertIsNotNone(sat["reading_writing"]["percentile_25"])
            self.assertIsNotNone(sat["math"]["percentile_75"])
            self.assertNotIn("minimum_score", sat)

    def test_act_evidence_is_separate_from_sat(self):
        for record in self.admissions:
            self.assertIn("act", record)
            if record["act"]["availability_status"] == "verified":
                self.assertEqual(record["act"]["evidence_type"], "middle_50_percent_range")

    def test_test_optional_is_not_inferred_from_score_reporting(self):
        for policy in self.test_policies:
            self.assertEqual(policy["test_optional_policy"]["policy_status"], "not_found")
            self.assertEqual(
                policy["test_optional_policy"]["verification_status"], "pending"
            )
            validate_test_policy_record(policy)

    def test_toefl_policy_uses_policy_model_not_forced_number(self):
        for policy in self.test_policies:
            english = policy["english_proficiency_policy"]
            self.assertEqual(english["policy_status"], "not_found")
            self.assertIsNone(english["minimum_score"])
            self.assertEqual(english["applicant_scope"], "undergraduate_international")
            validate_test_policy_record(policy)

    def test_invalid_toefl_policy_variant_rejected(self):
        invalid = deepcopy(self.test_policies[0])
        invalid["english_proficiency_policy"]["policy_status"] = "probably_required"
        with self.assertRaises(Stage4BValidationError):
            validate_test_policy_record(invalid)

    def test_source_cache_sha_matches_frozen_official_inputs(self):
        scorecard = (
            PIPELINE_ROOT
            / "cache/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip"
        )
        ipeds = PIPELINE_ROOT / "cache/stage3-ipeds/HD2024.zip"
        self.assertEqual(len(sha256_file(scorecard)), 64)
        self.assertEqual(len(sha256_file(ipeds)), 64)

    def test_immutable_input_pin_mismatch_rejected(self):
        pins = build_immutable_input_pins(REPO_ROOT)
        validate_immutable_input_pins(pins, REPO_ROOT)
        invalid = deepcopy(pins)
        invalid["inputs"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage4BValidationError):
            validate_immutable_input_pins(invalid, REPO_ROOT)

    def test_frozen_stage4a_and_people_counts(self):
        pins = build_immutable_input_pins(REPO_ROOT)
        self.assertEqual(pins["expected_counts"]["schools"], 62)
        self.assertEqual(pins["expected_counts"]["program_slots"], 310)
        self.assertEqual(pins["expected_counts"]["program_people_identified"], 180)
        self.assertEqual(pins["expected_counts"]["program_people_gaps"], 130)
        self.assertEqual(pins["expected_counts"]["stage4a_verified_contributions"], 0)
        self.assertEqual(pins["expected_counts"]["duplicate_people"], 0)

    def test_generated_records_are_json_serializable(self):
        json.dumps(
            {
                "school_profiles": self.school_profiles,
                "admissions": self.admissions,
                "test_policies": self.test_policies,
            },
            sort_keys=True,
        )


if __name__ == "__main__":
    unittest.main()
