"""TDD contracts for accelerated Stage 3D-Fill Program People Wave 10."""

import hashlib
import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_program_people_wave10 import (
        Stage3DFillProgramPeopleWave10ValidationError,
        build_stage3d_fill_program_people_wave10,
        validate_preflight_state,
        validate_stage3d_fill_program_people_wave10,
    )
except ImportError:
    Stage3DFillProgramPeopleWave10ValidationError = ValueError
    build_stage3d_fill_program_people_wave10 = None
    validate_preflight_state = None
    validate_stage3d_fill_program_people_wave10 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-program-people-wave10"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
EXPECTED_HEAD = "1f71d03c248fa3b3aec26ecb920575a61adee953"
PRIOR_WAVE_DIRS = tuple(
    ROOT / f"artifacts/stage3d-fill-bulk-completion-wave{wave}" for wave in (1, 2, 3)
) + tuple(
    ROOT / f"artifacts/stage3d-fill-program-people-wave{wave}"
    for wave in (4, 5, 6, 7, 8, 9)
)


class Stage3DFillProgramPeopleWave10Tests(unittest.TestCase):
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

    def _pins_for(self, **paths):
        document = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        by_id = {row["pin_id"]: row for row in document["pins"]}
        pin_ids = {
            "source_manifest_path": "wave10_source_manifest_input",
            "cache_manifest_path": "wave10_cache_manifest_input",
            "observations_path": "wave10_observations_input",
            "exclusions_path": "wave10_exclusions_input",
        }
        for argument, path in paths.items():
            row = by_id[pin_ids[argument]]
            row["path"] = str(path)
            row["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return self._write("temporary-pins.json", document)

    def _identified_observations(self):
        document = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        rows = [row for row in document["observations"] if row["slot_status"] == "identified_person"]
        self.assertGreater(len(rows), 0)
        return document, rows

    def test_preflight_rejects_dirty_or_stale_wave9_baselines(self):
        self.assertIsNotNone(validate_preflight_state)
        validate_preflight_state(EXPECTED_HEAD, "", EXPECTED_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            validate_preflight_state(EXPECTED_HEAD, "?? audit-helper.py", EXPECTED_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            validate_preflight_state("stale-head", "", EXPECTED_HEAD)

    def test_remaining_slots_are_derived_and_accelerated_cap_is_enforced(self):
        self.assertIsNotNone(build_stage3d_fill_program_people_wave10)
        artifacts = build_stage3d_fill_program_people_wave10(**self._inputs())
        plan = artifacts["stage3d-fill-program-people-wave10-plan.json"]
        rows = artifacts["stage3d-fill-program-people-wave10-program-people.json"]["slots"]
        self.assertEqual(plan["remaining_slots_before_wave10"], 160)
        self.assertGreater(plan["attempted_remaining_slots"], 100)
        self.assertLessEqual(plan["attempted_remaining_slots"], 160)
        self.assertTrue(plan["accelerated_mode"])
        self.assertEqual(plan["accelerated_slot_cap"], 160)
        self.assertEqual(
            plan["evidence_standard"],
            "unchanged_fail_closed_dual_source_stated_cache_verified",
        )
        self.assertEqual(len(rows), plan["attempted_remaining_slots"])
        self.assertEqual(len({row["slot_id"] for row in rows}), len(rows))
        self.assertGreaterEqual(len({row["candidate_id"] for row in rows}), min(50, len(rows)))
        self.assertTrue(all(row["priority_tier"] in {1, 2, 3} for row in rows))
        self.assertGreater(plan["priority_tier_counts"].get("1", 0), 0)

    def test_positive_records_keep_full_dual_evidence_in_accelerated_mode(self):
        artifacts = build_stage3d_fill_program_people_wave10(**self._inputs())
        rows = artifacts["stage3d-fill-program-people-wave10-program-people.json"]["slots"]
        identified = [row for row in rows if row["slot_status"] == "identified_person"]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "alumnus_unspecified", "attended_no_degree"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)
            self.assertTrue(row["source_sha256"])
            for role in ("attendance", "program_match"):
                anchor = row["evidence_anchor"][role]
                self.assertTrue(anchor["source_id"])
                self.assertTrue(anchor["quote"])
                self.assertEqual(anchor["quote_verification_method"], "local_cache_substring_check")

    def test_inference_bases_remain_rejected_in_accelerated_mode(self):
        observations, identified = self._identified_observations()
        slot_id = identified[0]["slot_id"]
        for basis in ("career_inferred", "company_inferred", "fame_inferred", "research_direction_inferred"):
            mutated = deepcopy(observations)
            next(row for row in mutated["observations"] if row["slot_id"] == slot_id)["program_match_basis"] = basis
            path = self._write(f"{basis}.json", mutated)
            with self.subTest(basis=basis), self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
                build_stage3d_fill_program_people_wave10(**self._inputs(
                    observations_path=path,
                    input_pin_manifest_path=self._pins_for(observations_path=path),
                ))

    def test_manual_missing_cache_and_sha_mismatch_are_rejected(self):
        cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
        mutations = []
        manual = deepcopy(cache)
        manual["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        mutations.append(("manual.json", manual))
        missing = deepcopy(cache)
        missing["entries"][0]["cache_path"] = "cache/stage3d-fill-program-people-wave10/missing.txt"
        mutations.append(("missing.json", missing))
        bad_sha = deepcopy(cache)
        bad_sha["entries"][0]["sha256"] = "0" * 64
        mutations.append(("bad-sha.json", bad_sha))
        for name, document in mutations:
            path = self._write(name, document)
            with self.subTest(name=name), self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
                build_stage3d_fill_program_people_wave10(**self._inputs(
                    cache_manifest_path=path,
                    input_pin_manifest_path=self._pins_for(cache_manifest_path=path),
                ))

    def test_reviewed_inputs_and_old_waves_are_immutable(self):
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        source["sources"][0]["publisher"] = "Changed after review"
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            build_stage3d_fill_program_people_wave10(**self._inputs(
                source_manifest_path=self._write("changed-source.json", source)
            ))
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                  for directory in PRIOR_WAVE_DIRS for path in directory.glob("*.json")}
        build_stage3d_fill_program_people_wave10(**self._inputs())
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                 for directory in PRIOR_WAVE_DIRS for path in directory.glob("*.json")}
        self.assertEqual(before, after)

    def test_candidate_bound_source_policy_and_ranking_isolation_fail_closed(self):
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        source["sources"][0]["ranking"] = 1
        path = self._write("ranking-source.json", source)
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            build_stage3d_fill_program_people_wave10(**self._inputs(
                source_manifest_path=path,
                input_pin_manifest_path=self._pins_for(source_manifest_path=path),
            ))

    def test_gap_semantics_never_render_unreviewed_as_none(self):
        observations, identified = self._identified_observations()
        target = next(row for row in observations["observations"] if row["slot_id"] == identified[0]["slot_id"])
        target.update({"slot_status": "no_qualifying_person_found", "reviewed_scope": [], "reviewed_source_ids": []})
        path = self._write("bad-none.json", observations)
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            build_stage3d_fill_program_people_wave10(**self._inputs(
                observations_path=path,
                input_pin_manifest_path=self._pins_for(observations_path=path),
            ))
        artifacts = build_stage3d_fill_program_people_wave10(**self._inputs())
        gaps = artifacts["stage3d-fill-program-people-wave10-gap-disclosure.json"]
        self.assertTrue(gaps["source_review_not_completed_is_not_none"])
        for row in gaps["gaps"]:
            if row["slot_status"] == "source_review_not_completed":
                self.assertIsNone(row["person_id"])
                self.assertIsNone(row["person_name"])
                self.assertFalse(row["display_as_none"])

    def test_cross_wave_dedup_and_dashboard_are_consistent(self):
        artifacts = build_stage3d_fill_program_people_wave10(**self._inputs())
        dedup = artifacts["stage3d-fill-program-people-wave10-dedup-report.json"]
        keys = [(row["candidate_id"], row["canonical_person_id"]) for row in dedup["records"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)
        summary = artifacts["stage3d-fill-program-people-wave10-summary.json"]
        self.assertEqual(summary["prior_cumulative_identified_person_count"], 150)
        self.assertEqual(summary["cumulative_total_program_slots"], 310)
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(summary["coverage_delta_from_wave9"], summary["newly_identified_person_count"])
        self.assertEqual(summary["manual_verbatim_check_count"], 0)
        self.assertEqual(summary["cache_missing_count"], 0)
        self.assertEqual(summary["source_policy_violations"], 0)
        self.assertEqual(summary["ranking_field_contamination"], 0)
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")

    def test_180_coverage_milestone_never_implies_final_or_export_readiness(self):
        artifacts = build_stage3d_fill_program_people_wave10(**self._inputs())
        summary = artifacts["stage3d-fill-program-people-wave10-summary.json"]
        self.assertGreaterEqual(summary["cumulative_identified_person_count"], 180)
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")
        self.assertFalse(summary["final_universe_generated"])
        self.assertFalse(summary["frontend_export_generated"])
        self.assertFalse(summary["official_selection_memberships_generated"])

    def test_deterministic_regeneration_and_validator(self):
        first = build_stage3d_fill_program_people_wave10(**self._inputs())
        second = build_stage3d_fill_program_people_wave10(**self._inputs())
        self.assertEqual(first, second)
        result = validate_stage3d_fill_program_people_wave10(first, **self._inputs())
        self.assertEqual(result["status"], "passed")
        invalid = deepcopy(first)
        invalid["stage3d-fill-program-people-wave10-summary.json"]["ranking_field_contamination"] = 1
        with self.assertRaises(Stage3DFillProgramPeopleWave10ValidationError):
            validate_stage3d_fill_program_people_wave10(invalid, **self._inputs())

    def test_cli_generates_and_validates_independent_overlay(self):
        output, report = self.temp / "artifacts", self.temp / "report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--candidate-v2", str(CANDIDATES), "--programs", str(PROGRAMS),
            "--input-pin-manifest", str(PIN_MANIFEST), "--source-manifest", str(SOURCE_MANIFEST),
            "--cache-manifest", str(CACHE_MANIFEST), "--observations", str(OBSERVATIONS),
            "--exclusions", str(EXCLUSIONS),
        ]
        generated = subprocess.run([
            sys.executable, "-m", "pathos_data", "generate-stage3d-fill-program-people-wave10",
            *shared, "--output", str(output), "--report-output", str(report),
        ], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result = self.temp / "validation.json"
        validated = subprocess.run([
            sys.executable, "-m", "pathos_data", "validate-stage3d-fill-program-people-wave10",
            *shared, "--artifact-dir", str(output), "--result-output", str(result),
        ], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
