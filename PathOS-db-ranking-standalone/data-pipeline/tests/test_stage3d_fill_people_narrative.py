"""Regression tests for the reviewed-source Stage 3D-Fill overlay."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_people_narrative import (
        Stage3DFillValidationError,
        build_stage3d_fill,
        render_stage3d_fill_report,
        validate_stage3d_fill,
    )
except ImportError:
    build_stage3d_fill = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillPeopleNarrativeTests(unittest.TestCase):
    def inputs(self):
        source_dir = ROOT / "data/stage3d-fill"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "stage3d_dir": ROOT / "artifacts/stage3d-people-narrative-enrichment",
            "source_manifest_path": source_dir / "source-manifest.json",
            "person_mappings_path": source_dir / "person-identity-mappings.json",
            "program_observations_path": source_dir / "program-people-observations.json",
            "attendance_observations_path": source_dir / "notable-attendance-observations.json",
            "history_observations_path": source_dir / "history-observations.json",
            "anecdote_observations_path": source_dir / "anecdote-observations.json",
        }

    def test_all_slots_remain_explicit_source_gaps_until_reviewed(self):
        self.assertIsNotNone(build_stage3d_fill)
        artifacts = build_stage3d_fill(**self.inputs())
        records = artifacts["stage3d-fill-program-people.json"]["records"]
        self.assertEqual(len(records), 310)
        self.assertTrue(all(row["record_status"] == "source_review_not_completed" for row in records))
        self.assertTrue(all(row["display_value"] is None for row in records))

    def test_validator_rejects_unreviewed_slot_masquerading_as_wu(self):
        artifacts = build_stage3d_fill(**self.inputs())
        with TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "stage3d-fill.md"
            report_path.write_text(render_stage3d_fill_report(artifacts), encoding="utf-8")
            self.assertEqual(validate_stage3d_fill(artifacts, **self.inputs(), report_path=report_path)["result"], "passed")
            artifacts["stage3d-fill-program-people.json"]["records"][0].update({"record_status": "no_qualifying_person_found", "display_value": "无"})
            with self.assertRaises(Stage3DFillValidationError):
                validate_stage3d_fill(artifacts, **self.inputs(), report_path=report_path)

    def test_deterministic_scope_and_ranking_isolation(self):
        first = build_stage3d_fill(**self.inputs())
        self.assertEqual(first, build_stage3d_fill(**self.inputs()))
        self.assertEqual(len(first["stage3d-fill-history.json"]["universities"]), 62)
        first["stage3d-fill-program-people.json"]["records"][0]["usnews_rank"] = 1
        with TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "stage3d-fill.md"
            report_path.write_text(render_stage3d_fill_report(build_stage3d_fill(**self.inputs())), encoding="utf-8")
            with self.assertRaises(Stage3DFillValidationError):
                validate_stage3d_fill(first, **self.inputs(), report_path=report_path)

    def test_reviewed_official_history_fact_is_short_sourced_paraphrase(self):
        artifacts = build_stage3d_fill(**self.inputs())
        facts = artifacts["stage3d-fill-history.json"]["facts"]
        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["candidate_id"], "candidate-v2:harvard-university")
        self.assertEqual(fact["source_id"], "source_harvard_official_history_2026")
        self.assertLessEqual(len(fact["paraphrase"]), 280)
        self.assertLessEqual(len(fact["evidence_anchor"]["quote"]), 280)
        self.assertEqual(fact["evidence_anchor"]["source_id"], fact["source_id"])
        self.assertEqual(
            fact["evidence_anchor"]["quote"],
            "On October 28, 1636, Harvard, the first college in the American colonies, was founded.",
        )
        self.assertEqual(fact["evidence_anchor"]["quote_verification_method"], "manual_verbatim_check")

    def test_rejects_paraphrase_labeled_as_direct_quote(self):
        inputs = self.inputs()
        observation = json.loads(inputs["history_observations_path"].read_text(encoding="utf-8"))
        observation["observations"][0]["evidence_anchor"]["quote"] = "Harvard was founded in 1636."
        with TemporaryDirectory() as temporary:
            observation_path = Path(temporary) / "history-observations.json"
            observation_path.write_text(json.dumps(observation), encoding="utf-8")
            inputs["history_observations_path"] = observation_path
            with self.assertRaises(Stage3DFillValidationError):
                build_stage3d_fill(**inputs)
