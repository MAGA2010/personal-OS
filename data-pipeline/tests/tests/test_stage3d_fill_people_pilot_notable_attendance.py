"""Contracts for the independent Stage 3D-Fill People Pilot."""

import json
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_people_pilot_notable_attendance import (
        Stage3DFillPeoplePilotValidationError,
        build_stage3d_fill_people_pilot,
    )
except ImportError:
    build_stage3d_fill_people_pilot = None


ROOT = Path(__file__).resolve().parents[1]


class Stage3DFillPeoplePilotNotableAttendanceTests(unittest.TestCase):
    def inputs(self):
        source_dir = ROOT / "data/stage3d-fill-people-pilot"
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3c_dir": ROOT / "artifacts/stage3c-academic-geo-enrichment",
            "stage3d_fill_seed_dir": ROOT / "artifacts/stage3d-fill-reviewed-people-narrative",
            "batch1_dir": ROOT / "artifacts/stage3d-fill-batch1-history-anecdotes",
            "batch2_dir": ROOT / "artifacts/stage3d-fill-batch2-history-anecdotes",
            "source_manifest_path": source_dir / "source-manifest.json",
            "cache_manifest_path": source_dir / "reviewed-source-cache-manifest.json",
            "attendance_observations_path": source_dir / "notable-attendance-observations.json",
            "program_people_observations_path": source_dir / "program-people-observations.json",
            "exclusions_path": source_dir / "exclusions.json",
        }

    def test_builds_fixed_scope_with_reviewed_attendance_and_unreviewed_program_slots(self):
        self.assertIsNotNone(build_stage3d_fill_people_pilot)
        artifacts = build_stage3d_fill_people_pilot(**self.inputs())
        summary = artifacts["stage3d-fill-people-pilot-summary.json"]
        self.assertEqual(summary["total_universities"], 62)
        self.assertGreaterEqual(summary["notable_attendance_resolved_count"], 8)
        self.assertLessEqual(summary["notable_attendance_resolved_count"], 12)
        self.assertEqual(
            summary["program_people_source_review_not_completed_count"]
            + summary["program_people_identified_count"],
            310,
        )
        self.assertTrue(summary["ready_for_claude_gate_review"])

    def test_rejects_honorary_relationship_from_attendance(self):
        inputs = self.inputs()
        document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        document["observations"][0]["attendance_relationship"] = "honorary_degree_only"
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "notable-attendance-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["attendance_observations_path"] = path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_rejects_direct_quote_outside_reviewed_allowlist(self):
        inputs = self.inputs()
        document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        document["observations"][0]["evidence_anchor"]["quote"] = "A paraphrase is not a direct quote."
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "notable-attendance-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["attendance_observations_path"] = path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_rejects_cached_source_without_a_valid_local_cache_hash(self):
        inputs = self.inputs()
        document = json.loads(inputs["cache_manifest_path"].read_text(encoding="utf-8"))
        document["entries"][0].update({
            "cache_status": "cached",
            "cache_path": "/tmp/not-a-reviewed-source-cache.html",
            "sha256": "0" * 64,
        })
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "reviewed-source-cache-manifest.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["cache_manifest_path"] = path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_rejects_cached_quote_not_present_in_local_cache(self):
        inputs = self.inputs()
        cache_document = json.loads(inputs["cache_manifest_path"].read_text(encoding="utf-8"))
        for entry in cache_document["entries"]:
            entry["cache_path"] = str(ROOT / entry["cache_path"])
        attendance_document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        with TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "reviewed-source.txt"
            cache_path.write_text("Reviewed source excerpt without the asserted quote.", encoding="utf-8")
            cache_document["entries"][0].update({
                "cache_status": "cached",
                "cache_path": str(cache_path),
                "sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
                "quote_verification_method": "local_cache_substring_check",
            })
            attendance_document["observations"][0]["evidence_anchor"]["quote_verification_method"] = "local_cache_substring_check"
            cache_manifest_path = Path(temporary) / "reviewed-source-cache-manifest.json"
            observations_path = Path(temporary) / "notable-attendance-observations.json"
            cache_manifest_path.write_text(json.dumps(cache_document), encoding="utf-8")
            observations_path.write_text(json.dumps(attendance_document), encoding="utf-8")
            inputs["cache_manifest_path"] = cache_manifest_path
            inputs["attendance_observations_path"] = observations_path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_rejects_name_only_person_id_without_disambiguator(self):
        inputs = self.inputs()
        document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        document["observations"][0]["canonical_person_id"] = "person:jeff-bezos"
        del document["observations"][0]["person_identity_disambiguator_source_id"]
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "notable-attendance-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["attendance_observations_path"] = path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_rejects_same_name_reused_across_candidate_contexts(self):
        inputs = self.inputs()
        source_document = json.loads(inputs["source_manifest_path"].read_text(encoding="utf-8"))
        cache_document = json.loads(inputs["cache_manifest_path"].read_text(encoding="utf-8"))
        for entry in cache_document["entries"]:
            entry["cache_path"] = str(ROOT / entry["cache_path"])
        attendance_document = json.loads(inputs["attendance_observations_path"].read_text(encoding="utf-8"))
        duplicate_source = dict(source_document["sources"][0])
        duplicate_source.update({
            "source_id": "source_test_harvard_jeff_bezos",
            "candidate_id": "candidate-v2:harvard-university",
        })
        source_document["sources"].append(duplicate_source)
        duplicate_cache = dict(cache_document["entries"][0])
        duplicate_cache["source_id"] = "source_test_harvard_jeff_bezos"
        cache_document["entries"].append(duplicate_cache)
        duplicate = dict(attendance_document["observations"][0])
        duplicate.update({
            "candidate_id": "candidate-v2:harvard-university",
            "source_id": "source_test_harvard_jeff_bezos",
            "person_identity_disambiguator_source_id": "source_test_harvard_jeff_bezos",
        })
        duplicate["evidence_anchor"] = dict(duplicate["evidence_anchor"])
        duplicate["evidence_anchor"]["source_id"] = "source_test_harvard_jeff_bezos"
        attendance_document["observations"].append(duplicate)
        with TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "source-manifest.json"
            cache_path = Path(temporary) / "reviewed-source-cache-manifest.json"
            observations_path = Path(temporary) / "notable-attendance-observations.json"
            source_path.write_text(json.dumps(source_document), encoding="utf-8")
            cache_path.write_text(json.dumps(cache_document), encoding="utf-8")
            observations_path.write_text(json.dumps(attendance_document), encoding="utf-8")
            inputs["source_manifest_path"] = source_path
            inputs["cache_manifest_path"] = cache_path
            inputs["attendance_observations_path"] = observations_path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)

    def test_reuses_hardened_attendance_identity_for_jeff_bezos_program_slot(self):
        artifacts = build_stage3d_fill_people_pilot(**self.inputs())
        attendance = artifacts["stage3d-fill-people-pilot-notable-attendance.json"]["records"]
        program_people = artifacts["stage3d-fill-people-pilot-program-people.json"]["records"]
        jeff_attendance = next(row for row in attendance if row["person_name"] == "Jeff Bezos")
        jeff_program = next(row for row in program_people if row["record_status"] == "identified")
        self.assertEqual(
            jeff_attendance["canonical_person_id"],
            "person:jeff-bezos:princeton-university:source-people-pilot-princeton-bezos-attendance",
        )
        self.assertEqual(jeff_program["canonical_person_id"], jeff_attendance["canonical_person_id"])
        summary = artifacts["stage3d-fill-people-pilot-summary.json"]
        self.assertEqual(summary["cache_verified_quote_count"], 11)
        self.assertEqual(summary["cache_missing_count"], 0)

    def test_rejects_program_person_without_direct_program_match(self):
        inputs = self.inputs()
        document = json.loads(inputs["program_people_observations_path"].read_text(encoding="utf-8"))
        document["observations"].append({
            "candidate_id": "candidate-v2:princeton-university",
            "normalized_program_name": "computer-science",
            "person_name": "Example Person",
            "canonical_person_id": "person:example-person",
            "attendance_relationship": "graduated",
            "relationship_to_program": "direct_program_match",
            "source_id": "source_pilot_princeton_example",
            "evidence_anchor": {
                "source_id": "source_pilot_princeton_example",
                "evidence_type": "direct_quote",
                "quote": "Example quote",
                "quote_verification_method": "manual_verbatim_check",
            },
            "match_notes": "Occupation is not a source-backed program match.",
        })
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "program-people-observations.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            inputs["program_people_observations_path"] = path
            with self.assertRaises(Stage3DFillPeoplePilotValidationError):
                build_stage3d_fill_people_pilot(**inputs)
