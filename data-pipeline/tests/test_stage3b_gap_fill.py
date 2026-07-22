"""Stage 3B overlay contract regressions."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.stage3b_gap_fill import (
    Stage3BValidationError,
    build_stage3b_gap_fill,
    validate_stage3b_gap_fill,
)


ROOT = Path(__file__).resolve().parents[1]


class Stage3BGapFillTests(unittest.TestCase):
    def inputs(self) -> dict:
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3_dir": ROOT / "artifacts/stage3-program-mvp-detail-pack",
            "ipeds_cache": ROOT / "cache/stage3-ipeds",
            "official_cache": ROOT / "cache/stage3b-official",
            "alias_mappings_path": ROOT / "data/stage3b/identity-alias-mappings.json",
            "program_observations_path": ROOT / "data/stage3b/official-program-observations.json",
        }

    def test_stage3b_uses_derived_program_gap_semantics_without_mutating_stage3(self) -> None:
        original = (ROOT / "artifacts/stage3-program-mvp-detail-pack/program-mvp-universities.json").read_bytes()
        artifacts = build_stage3b_gap_fill(**self.inputs())
        rows = artifacts["stage3b-mvp-universities.json"]["universities"]
        summary = artifacts["stage3b-summary.json"]

        self.assertEqual(len(rows), 62)
        self.assertEqual(summary["demo_program_gap_original_count"], 8)
        self.assertEqual(
            sum(row["top_5_gap_reason"] is not None for row in rows),
            summary["demo_program_gap_remaining_count"],
        )
        self.assertEqual(summary["stale_top5_gap_reason_original_count"], 6)
        self.assertEqual(summary["stale_top5_gap_reason_cleared_in_overlay_count"], 6)
        self.assertTrue(all(
            row["top_5_gap_reason"] is None
            for row in rows if len(row["top_5_programs_for_demo"]) == 5
        ))
        self.assertEqual((ROOT / "artifacts/stage3-program-mvp-detail-pack/program-mvp-universities.json").read_bytes(), original)

    def test_summary_recomputes_demo_readiness_on_the_same_four_coverage_dimensions(self) -> None:
        artifacts = build_stage3b_gap_fill(**self.inputs())
        summary = artifacts["stage3b-summary.json"]
        self.assertEqual(summary["demo_readiness_before"], 0.629)
        self.assertEqual(summary["demo_readiness_after"], 0.996)
        self.assertGreater(summary["demo_readiness_after"], summary["demo_readiness_before"])

    def test_ratios_are_directly_sourced_or_explicitly_null(self) -> None:
        artifacts = build_stage3b_gap_fill(**self.inputs())
        for row in artifacts["stage3b-student-faculty.json"]["universities"]:
            if row["student_faculty_ratio"] is None:
                self.assertTrue(row["null_reason"])
            else:
                self.assertTrue(row["source_id"])
                self.assertTrue(row["source_reference"])
                self.assertTrue(row["evidence_anchor"])
                self.assertFalse(row["derived_ratio"])
                self.assertIsNone(row["derivation_formula"])

    def test_new_unitid_without_explicit_mapping_is_rejected(self) -> None:
        artifacts = build_stage3b_gap_fill(**self.inputs())
        invalid = copy.deepcopy(artifacts)
        invalid["stage3b-identity-gap-fill.json"]["universities"][0]["mapping_id"] = None
        with self.assertRaises(Stage3BValidationError):
            validate_stage3b_gap_fill(invalid, **self.inputs())

    def test_added_programs_are_official_undergraduate_and_not_rank_overwrites(self) -> None:
        artifacts = build_stage3b_gap_fill(**self.inputs())
        for row in artifacts["stage3b-program-gap-fill.json"]["universities"]:
            for program in row["added_demo_programs"]:
                self.assertEqual(program["source_type"], "official_institutional")
                self.assertEqual(program["undergraduate_status"], "undergraduate")
                self.assertIsNone(program["usnews_category"])
                self.assertIsNone(program["usnews_rank"])

    def test_source_policy_guard_is_in_the_stage3b_write_path(self) -> None:
        with patch(
            "pathos_data.stage3b_gap_fill.validate_source_policy_use",
            side_effect=Stage3BValidationError("blocked"),
        ):
            with self.assertRaises(Stage3BValidationError):
                build_stage3b_gap_fill(**self.inputs())
