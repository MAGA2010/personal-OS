"""Stage 2C full-ranking-corpus validation behavior."""

import copy
import unittest
from pathlib import Path

from pathos_data.ranking_corpus import CorpusValidationError, validate_corpus


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"


class RankingCorpusTests(unittest.TestCase):
    def test_committed_corpus_is_candidate_ready_with_coverage_gaps(self) -> None:
        result = validate_corpus(CORPUS_ROOT)
        self.assertTrue(result["readiness"]["universe_candidate_ready"])
        self.assertGreater(result["gaps"]["no_verified_stream_count"], 0)

    def test_duplicate_records_are_detected(self) -> None:
        corpus = validate_corpus(CORPUS_ROOT, materialize=True)
        duplicate = copy.deepcopy(corpus["seed_batches"][0]["records"][0])
        corpus["seed_batches"][1]["records"].append(duplicate)
        with self.assertRaises(CorpusValidationError):
            validate_corpus(CORPUS_ROOT, materialized=corpus)

    def test_edition_mismatch_is_detected(self) -> None:
        corpus = validate_corpus(CORPUS_ROOT, materialize=True)
        corpus["seed_batches"][0]["records"][0]["edition"] = "2025 Best Colleges"
        with self.assertRaises(CorpusValidationError):
            validate_corpus(CORPUS_ROOT, materialized=corpus)

    def test_identity_conflict_is_detected(self) -> None:
        corpus = validate_corpus(CORPUS_ROOT, materialize=True)
        mapping = copy.deepcopy(corpus["identity_documents"][0]["mappings"][0])
        mapping["record_id"] = "conflicting-alias"
        mapping["canonical_identity_id"] = "institution:conflicting-identity"
        corpus["identity_documents"][0]["mappings"].append(mapping)
        with self.assertRaises(CorpusValidationError):
            validate_corpus(CORPUS_ROOT, materialized=corpus)

    def test_partial_candidates_are_not_staging_records(self) -> None:
        result = validate_corpus(CORPUS_ROOT)
        self.assertEqual(result["counts"]["partial_rejected"], 2)
        self.assertEqual(result["counts"]["unresolved"], 0)

    def test_corpus_validation_does_not_generate_universe(self) -> None:
        result = validate_corpus(CORPUS_ROOT)
        self.assertFalse(result["readiness"]["universe_generated"])
