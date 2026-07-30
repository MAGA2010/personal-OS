"""Stage 2F user-provided National Universities manual-seed safeguards."""

import copy
import json
import unittest
from pathlib import Path

from pathos_data.national_completion import (
    NationalCompletionValidationError,
    validate_national_completion_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
NATIONAL = ROOT / "data" / "ranking-seeds" / "2026-best-colleges" / "completion-national"


def load(name: str) -> dict:
    return json.loads((NATIONAL / name).read_text(encoding="utf-8"))


def validate() -> dict:
    return validate_national_completion_artifacts(
        [load("national-universities-top-50.json")],
        load("identity-mappings.json"),
        load("candidate-observations.json"),
        load("coverage-matrix.json"),
        load("source-manifest.json"),
        load("excluded-entries.json"),
    )


class NationalCompletionTests(unittest.TestCase):
    def test_committed_manual_seed_bundle_validates_exactly_fifty_entries(self) -> None:
        result = validate()
        self.assertEqual(result["accepted_us_domestic_entries"], 50)
        self.assertTrue(result["national_completion_accepted"])

    def test_manual_pdf_source_is_not_treated_as_official_usnews_source(self) -> None:
        manifest = load("source-manifest.json")
        source = next(item for item in manifest["sources"] if item["source_id"] == "source_think_academy_top100_2026_pdf")
        self.assertEqual(source["source_access_type"], "user_provided_document")
        self.assertEqual(source["source_role"], "manual_seed_reference")
        self.assertFalse(source["official_usnews_source"])
        with self.assertRaises(NationalCompletionValidationError):
            mutated = copy.deepcopy(manifest)
            next(item for item in mutated["sources"] if item["source_id"] == "source_think_academy_top100_2026_pdf")["official_usnews_source"] = True
            validate_national_completion_artifacts([load("national-universities-top-50.json")], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), mutated, load("excluded-entries.json"))
        with self.assertRaises(NationalCompletionValidationError):
            mutated = copy.deepcopy(manifest)
            next(item for item in mutated["sources"] if item["source_id"] == "source_think_academy_top100_2026_pdf")["permission_note"] = "User supplied source."
            validate_national_completion_artifacts([load("national-universities-top-50.json")], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), mutated, load("excluded-entries.json"))
        with self.assertRaises(NationalCompletionValidationError):
            mutated = copy.deepcopy(manifest)
            next(item for item in mutated["sources"] if item["source_id"] == "source_think_academy_top100_2026_pdf")["limitation_note"] = "Compiled table."
            validate_national_completion_artifacts([load("national-universities-top-50.json")], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), mutated, load("excluded-entries.json"))

    def test_selection_is_first_fifty_entries_not_numeric_rank_cutoff(self) -> None:
        batch = load("national-universities-top-50.json")
        self.assertEqual(len(batch["records"]), 50)
        self.assertEqual(batch["records"][-1]["school_display_name"], "University of Rochester")
        self.assertEqual(batch["records"][-1]["numeric_rank"], 46)
        self.assertNotIn(51, {record["numeric_rank"] for record in batch["records"]})

    def test_rank_46_boundary_tie_group_is_complete_and_rank_51_is_excluded(self) -> None:
        batch = load("national-universities-top-50.json")
        rank_46 = {record["school_display_name"] for record in batch["records"] if record["numeric_rank"] == 46}
        self.assertEqual(rank_46, {"Lehigh University", "Northeastern University", "Purdue University—Main Campus", "University of Georgia", "University of Rochester"})
        excluded = load("excluded-entries.json")
        self.assertEqual({item["numeric_rank"] for item in excluded["entries"]}, {51})
        with self.assertRaises(NationalCompletionValidationError):
            mutated = copy.deepcopy(batch)
            mutated["records"].pop()
            validate_national_completion_artifacts([mutated], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), excluded)

    def test_ties_are_inferred_not_claimed_as_direct_pdf_quotes(self) -> None:
        batch = load("national-universities-top-50.json")
        tied = next(record for record in batch["records"] if record["numeric_rank"] == 46)
        self.assertTrue(tied["tied"])
        self.assertNotIn("tied", tied["evidence"]["directly_supported_fields"])
        self.assertIn("Tie inferred", tied["inference_notes"])
        with self.assertRaises(NationalCompletionValidationError):
            mutated = copy.deepcopy(batch)
            mutated["records"][-1]["evidence"]["directly_supported_fields"].append("tied")
            validate_national_completion_artifacts([mutated], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("excluded-entries.json"))

    def test_missing_manual_seed_evidence_anchor_fails(self) -> None:
        batch = load("national-universities-top-50.json")
        mutated = copy.deepcopy(batch)
        mutated["records"][3]["evidence_anchors"] = []
        with self.assertRaises(NationalCompletionValidationError):
            validate_national_completion_artifacts([mutated], load("identity-mappings.json"), load("candidate-observations.json"), load("coverage-matrix.json"), load("source-manifest.json"), load("excluded-entries.json"))

    def test_existing_top_three_canonical_identity_ids_are_reused(self) -> None:
        mappings = {item["record_id"]: item["canonical_identity_id"] for item in load("identity-mappings.json")["mappings"]}
        self.assertEqual(mappings["completion-national-princeton-university"], "institution:princeton-university")
        self.assertEqual(mappings["completion-national-massachusetts-institute-of-technology"], "institution:massachusetts-institute-of-technology")
        self.assertEqual(mappings["completion-national-harvard-university"], "institution:harvard-university")

    def test_no_final_universe_or_frontend_export_is_created(self) -> None:
        result = validate()
        self.assertFalse(result["canonical_universe_created"])
        self.assertFalse(result["selection_memberships_created"])
        self.assertFalse(result["frontend_export_created"])
