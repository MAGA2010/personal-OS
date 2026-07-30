"""Fail-closed contracts for Stage 3D-Fill Bulk People Completion v1."""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_people_completion_v1 import (
        Stage3DFillBulkPeopleCompletionV1ValidationError,
        build_stage3d_fill_bulk_people_completion_v1,
    )
except ImportError:
    Stage3DFillBulkPeopleCompletionV1ValidationError = ValueError
    build_stage3d_fill_bulk_people_completion_v1 = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillBulkPeopleCompletionV1Tests(unittest.TestCase):
    def inputs(self):
        source = ROOT / "data/stage3d-fill-bulk-people-completion-v1"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "people_pilot_dir": ROOT / "artifacts/stage3d-fill-people-pilot-notable-attendance",
            "bulk_v2_dir": ROOT / "artifacts/stage3d-fill-bulk-completion-v2",
            "source_manifest_path": source / "source-manifest.json",
            "cache_manifest_path": source / "cache-manifest.json",
            "attendance_observations_path": source / "notable-attendance-observations.json",
            "exclusions_path": source / "exclusions.json",
        }

    def _temporary_document(self, document, name, temporary):
        path = Path(temporary) / name
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_completes_reviewed_attendance_coverage_for_all_62_without_program_expansion(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_people_completion_v1)
        artifacts = build_stage3d_fill_bulk_people_completion_v1(**self.inputs())
        summary = artifacts["stage3d-fill-bulk-people-v1-summary.json"]
        records = artifacts["stage3d-fill-bulk-people-v1-notable-attendance.json"]["records"]
        sources = {
            row["source_id"]: row
            for row in artifacts["stage3d-fill-bulk-people-v1-source-manifest.json"]["sources"]
        }
        caches = {
            row["source_id"]: row
            for row in artifacts["stage3d-fill-bulk-people-v1-cache-manifest.json"]["entries"]
        }
        self.assertEqual(summary["total_universities"], 62)
        self.assertEqual(summary["notable_attendance_before_count"], 10)
        self.assertEqual(summary["notable_attendance_covered_university_count"], 62)
        self.assertGreaterEqual(summary["notable_attendance_after_count"], 62)
        self.assertEqual({row["candidate_id"] for row in records}, set(summary["covered_candidate_ids"]))
        self.assertEqual(summary["program_people_before_count"], 0)
        self.assertEqual(summary["program_people_after_count"], 0)
        self.assertEqual(summary["program_people_source_review_not_completed_count"], 310)
        self.assertEqual(summary["manual_verbatim_check_count"], 0)
        for row in records:
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertIn(row["source_id"], sources)
            self.assertIn(row["source_id"], caches)
            self.assertEqual(row["quote_verification_method"], "local_cache_substring_check")
            self.assertEqual(len(caches[row["source_id"]]["sha256"]), 64)
            self.assertGreaterEqual(row["canonical_person_id"].count(":"), 3)

    def test_rejects_manual_quote_and_disallowed_relationship(self):
        inputs = self.inputs()
        observations = json.loads(inputs["attendance_observations_path"].read_text())
        observations["observations"][0]["evidence_anchor"]["quote_verification_method"] = "manual_verbatim_check"
        observations["observations"][1]["attendance_relationship"] = "faculty_only"
        with TemporaryDirectory() as temporary:
            inputs["attendance_observations_path"] = self._temporary_document(observations, "attendance.json", temporary)
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)

    def test_rejects_cache_sha_mismatch_and_quote_missing_from_cache(self):
        inputs = self.inputs()
        cache = json.loads(inputs["cache_manifest_path"].read_text())
        with TemporaryDirectory() as temporary:
            excerpt = Path(temporary) / "excerpt.txt"
            excerpt.write_text("Reviewed official source without the asserted quote.", encoding="utf-8")
            cache["entries"][0].update({
                "cache_path": str(excerpt),
                "sha256": hashlib.sha256(excerpt.read_bytes()).hexdigest(),
            })
            inputs["cache_manifest_path"] = self._temporary_document(cache, "cache.json", temporary)
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)
            cache["entries"][0]["sha256"] = "0" * 64
            inputs["cache_manifest_path"] = self._temporary_document(cache, "cache-bad-sha.json", temporary)
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)

    def test_rejects_name_only_identity_and_same_id_for_different_person(self):
        inputs = self.inputs()
        observations = json.loads(inputs["attendance_observations_path"].read_text())
        observations["observations"][0]["canonical_person_id"] = "person:name-only"
        duplicate = dict(observations["observations"][1])
        duplicate["canonical_person_id"] = observations["observations"][0]["canonical_person_id"]
        observations["observations"].append(duplicate)
        with TemporaryDirectory() as temporary:
            inputs["attendance_observations_path"] = self._temporary_document(observations, "attendance.json", temporary)
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)

    def test_rejects_person_name_not_identified_by_reviewed_quote_or_source_title(self):
        inputs = self.inputs()
        observations = json.loads(inputs["attendance_observations_path"].read_text())
        observations["observations"][0]["person_name"] = "Unrelated Same Name"
        with TemporaryDirectory() as temporary:
            inputs["attendance_observations_path"] = self._temporary_document(
                observations, "attendance.json", temporary,
            )
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)

    def test_rejects_missing_source_fields_and_ranking_contamination(self):
        inputs = self.inputs()
        sources = json.loads(inputs["source_manifest_path"].read_text())
        observations = json.loads(inputs["attendance_observations_path"].read_text())
        sources["sources"][0]["source_url_or_reference"] = None
        observations["observations"][0]["usnews_rank"] = 1
        with TemporaryDirectory() as temporary:
            inputs["source_manifest_path"] = self._temporary_document(sources, "sources.json", temporary)
            inputs["attendance_observations_path"] = self._temporary_document(observations, "attendance.json", temporary)
            with self.assertRaises(Stage3DFillBulkPeopleCompletionV1ValidationError):
                build_stage3d_fill_bulk_people_completion_v1(**inputs)

    def test_build_is_deterministic_and_preserves_truthful_major_nulls(self):
        first = build_stage3d_fill_bulk_people_completion_v1(**self.inputs())
        second = build_stage3d_fill_bulk_people_completion_v1(**self.inputs())
        self.assertEqual(first, second)
        for row in first["stage3d-fill-bulk-people-v1-notable-attendance.json"]["records"]:
            if row["major_or_program"] is None:
                self.assertEqual(row["major_confidence"], "unknown")
                self.assertEqual(row["null_reason"], "major_not_stated_in_accepted_source")


if __name__ == "__main__":
    unittest.main()
