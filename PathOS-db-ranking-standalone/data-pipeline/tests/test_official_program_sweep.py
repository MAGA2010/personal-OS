"""Stage 2G-B safeguards for the all-stream official-source sweep."""

import copy
import json
import unittest
from pathlib import Path

from pathos_data.official_program_sweep import (
    OfficialProgramSweepValidationError,
    validate_official_program_sweep_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
SWEEP = (
    ROOT
    / "data"
    / "ranking-seeds"
    / "2026-best-colleges"
    / "completion-programs-official-sweep"
)
EXISTING = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"


def load(name: str) -> dict:
    return json.loads((SWEEP / name).read_text(encoding="utf-8"))


def validate() -> dict:
    return validate_official_program_sweep_artifacts(
        [load("official-program-sweep.json")],
        load("identity-mappings.json"),
        load("candidate-observations.json"),
        load("coverage-matrix.json"),
        load("source-manifest.json"),
        load("gap-report.json"),
        load("duplicate-dedupe-report.json"),
        EXISTING,
    )


class OfficialProgramSweepTests(unittest.TestCase):
    def test_committed_sweep_represents_every_in_scope_stream(self) -> None:
        result = validate()
        self.assertEqual(result["streams_represented"], 28)
        self.assertFalse(result["canonical_universe_created"])
        self.assertFalse(result["frontend_export_created"])

    def test_duplicate_existing_stream_school_rank_is_rejected(self) -> None:
        batch = load("official-program-sweep.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0].update({
            "category_id": "undergraduate-business-programs",
            "school_display_name": "Haas Undergraduate Program",
            "source_display_name": "Haas Undergraduate Program",
            "numeric_rank": 3,
            "displayed_rank": "#3",
        })
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"),
                load("gap-report.json"), load("duplicate-dedupe-report.json"), EXISTING,
            )

    def test_partial_record_cannot_enter_accepted_sweep(self) -> None:
        batch = load("official-program-sweep.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["verification_status"] = "partially_verified"
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"),
                load("duplicate-dedupe-report.json"), EXISTING,
            )

    def test_complete_status_requires_full_top20_boundary_proof(self) -> None:
        coverage = load("coverage-matrix.json")
        mutated = copy.deepcopy(coverage)
        mutated["streams"][0]["stream_status"] = "complete"
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [load("official-program-sweep.json")], load("identity-mappings.json"), load("candidate-observations.json"),
                mutated, load("source-manifest.json"), load("gap-report.json"), load("duplicate-dedupe-report.json"), EXISTING,
            )

    def test_not_collected_streams_are_still_visible(self) -> None:
        coverage = load("coverage-matrix.json")
        rows = {row["stream_id"]: row for row in coverage["streams"]}
        self.assertEqual(rows["undergraduate-economics"]["stream_status"], "no_verified_records")
        self.assertEqual(rows["undergraduate-psychology"]["stream_status"], "no_verified_records")

    def test_missing_evidence_anchor_fails(self) -> None:
        batch = load("official-program-sweep.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["evidence_anchors"] = []
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"), load("duplicate-dedupe-report.json"), EXISTING,
            )

    def test_national_or_graduate_record_cannot_enter_sweep(self) -> None:
        batch = load("official-program-sweep.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][0]["ranking_family"] = "national_universities"
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [mutated], load("identity-mappings.json"), load("candidate-observations.json"),
                load("coverage-matrix.json"), load("source-manifest.json"), load("gap-report.json"), load("duplicate-dedupe-report.json"), EXISTING,
            )

    def test_final_output_flags_must_remain_false(self) -> None:
        coverage = load("coverage-matrix.json")
        mutated = copy.deepcopy(coverage)
        mutated["frontend_export_created"] = True
        with self.assertRaises(OfficialProgramSweepValidationError):
            validate_official_program_sweep_artifacts(
                [load("official-program-sweep.json")], load("identity-mappings.json"), load("candidate-observations.json"),
                mutated, load("source-manifest.json"), load("gap-report.json"), load("duplicate-dedupe-report.json"), EXISTING,
            )
