"""Regression tests for the independent Stage 3D people/narrative overlay."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

try:
    from pathos_data.stage3d_people_narrative import (
        Stage3DPeopleNarrativeValidationError,
        build_stage3d_people_narrative,
        render_stage3d_report,
        validate_stage3d_people_narrative,
    )
except ImportError:
    build_stage3d_people_narrative = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DPeopleNarrativeTests(unittest.TestCase):
    def inputs(self) -> dict:
        source_dir = ROOT / "data/stage3d"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3_dir": ROOT / "artifacts/stage3-program-mvp-detail-pack",
            "stage3b_dir": ROOT / "artifacts/stage3b-demo-critical-gap-fill",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "stage3c2_dir": ROOT / "artifacts/stage3c2-nearest-towns-gap-repair",
            "source_manifest_path": source_dir / "source-manifest.json",
            "person_mappings_path": source_dir / "person-identity-mappings.json",
            "program_alias_mappings_path": source_dir / "program-alias-mappings.json",
            "top_program_observations_path": source_dir / "top-program-notable-student-observations.json",
            "attendance_observations_path": source_dir / "notable-attendance-observations.json",
            "history_observations_path": source_dir / "history-observations.json",
            "interesting_fact_observations_path": source_dir / "interesting-fact-observations.json",
        }

    def test_unreviewed_slots_are_explicit_gaps_not_false_wu_results(self):
        self.assertIsNotNone(build_stage3d_people_narrative)
        artifacts = build_stage3d_people_narrative(**self.inputs())
        slots = artifacts["stage3d-top-program-notable-students.json"]["records"]

        self.assertEqual(len(slots), 310)
        self.assertTrue(all(slot["record_status"] == "source_review_not_completed" for slot in slots))
        self.assertTrue(all(slot["display_value"] is None for slot in slots))
        self.assertTrue(all(slot["reviewed_scope"] == [] for slot in slots))
        self.assertTrue(all(slot["null_reason"] == "stage3d_source_review_not_completed" for slot in slots))

    def test_validator_rejects_forbidden_relationship_and_ranking_contamination(self):
        artifacts = build_stage3d_people_narrative(**self.inputs())
        with TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "stage3d-report.md"
            report_path.write_text(render_stage3d_report(artifacts), encoding="utf-8")
            result = validate_stage3d_people_narrative(artifacts, **self.inputs(), report_path=report_path)
            self.assertEqual(result["result"], "passed")

            slot = artifacts["stage3d-top-program-notable-students.json"]["records"][0]
            slot["record_status"] = "identified"
            slot["relationship_type"] = "faculty_only"
            with self.assertRaises(Stage3DPeopleNarrativeValidationError):
                validate_stage3d_people_narrative(artifacts, **self.inputs(), report_path=report_path)

            artifacts = build_stage3d_people_narrative(**self.inputs())
            artifacts["stage3d-top-program-notable-students.json"]["records"][0]["usnews_rank"] = 1
            with self.assertRaises(Stage3DPeopleNarrativeValidationError):
                validate_stage3d_people_narrative(artifacts, **self.inputs(), report_path=report_path)

    def test_bundle_is_deterministic_and_requires_all_candidate_rows(self):
        first = build_stage3d_people_narrative(**self.inputs())
        second = build_stage3d_people_narrative(**self.inputs())
        self.assertEqual(first, second)
        universities = first["stage3d-universities.json"]["universities"]
        self.assertEqual(len(universities), 62)
        self.assertTrue(all(row["people_status"] == "source_review_not_completed" for row in universities))
        self.assertTrue(all(row["history_status"] == "source_review_not_completed" for row in universities))

    def test_source_policy_guard_is_called_for_stage3d_detail_source_ingestion(self):
        inputs = self.inputs()
        with TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "source-manifest.json"
            source_path.write_text(json.dumps({
                "record_type": "stage3d_source_manifest",
                "sources": [{
                    "source_id": "source_test_detail", "source_type": "reputable_reference",
                    "field_domain": "people", "source_title": "Reviewed test detail source",
                    "source_url_or_reference": "https://example.invalid/detail", "publisher": "CollegeData",
                    "source_confidence": "medium", "official_institutional": False,
                }],
            }), encoding="utf-8")
            inputs["source_manifest_path"] = source_path
            with patch(
                "pathos_data.stage3d_people_narrative.validate_source_policy_use",
                side_effect=Stage3DPeopleNarrativeValidationError("blocked"),
            ):
                with self.assertRaises(Stage3DPeopleNarrativeValidationError):
                    build_stage3d_people_narrative(**inputs)


if __name__ == "__main__":
    unittest.main()
