"""Fail-closed TDD contracts for Stage 3D-Fill Bulk People v2."""

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from pathos_data.stage3d_fill_bulk_people_v2 import (
        Stage3DFillBulkPeopleV2ValidationError,
        build_stage3d_fill_bulk_people_v2,
        validate_stage3d_fill_bulk_people_v2,
    )
except ImportError:
    Stage3DFillBulkPeopleV2ValidationError = ValueError
    build_stage3d_fill_bulk_people_v2 = None
    validate_stage3d_fill_bulk_people_v2 = None


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json"
PROGRAMS = ROOT / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json"
BULK_PEOPLE_V1 = ROOT / "artifacts/stage3d-fill-bulk-people-completion-v1"


class Stage3DFillBulkPeopleV2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)
        self.sources = {
            "record_type": "stage3d_fill_bulk_people_v2_source_manifest",
            "sources": [],
        }
        self.cache = {
            "record_type": "stage3d_fill_bulk_people_v2_cache_manifest",
            "cache_is_gitignored": True,
            "cache_root": "cache/stage3d-fill-bulk-people-v2",
            "entries": [],
        }
        self.observations = {
            "record_type": "stage3d_fill_bulk_people_v2_program_people_observations",
            "observations": [],
        }
        self.exclusions = {
            "record_type": "stage3d_fill_bulk_people_v2_exclusions",
            "records": [],
        }

    def tearDown(self):
        self.temporary.cleanup()

    def _write(self, name, document):
        path = self.temp / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def _inputs(self, *, candidate_path=CANDIDATES):
        return {
            "candidate_path": candidate_path,
            "stage3c_programs_path": PROGRAMS,
            "bulk_people_v1_dir": BULK_PEOPLE_V1,
            "source_manifest_path": self._write("sources.json", self.sources),
            "cache_manifest_path": self._write("cache.json", self.cache),
            "observations_path": self._write("observations.json", self.observations),
            "exclusions_path": self._write("exclusions.json", self.exclusions),
        }

    def _add_source(self, source_id, candidate_id, quote):
        cache_path = self.temp / f"{source_id}.txt"
        source_url = f"https://example.edu/{source_id}"
        cache_path.write_text(f"{source_url}\n{quote}\n", encoding="utf-8")
        self.sources["sources"].append({
            "source_id": source_id,
            "candidate_id": candidate_id,
            "source_url": source_url,
            "publisher": "Example University",
            "source_type": "official_institutional",
            "field_domain": "attendance_and_program_people",
            "accessed_date": "2026-07-14",
            "verified_direct_quotes": [quote],
            "field_level_provenance_required": True,
        })
        self.cache["entries"].append({
            "source_id": source_id,
            "source_url": source_url,
            "cache_path": str(cache_path),
            "sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
            "quote_verification_method": "local_cache_substring_check",
            "retrieval_or_review_notes": "Test-only reviewed official excerpt.",
        })

    def _positive_observation(self, candidate_id, program_name, source_id, person_name="Alex Example"):
        quote = f"{person_name} graduated from Example University with a degree in {program_name}."
        self._add_source(source_id, candidate_id, quote)
        candidate_suffix = candidate_id.removeprefix("candidate-v2:")
        person_slug = person_name.lower().replace(" ", "-")
        source_slug = source_id.replace("_", "-")
        return {
            "candidate_id": candidate_id,
            "normalized_program_name": program_name,
            "slot_status": "identified_person",
            "person_id": f"person:{person_slug}:{candidate_suffix}:{source_slug}",
            "person_name": person_name,
            "person_identity_disambiguator_source_id": source_id,
            "identity_resolution_method": "source_context_exact",
            "identity_confirmation_notes": "Official source names person, institution, and degree program.",
            "relationship_type": "graduated",
            "match_type": "direct_program_match",
            "program_match_basis": "source_stated_exact_program",
            "match_notes": "The source-stated degree program exactly matches the immutable top-1 slot.",
            "source_ids": [source_id],
            "evidence_anchor": {
                "attendance": {
                    "source_id": source_id,
                    "evidence_type": "direct_quote",
                    "quote": quote,
                    "quote_verification_method": "local_cache_substring_check",
                },
                "program_match": {
                    "source_id": source_id,
                    "evidence_type": "direct_quote",
                    "quote": quote,
                    "quote_verification_method": "local_cache_substring_check",
                },
            },
            "reviewed_scope": ["official alumni and degree profile"],
            "reviewed_source_ids": [source_id],
            "null_reason": None,
        }

    def test_generates_exactly_62_top1_slots_with_only_allowed_statuses_and_provenance(self):
        self.assertIsNotNone(build_stage3d_fill_bulk_people_v2)
        artifacts = build_stage3d_fill_bulk_people_v2(**self._inputs())
        slots = artifacts["stage3d-fill-bulk-people-v2-slot-inventory.json"]["slots"]
        summary = artifacts["stage3d-fill-bulk-people-v2-summary.json"]
        upstream = json.loads(PROGRAMS.read_text())["universities"]
        top1 = {row["candidate_id"]: row["top_5_programs_for_demo"][0] for row in upstream}
        self.assertEqual(len(slots), 62)
        self.assertEqual(len({row["candidate_id"] for row in slots}), 62)
        self.assertEqual({row["slot_status"] for row in slots}, {"source_review_not_completed"})
        self.assertEqual(summary["slots_processed"], 62)
        self.assertEqual(summary["identified_person_count"], 0)
        self.assertEqual(summary["source_review_not_completed_count"], 62)
        self.assertEqual(summary["no_qualifying_person_found_count"], 0)
        for slot in slots:
            expected = top1[slot["candidate_id"]]
            self.assertEqual(slot["program_name"], expected["program_name"])
            self.assertEqual(slot["normalized_program_name"], expected["normalized_program_name"])
            self.assertEqual(slot["program_source_reference"]["source_id"], expected["source_id"])
            self.assertEqual(slot["program_source_reference"]["evidence_anchor"], expected["evidence_anchor"])

    def test_identified_person_requires_attendance_program_identity_and_cache_evidence(self):
        candidate_id = "candidate-v2:arizona-state-university"
        program = "Supply Chain Management/Logistics"
        self.observations["observations"] = [
            self._positive_observation(candidate_id, program, "source_test_asu_program_person")
        ]
        artifacts = build_stage3d_fill_bulk_people_v2(**self._inputs())
        identified = artifacts["stage3d-fill-bulk-people-v2-program-person-matches.json"]["records"]
        self.assertEqual(len(identified), 1)
        self.assertEqual(identified[0]["slot_status"], "identified_person")
        self.assertEqual(identified[0]["quote_verification_method"], "local_cache_substring_check")

        for mutation in ("relationship", "program_basis", "identity", "manual_quote"):
            with self.subTest(mutation=mutation):
                row = deepcopy(self.observations["observations"][0])
                if mutation == "relationship":
                    row["relationship_type"] = "faculty_only"
                elif mutation == "program_basis":
                    row["program_match_basis"] = "profession_inference"
                elif mutation == "identity":
                    row["person_id"] = "person:alex-example"
                else:
                    row["evidence_anchor"]["program_match"]["quote_verification_method"] = "manual_verbatim_check"
                self.observations["observations"] = [row]
                with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
                    build_stage3d_fill_bulk_people_v2(**self._inputs())

    def test_no_qualifying_requires_reviewed_scope_and_source_ids(self):
        self.observations["observations"] = [{
            "candidate_id": "candidate-v2:arizona-state-university",
            "normalized_program_name": "Supply Chain Management/Logistics",
            "slot_status": "no_qualifying_person_found",
            "reviewed_scope": [],
            "reviewed_source_ids": [],
            "review_notes": "No qualifying evidence in reviewed scope.",
        }]
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs())

    def test_cache_sha_and_substring_are_fail_closed(self):
        row = self._positive_observation(
            "candidate-v2:arizona-state-university",
            "Supply Chain Management/Logistics",
            "source_test_cache",
        )
        self.observations["observations"] = [row]
        self.cache["entries"][0]["sha256"] = "0" * 64
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs())
        cache_path = Path(self.cache["entries"][0]["cache_path"])
        cache_path.write_text(self.sources["sources"][0]["source_url"] + "\nDifferent quote\n", encoding="utf-8")
        self.cache["entries"][0]["sha256"] = hashlib.sha256(cache_path.read_bytes()).hexdigest()
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs())

    def test_same_name_is_context_disambiguated_and_cross_source_same_school_requires_confirmation(self):
        first = self._positive_observation(
            "candidate-v2:arizona-state-university",
            "Supply Chain Management/Logistics",
            "source_test_same_name_asu",
            person_name="Jordan Lee",
        )
        second = self._positive_observation(
            "candidate-v2:boston-college",
            "Finance",
            "source_test_same_name_bc",
            person_name="Jordan Lee",
        )
        self.observations["observations"] = [first, second]
        artifacts = build_stage3d_fill_bulk_people_v2(**self._inputs())
        people = artifacts["stage3d-fill-bulk-people-v2-program-person-matches.json"]["records"]
        self.assertEqual(len({row["person_id"] for row in people}), 2)

        secondary_source = "source_test_same_name_asu_secondary"
        self._add_source(
            secondary_source,
            "candidate-v2:arizona-state-university",
            "Jordan Lee graduated from Example University with a degree in Supply Chain Management/Logistics.",
        )
        first["source_ids"] = [first["source_ids"][0], secondary_source]
        first["reviewed_source_ids"] = list(first["source_ids"])
        first["identity_resolution_method"] = "source_context_exact"
        self.observations["observations"] = [first]
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs())

        first["identity_resolution_method"] = "manual_source_context_confirmation"
        first["identity_confirmation_notes"] = "Both reviewed sources were manually confirmed to refer to the same person and school context."
        self.observations["observations"] = [first]
        artifacts = build_stage3d_fill_bulk_people_v2(**self._inputs())
        self.assertEqual(
            artifacts["stage3d-fill-bulk-people-v2-program-person-matches.json"]["records"][0]["person_name"],
            "Jordan Lee",
        )

    def test_unconfirmed_same_name_is_recorded_as_an_exclusion(self):
        self.exclusions["records"] = [{
            "candidate_id": "candidate-v2:arizona-state-university",
            "person_name": "Jordan Lee",
            "observed_relationship": "unclear",
            "exclusion_reason": "same_name_unresolved",
            "source_id": None,
            "evidence_anchor": None,
            "notes": "No reviewed evidence uniquely resolves the observed name to one person.",
        }]
        artifacts = build_stage3d_fill_bulk_people_v2(**self._inputs())
        exclusions = artifacts["stage3d-fill-bulk-people-v2-exclusions.json"]["records"]
        self.assertEqual(exclusions[0]["exclusion_reason"], "same_name_unresolved")

    def test_ranking_contamination_and_upstream_sha_drift_are_rejected(self):
        row = self._positive_observation(
            "candidate-v2:arizona-state-university",
            "Supply Chain Management/Logistics",
            "source_test_contamination",
        )
        row["usnews_rank"] = 1
        self.observations["observations"] = [row]
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs())

        candidate = json.loads(CANDIDATES.read_text())
        candidate["universities"][0]["display_name"] += " tampered"
        tampered = self._write("candidate-tampered.json", candidate)
        self.observations["observations"] = []
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            build_stage3d_fill_bulk_people_v2(**self._inputs(candidate_path=tampered))

    def test_status_enum_and_deterministic_rebuild_are_enforced(self):
        inputs = self._inputs()
        first = build_stage3d_fill_bulk_people_v2(**inputs)
        second = build_stage3d_fill_bulk_people_v2(**inputs)
        self.assertEqual(first, second)
        invalid = deepcopy(first)
        invalid["stage3d-fill-bulk-people-v2-slot-inventory.json"]["slots"][0]["slot_status"] = "unknown"
        with self.assertRaises(Stage3DFillBulkPeopleV2ValidationError):
            validate_stage3d_fill_bulk_people_v2(invalid, **inputs)


if __name__ == "__main__":
    unittest.main()
