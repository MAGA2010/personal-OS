"""TDD contracts for Stage 3D-Fill Program People Coverage Expansion Wave 7."""

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
    from pathos_data.stage3d_fill_program_people_wave7 import (
        Stage3DFillProgramPeopleWave7ValidationError,
        build_stage3d_fill_program_people_wave7,
        validate_preflight_state,
        validate_stage3d_fill_program_people_wave7,
    )
except ImportError:
    Stage3DFillProgramPeopleWave7ValidationError = ValueError
    build_stage3d_fill_program_people_wave7 = None
    validate_preflight_state = None
    validate_stage3d_fill_program_people_wave7 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-program-people-wave7"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"
EXPECTED_HEAD = "ae4cc830ca687be3743a29e821a7f669b8bbf480"
PRIOR_WAVE_DIRS = tuple(
    ROOT / f"artifacts/stage3d-fill-bulk-completion-wave{wave}"
    for wave in (1, 2, 3)
) + tuple(
    ROOT / f"artifacts/stage3d-fill-program-people-wave{wave}"
    for wave in (4, 5, 6)
)


class Stage3DFillProgramPeopleWave7Tests(unittest.TestCase):
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
        """Create a temporary manifest that pins intentionally mutated inputs."""
        document = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        by_id = {row["pin_id"]: row for row in document["pins"]}
        pin_ids = {
            "source_manifest_path": "wave7_source_manifest_input",
            "cache_manifest_path": "wave7_cache_manifest_input",
            "observations_path": "wave7_observations_input",
            "exclusions_path": "wave7_exclusions_input",
        }
        for argument, path in paths.items():
            row = by_id[pin_ids[argument]]
            row["path"] = str(path)
            row["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return self._write("temporary-pins.json", document)

    def _identified_observations(self):
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        identified = [
            row
            for row in observations["observations"]
            if row["slot_status"] == "identified_person"
        ]
        self.assertGreater(len(identified), 0)
        return observations, identified

    def test_preflight_rejects_dirty_or_stale_wave6_baselines(self):
        self.assertIsNotNone(validate_preflight_state)
        validate_preflight_state(EXPECTED_HEAD, "", EXPECTED_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            validate_preflight_state(EXPECTED_HEAD, "?? audit-helper.py", EXPECTED_HEAD)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            validate_preflight_state("stale-head", "", EXPECTED_HEAD)

    def test_remaining_slots_are_derived_with_school_spread_and_priority(self):
        self.assertIsNotNone(build_stage3d_fill_program_people_wave7)
        artifacts = build_stage3d_fill_program_people_wave7(**self._inputs())
        plan = artifacts["stage3d-fill-program-people-wave7-plan.json"]
        rows = artifacts["stage3d-fill-program-people-wave7-program-people.json"]["slots"]
        self.assertEqual(plan["remaining_slots_before_wave7"], 237)
        self.assertGreater(plan["attempted_remaining_slots"], 0)
        self.assertLessEqual(plan["attempted_remaining_slots"], 100)
        self.assertEqual(len(rows), plan["attempted_remaining_slots"])
        self.assertEqual(len({row["slot_id"] for row in rows}), len(rows))
        self.assertGreaterEqual(
            len({row["candidate_id"] for row in rows}),
            min(50, len(rows)),
        )
        self.assertTrue(all(row["priority_tier"] in {1, 2, 3} for row in rows))
        tier_counts = plan["priority_tier_counts"]
        self.assertGreater(tier_counts.get("1", 0), 0)
        self.assertEqual(sum(tier_counts.values()), len(rows))

    def test_identified_records_require_dual_source_stated_cache_evidence(self):
        artifacts = build_stage3d_fill_program_people_wave7(**self._inputs())
        identified = [
            row
            for row in artifacts["stage3d-fill-program-people-wave7-program-people.json"]["slots"]
            if row["slot_status"] == "identified_person"
        ]
        self.assertGreater(len(identified), 0)
        for row in identified:
            self.assertIn(
                row["relationship_type"],
                {"graduated", "alumnus_unspecified", "attended_no_degree"},
            )
            self.assertIn(
                row["match_type"],
                {"direct_program_match", "direct_related_program_match"},
            )
            self.assertIn(
                row["program_match_basis"],
                {"source_stated_exact_program", "source_stated_related_program"},
            )
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            for role in ("attendance", "program_match"):
                anchor = row["evidence_anchor"][role]
                self.assertTrue(anchor["source_id"])
                self.assertTrue(anchor["quote"])
                self.assertEqual(
                    anchor["quote_verification_method"],
                    "local_cache_substring_check",
                )
            self.assertTrue(row["source_sha256"])
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)

    def test_career_company_fame_or_research_inference_is_rejected(self):
        observations, identified = self._identified_observations()
        target_slot = identified[0]["slot_id"]
        for basis in (
            "career_inferred",
            "company_inferred",
            "fame_inferred",
            "research_direction_inferred",
        ):
            mutated = deepcopy(observations)
            target = next(row for row in mutated["observations"] if row["slot_id"] == target_slot)
            target["program_match_basis"] = basis
            with self.subTest(basis=basis), self.assertRaises(
                Stage3DFillProgramPeopleWave7ValidationError
            ):
                path = self._write(f"{basis}.json", mutated)
                build_stage3d_fill_program_people_wave7(
                    **self._inputs(
                        observations_path=path,
                        input_pin_manifest_path=self._pins_for(observations_path=path),
                    )
                )

    def test_manual_verification_is_rejected(self):
        cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
        cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
        path = self._write("manual.json", cache)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    cache_manifest_path=path,
                    input_pin_manifest_path=self._pins_for(cache_manifest_path=path),
                )
            )

    def test_missing_cache_and_sha_mismatch_are_rejected(self):
        cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
        missing = deepcopy(cache)
        missing["entries"][0]["cache_path"] = (
            "cache/stage3d-fill-program-people-wave7/missing.txt"
        )
        path = self._write("missing.json", missing)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    cache_manifest_path=path,
                    input_pin_manifest_path=self._pins_for(cache_manifest_path=path),
                )
            )
        mismatched = deepcopy(cache)
        mismatched["entries"][0]["sha256"] = "0" * 64
        path = self._write("bad-sha.json", mismatched)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    cache_manifest_path=path,
                    input_pin_manifest_path=self._pins_for(cache_manifest_path=path),
                )
            )

    def test_reviewed_inputs_are_immutable_pinned(self):
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        source["sources"][0]["publisher"] = "Changed after review"
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(source_manifest_path=self._write("changed-source.json", source))
            )

    def test_cross_school_official_source_and_cache_ranking_fields_are_rejected(self):
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
        first_source = source["sources"][0]
        first_cache = cache["entries"][0]
        fake_url = "https://www.stanford.edu/fake-official-profile"
        fake_cache = self.temp / "fake-source.txt"
        fake_cache.write_text(
            "\n".join(
                [
                    f"Source ID: {first_source['source_id']}",
                    f"Source URL: {fake_url}",
                    "Reviewed short excerpts:",
                    *first_source["verified_direct_quotes"],
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        first_source["source_url"] = fake_url
        first_cache["cache_path"] = str(fake_cache)
        first_cache["sha256"] = hashlib.sha256(fake_cache.read_bytes()).hexdigest()
        source_path = self._write("fake-domain-source.json", source)
        cache_path = self._write("fake-domain-cache.json", cache)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    source_manifest_path=source_path,
                    cache_manifest_path=cache_path,
                    input_pin_manifest_path=self._pins_for(
                        source_manifest_path=source_path,
                        cache_manifest_path=cache_path,
                    ),
                )
            )
        cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
        cache["entries"][0]["ranking"] = 1
        cache_path = self._write("ranked-cache.json", cache)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    cache_manifest_path=cache_path,
                    input_pin_manifest_path=self._pins_for(cache_manifest_path=cache_path),
                )
            )

    def test_empty_person_identity_and_incomplete_exclusion_are_rejected(self):
        observations, identified = self._identified_observations()
        target_slot = identified[0]["slot_id"]
        target = next(row for row in observations["observations"] if row["slot_id"] == target_slot)
        target["person_name"] = ""
        target["person_id"] = (
            f"person::{target['candidate_id'].removeprefix('candidate-v2:')}:"
            f"{target['source_ids'][0]}"
        )
        observations_path = self._write("empty-person.json", observations)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    observations_path=observations_path,
                    input_pin_manifest_path=self._pins_for(
                        observations_path=observations_path
                    ),
                )
            )
        exclusions = {
            "record_type": "stage3d_fill_program_people_wave7_exclusions_input",
            "exclusions": [{"exclusion_reason": "faculty_only"}],
        }
        exclusions_path = self._write("incomplete-exclusion.json", exclusions)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    exclusions_path=exclusions_path,
                    input_pin_manifest_path=self._pins_for(exclusions_path=exclusions_path),
                )
            )

    def test_pin_manifest_requires_recorded_clean_preflight(self):
        pins = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        pins["preflight"]["status_short"] = "?? audit-helper.py"
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(input_pin_manifest_path=self._write("dirty-preflight.json", pins))
            )
        pins = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        pins["preflight"]["initial_head"] = "bogus"
        pins["preflight"]["expected_wave6_head"] = "bogus"
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(input_pin_manifest_path=self._write("bogus-preflight.json", pins))
            )

    def test_gap_semantics_fail_closed_and_never_render_unreviewed_as_none(self):
        observations, identified = self._identified_observations()
        target_slot = identified[0]["slot_id"]
        invalid = deepcopy(observations)
        target = next(row for row in invalid["observations"] if row["slot_id"] == target_slot)
        target.update(
            {
                "slot_status": "no_qualifying_person_found",
                "reviewed_scope": [],
                "reviewed_source_ids": [],
            }
        )
        observations_path = self._write("bad-none.json", invalid)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    observations_path=observations_path,
                    input_pin_manifest_path=self._pins_for(
                        observations_path=observations_path
                    ),
                )
            )
        invalid = deepcopy(observations)
        target = next(row for row in invalid["observations"] if row["slot_id"] == target_slot)
        target.update(
            {
                "slot_status": "no_qualifying_person_found",
                "reviewed_scope": ["official alumni directory"],
                "reviewed_source_ids": ["unverified-source"],
            }
        )
        observations_path = self._write("fake-none.json", invalid)
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            build_stage3d_fill_program_people_wave7(
                **self._inputs(
                    observations_path=observations_path,
                    input_pin_manifest_path=self._pins_for(
                        observations_path=observations_path
                    ),
                )
            )
        artifacts = build_stage3d_fill_program_people_wave7(**self._inputs())
        gaps = artifacts["stage3d-fill-program-people-wave7-gap-disclosure.json"]
        self.assertTrue(gaps["source_review_not_completed_is_not_none"])
        for row in gaps["gaps"]:
            if row["slot_status"] == "source_review_not_completed":
                self.assertIsNone(row["person_id"])
                self.assertIsNone(row["person_name"])
                self.assertFalse(row["display_as_none"])

    def test_cross_wave_dedup_is_unique_and_validator_fails_closed(self):
        artifacts = build_stage3d_fill_program_people_wave7(**self._inputs())
        dedup = artifacts["stage3d-fill-program-people-wave7-dedup-report.json"]
        keys = [
            (row["candidate_id"], row["canonical_person_id"])
            for row in dedup["records"]
        ]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dedup["post_merge_duplicate_count"], 0)
        invalid = deepcopy(artifacts)
        invalid_dedup = invalid["stage3d-fill-program-people-wave7-dedup-report.json"]
        invalid_dedup["records"].append(deepcopy(invalid_dedup["records"][0]))
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            validate_stage3d_fill_program_people_wave7(invalid, **self._inputs())

    def test_all_prior_wave_artifacts_are_immutable(self):
        before = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in PRIOR_WAVE_DIRS
            for path in directory.glob("*.json")
        }
        build_stage3d_fill_program_people_wave7(**self._inputs())
        after = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in PRIOR_WAVE_DIRS
            for path in directory.glob("*.json")
        }
        self.assertEqual(before, after)

    def test_cumulative_summary_accounts_for_all_310_slots(self):
        artifacts = build_stage3d_fill_program_people_wave7(**self._inputs())
        summary = artifacts["stage3d-fill-program-people-wave7-summary.json"]
        self.assertEqual(summary["prior_cumulative_identified_person_count"], 73)
        self.assertEqual(summary["cumulative_total_program_slots"], 310)
        self.assertEqual(
            summary["cumulative_identified_person_count"]
            + summary["cumulative_source_review_not_completed_count"]
            + summary["cumulative_no_qualifying_person_found_count"],
            310,
        )
        self.assertEqual(
            summary["coverage_delta_from_wave6"],
            summary["newly_identified_person_count"],
        )
        self.assertEqual(summary["manual_verbatim_check_count"], 0)
        self.assertEqual(summary["cache_missing_count"], 0)
        self.assertEqual(summary["source_policy_violations"], 0)
        self.assertEqual(summary["ranking_field_contamination"], 0)
        self.assertFalse(summary["final_universe_generated"])
        self.assertFalse(summary["frontend_export_generated"])
        self.assertFalse(summary["official_selection_memberships_generated"])
        self.assertEqual(summary["readiness_status"], "source_limited / incomplete / not_final")

    def test_deterministic_regeneration_and_validator(self):
        first = build_stage3d_fill_program_people_wave7(**self._inputs())
        second = build_stage3d_fill_program_people_wave7(**self._inputs())
        self.assertEqual(first, second)
        result = validate_stage3d_fill_program_people_wave7(first, **self._inputs())
        self.assertEqual(result["status"], "passed")
        invalid = deepcopy(first)
        invalid["stage3d-fill-program-people-wave7-summary.json"][
            "ranking_field_contamination"
        ] = 1
        with self.assertRaises(Stage3DFillProgramPeopleWave7ValidationError):
            validate_stage3d_fill_program_people_wave7(invalid, **self._inputs())

    def test_cli_generates_and_validates_independent_overlay(self):
        output = self.temp / "artifacts"
        report = self.temp / "report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--candidate-v2", str(CANDIDATES),
            "--programs", str(PROGRAMS),
            "--input-pin-manifest", str(PIN_MANIFEST),
            "--source-manifest", str(SOURCE_MANIFEST),
            "--cache-manifest", str(CACHE_MANIFEST),
            "--observations", str(OBSERVATIONS),
            "--exclusions", str(EXCLUSIONS),
        ]
        generated = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "generate-stage3d-fill-program-people-wave7",
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
        result = self.temp / "validation.json"
        validated = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "validate-stage3d-fill-program-people-wave7",
                *shared,
                "--artifact-dir",
                str(output),
                "--result-output",
                str(result),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result.read_text(encoding="utf-8"))["status"], "passed")

        unexpected = output / "unexpected.json"
        unexpected.write_text("{}\n", encoding="utf-8")
        rejected_extra = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "validate-stage3d-fill-program-people-wave7",
                *shared,
                "--artifact-dir",
                str(output),
                "--result-output",
                str(self.temp / "unexpected-validation.json"),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(rejected_extra.returncode, 0)
        unexpected.unlink()

        collision = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "generate-stage3d-fill-program-people-wave7",
                *shared,
                "--output",
                str(self.temp / "collision-artifacts"),
                "--report-output",
                str(
                    self.temp
                    / "collision-artifacts"
                    / "stage3d-fill-program-people-wave7-summary.json"
                ),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(collision.returncode, 0)

        committed_validation = output / "stage3d-fill-program-people-wave7-validation-result.json"
        drifted = json.loads(committed_validation.read_text(encoding="utf-8"))
        drifted["status"] = "tampered"
        committed_validation.write_text(
            json.dumps(drifted, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rejected = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "validate-stage3d-fill-program-people-wave7",
                *shared,
                "--artifact-dir",
                str(output),
                "--result-output",
                str(self.temp / "drift-validation.json"),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(rejected.returncode, 0)


if __name__ == "__main__":
    unittest.main()
