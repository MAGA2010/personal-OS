"""TDD contracts for Stage 3D-Fill Program People Coverage Expansion Wave 6."""

import json
import hashlib
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_program_people_wave6 import (
        Stage3DFillProgramPeopleWave6ValidationError,
        build_stage3d_fill_program_people_wave6,
        validate_stage3d_fill_program_people_wave6,
    )
except ImportError:
    Stage3DFillProgramPeopleWave6ValidationError = ValueError
    build_stage3d_fill_program_people_wave6 = None
    validate_stage3d_fill_program_people_wave6 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-program-people-wave6"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
WAVE5_DIR = ROOT / "artifacts/stage3d-fill-program-people-wave5"


class Stage3DFillProgramPeopleWave6Tests(unittest.TestCase):
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

    def test_remaining_slots_are_derived_and_only_high_yield_slots_are_selected(self):
        self.assertIsNotNone(build_stage3d_fill_program_people_wave6)
        artifacts = build_stage3d_fill_program_people_wave6(**self._inputs())
        plan = artifacts["stage3d-fill-program-people-wave6-plan.json"]
        rows = artifacts["stage3d-fill-program-people-wave6-program-people.json"]["slots"]
        self.assertEqual(plan["remaining_slots_before_wave6"], 248)
        self.assertEqual(plan["attempted_remaining_slots"], 100)
        self.assertEqual(len(rows), 100)
        self.assertGreaterEqual(len({row["candidate_id"] for row in rows}), 50)
        self.assertTrue(all(row["priority_tier"] == 1 for row in rows))
        self.assertEqual(len({row["slot_id"] for row in rows}), 100)

    def test_identified_records_require_dual_source_stated_evidence_and_local_cache(self):
        artifacts = build_stage3d_fill_program_people_wave6(**self._inputs())
        identified = [
            row for row in artifacts["stage3d-fill-program-people-wave6-program-people.json"]["slots"]
            if row["slot_status"] == "identified_person"
        ]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "alumnus_unspecified", "attended_no_degree"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertEqual(row["evidence_anchor"]["attendance"]["quote_verification_method"], "local_cache_substring_check")
            self.assertEqual(row["evidence_anchor"]["program_match"]["quote_verification_method"], "local_cache_substring_check")
            self.assertTrue(row["source_sha256"])
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)

    def test_inference_manual_verification_and_missing_cache_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        first = observations["observations"][0]
        inferred = deepcopy(observations)
        inferred["observations"][0]["program_match_basis"] = "profession_inferred"
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(observations_path=self._write("inferred.json", inferred))
            )
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(cache_manifest_path=self._write("manual.json", cache))
            )
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["cache_path"] = "cache/stage3d-fill-program-people-wave6/missing.txt"
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(cache_manifest_path=self._write("missing.json", cache))
            )
        self.assertEqual(first["slot_status"], "identified_person")

    def test_gap_semantics_and_cross_wave_dedup_are_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        observations["observations"][0].update(
            {
                "slot_status": "no_qualifying_person_found",
                "reviewed_scope": [],
                "reviewed_source_ids": [],
            }
        )
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(observations_path=self._write("bad-none.json", observations))
            )
        observations = json.loads(OBSERVATIONS.read_text())
        observations["observations"][0].update(
            {
                "slot_status": "no_qualifying_person_found",
                "reviewed_scope": ["official alumni profile"],
                "reviewed_source_ids": ["not-a-real-reviewed-source"],
            }
        )
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(observations_path=self._write("fake-none-source.json", observations))
            )
        artifacts = build_stage3d_fill_program_people_wave6(**self._inputs())
        gaps = artifacts["stage3d-fill-program-people-wave6-gap-disclosure.json"]
        self.assertTrue(gaps["source_review_not_completed_is_not_none"])
        dedup = artifacts["stage3d-fill-program-people-wave6-dedup-report.json"]
        keys = [(row["candidate_id"], row["canonical_person_id"]) for row in dedup["records"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)

    def test_prior_cumulative_people_must_match_identified_slot_state(self):
        pin_manifest = json.loads(PIN_MANIFEST.read_text())
        cumulative_pin = next(
            row
            for row in pin_manifest["pins"]
            if row["pin_id"] == pin_manifest["prior_cumulative_pin_id"]
        )
        original = ROOT / cumulative_pin["path"]
        cumulative = json.loads(original.read_text())
        cumulative["records"] = cumulative["records"][1:]
        mutated_path = self._write("mutated-prior-cumulative.json", cumulative)
        cumulative_pin["path"] = str(mutated_path)
        cumulative_pin["sha256"] = hashlib.sha256(mutated_path.read_bytes()).hexdigest()
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            build_stage3d_fill_program_people_wave6(
                **self._inputs(
                    input_pin_manifest_path=self._write("mutated-pins.json", pin_manifest)
                )
            )

    def test_cumulative_summary_and_wave5_artifacts_are_preserved(self):
        before = {str(path): path.read_bytes() for path in WAVE5_DIR.glob("*.json")}
        artifacts = build_stage3d_fill_program_people_wave6(**self._inputs())
        summary = artifacts["stage3d-fill-program-people-wave6-summary.json"]
        after = {str(path): path.read_bytes() for path in WAVE5_DIR.glob("*.json")}
        self.assertEqual(before, after)
        self.assertEqual(summary["prior_cumulative_identified_person_count"], 62)
        self.assertEqual(summary["cumulative_program_slots_processed"], 310)
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")

    def test_deterministic_regeneration_and_validator(self):
        first = build_stage3d_fill_program_people_wave6(**self._inputs())
        second = build_stage3d_fill_program_people_wave6(**self._inputs())
        self.assertEqual(first, second)
        result = validate_stage3d_fill_program_people_wave6(first, **self._inputs())
        self.assertEqual(result["status"], "passed")
        invalid = deepcopy(first)
        invalid["stage3d-fill-program-people-wave6-summary.json"]["ranking_field_contamination"] = 1
        with self.assertRaises(Stage3DFillProgramPeopleWave6ValidationError):
            validate_stage3d_fill_program_people_wave6(invalid, **self._inputs())

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
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-program-people-wave6", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-program-people-wave6", *shared,
             "--artifact-dir", str(output), "--result-output", str(result)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
