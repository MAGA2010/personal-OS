"""Contracts for the independent Stage 3D-Fill Batch 1 history/anecdote overlay."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_batch1_history_anecdotes import (
        Stage3DFillBatch1ValidationError,
        build_stage3d_fill_batch1,
        render_stage3d_fill_batch1_report,
        validate_stage3d_fill_batch1,
    )
except ImportError:
    build_stage3d_fill_batch1 = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillBatch1HistoryAnecdotesTests(unittest.TestCase):
    def inputs(self):
        source_dir = ROOT / "data/stage3d-fill-batch1"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "stage3d_fill_seed_dir": ROOT / "artifacts/stage3d-fill-reviewed-people-narrative",
            "source_manifest_path": source_dir / "source-manifest.json",
            "history_observations_path": source_dir / "history-observations.json",
            "anecdote_observations_path": source_dir / "anecdote-observations.json",
            "attendance_observations_path": source_dir / "attendance-observations.json",
            "program_people_observations_path": source_dir / "program-people-observations.json",
            "exclusions_path": source_dir / "exclusions.json",
        }

    def test_full_scope_uses_sourced_history_and_explicit_unreviewed_gaps(self):
        self.assertIsNotNone(build_stage3d_fill_batch1)
        artifacts = build_stage3d_fill_batch1(**self.inputs())
        history = artifacts["stage3d-fill-batch1-history.json"]
        anecdotes = artifacts["stage3d-fill-batch1-anecdotes.json"]
        program_people = artifacts["stage3d-fill-batch1-program-people.json"]["records"]
        self.assertEqual(len(history["universities"]), 62)
        self.assertEqual(len(anecdotes["universities"]), 62)
        self.assertEqual(len(history["facts"]), 8)
        self.assertEqual(len(anecdotes["facts"]), 8)
        self.assertEqual(len(program_people), 310)
        self.assertTrue(all(row["record_status"] == "source_review_not_completed" for row in program_people))
        self.assertEqual(history["facts"][0]["evidence_anchor"]["quote_verification_method"], "manual_verbatim_check")

    def test_rejects_paraphrase_labeled_as_direct_quote(self):
        inputs = self.inputs()
        document = json.loads(inputs["history_observations_path"].read_text(encoding="utf-8"))
        document["observations"][0]["evidence_anchor"]["quote"] = "Harvard was founded in 1636."
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "history-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["history_observations_path"] = path
            with self.assertRaises(Stage3DFillBatch1ValidationError):
                build_stage3d_fill_batch1(**inputs)

    def test_validator_rejects_excluded_attendance_relationship(self):
        inputs = self.inputs()
        document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        document["observations"].append({
            "candidate_id": "candidate-v2:harvard-university",
            "attendance_relationship": "faculty_only",
        })
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "attendance-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["attendance_observations_path"] = path
            with self.assertRaises(Stage3DFillBatch1ValidationError):
                build_stage3d_fill_batch1(**inputs)
