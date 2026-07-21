"""Stage 3 program-centric MVP detail pack safeguards."""

import json
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.stage3_program_mvp import (
    Stage3ProgramMvpValidationError,
    build_stage3_program_mvp,
    validate_undergraduate_tuition_record,
    validate_stage3_program_mvp,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "stage3-program-mvp-detail-pack"
V2 = ROOT / "data" / "university-universe-candidates" / "v2-source-limited" / "candidate-universities.json"
RANKING_ROOT = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"
CACHE = ROOT / "cache" / "stage3-ipeds"


class Stage3ProgramMvpTests(unittest.TestCase):
    def artifacts(self) -> dict:
        return {
            name: json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))
            for name in (
                "program-mvp-universities.json", "program-mvp-programs.json",
                "program-mvp-tuition.json", "program-mvp-student-faculty.json",
                "program-mvp-majors.json", "program-mvp-gap-disclosure.json",
                "program-mvp-summary.json",
            )
        }

    def validate(self, artifacts=None) -> dict:
        return validate_stage3_program_mvp(artifacts or self.artifacts(), V2, RANKING_ROOT, CACHE)

    def test_stage3_summary_covers_every_candidate_without_creating_final_outputs(self) -> None:
        summary_path = ARTIFACTS / "program-mvp-summary.json"
        self.assertTrue(summary_path.exists())
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["total_universities"], 62)
        self.assertFalse(summary["final_universe_generated"])
        self.assertFalse(summary["official_selection_memberships_generated"])
        self.assertFalse(summary["frontend_export_generated"])

    def test_every_candidate_has_provenance_backed_programs_or_a_gap(self) -> None:
        self.validate()
        universities = self.artifacts()["program-mvp-universities.json"]["universities"]
        self.assertEqual(len(universities), 62)
        for university in universities:
            self.assertLessEqual(len(university["top_5_programs_for_demo"]), 5)
            if len(university["top_5_programs_for_demo"]) < 5:
                self.assertTrue(university["top_5_gap_reason"])
            for program in university["top_5_programs_for_demo"]:
                self.assertTrue(program["source_id"])
                self.assertTrue(program["evidence_anchor"])

    def test_public_and_private_tuition_models_preserve_real_residency_semantics(self) -> None:
        tuition = self.artifacts()["program-mvp-tuition.json"]["universities"]
        public = next(row for row in tuition if any(item["tuition_charge_model"] == "public_in_state_out_of_state" for item in row["tuition_records"]))
        residencies = {item["residency_scope"] for item in public["tuition_records"]}
        self.assertEqual(residencies, {"in_state", "out_of_state"})
        self.assertEqual(public["highest_lowest_basis"], "university_level_same_for_all")
        private = next(row for row in tuition if any(item["tuition_charge_model"] == "private_single_rate" for item in row["tuition_records"]))
        display = private["program_tuition_display"][0]
        self.assertIsNone(display["in_state_base_tuition"])
        self.assertIsNone(display["out_of_state_base_tuition"])
        self.assertFalse(display["program_specific"])
        self.assertIn("not program-specific", display["display_label"])

    def test_cost_of_attendance_and_graduate_tuition_cannot_enter_comparison(self) -> None:
        row = next(item for item in self.artifacts()["program-mvp-tuition.json"]["universities"] if item["highest_tuition_program"])["tuition_records"][0]
        # "undergraduate tuition" is explicitly permitted; the guard must not
        # misread its substring as a graduate-tuition marker.
        validate_undergraduate_tuition_record(row)
        co_a = copy.deepcopy(row)
        co_a["estimated_cost_of_attendance_amount"] = 99999
        with self.assertRaises(Stage3ProgramMvpValidationError):
            validate_undergraduate_tuition_record(co_a)
        graduate = copy.deepcopy(row)
        graduate["evidence_anchor"]["quote"] = "graduate MBA tuition"
        with self.assertRaises(Stage3ProgramMvpValidationError):
            validate_undergraduate_tuition_record(graduate)

    def test_majors_and_ratio_rows_have_provenance_or_explicit_gap(self) -> None:
        artifacts = self.artifacts()
        self.assertGreaterEqual(artifacts["program-mvp-summary.json"]["universities_with_all_undergraduate_majors_list"], 38)
        for row in artifacts["program-mvp-majors.json"]["universities"]:
            for major in row["all_undergraduate_majors"]:
                self.assertTrue(major["source_id"])
                self.assertTrue(major["evidence_anchor"])
        for row in artifacts["program-mvp-student-faculty.json"]["universities"]:
            self.assertIsNotNone(row["null_reason"])

    def test_ipeds_award_area_fallback_is_not_mislabeled_as_a_school_major_list(self) -> None:
        for row in self.artifacts()["program-mvp-programs.json"]["universities"]:
            for program in row["top_5_programs_for_demo"]:
                if program["source_id"] == "source_ipeds_c2023_completions":
                    self.assertEqual(program["source_basis"], "ipeds_reported_award_area")

    def test_source_policy_guard_is_called_by_generator(self) -> None:
        with patch("pathos_data.stage3_program_mvp.validate_source_policy_use", side_effect=Stage3ProgramMvpValidationError("blocked")):
            with self.assertRaises(Stage3ProgramMvpValidationError):
                build_stage3_program_mvp(V2, RANKING_ROOT, CACHE)
