"""TDD contracts for Stage 3D-Fill Bulk Completion Wave 3."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_completion_wave3 import (
        Stage3DFillBulkCompletionWave3ValidationError,
        build_stage3d_fill_bulk_completion_wave3,
        validate_preflight_state,
        validate_stage3d_fill_bulk_completion_wave3,
    )
except ImportError:
    Stage3DFillBulkCompletionWave3ValidationError = ValueError
    build_stage3d_fill_bulk_completion_wave3 = None
    validate_preflight_state = None
    validate_stage3d_fill_bulk_completion_wave3 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-bulk-completion-wave3"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
WAVE1_PROGRAM_PEOPLE = ROOT / "artifacts/stage3d-fill-bulk-completion-wave1/stage3d-fill-bulk-completion-wave1-program-people.json"
WAVE2_PROGRAM_PEOPLE = ROOT / "artifacts/stage3d-fill-bulk-completion-wave2/stage3d-fill-bulk-completion-wave2-program-people.json"
WAVE1_ARTIFACTS = ROOT / "artifacts/stage3d-fill-bulk-completion-wave1"
WAVE2_ARTIFACTS = ROOT / "artifacts/stage3d-fill-bulk-completion-wave2"
EXPECTED_WAVE2_HEAD = "cd42b2ce9ade7063c4ceb3ec4952cfbaaf65a85c"


class Stage3DFillBulkCompletionWave3Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _inputs(self, **overrides):
        values = {
            "candidate_path": CANDIDATES,
            "programs_path": PROGRAMS,
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

    @staticmethod
    def _candidate_ids():
        return {
            row["candidate_university_id"]
            for row in json.loads(CANDIDATES.read_text())["universities"]
        }

    @staticmethod
    def _processed_ids(path):
        return {row["candidate_id"] for row in json.loads(path.read_text())["slots"]}

    def test_preflight_rejects_dirty_or_stale_state(self):
        self.assertIsNotNone(validate_preflight_state)
        validate_preflight_state(EXPECTED_WAVE2_HEAD, "", EXPECTED_WAVE2_HEAD)
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            validate_preflight_state(EXPECTED_WAVE2_HEAD, "?? audit-helper.py\n", EXPECTED_WAVE2_HEAD)
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            validate_preflight_state("0" * 40, "", EXPECTED_WAVE2_HEAD)

    def test_remaining_scope_is_computed_from_candidate_v2_minus_wave1_and_wave2(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_completion_wave3)
        artifacts = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        plan = artifacts["stage3d-fill-bulk-completion-wave3-plan.json"]
        slots = artifacts["stage3d-fill-bulk-completion-wave3-program-people.json"]["slots"]
        candidate_ids = self._candidate_ids()
        wave1_ids = self._processed_ids(WAVE1_PROGRAM_PEOPLE)
        wave2_ids = self._processed_ids(WAVE2_PROGRAM_PEOPLE)
        expected = candidate_ids - wave1_ids - wave2_ids
        actual = {row["candidate_id"] for row in slots}
        self.assertEqual(len(candidate_ids), 62)
        self.assertEqual(len(wave1_ids), 20)
        self.assertEqual(len(wave2_ids), 20)
        self.assertTrue(wave1_ids.isdisjoint(wave2_ids))
        self.assertEqual(len(expected), 22)
        self.assertEqual(actual, expected)
        self.assertTrue(actual <= candidate_ids)
        self.assertEqual(len(plan["schools"]), 22)
        self.assertEqual({row["reason"] for row in plan["schools"]}, {"remaining_after_wave1_wave2"})
        self.assertTrue(all(len(row["top_5_program_slots"]) == 5 for row in plan["schools"]))

    def test_processes_all_one_hundred_ten_slots_with_exact_statuses(self):
        artifacts = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave3-program-people.json"]["slots"]
        summary = artifacts["stage3d-fill-bulk-completion-wave3-summary.json"]
        allowed = {"identified_person", "source_review_not_completed", "no_qualifying_person_found"}
        self.assertEqual(len(slots), 110)
        self.assertEqual({row["program_slot"] for row in slots}, {1, 2, 3, 4, 5})
        self.assertEqual({row["slot_status"] for row in slots} - allowed, set())
        self.assertEqual(summary["wave3_schools_processed"], 22)
        self.assertEqual(summary["wave3_program_slots_processed"], 110)

    def test_identified_person_requires_dual_source_stated_cache_verified_evidence(self):
        artifacts = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave3-program-people.json"]["slots"]
        identified = [row for row in slots if row["slot_status"] == "identified_person"]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertIn("attendance", row["evidence_anchor"])
            self.assertIn("program_match", row["evidence_anchor"])
            self.assertTrue(row["source_ids"])
            self.assertTrue(all(len(value) == 64 for value in row["source_sha256"].values()))
            self.assertEqual(row["canonical_person_id"], row["person_id"])
            self.assertEqual(row["source_id"], row["source_ids"][0])
            self.assertEqual(row["source_url"], row["source_urls"][row["source_id"]])
            self.assertGreaterEqual(row["person_id"].count(":"), 3)

    def test_inference_forbidden_relationship_and_manual_quote_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        identified = next(row for row in observations["observations"] if row["slot_status"] == "identified_person")
        for field, value in (
            ("program_match_basis", "profession_inference"),
            ("program_match_basis", "company_inference"),
            ("program_match_basis", "fame_inference"),
            ("program_match_basis", "research_area_inference"),
            ("relationship_type", "faculty_only"),
            ("usnews_rank", 1),
        ):
            mutated = deepcopy(observations)
            target = next(row for row in mutated["observations"] if row["slot_id"] == identified["slot_id"])
            target[field] = value
            with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
                build_stage3d_fill_bulk_completion_wave3(
                    **self._inputs(observations_path=self._write(f"bad-{field}.json", mutated))
                )
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            build_stage3d_fill_bulk_completion_wave3(
                **self._inputs(cache_manifest_path=self._write("manual-cache.json", cache))
            )

    def test_cache_sha_mismatch_fails_closed(self):
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            build_stage3d_fill_bulk_completion_wave3(
                **self._inputs(cache_manifest_path=self._write("bad-cache-sha.json", cache))
            )

    def test_gap_semantics_are_fail_closed(self):
        artifacts = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave3-program-people.json"]["slots"]
        for row in slots:
            if row["slot_status"] == "source_review_not_completed":
                self.assertFalse(row["display_as_none"])
                self.assertEqual(row["null_reason"], "source_review_not_completed")
            if row["slot_status"] == "no_qualifying_person_found":
                self.assertTrue(row["reviewed_scope"])
                self.assertTrue(row["reviewed_source_ids"])
        observations = json.loads(OBSERVATIONS.read_text())
        exemplar = deepcopy(observations["observations"][0])
        exemplar.update({"slot_status": "no_qualifying_person_found", "reviewed_scope": [], "reviewed_source_ids": []})
        observations["observations"][0] = exemplar
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            build_stage3d_fill_bulk_completion_wave3(
                **self._inputs(observations_path=self._write("unscoped-none.json", observations))
            )

    def test_cross_wave_dedup_and_cumulative_dashboard_are_consistent(self):
        artifacts = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        dedup = artifacts["stage3d-fill-bulk-completion-wave3-cumulative-dedup.json"]
        summary = artifacts["stage3d-fill-bulk-completion-wave3-summary.json"]
        records = dedup["records"]
        keys = [(row["candidate_id"], row["person_id"]) for row in records]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)
        self.assertEqual(summary["wave1_schools_processed"], 20)
        self.assertEqual(summary["wave2_schools_processed"], 20)
        self.assertEqual(summary["wave3_schools_processed"], 22)
        self.assertEqual(summary["cumulative_schools_processed"], 62)
        self.assertEqual(summary["total_program_slots"], 310)
        self.assertEqual(summary["cumulative_program_slots_processed"], 310)
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(summary["post_merge_duplicate_count"], 0)
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")

    def test_wave3_preserves_wave1_wave2_and_regenerates_deterministically(self):
        before = {
            str(path.relative_to(ROOT)): path.read_bytes()
            for directory in (WAVE1_ARTIFACTS, WAVE2_ARTIFACTS)
            for path in directory.glob("*.json")
        }
        first = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        second = build_stage3d_fill_bulk_completion_wave3(**self._inputs())
        after = {
            str(path.relative_to(ROOT)): path.read_bytes()
            for directory in (WAVE1_ARTIFACTS, WAVE2_ARTIFACTS)
            for path in directory.glob("*.json")
        }
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        invalid = deepcopy(first)
        invalid["stage3d-fill-bulk-completion-wave3-summary.json"]["cumulative_program_slots_processed"] = 309
        with self.assertRaises(Stage3DFillBulkCompletionWave3ValidationError):
            validate_stage3d_fill_bulk_completion_wave3(invalid, **self._inputs())

    def test_cli_generates_and_validates_independent_overlay(self):
        output = self.temp / "artifacts"
        report = self.temp / "report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--candidate-v2", str(CANDIDATES), "--programs", str(PROGRAMS),
            "--input-pin-manifest", str(PIN_MANIFEST), "--source-manifest", str(SOURCE_MANIFEST),
            "--cache-manifest", str(CACHE_MANIFEST), "--observations", str(OBSERVATIONS),
            "--exclusions", str(EXCLUSIONS),
        ]
        generated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-bulk-completion-wave3", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-bulk-completion-wave3", *shared,
             "--artifact-dir", str(output), "--result-output", str(result_output)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
