"""Stage 2G-C remaining-gap repair safeguards."""

import copy
import json
import unittest
from pathlib import Path

from pathos_data.program_gap_repair import (
    ProgramGapRepairValidationError,
    validate_program_gap_repair_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT / "data" / "ranking-seeds" / "2026-best-colleges" / "completion-programs-gap-repair"
EXISTING = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"


def load(name: str) -> dict:
    return json.loads((REPAIR / name).read_text(encoding="utf-8"))


def validate() -> dict:
    return validate_program_gap_repair_artifacts(
        [load("program-gap-repair.json")], load("identity-mappings.json"),
        load("candidate-observations.json"), load("coverage-matrix.json"),
        load("source-manifest.json"), load("gap-repair-report.json"),
        load("duplicate-dedupe-report.json"), EXISTING,
    )


class ProgramGapRepairTests(unittest.TestCase):
    def test_committed_gap_repair_adds_records_without_duplicate_sweep_rows(self) -> None:
        result = validate()
        self.assertEqual(result["new_verified_records_stageable"], 18)
        self.assertEqual(result["psychology_newly_added"], 1)

    def test_economics_remains_no_verified_when_only_out_of_scope_evidence_exists(self) -> None:
        coverage = {row["stream_id"]: row for row in load("coverage-matrix.json")["streams"]}
        self.assertEqual(coverage["undergraduate-economics"]["previous_accepted_count"], 0)
        self.assertEqual(coverage["undergraduate-economics"]["newly_added_accepted_count"], 0)
        self.assertEqual(coverage["undergraduate-economics"]["stream_status_after_repair"], "no_verified_records")

    def test_duplicate_stream_school_rank_is_rejected(self) -> None:
        batch = load("program-gap-repair.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0].update({
            "category_id": "engineering-aerospace",
            "school_display_name": "Daniel Guggenheim School of Aerospace Engineering",
            "source_display_name": "Daniel Guggenheim School of Aerospace Engineering",
            "numeric_rank": 2,
            "displayed_rank": "#2",
        })
        with self.assertRaises(ProgramGapRepairValidationError):
            validate_program_gap_repair_artifacts([mutated], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("gap-repair-report.json"), load("duplicate-dedupe-report.json"), EXISTING)

    def test_partial_record_cannot_enter_accepted_repair(self) -> None:
        batch = load("program-gap-repair.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["verification_status"] = "partially_verified"
        with self.assertRaises(ProgramGapRepairValidationError):
            validate_program_gap_repair_artifacts([mutated], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("gap-repair-report.json"), load("duplicate-dedupe-report.json"), EXISTING)

    def test_missing_anchor_national_record_and_final_output_are_rejected(self) -> None:
        batch = load("program-gap-repair.json")
        missing_anchor = copy.deepcopy(batch)
        missing_anchor["records"][0]["evidence_anchors"] = []
        with self.assertRaises(ProgramGapRepairValidationError):
            validate_program_gap_repair_artifacts([missing_anchor], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("gap-repair-report.json"), load("duplicate-dedupe-report.json"), EXISTING)
        national = copy.deepcopy(batch)
        national["records"][0]["ranking_family"] = "national_universities"
        with self.assertRaises(ProgramGapRepairValidationError):
            validate_program_gap_repair_artifacts([national], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("gap-repair-report.json"), load("duplicate-dedupe-report.json"), EXISTING)
        coverage = copy.deepcopy(load("coverage-matrix.json"))
        coverage["frontend_export_created"] = True
        with self.assertRaises(ProgramGapRepairValidationError):
            validate_program_gap_repair_artifacts([load("program-gap-repair.json")], load("identity-mappings.json"), load("candidate-observations.json"), coverage, load("source-manifest.json"), load("gap-repair-report.json"), load("duplicate-dedupe-report.json"), EXISTING)
