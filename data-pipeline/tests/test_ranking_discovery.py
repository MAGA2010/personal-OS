"""Stage 2A ranking discovery contracts without real ranking records."""

import copy
import json
import unittest
from pathlib import Path

from pathos_data.ranking_discovery import (
    RankingDiscoveryValidationError,
    stage_manual_seed_batch,
    validate_category_inventory,
    validate_manual_seed_batch,
    validate_ranking_family_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ranking-discovery"
DISCOVERY = ROOT / "data" / "ranking-discovery" / "2026-best-colleges"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RankingDiscoveryTests(unittest.TestCase):
    def test_category_inventory_validates_against_its_versioned_contract(self) -> None:
        validate_category_inventory(load_fixture("category-inventory.json"))

    def test_duplicate_category_id_is_rejected(self) -> None:
        inventory = load_fixture("category-inventory.json")
        inventory["categories"].append(copy.deepcopy(inventory["categories"][0]))
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_category_inventory(inventory)

    def test_global_ranking_family_cannot_be_included(self) -> None:
        families = load_fixture("ranking-family-inventory.json")
        global_family = next(item for item in families["families"] if item["ranking_family"] == "global_universities")
        global_family["inclusion_status"] = "included"
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_ranking_family_inventory(families)

    def test_graduate_ranking_family_cannot_be_included(self) -> None:
        families = load_fixture("ranking-family-inventory.json")
        graduate_family = next(item for item in families["families"] if item["ranking_family"] == "graduate_program")
        graduate_family["inclusion_status"] = "included"
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_ranking_family_inventory(families)

    def test_manual_seed_schema_validates_and_can_enter_staging(self) -> None:
        batch = load_fixture("manual-seed-batch.json")
        validate_manual_seed_batch(batch)
        staged = stage_manual_seed_batch(batch)
        self.assertEqual(staged["record_type"], "manual_ranking_seed_staging")

    def test_duplicate_manual_seed_is_rejected(self) -> None:
        batch = load_fixture("manual-seed-batch.json")
        batch["records"].append(copy.deepcopy(batch["records"][0]))
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_manual_seed_batch(batch)

    def test_out_of_scope_rank_is_rejected(self) -> None:
        batch = load_fixture("manual-seed-batch.json")
        batch["records"][0]["numeric_rank"] = 51
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_manual_seed_batch(batch)

    def test_manual_seed_requires_a_source(self) -> None:
        batch = load_fixture("manual-seed-batch.json")
        del batch["records"][0]["source"]
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_manual_seed_batch(batch)

    def test_category_edition_must_match_its_inventory(self) -> None:
        inventory = load_fixture("category-inventory.json")
        inventory["categories"][0]["edition"] = "2025 Best Colleges"
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_category_inventory(inventory)

    def test_category_inventory_requires_explicit_versioned_lineage(self) -> None:
        inventory = load_fixture("category-inventory.json")
        inventory["categories"][0]["lineage"]["change_type"] = "renamed"
        with self.assertRaises(RankingDiscoveryValidationError):
            validate_category_inventory(inventory)

    def test_committed_stage_2a_inventories_validate(self) -> None:
        validate_ranking_family_inventory(
            json.loads((DISCOVERY / "ranking-family-inventory.json").read_text(encoding="utf-8"))
        )
        validate_category_inventory(
            json.loads((DISCOVERY / "category-inventory.json").read_text(encoding="utf-8"))
        )
