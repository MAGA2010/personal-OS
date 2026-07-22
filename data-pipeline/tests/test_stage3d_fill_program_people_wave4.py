"""TDD contracts for Stage 3D-Fill Program People Coverage Expansion Wave 4."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_program_people_wave4 import (
        Stage3DFillProgramPeopleWave4ValidationError,
        build_stage3d_fill_program_people_wave4,
        validate_preflight_state,
        validate_stage3d_fill_program_people_wave4,
    )
except ImportError:
    Stage3DFillProgramPeopleWave4ValidationError = ValueError
    build_stage3d_fill_program_people_wave4 = None
    validate_preflight_state = None
    validate_stage3d_fill_program_people_wave4 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-program-people-wave4"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
WAVE_DIRS = tuple(
    ROOT / f"artifacts/stage3d-fill-bulk-completion-wave{wave}" for wave in (1, 2, 3)
)
EXPECTED_WAVE3_HEAD = "ddcfcedd753cb85f3b1aa95ed356a7eed268d0ce"


class Stage3DFillProgramPeopleWave4Tests(unittest.TestCase):
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

    def test_preflight_rejects_dirty_or_stale_state(self):
        self.assertIsNotNone(validate_preflight_state)
        validate_preflight_state(EXPECTED_WAVE3_HEAD, "", EXPECTED_WAVE3_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            validate_preflight_state(EXPECTED_WAVE3_HEAD, "?? gate-audit-helper.py\n", EXPECTED_WAVE3_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            validate_preflight_state("0" * 40, "", EXPECTED_WAVE3_HEAD)

    def test_attempted_slots_are_derived_from_current_pending_slots(self):
        self.assertIsNotNone(build_stage3d_fill_program_people_wave4)
        artifacts = build_stage3d_fill_program_people_wave4(**self._inputs())
        plan = artifacts["stage3d-fill-program-people-wave4-plan.json"]
        slots = artifacts["stage3d-fill-program-people-wave4-program-people.json"]["slots"]
        prior = []
        for wave, directory in zip((1, 2, 3), WAVE_DIRS):
            path = directory / f"stage3d-fill-bulk-completion-wave{wave}-program-people.json"
            prior.extend(json.loads(path.read_text())["slots"])
        pending_ids = {row["slot_id"] for row in prior if row["slot_status"] == "source_review_not_completed"}
        attempted_ids = {row["slot_id"] for row in slots}
        self.assertEqual(len(prior), 310)
        self.assertEqual(len(pending_ids), 272)
        self.assertEqual(len(slots), 100)
        self.assertEqual(plan["attempted_remaining_slots"], 100)
        self.assertTrue(attempted_ids <= pending_ids)
        self.assertEqual(len(attempted_ids), len(slots))

    def test_high_priority_program_family_selection_is_deterministic(self):
        artifacts = build_stage3d_fill_program_people_wave4(**self._inputs())
        selected = artifacts["stage3d-fill-program-people-wave4-plan.json"]["selected_slots"]
        self.assertEqual(len(selected), 100)
        self.assertEqual({row["priority_group"] for row in selected}, {"A"})
        self.assertEqual(
            [row["slot_id"] for row in selected],
            [row["slot_id"] for row in build_stage3d_fill_program_people_wave4(**self._inputs())[
                "stage3d-fill-program-people-wave4-plan.json"
            ]["selected_slots"]],
        )

    def test_positive_record_requires_dual_source_stated_cache_verified_evidence(self):
        artifacts = build_stage3d_fill_program_people_wave4(**self._inputs())
        slots = artifacts["stage3d-fill-program-people-wave4-program-people.json"]["slots"]
        identified = [row for row in slots if row["slot_status"] == "identified_person"]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertEqual(row["canonical_person_id"], row["person_id"])
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)
            self.assertTrue(row["source_ids"])
            self.assertTrue(all(len(value) == 64 for value in row["source_sha256"].values()))
            self.assertEqual(set(row["evidence_anchor"]), {"attendance", "program_match"})

    def test_inference_forbidden_relationship_ranking_and_manual_quote_fail_closed(self):
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
            with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
                build_stage3d_fill_program_people_wave4(
                    **self._inputs(observations_path=self._write(f"bad-{field}.json", mutated))
                )
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            build_stage3d_fill_program_people_wave4(
                **self._inputs(cache_manifest_path=self._write("manual-cache.json", cache))
            )

    def test_cache_sha_mismatch_fails_closed(self):
        cache = json.loads(CACHE_MANIFEST.read_text())
        cache["entries"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            build_stage3d_fill_program_people_wave4(
                **self._inputs(cache_manifest_path=self._write("bad-cache-sha.json", cache))
            )

    def test_gap_semantics_are_fail_closed(self):
        artifacts = build_stage3d_fill_program_people_wave4(**self._inputs())
        slots = artifacts["stage3d-fill-program-people-wave4-program-people.json"]["slots"]
        for row in slots:
            if row["slot_status"] == "source_review_not_completed":
                self.assertFalse(row["display_as_none"])
                self.assertEqual(row["null_reason"], "source_review_not_completed")
        observations = json.loads(OBSERVATIONS.read_text())
        exemplar = deepcopy(observations["observations"][0])
        exemplar.update({"slot_status": "no_qualifying_person_found", "reviewed_scope": [], "reviewed_source_ids": []})
        observations["observations"][0] = exemplar
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            build_stage3d_fill_program_people_wave4(
                **self._inputs(observations_path=self._write("unscoped-none.json", observations))
            )

    def test_cross_wave_dedup_and_cumulative_dashboard_are_consistent(self):
        artifacts = build_stage3d_fill_program_people_wave4(**self._inputs())
        dedup = artifacts["stage3d-fill-program-people-wave4-cumulative-dedup.json"]
        summary = artifacts["stage3d-fill-program-people-wave4-summary.json"]
        keys = [(row["candidate_id"], row["canonical_person_id"]) for row in dedup["records"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)
        self.assertEqual(summary["total_candidate_schools"], 62)
        self.assertEqual(summary["total_program_slots"], 310)
        self.assertEqual(summary["cumulative_program_slots_processed"], 310)
        self.assertEqual(summary["wave1_identified_count"], 20)
        self.assertEqual(summary["wave2_identified_count"], 8)
        self.assertEqual(summary["wave3_identified_count"], 10)
        self.assertEqual(summary["coverage_delta_from_wave3"], summary["wave4_identified_count"])
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")

    def test_wave4_preserves_prior_waves_and_regenerates_deterministically(self):
        before = {
            str(path.relative_to(ROOT)): path.read_bytes()
            for directory in WAVE_DIRS for path in directory.glob("*.json")
        }
        first = build_stage3d_fill_program_people_wave4(**self._inputs())
        second = build_stage3d_fill_program_people_wave4(**self._inputs())
        after = {
            str(path.relative_to(ROOT)): path.read_bytes()
            for directory in WAVE_DIRS for path in directory.glob("*.json")
        }
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        invalid = deepcopy(first)
        invalid["stage3d-fill-program-people-wave4-summary.json"]["cumulative_program_slots_processed"] = 309
        with self.assertRaises(Stage3DFillProgramPeopleWave4ValidationError):
            validate_stage3d_fill_program_people_wave4(invalid, **self._inputs())

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
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-program-people-wave4", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-program-people-wave4", *shared,
             "--artifact-dir", str(output), "--result-output", str(result_output)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
