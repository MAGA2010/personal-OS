"""防止 Global 或 Graduate 排名进入本科 canonical universe。"""

import json
import unittest
from pathlib import Path


CONFIG = Path(__file__).resolve().parents[1] / "config" / "ranking-scope.json"


class RankingScopeTests(unittest.TestCase):
    def test_scope_includes_only_national_and_undergraduate_families(self) -> None:
        scope = json.loads(CONFIG.read_text(encoding="utf-8"))
        included = {entry["ranking_family"] for entry in scope["categories"] if entry["included_in_pathos_scope"]}
        self.assertEqual(included, {"national_universities", "undergraduate_program"})
        self.assertEqual(scope["selection_rules"]["national_universities_max_numeric_rank"], 50)
        self.assertEqual(scope["selection_rules"]["undergraduate_program_max_numeric_rank"], 20)
