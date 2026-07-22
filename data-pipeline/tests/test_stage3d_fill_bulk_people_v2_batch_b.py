"""TDD contracts for the corrected Stage 3D-Fill Bulk People v2 Batch B."""

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_people_v2_batch_b import (
        Stage3DFillBulkPeopleV2BatchBValidationError,
        build_stage3d_fill_bulk_people_v2_batch_b,
        validate_stage3d_fill_bulk_people_v2_batch_b,
    )
except ImportError:
    Stage3DFillBulkPeopleV2BatchBValidationError = ValueError
    build_stage3d_fill_bulk_people_v2_batch_b = None
    validate_stage3d_fill_bulk_people_v2_batch_b = None


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PIPELINE_V2 = ROOT / "artifacts/stage3d-fill-bulk-people-v2"
BULK_PEOPLE_V1 = ROOT / "artifacts/stage3d-fill-bulk-people-completion-v1"
BATCH_A = ROOT / "artifacts/stage3d-fill-bulk-people-v2-batch-a"
DATA = ROOT / "data/stage3d-fill-bulk-people-v2-batch-b"
SCHOOL_MANIFEST = DATA / "school-manifest.json"
SOURCE_MANIFEST = DATA / "source-manifest.json"
CACHE_MANIFEST = DATA / "cache-manifest.json"
OBSERVATIONS = DATA / "program-people-observations.json"
EXCLUSIONS = DATA / "exclusions.json"

EXPECTED_SCHOOLS = {
    "candidate-v2:brown-university",
    "candidate-v2:vanderbilt-university",
    "candidate-v2:rice-university",
    "candidate-v2:university-of-notre-dame",
    "candidate-v2:emory-university",
    "candidate-v2:university-of-california-los-angeles",
    "candidate-v2:university-of-north-carolina-chapel-hill",
    "candidate-v2:university-of-texas-austin",
    "candidate-v2:university-of-illinois-urbana-champaign",
    "candidate-v2:university-of-washington",
    "candidate-v2:georgia-institute-of-technology",
    "candidate-v2:purdue-university-main-campus",
    "candidate-v2:texas-a-and-m-university",
    "candidate-v2:carnegie-mellon-university",
    "candidate-v2:university-of-michigan-ann-arbor",
    "candidate-v2:university-of-wisconsin-madison",
    "candidate-v2:northwestern-university",
    "candidate-v2:johns-hopkins-university",
    "candidate-v2:university-of-florida",
    "candidate-v2:ohio-state-university",
}


class Stage3DFillBulkPeopleV2BatchBTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _inputs(self, **overrides):
        inputs = {
            "candidate_path": CANDIDATES,
            "pipeline_v2_dir": PIPELINE_V2,
            "bulk_people_v1_dir": BULK_PEOPLE_V1,
            "batch_a_dir": BATCH_A,
            "school_manifest_path": SCHOOL_MANIFEST,
            "source_manifest_path": SOURCE_MANIFEST,
            "cache_manifest_path": CACHE_MANIFEST,
            "observations_path": OBSERVATIONS,
            "exclusions_path": EXCLUSIONS,
        }
        inputs.update(overrides)
        return inputs

    def _write(self, name, document):
        path = self.temp / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def test_corrected_manifest_is_exact_candidate_v2_subset(self):
        manifest_ids = {row["candidate_id"] for row in json.loads(SCHOOL_MANIFEST.read_text())["schools"]}
        candidate_ids = {
            row["candidate_university_id"]
            for row in json.loads(CANDIDATES.read_text())["universities"]
        }
        self.assertEqual(manifest_ids, EXPECTED_SCHOOLS)
        self.assertEqual(len(manifest_ids), 20)
        self.assertLessEqual(manifest_ids, candidate_ids)
        self.assertNotIn("candidate-v2:virginia-tech", manifest_ids)
        self.assertIn("candidate-v2:texas-a-and-m-university", manifest_ids)

    def test_builds_twenty_attendance_records_and_twenty_processed_program_slots(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_people_v2_batch_b)
        artifacts = build_stage3d_fill_bulk_people_v2_batch_b(**self._inputs())
        attendance = artifacts["stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json"]["records"]
        slots = artifacts["stage3d-fill-bulk-people-v2-batch-b-program-people.json"]["slots"]
        summary = artifacts["stage3d-fill-bulk-people-v2-batch-b-summary.json"]
        self.assertEqual({row["candidate_id"] for row in attendance}, EXPECTED_SCHOOLS)
        self.assertEqual({row["candidate_id"] for row in slots}, EXPECTED_SCHOOLS)
        self.assertEqual(summary["total_batch_b_universities"], 20)
        self.assertEqual(summary["notable_attendance_identified_count"], 20)
        self.assertEqual(summary["program_slots_processed_count"], 20)
        self.assertEqual(summary["manual_verbatim_check_count"], 0)
        self.assertEqual(summary["cache_missing_count"], 0)
        sources = artifacts["stage3d-fill-bulk-people-v2-batch-b-source-manifest.json"]["sources"]
        for source in sources:
            self.assertTrue(source["source_url"])
            self.assertTrue(source["publisher"])
            self.assertTrue(source["cache_path"])
            self.assertEqual(len(source["sha256"]), 64)
            self.assertTrue(source["verified_quotes"])
            self.assertTrue(source["retrieval_or_review_notes"])

    def test_positive_records_are_cache_verified_and_program_identification_has_both_evidence_types(self):
        artifacts = build_stage3d_fill_bulk_people_v2_batch_b(**self._inputs())
        attendance = artifacts["stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json"]["records"]
        slots = artifacts["stage3d-fill-bulk-people-v2-batch-b-program-people.json"]["slots"]
        self.assertEqual({row["quote_verification_method"] for row in attendance}, {"local_cache_substring_check"})
        identified = [row for row in slots if row["slot_status"] == "identified_person"]
        self.assertGreaterEqual(len(identified), 1)
        for row in identified:
            self.assertIn(row["relationship_type"], {"graduated", "attended_no_degree", "alumnus_unspecified"})
            self.assertIn(row["match_type"], {"direct_program_match", "direct_related_program_match"})
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertIn("attendance", row["evidence_anchor"])
            self.assertIn("program_match", row["evidence_anchor"])

    def test_cache_sha_manual_verification_and_uncached_quote_fail_closed(self):
        for mutation in ("sha_mismatch", "manual_only", "quote_not_cached"):
            with self.subTest(mutation=mutation):
                cache = json.loads(CACHE_MANIFEST.read_text())
                sources = json.loads(SOURCE_MANIFEST.read_text())
                observations = json.loads(OBSERVATIONS.read_text())
                if mutation == "sha_mismatch":
                    cache["entries"][0]["sha256"] = "0" * 64
                elif mutation == "manual_only":
                    cache["entries"][0]["quote_verification_method"] = "manual_verbatim_check"
                else:
                    source_id = sources["sources"][0]["source_id"]
                    missing = "This reviewed quote is not present in the local cache."
                    sources["sources"][0]["verified_direct_quotes"] = [missing]
                    row = next(item for item in observations["observations"] if source_id in item["source_ids"])
                    row["evidence_anchor"]["attendance"]["quote"] = missing
                    row["evidence_anchor"]["program_match"]["quote"] = missing
                with self.assertRaises(Stage3DFillBulkPeopleV2BatchBValidationError):
                    build_stage3d_fill_bulk_people_v2_batch_b(**self._inputs(
                        cache_manifest_path=self._write("cache.json", cache),
                        source_manifest_path=self._write("sources.json", sources),
                        observations_path=self._write("observations.json", observations),
                    ))

    def test_no_qualifying_and_inference_rules_fail_closed(self):
        observations = json.loads(OBSERVATIONS.read_text())
        positive = next(row for row in observations["observations"] if row["slot_status"] == "identified_person")
        for mutation in ("empty_scope", "profession_inference", "name_only_id", "forbidden_relationship"):
            with self.subTest(mutation=mutation):
                document = deepcopy(observations)
                row = next(item for item in document["observations"] if item["candidate_id"] == positive["candidate_id"])
                if mutation == "empty_scope":
                    row.update({"slot_status": "no_qualifying_person_found", "reviewed_scope": [], "reviewed_source_ids": []})
                elif mutation == "profession_inference":
                    row["program_match_basis"] = "profession_inference"
                elif mutation == "name_only_id":
                    row["person_id"] = "person:" + row["person_name"].casefold().replace(" ", "-")
                else:
                    row["relationship_type"] = "faculty_only"
                with self.assertRaises(Stage3DFillBulkPeopleV2BatchBValidationError):
                    build_stage3d_fill_bulk_people_v2_batch_b(
                        **self._inputs(observations_path=self._write(f"{mutation}.json", document))
                    )

    def test_batch_a_is_not_overwritten_and_cumulative_counts_are_derived(self):
        before = {path.name: path.read_bytes() for path in BATCH_A.glob("*.json")}
        artifacts = build_stage3d_fill_bulk_people_v2_batch_b(**self._inputs())
        after = {path.name: path.read_bytes() for path in BATCH_A.glob("*.json")}
        summary = artifacts["stage3d-fill-bulk-people-v2-batch-b-summary.json"]
        self.assertEqual(before, after)
        self.assertEqual(summary["cumulative_batch_a_b_university_occurrences"], 30)
        self.assertEqual(summary["cumulative_batch_a_b_universities_processed"], 29)
        self.assertEqual(summary["cumulative_batch_a_b_notable_attendance_identified"], 29)
        self.assertEqual(
            summary["cumulative_batch_a_b_program_slots_processed"],
            summary["cumulative_batch_a_b_program_people_identified"]
            + summary["cumulative_batch_a_b_program_people_source_review_not_completed"]
            + summary["cumulative_batch_a_b_program_people_no_qualifying_person_found"],
        )
        gaps = artifacts["stage3d-fill-bulk-people-v2-batch-b-gap-disclosure.json"]["gaps"]
        self.assertTrue(gaps)
        self.assertTrue(all(row["slot_status"] == "source_review_not_completed" for row in gaps))
        self.assertTrue(all(row["display_as_none"] is False for row in gaps))

    def test_artifacts_are_deterministic_and_validator_rejects_mutation(self):
        inputs = self._inputs()
        first = build_stage3d_fill_bulk_people_v2_batch_b(**inputs)
        second = build_stage3d_fill_bulk_people_v2_batch_b(**inputs)
        self.assertEqual(first, second)
        invalid = deepcopy(first)
        invalid["stage3d-fill-bulk-people-v2-batch-b-summary.json"]["ranking_field_contamination"] = 1
        with self.assertRaises(Stage3DFillBulkPeopleV2BatchBValidationError):
            validate_stage3d_fill_bulk_people_v2_batch_b(invalid, **inputs)

    def test_cli_generates_and_validates_the_independent_overlay(self):
        output = self.temp / "artifacts"
        report = self.temp / "report.md"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--candidate-v2", str(CANDIDATES),
            "--pipeline-v2-dir", str(PIPELINE_V2),
            "--bulk-people-v1-dir", str(BULK_PEOPLE_V1),
            "--batch-a-dir", str(BATCH_A),
            "--school-manifest", str(SCHOOL_MANIFEST),
            "--source-manifest", str(SOURCE_MANIFEST),
            "--cache-manifest", str(CACHE_MANIFEST),
            "--observations", str(OBSERVATIONS),
            "--exclusions", str(EXCLUSIONS),
        ]
        generated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "generate-stage3d-fill-bulk-people-v2-batch-b", *shared,
             "--output", str(output), "--report-output", str(report)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.assertTrue(report.is_file())
        validation_args = []
        for name in (
            "plan", "notable-attendance", "program-people", "exclusions-output",
            "source-manifest-output", "cache-manifest-output", "gap-disclosure", "summary",
        ):
            filename = "stage3d-fill-bulk-people-v2-batch-b-" + name.replace("-output", "") + ".json"
            validation_args.extend(["--" + name, str(output / filename)])
        result_output = self.temp / "validation.json"
        validated = subprocess.run(
            [sys.executable, "-m", "pathos_data", "validate-stage3d-fill-bulk-people-v2-batch-b", *shared,
             *validation_args, "--result-output", str(result_output)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result_output.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
