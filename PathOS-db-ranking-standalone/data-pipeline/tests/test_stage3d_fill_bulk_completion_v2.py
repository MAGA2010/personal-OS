"""Fail-closed contracts for the independent Stage 3D-Fill Bulk Completion v2 overlay."""

import hashlib
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_completion_v2 import (
        Stage3DFillBulkCompletionV2ValidationError,
        build_stage3d_fill_bulk_completion_v2,
    )
except ImportError:
    Stage3DFillBulkCompletionV2ValidationError = ValueError
    build_stage3d_fill_bulk_completion_v2 = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillBulkCompletionV2Tests(unittest.TestCase):
    def inputs(self):
        source = ROOT / "data/stage3d-fill-bulk-completion-v2"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "batch1_dir": ROOT / "artifacts/stage3d-fill-batch1-history-anecdotes",
            "batch2_dir": ROOT / "artifacts/stage3d-fill-batch2-history-anecdotes",
            "people_pilot_dir": ROOT / "artifacts/stage3d-fill-people-pilot-notable-attendance",
            "source_manifest_path": source / "source-manifest.json",
            "cache_manifest_path": source / "cache-manifest.json",
            "history_observations_path": source / "history-observations.json",
            "anecdote_observations_path": source / "anecdote-observations.json",
            "attendance_observations_path": source / "notable-attendance-observations.json",
            "program_people_observations_path": source / "program-people-observations.json",
            "exclusions_path": source / "exclusions.json",
        }

    def test_builds_full_scope_with_truthful_unreviewed_statuses(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_completion_v2)
        artifacts = build_stage3d_fill_bulk_completion_v2(**self.inputs())
        summary = artifacts["stage3d-fill-bulk-v2-summary.json"]
        history = artifacts["stage3d-fill-bulk-v2-history.json"]["universities"]
        anecdotes = artifacts["stage3d-fill-bulk-v2-anecdotes.json"]["universities"]
        self.assertEqual(summary["total_universities"], 62)
        self.assertEqual(len(history), 62)
        self.assertEqual(len(anecdotes), 62)
        self.assertTrue(all(
            row.get("history_summary") or row.get("history_status") == "source_review_not_completed"
            for row in history
        ))
        self.assertTrue(all(
            row.get("anecdote_text") or row.get("anecdote_status") == "source_review_not_completed"
            for row in anecdotes
        ))

    def test_checkpoint_reaches_cache_verified_history_and_anecdotes_for_all_62(self):
        artifacts = build_stage3d_fill_bulk_completion_v2(**self.inputs())
        summary = artifacts["stage3d-fill-bulk-v2-summary.json"]
        self.assertEqual(summary["history_resolved_count"], 62)
        self.assertEqual(summary["anecdotes_resolved_count"], 62)
        self.assertEqual(summary["manual_verbatim_check_count"], 0)

    def test_rejects_quote_missing_from_local_cache(self):
        inputs = self.inputs()
        cache = json.loads(inputs["cache_manifest_path"].read_text())
        with TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "excerpt.txt"
            cache_path.write_text("Source URL: https://example.edu/history\nDifferent excerpt only.", encoding="utf-8")
            cache["entries"][0].update({"cache_path": str(cache_path), "sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest()})
            cache_manifest = Path(temporary) / "cache.json"
            cache_manifest.write_text(json.dumps(cache), encoding="utf-8")
            inputs["cache_manifest_path"] = cache_manifest
            with self.assertRaises(Stage3DFillBulkCompletionV2ValidationError):
                build_stage3d_fill_bulk_completion_v2(**inputs)

    def test_rejects_sha_mismatch_and_pure_name_person_id(self):
        inputs = self.inputs()
        cache = json.loads(inputs["cache_manifest_path"].read_text())
        attendance = json.loads(inputs["attendance_observations_path"].read_text())
        cache["entries"][0]["sha256"] = "0" * 64
        attendance["observations"].append({"canonical_person_id": "person:jeff-bezos"})
        with TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "cache.json"
            attendance_path = Path(temporary) / "attendance.json"
            cache_path.write_text(json.dumps(cache), encoding="utf-8")
            attendance_path.write_text(json.dumps(attendance), encoding="utf-8")
            inputs.update(cache_manifest_path=cache_path, attendance_observations_path=attendance_path)
            with self.assertRaises(Stage3DFillBulkCompletionV2ValidationError):
                build_stage3d_fill_bulk_completion_v2(**inputs)

    def test_rejects_disallowed_relationship_and_profession_program_inference(self):
        inputs = self.inputs()
        attendance = json.loads(inputs["attendance_observations_path"].read_text())
        program_people = json.loads(inputs["program_people_observations_path"].read_text())
        attendance["observations"].append({"attendance_relationship": "faculty_only"})
        program_people["observations"].append({"match_notes": "Occupation suggests this program."})
        with TemporaryDirectory() as temporary:
            attendance_path = Path(temporary) / "attendance.json"
            program_path = Path(temporary) / "program.json"
            attendance_path.write_text(json.dumps(attendance), encoding="utf-8")
            program_path.write_text(json.dumps(program_people), encoding="utf-8")
            inputs.update(attendance_observations_path=attendance_path, program_people_observations_path=program_path)
            with self.assertRaises(Stage3DFillBulkCompletionV2ValidationError):
                build_stage3d_fill_bulk_completion_v2(**inputs)

    def test_rejects_unreviewed_none_without_scope_and_is_deterministic(self):
        inputs = self.inputs()
        artifacts = build_stage3d_fill_bulk_completion_v2(**inputs)
        self.assertEqual(
            artifacts,
            build_stage3d_fill_bulk_completion_v2(**inputs),
        )
        program_people = json.loads(inputs["program_people_observations_path"].read_text())
        program_people["observations"].append({
            "candidate_id": "candidate-v2:harvard-university",
            "normalized_program_name": "computer-science",
            "record_status": "no_qualifying_person_found",
        })
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "program.json"
            path.write_text(json.dumps(program_people), encoding="utf-8")
            inputs["program_people_observations_path"] = path
            with self.assertRaises(Stage3DFillBulkCompletionV2ValidationError):
                build_stage3d_fill_bulk_completion_v2(**inputs)

    def test_source_policy_guard_is_in_the_bulk_write_path(self):
        with patch("pathos_data.stage3d_fill_bulk_completion_v2.validate_source_policy_use", side_effect=RuntimeError("guard called")):
            with self.assertRaisesRegex(RuntimeError, "guard called"):
                build_stage3d_fill_bulk_completion_v2(**self.inputs())
