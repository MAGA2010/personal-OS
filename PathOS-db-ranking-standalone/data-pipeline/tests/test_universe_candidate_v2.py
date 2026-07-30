"""Stage 2I source-limited university-universe candidate v2 safeguards."""

import json
import copy
import unittest
from pathlib import Path
from typing import Dict, Optional

from pathos_data.universe_candidate_v2 import (
    UniverseCandidateV2ValidationError,
    validate_candidate_v2_artifacts,
    validate_source_policy_use,
)


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "data" / "university-universe-candidates" / "v2-source-limited"
RANKING_ROOT = ROOT / "data" / "ranking-seeds" / "2026-best-colleges"
STAGE2H = RANKING_ROOT / "completion-programs-top20-attempt" / "completion-readiness-summary.json"
POLICY = ROOT.parent / "docs" / "database-source-policy.md"


class UniverseCandidateV2Tests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((V2 / name).read_text(encoding="utf-8"))

    def artifacts(self) -> dict:
        return {
            name: self.load(name)
            for name in (
                "candidate-universities.json", "candidate-memberships.json",
                "candidate-source-manifest.json", "candidate-identity-mappings.json",
                "candidate-gap-disclosure.json", "candidate-generation-summary.json",
                "candidate-dedupe-report.json",
            )
        }

    def validate(self, artifacts: Optional[Dict] = None, policy_text: Optional[str] = None) -> dict:
        return validate_candidate_v2_artifacts(
            artifacts or self.artifacts(), RANKING_ROOT,
            json.loads(STAGE2H.read_text(encoding="utf-8")),
            policy_text if policy_text is not None else POLICY.read_text(encoding="utf-8"),
        )

    def test_v2_summary_reports_the_full_accepted_national_and_program_inputs(self) -> None:
        summary_path = V2 / "candidate-generation-summary.json"
        self.assertTrue(summary_path.exists())
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["supporting_national_record_count"], 50)
        self.assertEqual(summary["supporting_program_record_count"], 80)
        self.assertEqual(summary["candidate_university_count"], 62)

    def test_v2_is_deterministic_and_uses_atomic_membership_reasons(self) -> None:
        result = self.validate()
        self.assertEqual(result["candidate_university_count"], 62)
        memberships = self.load("candidate-memberships.json")["memberships"]
        georgia_tech = [
            row for row in memberships
            if row["canonical_university_id"] == "institution:georgia-institute-of-technology"
        ]
        self.assertEqual(
            {row["membership_reason"] for row in georgia_tech},
            {"national_top_50_candidate", "program_top_20_candidate"},
        )
        self.assertNotIn("both_candidate", {row["membership_reason"] for row in memberships})

    def test_partial_unresolved_and_outside_scope_inputs_cannot_enter_v2(self) -> None:
        candidate_records = {
            record_id
            for candidate in self.load("candidate-universities.json")["universities"]
            for record_id in candidate["supporting_ranking_record_ids"]
        }
        self.assertNotIn("pilot-business-tepper-partial", candidate_records)
        self.assertNotIn("pilot-business-cornell-partial", candidate_records)
        self.assertNotIn("gap-economics-baylor-99", candidate_records)
        self.assertEqual(len(candidate_records), 130)

    def test_gap_disclosure_covers_economics_and_incomplete_program_corpus(self) -> None:
        disclosure = self.load("candidate-gap-disclosure.json")
        self.assertTrue(disclosure["national_top50_accepted"])
        self.assertEqual(disclosure["program_complete_stream_count"], 0)
        self.assertEqual(disclosure["program_incomplete_stream_count"], 27)
        self.assertTrue(disclosure["economics_manual_seed_needed"])

    def test_summary_counts_rejected_partial_and_outside_scope_observations(self) -> None:
        summary = self.load("candidate-generation-summary.json")
        self.assertEqual(summary["excluded_partial_record_count"], 2)
        self.assertEqual(summary["excluded_unresolved_record_count"], 0)
        self.assertEqual(summary["excluded_outside_scope_observation_count"], 1)

    def test_mutated_both_membership_or_final_flag_is_rejected(self) -> None:
        artifacts = copy.deepcopy(self.artifacts())
        artifacts["candidate-memberships.json"]["memberships"][0]["membership_reason"] = "both_candidate"
        with self.assertRaises(UniverseCandidateV2ValidationError):
            self.validate(artifacts)
        artifacts = copy.deepcopy(self.artifacts())
        artifacts["candidate-universities.json"]["metadata"]["final_universe"] = True
        with self.assertRaises(UniverseCandidateV2ValidationError):
            self.validate(artifacts)

    def test_source_policy_separates_detail_enrichment_from_usnews_rankings(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("CollegeData", policy)
        self.assertIn("field-level provenance", policy)
        self.assertIn("Times Higher Education", policy)
        self.assertIn("QS", policy)
        self.assertIn("xuanxiao.org", policy)
        with self.assertRaises(UniverseCandidateV2ValidationError):
            self.validate(policy_text=policy.replace("xuanxiao.org", "non-usnews-site"))

    def test_secondary_and_non_usnews_sources_cannot_write_usnews_ranks(self) -> None:
        validate_source_policy_use("CollegeData", "detail", has_field_provenance=True)
        for source in ("CollegeData", "THE", "QS", "xuanxiao.org"):
            with self.assertRaises(UniverseCandidateV2ValidationError, msg=source):
                validate_source_policy_use(source, "usnews_ranking", has_field_provenance=True)
        with self.assertRaises(UniverseCandidateV2ValidationError):
            validate_source_policy_use("CollegeData", "detail", has_field_provenance=False)
