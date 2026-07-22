"""TDD contracts for Stage 3D-Fill Bulk Completion Wave 2."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_completion_wave2 import (
        Stage3DFillBulkCompletionWave2ValidationError,
        build_stage3d_fill_bulk_completion_wave2,
        validate_stage3d_fill_bulk_completion_wave2,
    )
except ImportError:
    Stage3DFillBulkCompletionWave2ValidationError = ValueError
    build_stage3d_fill_bulk_completion_wave2 = None
    validate_stage3d_fill_bulk_completion_wave2 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-bulk-completion-wave2"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
SCHOOL_MANIFEST = DATA / "school-manifest.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
WAVE1_ARTIFACTS = ROOT / "artifacts/stage3d-fill-bulk-completion-wave1"

EXPECTED_SCHOOLS = {
    "candidate-v2:boston-college",
    "candidate-v2:california-institute-of-technology",
    "candidate-v2:columbia-university",
    "candidate-v2:cornell-university",
    "candidate-v2:dartmouth-college",
    "candidate-v2:emory-university",
    "candidate-v2:georgia-institute-of-technology",
    "candidate-v2:harvard-university",
    "candidate-v2:johns-hopkins-university",
    "candidate-v2:northwestern-university",
    "candidate-v2:texas-a-and-m-university",
    "candidate-v2:university-of-california-san-diego",
    "candidate-v2:university-of-maryland-college-park",
    "candidate-v2:university-of-minnesota-twin-cities",
    "candidate-v2:university-of-pennsylvania",
    "candidate-v2:university-of-rochester",
    "candidate-v2:university-of-southern-california",
    "candidate-v2:university-of-virginia",
    "candidate-v2:vanderbilt-university",
    "candidate-v2:washington-university-in-st-louis",
}


class Stage3DFillBulkCompletionWave2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _inputs(self, **overrides):
        values = {
            "candidate_path": CANDIDATES,
            "programs_path": PROGRAMS,
            "school_manifest_path": SCHOOL_MANIFEST,
            "input_pin_manifest_path": PIN_MANIFEST,
            "source_manifest_path": SOURCE_MANIFEST,
            "cache_manifest_path": CACHE_MANIFEST,
            "observations_path": OBSERVATIONS,
            "exclusions_path": EXCLUSIONS,
        }
        values.update(overrides)
        return values

    def _write(self, name, payload):
        path = self.temp / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def test_scope_is_twenty_remaining_candidate_schools_and_processes_top_five(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_completion_wave2)
        artifacts = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave2-program-people.json"]["slots"]
        summary = artifacts["stage3d-fill-bulk-completion-wave2-summary.json"]
        wave1 = json.loads((ROOT / "data/stage3d-fill-bulk-completion-wave1/school-manifest.json").read_text())
        wave1_ids = {row["candidate_id"] for row in wave1["schools"]}
        candidate_ids = {row["candidate_id"] for row in slots}
        candidate_scope = {
            row["candidate_university_id"]
            for row in json.loads(CANDIDATES.read_text())["universities"]
        }
        self.assertEqual(candidate_ids, EXPECTED_SCHOOLS)
        self.assertTrue(candidate_ids <= candidate_scope)
        self.assertTrue(candidate_ids.isdisjoint(wave1_ids))
        self.assertEqual(len(slots), 100)
        self.assertEqual({row["program_slot"] for row in slots}, {1, 2, 3, 4, 5})
        self.assertEqual(summary["schools_processed_count"], 20)
        self.assertEqual(summary["program_slots_processed_count"], 100)
        self.assertEqual(summary["attendance_records_added_count"], 0)

    def test_every_slot_has_exact_status_and_positive_records_have_dual_verified_evidence(self):
        artifacts = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave2-program-people.json"]["slots"]
        allowed = {"identified_person", "source_review_not_completed", "no_qualifying_person_found"}
        self.assertEqual({row["slot_status"] for row in slots} - allowed, set())
        identified = [row for row in slots if row["slot_status"] == "identified_person"]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertTrue(row["person_id"].startswith("person:"))
            self.assertGreaterEqual(row["person_id"].count(":"), 3)
            self.assertIn("attendance", row["evidence_anchor"])
            self.assertIn("program_match", row["evidence_anchor"])
            self.assertTrue(row["source_ids"])
            self.assertEqual(len(row["source_sha256"]), 64)

    def test_no_qualifying_requires_reviewed_scope_and_unreviewed_is_not_none(self):
        artifacts = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave2-program-people.json"]["slots"]
        for row in slots:
            if row["slot_status"] == "no_qualifying_person_found":
                self.assertTrue(row["reviewed_scope"])
                self.assertTrue(row["reviewed_source_ids"])
                self.assertTrue(row["display_as_none"])
            if row["slot_status"] == "source_review_not_completed":
                self.assertEqual(row["null_reason"], "source_review_not_completed")
                self.assertFalse(row["display_as_none"])

        observations = json.loads(OBSERVATIONS.read_text())
        exemplar = deepcopy(observations["observations"][0])
        exemplar.update({
            "slot_status": "no_qualifying_person_found",
            "reviewed_scope": [],
            "reviewed_source_ids": [],
        })
        observations["observations"][0] = exemplar
        with self.assertRaises(Stage3DFillBulkCompletionWave2ValidationError):
            build_stage3d_fill_bulk_completion_wave2(
                **self._inputs(observations_path=self._write("unscoped-none.json", observations))
            )

    def test_inference_forbidden_relationship_ranking_and_manual_quote_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        identified = next(row for row in observations["observations"] if row["slot_status"] == "identified_person")
        for field, value in (
            ("program_match_basis", "profession_inference"),
            ("relationship_type", "faculty_only"),
            ("usnews_rank", 1),
        ):
            mutated = deepcopy(observations)
            target = next(row for row in mutated["observations"] if row["slot_id"] == identified["slot_id"])
            target[field] = value
            with self.assertRaises(Stage3DFillBulkCompletionWave2ValidationError):
                build_stage3d_fill_bulk_completion_wave2(
                    **self._inputs(observations_path=self._write(f"bad-{field}.json", mutated))
                )

        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        with self.assertRaises(Stage3DFillBulkCompletionWave2ValidationError):
            build_stage3d_fill_bulk_completion_wave2(
                **self._inputs(cache_manifest_path=self._write("manual-cache.json", cache))
            )

    def test_input_pins_and_wave1_artifacts_are_immutable(self):
        pins = json.loads(PIN_MANIFEST.read_text())
        pin_ids = {row["pin_id"] for row in pins["pins"]}
        self.assertIn("wave1_cumulative_program_people", pin_ids)
        self.assertIn("bulk_people_v1_attendance", pin_ids)
        before = {path.name: path.read_bytes() for path in WAVE1_ARTIFACTS.glob("*.json")}
        build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        after = {path.name: path.read_bytes() for path in WAVE1_ARTIFACTS.glob("*.json")}
        self.assertEqual(before, after)

        bad = deepcopy(pins)
        bad["pins"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillBulkCompletionWave2ValidationError):
            build_stage3d_fill_bulk_completion_wave2(
                **self._inputs(input_pin_manifest_path=self._write("bad-pins.json", bad))
            )

    def test_cross_batch_dedup_uses_candidate_and_person_and_finishes_unique(self):
        artifacts = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        cumulative = artifacts["stage3d-fill-bulk-completion-wave2-cumulative-program-people.json"]["records"]
        summary = artifacts["stage3d-fill-bulk-completion-wave2-summary.json"]
        keys = [(row["candidate_id"], row["person_id"]) for row in cumulative]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(summary["cumulative_post_merge_duplicate_count"], 0)
        self.assertEqual(summary["wave2_duplicate_person_count"], 0)

    def test_artifacts_are_deterministic_and_validator_rejects_residual_duplicate(self):
        first = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        second = build_stage3d_fill_bulk_completion_wave2(**self._inputs())
        self.assertEqual(first, second)
        invalid = deepcopy(first)
        records = invalid["stage3d-fill-bulk-completion-wave2-cumulative-program-people.json"]["records"]
        records.append(deepcopy(records[0]))
        with self.assertRaises(Stage3DFillBulkCompletionWave2ValidationError):
            validate_stage3d_fill_bulk_completion_wave2(invalid, **self._inputs())

    def test_cli_generates_and_validates_independent_overlay(self):
        output = self.temp / "artifacts"
        report = self.temp / "report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--candidate-v2", str(CANDIDATES), "--programs", str(PROGRAMS),
            "--school-manifest", str(SCHOOL_MANIFEST), "--input-pin-manifest", str(PIN_MANIFEST),
            "--source-manifest", str(SOURCE_MANIFEST), "--cache-manifest", str(CACHE_MANIFEST),
            "--observations", str(OBSERVATIONS), "--exclusions", str(EXCLUSIONS),
        ]
        generated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-bulk-completion-wave2", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-bulk-completion-wave2", *shared,
             "--artifact-dir", str(output), "--result-output", str(result_output)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
