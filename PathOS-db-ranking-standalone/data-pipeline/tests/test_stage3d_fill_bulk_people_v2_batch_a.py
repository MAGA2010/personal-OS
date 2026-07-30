"""TDD contracts for reviewed-source intake Batch A."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_people_v2_batch_a import (
        Stage3DFillBulkPeopleV2BatchAValidationError,
        build_stage3d_fill_bulk_people_v2_batch_a,
        validate_stage3d_fill_bulk_people_v2_batch_a,
    )
except ImportError:
    Stage3DFillBulkPeopleV2BatchAValidationError = ValueError
    build_stage3d_fill_bulk_people_v2_batch_a = None
    validate_stage3d_fill_bulk_people_v2_batch_a = None


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_V2 = ROOT / "artifacts/stage3d-fill-bulk-people-v2"
BULK_PEOPLE_V1 = ROOT / "artifacts/stage3d-fill-bulk-people-completion-v1"
OBSERVATIONS = ROOT / "data/stage3d-fill-bulk-people-v2-batch-a/program-people-observations.json"


class Stage3DFillBulkPeopleV2BatchATests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _inputs(self, observations_path=OBSERVATIONS):
        return {
            "pipeline_v2_dir": PIPELINE_V2,
            "bulk_people_v1_dir": BULK_PEOPLE_V1,
            "observations_path": observations_path,
        }

    def _write_observations(self, document):
        path = self.temp / "observations.json"
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def test_batch_a_has_exactly_ten_target_schools_and_cache_verified_attendance(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_people_v2_batch_a)
        artifacts = build_stage3d_fill_bulk_people_v2_batch_a(**self._inputs())
        attendance = artifacts["stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json"]["records"]
        summary = artifacts["stage3d-fill-bulk-people-v2-batch-a-summary.json"]
        self.assertEqual(len(attendance), 10)
        self.assertEqual(len({row["candidate_id"] for row in attendance}), 10)
        self.assertEqual({row["quote_verification_method"] for row in attendance}, {"local_cache_substring_check"})
        self.assertEqual(summary["target_university_count"], 10)
        self.assertEqual(summary["notable_attendance_identified_count"], 10)
        self.assertEqual(summary["manual_verbatim_check_count"], 0)
        self.assertEqual(summary["cache_missing_count"], 0)

    def test_only_princeton_is_identified_and_other_top1_slots_remain_unreviewed(self):
        artifacts = build_stage3d_fill_bulk_people_v2_batch_a(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json"]["slots"]
        matches = artifacts["stage3d-fill-bulk-people-v2-batch-a-program-person-matches.json"]["records"]
        self.assertEqual(len(slots), 10)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["candidate_id"], "candidate-v2:princeton-university")
        self.assertEqual(matches[0]["person_name"], "Jeff Bezos")
        self.assertEqual(matches[0]["match_type"], "direct_related_program_match")
        self.assertEqual(matches[0]["quote_verification_method"], "local_cache_substring_check")
        self.assertEqual(sum(row["slot_status"] == "identified_person" for row in slots), 1)
        self.assertEqual(sum(row["slot_status"] == "source_review_not_completed" for row in slots), 9)
        self.assertEqual(sum(row["slot_status"] == "no_qualifying_person_found" for row in slots), 0)

    def test_program_person_requires_allowed_relationship_and_source_stated_match(self):
        document = json.loads(OBSERVATIONS.read_text())
        for field, value in (
            ("relationship_type", "faculty_only"),
            ("program_match_basis", "profession_inference"),
            ("match_type", "career_related_program_match"),
        ):
            with self.subTest(field=field):
                mutated = deepcopy(document)
                mutated["observations"][0][field] = value
                with self.assertRaises(Stage3DFillBulkPeopleV2BatchAValidationError):
                    build_stage3d_fill_bulk_people_v2_batch_a(
                        **self._inputs(self._write_observations(mutated))
                    )

    def test_program_person_requires_disambiguated_identity_and_two_evidence_anchors(self):
        document = json.loads(OBSERVATIONS.read_text())
        for mutation in ("name_only_id", "missing_attendance", "missing_program"):
            with self.subTest(mutation=mutation):
                mutated = deepcopy(document)
                row = mutated["observations"][0]
                if mutation == "name_only_id":
                    row["person_id"] = "person:jeff-bezos"
                elif mutation == "missing_attendance":
                    row["evidence_anchor"].pop("attendance")
                else:
                    row["evidence_anchor"].pop("program_match")
                with self.assertRaises(Stage3DFillBulkPeopleV2BatchAValidationError):
                    build_stage3d_fill_bulk_people_v2_batch_a(
                        **self._inputs(self._write_observations(mutated))
                    )

    def test_manual_quote_and_quote_outside_verified_cache_fail_closed(self):
        document = json.loads(OBSERVATIONS.read_text())
        for mutation in ("manual", "not_cached"):
            with self.subTest(mutation=mutation):
                mutated = deepcopy(document)
                anchor = mutated["observations"][0]["evidence_anchor"]["program_match"]
                if mutation == "manual":
                    anchor["quote_verification_method"] = "manual_verbatim_check"
                else:
                    anchor["quote"] = "This sentence is not present in the reviewed cache."
                with self.assertRaises(Stage3DFillBulkPeopleV2BatchAValidationError):
                    build_stage3d_fill_bulk_people_v2_batch_a(
                        **self._inputs(self._write_observations(mutated))
                    )

    def test_no_qualifying_person_found_requires_reviewed_scope_and_sources(self):
        document = json.loads(OBSERVATIONS.read_text())
        row = document["observations"][0]
        row.update({
            "slot_status": "no_qualifying_person_found",
            "reviewed_scope": [],
            "reviewed_source_ids": [],
        })
        with self.assertRaises(Stage3DFillBulkPeopleV2BatchAValidationError):
            build_stage3d_fill_bulk_people_v2_batch_a(
                **self._inputs(self._write_observations(document))
            )

    def test_artifacts_are_deterministic_and_validator_rejects_mutation(self):
        inputs = self._inputs()
        first = build_stage3d_fill_bulk_people_v2_batch_a(**inputs)
        second = build_stage3d_fill_bulk_people_v2_batch_a(**inputs)
        self.assertEqual(first, second)
        invalid = deepcopy(first)
        invalid["stage3d-fill-bulk-people-v2-batch-a-summary.json"]["ranking_field_contamination"] = 1
        with self.assertRaises(Stage3DFillBulkPeopleV2BatchAValidationError):
            validate_stage3d_fill_bulk_people_v2_batch_a(invalid, **inputs)


if __name__ == "__main__":
    unittest.main()
