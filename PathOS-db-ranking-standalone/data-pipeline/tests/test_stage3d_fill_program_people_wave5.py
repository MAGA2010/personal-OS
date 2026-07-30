"""TDD contracts for Stage 3D-Fill Program People Coverage Expansion Wave 5."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_program_people_wave5 import (
        Stage3DFillProgramPeopleWave5ValidationError,
        build_stage3d_fill_program_people_wave5,
        validate_stage3d_fill_program_people_wave5,
    )
except ImportError:
    Stage3DFillProgramPeopleWave5ValidationError = ValueError
    build_stage3d_fill_program_people_wave5 = None
    validate_stage3d_fill_program_people_wave5 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-program-people-wave5"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
WAVE4_DIR = ROOT / "artifacts/stage3d-fill-program-people-wave4"
BASE_WAVE_DIRS = tuple(ROOT / f"artifacts/stage3d-fill-bulk-completion-wave{wave}" for wave in (1, 2, 3))


class Stage3DFillProgramPeopleWave5Tests(unittest.TestCase):
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

    def test_remaining_slots_are_derived_and_selected_across_schools(self):
        self.assertIsNotNone(build_stage3d_fill_program_people_wave5)
        artifacts = build_stage3d_fill_program_people_wave5(**self._inputs())
        plan = artifacts["stage3d-fill-program-people-wave5-plan.json"]
        rows = artifacts["stage3d-fill-program-people-wave5-program-people.json"]["slots"]
        prior_by_slot = {}
        for wave, directory in zip((1, 2, 3), BASE_WAVE_DIRS):
            path = directory / f"stage3d-fill-bulk-completion-wave{wave}-program-people.json"
            prior_by_slot.update({row["slot_id"]: row for row in json.loads(path.read_text())["slots"]})
        wave4 = json.loads((WAVE4_DIR / "stage3d-fill-program-people-wave4-program-people.json").read_text())["slots"]
        prior_by_slot.update({row["slot_id"]: row for row in wave4})
        pending = {slot_id for slot_id, row in prior_by_slot.items() if row["slot_status"] == "source_review_not_completed"}
        self.assertEqual(len(pending), 258)
        self.assertEqual(len(rows), 100)
        self.assertEqual(plan["remaining_slots_before_wave5"], 258)
        self.assertEqual(plan["attempted_remaining_slots"], 100)
        self.assertTrue({row["slot_id"] for row in rows} <= pending)
        self.assertEqual(len({row["candidate_id"] for row in rows}), 62)
        self.assertLessEqual(max(__import__("collections").Counter(row["candidate_id"] for row in rows).values()), 2)

    def test_priority_and_selection_are_deterministic(self):
        first = build_stage3d_fill_program_people_wave5(**self._inputs())
        second = build_stage3d_fill_program_people_wave5(**self._inputs())
        selected = first["stage3d-fill-program-people-wave5-plan.json"]["selected_slots"]
        self.assertEqual(first, second)
        self.assertEqual(len(selected), 100)
        self.assertEqual({row["priority_tier"] for row in selected}, {1, 2})
        self.assertEqual(sum(row["priority_tier"] == 1 for row in selected), 99)

    def test_positive_records_require_dual_source_stated_cache_evidence(self):
        artifacts = build_stage3d_fill_program_people_wave5(**self._inputs())
        rows = artifacts["stage3d-fill-program-people-wave5-program-people.json"]["slots"]
        identified = [row for row in rows if row["slot_status"] == "identified_person"]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)
            self.assertEqual(set(row["evidence_anchor"]), {"attendance", "program_match"})
            self.assertTrue(all(len(value) == 64 for value in row["source_sha256"].values()))

    def test_inference_manual_cache_and_missing_cache_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        identified = next(row for row in observations["observations"] if row["slot_status"] == "identified_person")
        for value in ("profession_inference", "company_inference", "fame_inference", "research_area_inference"):
            mutated = deepcopy(observations)
            next(row for row in mutated["observations"] if row["slot_id"] == identified["slot_id"])["program_match_basis"] = value
            with self.assertRaises(Stage3DFillProgramPeopleWave5ValidationError):
                build_stage3d_fill_program_people_wave5(**self._inputs(observations_path=self._write(f"bad-{value}.json", mutated)))
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        with self.assertRaises(Stage3DFillProgramPeopleWave5ValidationError):
            build_stage3d_fill_program_people_wave5(**self._inputs(cache_manifest_path=self._write("manual.json", cache)))
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillProgramPeopleWave5ValidationError):
            build_stage3d_fill_program_people_wave5(**self._inputs(cache_manifest_path=self._write("bad-sha.json", cache)))

    def test_gap_semantics_and_cross_wave_dedup_are_fail_closed(self):
        artifacts = build_stage3d_fill_program_people_wave5(**self._inputs())
        rows = artifacts["stage3d-fill-program-people-wave5-program-people.json"]["slots"]
        for row in rows:
            if row["slot_status"] == "source_review_not_completed":
                self.assertFalse(row["display_as_none"])
        dedup = artifacts["stage3d-fill-program-people-wave5-dedup-report.json"]
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)
        keys = [(row["candidate_id"], row["canonical_person_id"]) for row in dedup["records"]]
        self.assertEqual(len(keys), len(set(keys)))
        observations = json.loads(OBSERVATIONS.read_text())
        observations["observations"][0].update({"slot_status": "no_qualifying_person_found", "reviewed_scope": [], "reviewed_source_ids": []})
        with self.assertRaises(Stage3DFillProgramPeopleWave5ValidationError):
            build_stage3d_fill_program_people_wave5(**self._inputs(observations_path=self._write("bad-none.json", observations)))

    def test_cumulative_summary_and_prior_artifacts_are_preserved(self):
        before = {str(path): path.read_bytes() for path in WAVE4_DIR.glob("*.json")}
        artifacts = build_stage3d_fill_program_people_wave5(**self._inputs())
        summary = artifacts["stage3d-fill-program-people-wave5-summary.json"]
        after = {str(path): path.read_bytes() for path in WAVE4_DIR.glob("*.json")}
        self.assertEqual(before, after)
        self.assertEqual(summary["wave4_identified_count"], 14)
        self.assertEqual(summary["prior_cumulative_identified_person_count"], 52)
        self.assertEqual(summary["cumulative_program_slots_processed"], 310)
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")
        invalid = deepcopy(artifacts)
        invalid["stage3d-fill-program-people-wave5-summary.json"]["source_policy_violations"] = 1
        with self.assertRaises(Stage3DFillProgramPeopleWave5ValidationError):
            validate_stage3d_fill_program_people_wave5(invalid, **self._inputs())

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
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-program-people-wave5", *shared,
             "--output", str(output), "--report-output", str(report)], cwd=ROOT, env=env,
            capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-program-people-wave5", *shared,
             "--artifact-dir", str(output), "--result-output", str(result)], cwd=ROOT, env=env,
            capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
