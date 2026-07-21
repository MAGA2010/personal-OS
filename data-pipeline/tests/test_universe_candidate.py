"""Stage 2D candidate provenance and non-final-output behavior."""

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from pathos_data.ranking_corpus import validate_corpus
from pathos_data.universe_candidate import (
    CandidateValidationError,
    build_candidate,
    validate_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"
CORPUS_RESULT = CORPUS_ROOT / "corpus" / "corpus-validation-result.json"
CANDIDATE_PATH = (
    ROOT
    / "data"
    / "university-universe"
    / "2026-best-colleges"
    / "candidate"
    / "university-universe-candidate.json"
)


class UniverseCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = validate_corpus(CORPUS_ROOT, materialize=True)
        self.corpus_result = json.loads(CORPUS_RESULT.read_text(encoding="utf-8"))
        self.candidate = build_candidate(self.corpus)

    def assert_formally_valid(self, candidate: dict) -> None:
        validate_candidate(candidate, self.corpus, self.corpus_result)

    def test_committed_candidate_is_source_limited_and_valid(self) -> None:
        committed = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        self.assert_formally_valid(committed)
        self.assertFalse(committed["metadata"]["final_universe"])

    def test_duplicate_identity_dedupes_to_one_candidate(self) -> None:
        gt = [
            item
            for item in self.candidate["universities"]
            if item["canonical_identity_id"]
            == "institution:georgia-institute-of-technology"
        ]
        self.assertEqual(len(gt), 1)

    def test_partial_and_no_verified_streams_cannot_create_candidates(self) -> None:
        names = {
            item["canonical_identity_id"] for item in self.candidate["universities"]
        }
        self.assertNotIn("institution:carnegie-mellon-university", names)
        self.assertNotIn("institution:no-verified-stream", names)

    def test_candidate_reference_to_nonexistent_record_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["universities"][0]["supporting_ranking_records"].append(
            "not-a-corpus-record"
        )
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_candidate_reference_to_partial_record_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["universities"][0]["supporting_ranking_records"].append(
            "pilot-business-tepper-partial"
        )
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_membership_reference_to_non_corpus_record_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["memberships"][0]["supporting_ranking_records"] = [
            "not-a-corpus-record"
        ]
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_anchor_reference_to_non_corpus_record_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["universities"][0]["evidence_anchor_references"][0][
            "record_id"
        ] = "not-a-corpus-record"
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_hand_edited_candidate_artifact_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["universities"][0]["official_or_normalized_name"] = "Hand edited"
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_formal_cli_requires_corpus_validation_result(self) -> None:
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pathos_data",
                "validate-universe-candidate",
                "--candidate",
                str(CANDIDATE_PATH),
                "--corpus-root",
                str(CORPUS_ROOT),
                "--result-output",
                str(ROOT / "data" / "cache" / "candidate-test-result.json"),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--corpus-validation-result", result.stderr)

    def test_empty_gap_disclosure_fails(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["gap_disclosure"] = {}
        with self.assertRaises(CandidateValidationError):
            self.assert_formally_valid(candidate)

    def test_required_metadata_truthful_flags_cannot_be_missing_or_false(self) -> None:
        for field in ("source_limited", "incomplete", "not_final"):
            candidate = copy.deepcopy(self.candidate)
            candidate["metadata"].pop(field)
            with self.assertRaises(CandidateValidationError, msg=field):
                self.assert_formally_valid(candidate)
            candidate = copy.deepcopy(self.candidate)
            candidate["metadata"][field] = False
            with self.assertRaises(CandidateValidationError, msg=f"{field}=false"):
                self.assert_formally_valid(candidate)

    def test_final_output_metadata_flags_must_be_false(self) -> None:
        for field in (
            "final_universe",
            "frontend_export",
            "selection_memberships",
        ):
            candidate = copy.deepcopy(self.candidate)
            candidate["metadata"][field] = True
            with self.assertRaises(CandidateValidationError, msg=field):
                self.assert_formally_valid(candidate)

    def test_membership_rows_use_atomic_reasons_only(self) -> None:
        self.assertNotIn(
            "both_candidate",
            {item["membership_reason"] for item in self.candidate["memberships"]},
        )

    def test_membership_retains_all_supporting_evidence(self) -> None:
        asu_membership = next(
            item
            for item in self.candidate["memberships"]
            if item["candidate_university_id"] == "candidate:arizona-state-university"
        )
        self.assertGreater(len(asu_membership["supporting_ranking_records"]), 1)
        self.assertTrue(asu_membership["source_ids"])
        self.assertTrue(asu_membership["evidence_anchor_references"])

    def test_both_candidate_expands_to_two_membership_rows(self) -> None:
        fixture = copy.deepcopy(self.candidate)
        national = next(
            item
            for item in fixture["memberships"]
            if item["membership_reason"] == "national_top_50_candidate"
        )
        fixture["memberships"].append(
            {**national, "membership_reason": "program_top_20_candidate"}
        )
        rows = [
            item
            for item in fixture["memberships"]
            if item["candidate_university_id"] == national["candidate_university_id"]
        ]
        self.assertEqual(
            {item["membership_reason"] for item in rows},
            {"national_top_50_candidate", "program_top_20_candidate"},
        )
