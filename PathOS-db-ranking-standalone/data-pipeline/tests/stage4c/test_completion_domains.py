"""TDD contracts for Stage 4C completion domains."""

import unittest
from copy import deepcopy
from pathlib import Path

from pathos_data.stage4c.config import Stage4CValidationError
from pathos_data.stage4c.enrollment import (
    build_enrollment_metrics,
    validate_enrollment_record,
)
from pathos_data.stage4c.geography import (
    build_census_place_resolution,
    validate_place_resolution,
)
from pathos_data.stage4c.localization import (
    build_chinese_display_names,
    validate_chinese_name_record,
)
from pathos_data.stage4c.ranking_status import (
    build_ranking_status,
    validate_ranking_status_record,
)
from pathos_data.stage4c.source_intake import build_context
from pathos_data.stage4c.testing_policy import (
    build_english_policies,
    build_sat_act_resolution,
    build_test_policies,
    validate_english_policy,
    validate_sat_act_record,
    validate_test_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class Stage4CCompletionDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = build_context(REPO_ROOT)

    def test_enrollment_has_62_scoped_observations(self):
        rows = build_enrollment_metrics(self.context)
        self.assertEqual(len(rows), 62)
        self.assertEqual(sum(r["graduate"]["status"] == "verified" for r in rows), 60)
        self.assertEqual(
            sum(r["total"]["status"] == "verified_derived_same_scope" for r in rows),
            60,
        )
        self.assertTrue(all(r["undergraduate"]["scope"] != r["graduate"]["scope"] for r in rows))

    def test_total_derivation_requires_same_scope_and_year(self):
        row = deepcopy(build_enrollment_metrics(self.context)[0])
        row["total"]["derivation"]["graduate_reference_year"] = 2018
        with self.assertRaises(Stage4CValidationError):
            validate_enrollment_record(row)

    def test_system_wide_enrollment_is_rejected(self):
        row = deepcopy(build_enrollment_metrics(self.context)[0])
        row["graduate"]["scope"] = "system_wide"
        with self.assertRaises(Stage4CValidationError):
            validate_enrollment_record(row)

    def test_every_school_has_explicit_test_policy_observation(self):
        rows = build_test_policies(self.context)
        self.assertEqual(len(rows), 62)
        self.assertTrue(all(r["applicant_scope"] == "first_year_undergraduate" for r in rows))
        self.assertTrue(all(r["verification_status"] == "pending_external_access" for r in rows))

    def test_test_policy_enum_and_stale_cycle_fail_closed(self):
        row = deepcopy(build_test_policies(self.context)[0])
        row["policy_status"] = "optional-ish"
        with self.assertRaises(Stage4CValidationError):
            validate_test_policy(row)
        row = deepcopy(build_test_policies(self.context)[0])
        row["reference_year"] = 2020
        row["verification_status"] = "verified"
        with self.assertRaises(Stage4CValidationError):
            validate_test_policy(row)

    def test_english_policy_is_undergraduate_and_unknown_scores_stay_null(self):
        rows = build_english_policies(self.context)
        self.assertEqual(len(rows), 62)
        self.assertTrue(
            all(r["applicant_scope"] == "international_first_year_undergraduate" for r in rows)
        )
        self.assertTrue(all(not r["accepted_tests"] for r in rows))
        for row in rows:
            validate_english_policy(row)

    def test_sat_act_all_62_have_value_or_explicit_status(self):
        rows = build_sat_act_resolution(self.context)
        self.assertEqual(len(rows), 62)
        self.assertEqual(sum(r["sat"]["status"] == "verified_middle_50" for r in rows), 53)
        self.assertEqual(sum(r["sat"]["status"] == "not_reported" for r in rows), 9)
        self.assertTrue(all(r["sat"]["value"] != 0 and r["act"]["value"] != 0 for r in rows))
        for row in rows:
            validate_sat_act_record(row)

    def test_chinese_names_cover_62_without_changing_identity(self):
        rows = build_chinese_display_names(self.context)
        self.assertEqual(len(rows), 62)
        self.assertTrue(all(r["display_name_zh"] for r in rows))
        self.assertTrue(all(r["name_status"] == "reviewed_established" for r in rows))
        for row in rows:
            validate_chinese_name_record(row)

    def test_chinese_name_cannot_be_used_as_identity(self):
        row = deepcopy(build_chinese_display_names(self.context)[0])
        row["identity_match_basis"] = "chinese_display_name"
        with self.assertRaises(Stage4CValidationError):
            validate_chinese_name_record(row)

    def test_remaining_place_gaps_become_explicit_county_fallback(self):
        rows = build_census_place_resolution(self.context)
        self.assertEqual(len(rows), 62)
        self.assertEqual(sum(r["resolution_status"] == "verified_place" for r in rows), 46)
        self.assertEqual(sum(r["resolution_status"] == "county_only_valid" for r in rows), 16)
        self.assertTrue(all(r["join_method"] != "nearest_town" for r in rows))
        for row in rows:
            validate_place_resolution(row)

    def test_national_ranking_null_semantics_cover_12(self):
        rows = build_ranking_status(self.context)
        self.assertEqual(len(rows), 62)
        self.assertEqual(sum(r["national_rank"] is not None for r in rows), 50)
        self.assertEqual(sum(r["national_rank"] is None for r in rows), 12)
        self.assertFalse(any(r["national_rank"] == 0 for r in rows))
        for row in rows:
            validate_ranking_status_record(row)


if __name__ == "__main__":
    unittest.main()
