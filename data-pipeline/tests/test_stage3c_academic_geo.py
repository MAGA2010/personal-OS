"""Regression tests for the immutable Stage 3C academic and geo overlay."""

import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.stage3c_academic_geo import (
    Stage3CAcademicGeoValidationError,
    _validate_fee,
    build_stage3c_academic_geo,
    validate_stage3c_academic_geo,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Stage3CAcademicGeoTests(unittest.TestCase):
    def inputs(self) -> dict:
        return {
            "candidate_path": ROOT / "data/university-universe-candidates/v2-source-limited/candidate-universities.json",
            "stage3_dir": ROOT / "artifacts/stage3-program-mvp-detail-pack",
            "stage3b_dir": ROOT / "artifacts/stage3b-demo-critical-gap-fill",
            "source_manifest_path": ROOT / "data/stage3c/source-manifest.json",
            "major_observations_path": ROOT / "data/stage3c/official-major-observations.json",
            "tuition_observations_path": ROOT / "data/stage3c/official-tuition-fee-observations.json",
            "region_mapping_path": ROOT / "data/stage3c/region-classification.json",
            "town_manifest_path": ROOT / "data/stage3c/town-source-manifest.json",
            "town_cache": ROOT / "cache/stage3c-geography",
        }

    def test_scope_and_upstream_artifacts_are_immutable(self):
        inputs = self.inputs()
        upstream = [
            *sorted(inputs["stage3_dir"].glob("*.json")),
            *sorted(inputs["stage3b_dir"].glob("*.json")),
        ]
        before = {path: _sha256(path) for path in upstream}

        artifacts = build_stage3c_academic_geo(**inputs)

        universities = artifacts["stage3c-universities.json"]["universities"]
        self.assertEqual(len(universities), 62)
        self.assertEqual({row["candidate_id"] for row in universities}, {
            row["candidate_id"] for row in artifacts["stage3c-official-major-sources.json"]["universities"]
        })
        self.assertEqual(before, {path: _sha256(path) for path in upstream})
        self.assertTrue(all(row["region"] in {"Northeast", "Midwest", "South", "West"} for row in universities))

    def test_unc_official_undergraduate_observations_resolve_demo_gap_without_ranking_contamination(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        rows = artifacts["stage3c-demo-programs-overlay.json"]["universities"]
        unc = next(row for row in rows if row["candidate_id"] == "candidate-v2:university-of-north-carolina-chapel-hill")
        self.assertEqual(len(unc["top_5_programs_for_demo"]), 5)
        self.assertIsNone(unc["top_5_gap_reason"])
        self.assertEqual(len(unc["added_official_undergraduate_programs"]), 2)
        for program in unc["added_official_undergraduate_programs"]:
            self.assertEqual(program["source_type"], "official_institutional")
            self.assertEqual(program["undergraduate_status"], "undergraduate")
            self.assertIsNone(program["usnews_category"])
            self.assertIsNone(program["usnews_rank"])

    def test_nearest_town_gap_is_disclosed_when_official_place_cache_is_unavailable(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        rows = artifacts["stage3c-universities.json"]["universities"]
        self.assertEqual(len(rows), 62)
        self.assertTrue(all(row["longitude"] is not None for row in rows))
        self.assertTrue(all(row["nearest_towns"] == [] for row in rows))
        self.assertTrue(all(row["nearest_towns_null_reason"] == "source_unavailable_in_execution_environment" for row in rows))

    def test_readiness_separates_completed_programs_from_unavailable_nearest_towns(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        summary = artifacts["stage3c-summary.json"]
        disclosure = artifacts["stage3c-gap-disclosure.json"]

        self.assertEqual(summary.get("demo_program_readiness_after"), 1.0)
        self.assertEqual(summary.get("geo_nearest_towns_readiness"), 0.0)
        self.assertEqual(summary.get("nearest_town_coverage_count"), 0)
        self.assertEqual(summary.get("nearest_town_total_count"), 62)
        self.assertEqual(summary.get("nearest_town_completion_status"), "incomplete_source_unavailable")
        self.assertEqual(summary.get("demo_readiness_after_scope"), "legacy_program_only")
        self.assertEqual(disclosure.get("nearest_towns_readiness", {}).get("null_reason"), "source_unavailable_in_execution_environment")

    def test_report_labels_stage3c_as_academic_complete_and_geo_partial(self):
        report = (ROOT / "reports/stage3c-academic-geo-enrichment-report.md").read_text(encoding="utf-8")

        self.assertIn("Academic/program readiness: complete.", report)
        self.assertIn("Region readiness: complete.", report)
        self.assertIn("Nearest towns readiness: 0/62.", report)
        self.assertIn("Academic + partial Geo overlay", report)
        self.assertIn("`demo_program_readiness_after=1.0` does not mean nearest towns are complete.", report)

    def test_validator_rejects_summary_that_claims_nearest_towns_are_complete(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        artifacts["stage3c-summary.json"]["geo_nearest_towns_readiness"] = 1.0

        with self.assertRaises(Stage3CAcademicGeoValidationError):
            validate_stage3c_academic_geo(
                artifacts,
                **self.inputs(),
                report_path=ROOT / "reports/stage3c-academic-geo-enrichment-report.md",
            )

    def test_stage3b_resolved_ipeds_major_fallbacks_are_not_lost(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        summary = artifacts["stage3c-summary.json"]
        self.assertEqual(summary["universities_missing_official_major_source"], 0)
        self.assertEqual(summary["universities_using_only_ipeds_award_areas"], 61)

    def test_tuition_guard_rejects_non_undergraduate_or_coa_component(self):
        with self.assertRaises(Stage3CAcademicGeoValidationError):
            _validate_fee({
                "fee_name": "Graduate cost of attendance", "fee_type": "program_extra_fee", "amount": 100,
                "currency": "USD", "academic_year": "2025-26", "residency_scope": "all_undergraduate",
                "undergraduate_only": True, "required_for_program": True, "source_id": "source_x",
                "evidence_anchor": {"source_id": "source_x", "quote": "Graduate cost of attendance"},
            }, {"source_x": {}})

    def test_full_validator_is_deterministic_and_source_policy_guard_is_called(self):
        artifacts = build_stage3c_academic_geo(**self.inputs())
        result = validate_stage3c_academic_geo(
            artifacts,
            **self.inputs(),
            report_path=ROOT / "reports/stage3c-academic-geo-enrichment-report.md",
        )
        self.assertEqual(result["result"], "passed")
        with patch("pathos_data.stage3c_academic_geo.validate_source_policy_use", side_effect=RuntimeError("guard called")):
            with self.assertRaises(RuntimeError):
                build_stage3c_academic_geo(**self.inputs())


if __name__ == "__main__":
    unittest.main()
