"""TDD contracts for Stage 3D-Fill Bulk Completion Wave 1."""

import json
import inspect
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_completion_wave1 import (
        Stage3DFillBulkCompletionWave1ValidationError,
        build_stage3d_fill_bulk_completion_wave1,
        validate_stage3d_fill_bulk_completion_wave1,
    )
except ImportError:
    Stage3DFillBulkCompletionWave1ValidationError = ValueError
    build_stage3d_fill_bulk_completion_wave1 = None
    validate_stage3d_fill_bulk_completion_wave1 = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-fill-bulk-completion-wave1"
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
SCHOOL_MANIFEST = DATA / "school-manifest.json"
PIN_MANIFEST = DATA / "immutable-input-pin-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"


class Stage3DFillBulkCompletionWave1Tests(unittest.TestCase):
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

    def test_builds_twenty_school_top_five_inventory_and_processes_all_slots(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_completion_wave1)
        artifacts = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        inventory = artifacts["stage3d-fill-bulk-completion-wave1-slot-inventory.json"]["slots"]
        slots = artifacts["stage3d-fill-bulk-completion-wave1-program-people.json"]["slots"]
        summary = artifacts["stage3d-fill-bulk-completion-wave1-summary.json"]
        self.assertEqual(len({row["candidate_id"] for row in slots}), 20)
        self.assertEqual(len(inventory), 100)
        self.assertEqual(len(slots), 100)
        self.assertEqual({row["program_slot"] for row in slots}, {1, 2, 3, 4, 5})
        self.assertEqual(summary["program_slots_processed_count"], 100)
        self.assertEqual(summary["program_people_identified_count"], 20)
        self.assertEqual(summary["program_people_source_review_not_completed_count"], 80)
        self.assertEqual(summary["program_people_no_qualifying_person_found_count"], 0)

    def test_identified_people_have_dual_cache_verified_source_stated_evidence(self):
        artifacts = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave1-program-people.json"]["slots"]
        identified = [row for row in slots if row["slot_status"] == "identified_person"]
        self.assertEqual(len(identified), 20)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertIn(row["program_match_basis"], {"source_stated_exact_program", "source_stated_related_program"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertTrue(row["person_id"].startswith("person:"))
            self.assertGreaterEqual(row["person_id"].count(":"), 3)
            self.assertIn("attendance", row["evidence_anchor"])
            self.assertIn("program_match", row["evidence_anchor"])
            self.assertEqual(len(row["source_ids"]), 1)
            self.assertEqual(len(row["source_sha256"]), 64)

    def test_program_provenance_is_copied_from_the_immutable_demo_program_overlay(self):
        artifacts = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        inventory = artifacts["stage3d-fill-bulk-completion-wave1-slot-inventory.json"]["slots"]
        source = json.loads(PROGRAMS.read_text(encoding="utf-8"))
        expected = {}
        for university in source["universities"]:
            for index, program in enumerate(university["top_5_programs_for_demo"], 1):
                expected[(university["candidate_id"], index)] = (
                    program["program_name"], program["normalized_program_name"], program["source_id"]
                )
        for row in inventory:
            self.assertEqual(
                (row["program_name"], row["normalized_program_name"], row["program_source_reference"]["source_id"]),
                expected[(row["candidate_id"], row["program_slot"])],
            )

    def test_attendance_and_program_evidence_can_use_distinct_verified_quotes(self):
        artifacts = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-completion-wave1-program-people.json"]["slots"]
        uchicago = next(
            row for row in slots
            if row["candidate_id"] == "candidate-v2:university-of-chicago" and row["program_slot"] == 5
        )
        self.assertEqual(uchicago["slot_status"], "identified_person")
        self.assertEqual(uchicago["evidence_anchor"]["attendance"]["quote"], "Sarah Koenig, AB’90")
        self.assertIn("majored in Political Science", uchicago["evidence_anchor"]["program_match"]["quote"])
        self.assertNotEqual(
            uchicago["evidence_anchor"]["attendance"]["quote"],
            uchicago["evidence_anchor"]["program_match"]["quote"],
        )

    def test_fail_closed_for_inference_forbidden_relationship_and_unscoped_none(self):
        original = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        identified = next(row for row in original["observations"] if row["slot_status"] == "identified_person")
        for mutation in ("profession", "faculty", "unscoped_none"):
            document = deepcopy(original)
            if mutation == "unscoped_none":
                row = deepcopy(identified)
                row.update({
                    "slot_id": row["candidate_id"] + ":slot-2",
                    "program_slot": 2,
                    "slot_status": "no_qualifying_person_found",
                    "reviewed_scope": [],
                    "reviewed_source_ids": [],
                })
                document["observations"].append(row)
            else:
                row = next(item for item in document["observations"] if item["slot_id"] == identified["slot_id"])
                row["program_match_basis" if mutation == "profession" else "relationship_type"] = (
                    "profession_inference" if mutation == "profession" else "faculty_only"
                )
            with self.assertRaises(Stage3DFillBulkCompletionWave1ValidationError):
                build_stage3d_fill_bulk_completion_wave1(
                    **self._inputs(observations_path=self._write(f"{mutation}.json", document))
                )

    def test_cache_sha_quote_and_manual_verification_fail_closed(self):
        for mutation in ("sha", "quote", "manual"):
            cache = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))
            sources = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
            if mutation == "sha":
                cache["entries"][0]["sha256"] = "0" * 64
            elif mutation == "manual":
                cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
            else:
                sources["sources"][0]["verified_direct_quotes"] = ["Quote absent from cache."]
            with self.assertRaises(Stage3DFillBulkCompletionWave1ValidationError):
                build_stage3d_fill_bulk_completion_wave1(**self._inputs(
                    cache_manifest_path=self._write("cache.json", cache),
                    source_manifest_path=self._write("sources.json", sources),
                ))

    def test_manifest_pin_sha_mismatch_and_ranking_contamination_fail_closed(self):
        pins = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        pins["pins"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillBulkCompletionWave1ValidationError):
            build_stage3d_fill_bulk_completion_wave1(
                **self._inputs(input_pin_manifest_path=self._write("pins.json", pins))
            )
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        observations["observations"][0]["usnews_rank"] = 1
        with self.assertRaises(Stage3DFillBulkCompletionWave1ValidationError):
            build_stage3d_fill_bulk_completion_wave1(
                **self._inputs(observations_path=self._write("contamination.json", observations))
            )

    def test_immutable_batch_hashes_are_manifest_driven_not_hardcoded(self):
        from pathos_data import stage3d_fill_bulk_people_v2_combined_dedup as combined

        self.assertNotIn("IMMUTABLE_BATCH_SHA256", inspect.getsource(combined))
        manifest = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
        program_batches = {row["batch_id"] for row in manifest["program_person_batches"]}
        self.assertEqual(program_batches, {
            "stage3d-fill-bulk-people-v2-batch-a",
            "stage3d-fill-bulk-people-v2-batch-b",
        })

    def test_cross_batch_program_people_are_deduplicated_by_candidate_and_person(self):
        artifacts = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        summary = artifacts["stage3d-fill-bulk-completion-wave1-summary.json"]
        cumulative = artifacts["stage3d-fill-bulk-completion-wave1-cumulative-program-people.json"]["records"]
        duplicates = artifacts["stage3d-fill-bulk-completion-wave1-duplicate-records.json"]["duplicate_records"]
        keys = [(row["candidate_id"], row["person_id"]) for row in cumulative]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(summary["cumulative_input_identified_occurrence_count"], 25)
        self.assertEqual(summary["cumulative_unique_program_person_count"], 20)
        self.assertEqual(summary["cumulative_duplicate_person_count"], 5)
        self.assertEqual(summary["cumulative_post_merge_duplicate_count"], 0)
        self.assertEqual(len(duplicates), 5)
        larry_page = [row for row in cumulative if row["person_name"] == "Larry Page"]
        self.assertEqual(len(larry_page), 2)
        self.assertEqual(len({row["candidate_id"] for row in larry_page}), 2)

    def test_artifacts_are_deterministic_and_validator_rejects_residual_duplicate(self):
        first = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        second = build_stage3d_fill_bulk_completion_wave1(**self._inputs())
        self.assertEqual(first, second)
        invalid = deepcopy(first)
        records = invalid["stage3d-fill-bulk-completion-wave1-cumulative-program-people.json"]["records"]
        records.append(deepcopy(records[0]))
        with self.assertRaises(Stage3DFillBulkCompletionWave1ValidationError):
            validate_stage3d_fill_bulk_completion_wave1(invalid, **self._inputs())

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
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-bulk-completion-wave1", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.assertTrue(report.is_file())
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-bulk-completion-wave1", *shared,
             "--artifact-dir", str(output), "--result-output", str(result_output)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
