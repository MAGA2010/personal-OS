"""Contracts for the independent Stage 3D-Fill Batch 2 history/anecdote overlay."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_batch2_history_anecdotes import (
        Stage3DFillBatch2ValidationError,
        build_stage3d_fill_batch2,
    )
except ImportError:
    build_stage3d_fill_batch2 = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillBatch2HistoryAnecdotesTests(unittest.TestCase):
    def inputs(self):
        source_dir = ROOT / "data/stage3d-fill-batch2"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "stage3d_fill_seed_dir": ROOT / "artifacts/stage3d-fill-reviewed-people-narrative",
            "batch1_dir": ROOT / "artifacts/stage3d-fill-batch1-history-anecdotes",
            "source_manifest_path": source_dir / "source-manifest.json",
            "history_observations_path": source_dir / "history-observations.json",
            "anecdote_observations_path": source_dir / "anecdote-observations.json",
            "attendance_observations_path": source_dir / "attendance-observations.json",
            "program_people_observations_path": source_dir / "program-people-observations.json",
            "exclusions_path": source_dir / "exclusions.json",
        }

    def test_builds_fixed_scope_with_batch_and_cumulative_coverage(self):
        self.assertIsNotNone(build_stage3d_fill_batch2)
        artifacts = build_stage3d_fill_batch2(**self.inputs())
        summary = artifacts["stage3d-fill-batch2-summary.json"]
        self.assertEqual(len(artifacts["stage3d-fill-batch2-history.json"]["universities"]), 62)
        self.assertEqual(len(artifacts["stage3d-fill-batch2-anecdotes.json"]["universities"]), 62)
        self.assertEqual(summary["batch2_history_resolved_count"], 8)
        self.assertEqual(summary["batch2_anecdotes_resolved_count"], 8)
        self.assertEqual(summary["cumulative_history_resolved_count_after_batch2"], 16)
        self.assertEqual(summary["cumulative_anecdotes_resolved_count_after_batch2"], 16)
        self.assertTrue(summary["ready_for_claude_gate_review"])

    def test_rejects_anchor_not_in_reviewed_short_quote_allowlist(self):
        inputs = self.inputs()
        document = json.loads(inputs["history_observations_path"].read_text(encoding="utf-8"))
        document["observations"][0]["evidence_anchor"]["quote"] = "This is a paraphrase, not a reviewed quote."
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "history-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["history_observations_path"] = path
            with self.assertRaises(Stage3DFillBatch2ValidationError):
                build_stage3d_fill_batch2(**inputs)

    def test_rejects_unreviewed_program_slot_as_scoped_none(self):
        inputs = self.inputs()
        document = json.loads(inputs["program_people_observations_path"].read_text(encoding="utf-8"))
        document["observations"].append({
            "candidate_id": "candidate-v2:arizona-state-university",
            "normalized_program_name": "computer-science",
            "record_status": "no_qualifying_person_found",
            "reviewed_scope": [],
            "reviewed_source_ids": [],
        })
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "program-people-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["program_people_observations_path"] = path
            with self.assertRaises(Stage3DFillBatch2ValidationError):
                build_stage3d_fill_batch2(**inputs)
