"""TDD contracts for cross-batch notable-attendance deduplication."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_people_v2_combined_dedup import (
        Stage3DFillBulkPeopleV2CombinedDedupValidationError,
        build_stage3d_fill_bulk_people_v2_combined_dedup,
        validate_stage3d_fill_bulk_people_v2_combined_dedup,
    )
except ImportError:
    Stage3DFillBulkPeopleV2CombinedDedupValidationError = ValueError
    build_stage3d_fill_bulk_people_v2_combined_dedup = None
    validate_stage3d_fill_bulk_people_v2_combined_dedup = None


ROOT = Path(__file__).resolve().parents[1]
BATCH_A = ROOT / "artifacts/stage3d-fill-bulk-people-v2-batch-a"
BATCH_B = ROOT / "artifacts/stage3d-fill-bulk-people-v2-batch-b"
PIN_MANIFEST = ROOT / "data/stage3d-fill-bulk-completion-wave1/immutable-input-pin-manifest.json"


class Stage3DFillBulkPeopleV2CombinedDedupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _record(self, candidate_id, person_id, name="Alex Smith", source_id="source_one"):
        return {
            "candidate_id": candidate_id,
            "canonical_id": "institution:" + candidate_id.removeprefix("candidate-v2:"),
            "university_display_name": candidate_id,
            "person_name": name,
            "canonical_person_id": person_id,
            "attendance_relationship": "graduated",
            "degree_or_program": None,
            "major_or_program": None,
            "major_confidence": "unknown",
            "source_id": source_id,
            "source_url": f"https://example.edu/{source_id}",
            "publisher": "Example University",
            "evidence_anchor": {
                "source_id": source_id,
                "evidence_type": "direct_quote",
                "quote": "Reviewed attendance statement.",
                "quote_verification_method": "local_cache_substring_check",
            },
            "quote_verification_method": "local_cache_substring_check",
            "person_identity_notes": "Source-backed identity context.",
            "relationship_notes": "Reviewed attendance relationship.",
            "null_reason": "major_not_stated_in_accepted_source",
        }

    def _batch(self, name, records):
        directory = self.temp / name
        directory.mkdir()
        (directory / f"{name}-notable-attendance.json").write_text(json.dumps({
            "record_type": f"{name}_notable_attendance",
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
            "final_universe_generated": False,
            "official_selection_memberships_generated": False,
            "frontend_export_generated": False,
            "records": records,
        }), encoding="utf-8")
        (directory / f"{name}-summary.json").write_text(json.dumps({
            "record_type": f"{name}_summary",
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
            "final_universe_generated": False,
            "official_selection_memberships_generated": False,
            "frontend_export_generated": False,
            "source_policy_violations": 0,
            "ranking_field_contamination": 0,
        }), encoding="utf-8")
        return directory

    def test_batch_a_b_duplicate_is_detected_and_collapsed(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_people_v2_combined_dedup)
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup([BATCH_A, BATCH_B])
        summary = artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]
        duplicates = artifacts["stage3d-fill-bulk-people-v2-combined-duplicate-records.json"]["duplicate_records"]
        records = artifacts["stage3d-fill-bulk-people-v2-combined-notable-attendance.json"]["records"]
        self.assertEqual(summary["input_record_count"], 30)
        self.assertEqual(summary["unique_person_count"], 29)
        self.assertEqual(summary["duplicate_person_count"], 1)
        self.assertEqual(summary["post_merge_duplicate_count"], 0)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["candidate_id"], "candidate-v2:university-of-michigan-ann-arbor")
        self.assertIn("james-earl-jones", duplicates[0]["canonical_person_id"])
        self.assertEqual(len(records), 29)

    def test_same_person_with_different_sources_merges_provenance_not_people_count(self):
        key = "person:alex-smith:example-university:source-backed-id"
        first = self._batch("batch-c", [self._record("candidate-v2:example-university", key, source_id="source_one")])
        second = self._batch("batch-d", [self._record("candidate-v2:example-university", key, source_id="source_two")])
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup([first, second])
        records = artifacts["stage3d-fill-bulk-people-v2-combined-notable-attendance.json"]["records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_ids"], ["source_one", "source_two"])
        self.assertEqual(len(records[0]["source_records"]), 2)
        self.assertEqual(artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]["post_merge_duplicate_count"], 0)

    def test_same_name_at_different_schools_is_not_merged(self):
        first = self._batch("batch-c", [self._record(
            "candidate-v2:school-one", "person:alex-smith:school-one:source-one",
        )])
        second = self._batch("batch-d", [self._record(
            "candidate-v2:school-two", "person:alex-smith:school-two:source-two",
        )])
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup([first, second])
        summary = artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]
        self.assertEqual(summary["unique_person_count"], 2)
        self.assertEqual(summary["duplicate_person_count"], 0)

    def test_same_canonical_person_text_with_different_candidate_is_not_merged(self):
        person_id = "person:alex-smith:shared-source-context"
        first = self._batch("batch-c", [self._record("candidate-v2:school-one", person_id)])
        second = self._batch("batch-d", [self._record("candidate-v2:school-two", person_id)])
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup([first, second])
        summary = artifacts["stage3d-fill-bulk-people-v2-combined-summary.json"]
        self.assertEqual(summary["unique_person_count"], 2)
        self.assertEqual(summary["duplicate_person_count"], 0)

    def test_duplicate_remaining_in_combined_output_fails_closed(self):
        inputs = [BATCH_A, BATCH_B]
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup(inputs)
        mutated = deepcopy(artifacts)
        records = mutated["stage3d-fill-bulk-people-v2-combined-notable-attendance.json"]["records"]
        records.append(deepcopy(records[0]))
        with self.assertRaises(Stage3DFillBulkPeopleV2CombinedDedupValidationError):
            validate_stage3d_fill_bulk_people_v2_combined_dedup(mutated, inputs)

    def test_deterministic_regeneration_and_policy_flags(self):
        inputs = [BATCH_A, BATCH_B]
        first = build_stage3d_fill_bulk_people_v2_combined_dedup(inputs)
        second = build_stage3d_fill_bulk_people_v2_combined_dedup(inputs)
        self.assertEqual(first, second)
        summary = first["stage3d-fill-bulk-people-v2-combined-summary.json"]
        self.assertEqual(summary["source_policy_violations"], 0)
        self.assertEqual(summary["ranking_field_contamination"], 0)
        self.assertFalse(summary["final_universe_generated"])
        self.assertFalse(summary["official_selection_memberships_generated"])
        self.assertFalse(summary["frontend_export_generated"])

    def test_cli_generates_and_validates_combined_overlay(self):
        output = self.temp / "combined"
        report = self.temp / "combined-report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--batch-dir", str(BATCH_A),
            "--batch-dir", str(BATCH_B),
            "--pin-manifest", str(PIN_MANIFEST),
        ]
        generated = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "generate-stage3d-fill-bulk-people-v2-combined-dedup",
                *shared,
                "--output",
                str(output),
                "--report-output",
                str(report),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.assertTrue(report.is_file())
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "validate-stage3d-fill-bulk-people-v2-combined-dedup",
                *shared,
                "--combined-attendance",
                str(output / "stage3d-fill-bulk-people-v2-combined-notable-attendance.json"),
                "--duplicate-records",
                str(output / "stage3d-fill-bulk-people-v2-combined-duplicate-records.json"),
                "--summary",
                str(output / "stage3d-fill-bulk-people-v2-combined-summary.json"),
                "--result-output",
                str(result_output),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
