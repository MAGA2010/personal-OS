"""第一阶段的 fixture 隔离与正式数据流回归测试。"""

import json
import tempfile
import unittest
from pathlib import Path

from pathos_data.exporter import export_preview, write_formal_frontend_export
from pathos_data.pipeline import normalize_staged, stage_raw
from pathos_data.schema_validation import (
    SchemaValidationError,
    load_schema,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "test-university-raw.json"


class EndToEndPipelineTests(unittest.TestCase):
    def test_fixture_completes_only_the_test_preview_flow(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        validate_instance(raw, load_schema("raw-university.json"))

        staged = stage_raw(raw)
        validate_instance(staged, load_schema("staging-university.json"))

        canonical = normalize_staged(staged)
        validate_instance(canonical, load_schema("canonical-university.json"))

        exported = export_preview([canonical])
        poi = exported["universities"][0]
        self.assertTrue(raw["is_test_fixture"])
        self.assertEqual(poi["id"], "test-harvard")
        self.assertEqual(poi["name"], "Harvard University")
        for field in (
            "chineseName", "country", "city", "latitude", "longitude",
            "rankingBand", "rankingTier", "annualCostRmb", "safetyScore",
            "recognitionScore", "chineseCommunity", "directFlight",
            "postStudyVisa", "programs", "parentHighlights",
            "studentHighlights", "verifiedAt", "sourceCount", "campusImages",
            "nearby",
        ):
            self.assertIn(field, poi)

    def test_fixture_cannot_write_a_formal_frontend_export(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        canonical = normalize_staged(stage_raw(raw))
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "universities.json"
            with self.assertRaises(SchemaValidationError):
                write_formal_frontend_export([canonical], output)

    def test_both_selection_reason_expands_to_two_canonical_memberships(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["university"]["selection_reason"] = "both"

        canonical = normalize_staged(stage_raw(raw))
        reasons = {membership["selection_reason"] for membership in canonical["selection_memberships"]}

        self.assertEqual(reasons, {"national_top_50", "program_top_20"})
        self.assertNotIn("both", reasons)
