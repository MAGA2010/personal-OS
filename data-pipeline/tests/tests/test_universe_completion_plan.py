"""Stage 2E universe completion plan contract."""

import copy
import json
import unittest
from pathlib import Path

from pathos_data.universe_completion import (
    UniverseCompletionPlanValidationError,
    validate_universe_completion_plan,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "data"
    / "university-universe"
    / "2026-best-colleges"
    / "completion-plan.json"
)
INVENTORY_PATH = (
    ROOT
    / "data"
    / "ranking-discovery"
    / "2026-best-colleges"
    / "category-inventory.json"
)
CORPUS_PATH = (
    ROOT
    / "data"
    / "ranking-seeds"
    / "2026-best-colleges"
    / "corpus"
    / "corpus-validation-result.json"
)


class UniverseCompletionPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        self.inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        self.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def validate(self, plan: dict) -> None:
        validate_universe_completion_plan(plan, self.inventory, self.corpus)

    def test_committed_plan_matches_current_corpus_baseline(self) -> None:
        self.validate(self.plan)

    def test_national_phase_requires_top_50_and_tie_handling(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["phases"][0]["target_numeric_rank"] = 49
        with self.assertRaises(UniverseCompletionPlanValidationError):
            self.validate(plan)

    def test_priority_streams_must_be_unique_in_scope_categories(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["phases"][1]["priority_streams"].append(
            plan["phases"][1]["priority_streams"][0]
        )
        with self.assertRaises(UniverseCompletionPlanValidationError):
            self.validate(plan)

    def test_plan_must_preserve_non_final_output_boundary(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["output_boundaries"]["final_universe_generated"] = True
        with self.assertRaises(UniverseCompletionPlanValidationError):
            self.validate(plan)
