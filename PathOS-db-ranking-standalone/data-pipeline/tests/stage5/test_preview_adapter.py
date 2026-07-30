from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pathos_data.stage5_preview_adapter.generator import (
    ARTIFACT_FILES,
    build_validated_preview_bundle,
    write_preview_bundle,
)
from pathos_data.stage5_preview_adapter.validator import (
    EXPECTED_CHECK_IDS,
    validate_preview_bundle,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT = "ec8c66e200b566dba4de35987aa5213960749a57"


def _field(detail: dict, *path: str) -> dict:
    value: object = detail
    for key in path:
        value = value[key]  # type: ignore[index]
    assert isinstance(value, dict)
    return value


def _source_ids(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "sourceIds" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            else:
                found.update(_source_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_source_ids(child))
    return found


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class Stage5PreviewAdapterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = build_validated_preview_bundle(REPO_ROOT)
        cls.manifest = cls.bundle["manifest"]
        cls.summaries = cls.bundle["universities"]
        cls.details = cls.bundle["university_details"]
        cls.details_by_id = cls.details

    def test_01_deterministic_preview_generation(self) -> None:
        self.assertEqual(self.bundle, build_validated_preview_bundle(REPO_ROOT))

    def test_02_manifest_contract_version(self) -> None:
        self.assertEqual(self.manifest["contractVersion"], "pathos-preview-v1")
        self.assertEqual(self.manifest["sourceCheckpoint"], CHECKPOINT)

    def test_03_manifest_view_is_preview(self) -> None:
        self.assertEqual(self.manifest["view"], "preview")
        self.assertNotIn("production", self.manifest)

    def test_04_has_62_summaries(self) -> None:
        self.assertEqual(len(self.summaries), 62)
        self.assertEqual(self.manifest["summaryCount"], 62)

    def test_05_has_62_details(self) -> None:
        self.assertEqual(len(self.details), 62)
        self.assertEqual(self.manifest["detailCount"], 62)

    def test_06_university_ids_are_unique(self) -> None:
        ids = [row["id"] for row in self.summaries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith("candidate-v2:") for value in ids))

    def test_07_coordinates_are_valid(self) -> None:
        for row in self.summaries:
            self.assertGreaterEqual(row["latitude"], -90)
            self.assertLessEqual(row["latitude"], 90)
            self.assertGreaterEqual(row["longitude"], -180)
            self.assertLessEqual(row["longitude"], 180)

    def test_08_no_null_island_coordinates(self) -> None:
        self.assertFalse(
            any(row["latitude"] == 0 and row["longitude"] == 0 for row in self.summaries)
        )

    def test_09_summary_detail_identity_consistency(self) -> None:
        self.assertEqual({row["id"] for row in self.summaries}, set(self.details))
        for row in self.summaries:
            self.assertEqual(self.details[row["id"]]["id"], row["id"])

    def test_10_english_name_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(self.details[row["id"]]["name"], row["name"])

    def test_11_chinese_name_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(self.details[row["id"]]["nameZh"], row["nameZh"])
            self.assertTrue(row["nameZh"])

    def test_12_city_state_consistency(self) -> None:
        for row in self.summaries:
            detail = self.details[row["id"]]
            self.assertEqual((detail["city"], detail["state"]), (row["city"], row["state"]))

    def test_13_coordinate_consistency(self) -> None:
        for row in self.summaries:
            detail = self.details[row["id"]]
            self.assertEqual(
                (detail["latitude"], detail["longitude"]),
                (row["latitude"], row["longitude"]),
            )

    def test_14_ranking_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(
                self.details[row["id"]]["rankingSummary"], row["rankingSummary"]
            )

    def test_15_acceptance_consistency(self) -> None:
        for row in self.summaries:
            detail_value = _field(
                self.details[row["id"]], "admissions", "acceptanceRate"
            )["value"]
            self.assertEqual(detail_value, row["acceptanceRate"]["value"])

    def test_16_tuition_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(self.details[row["id"]]["costSummary"], row["costSummary"])

    def test_17_ratio_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(
                self.details[row["id"]]["studentFacultyRatio"],
                row["studentFacultyRatio"],
            )

    def test_18_school_type_consistency(self) -> None:
        for row in self.summaries:
            self.assertEqual(self.details[row["id"]]["schoolType"], row["schoolType"])

    def test_19_warning_consistency(self) -> None:
        for row in self.summaries:
            detail = self.details[row["id"]]
            self.assertEqual(row["warningSummary"], detail["warningSummary"])
            self.assertEqual(
                row["qualitySummary"]["warningCodes"], detail["qualitySummary"]["warningCodes"]
            )

    def test_20_verified_boundary_is_904(self) -> None:
        self.assertEqual(self.manifest["verifiedRecordCount"], 904)

    def test_21_pending_never_enters_fact_value(self) -> None:
        for detail in self.details.values():
            self.assertIsNone(_field(detail, "admissions", "testPolicy")["value"])
            self.assertEqual(
                _field(detail, "admissions", "testPolicy")["status"],
                "pending_external_access",
            )

    def test_22_deferred_never_enters_region_fact_value(self) -> None:
        region = self.bundle["region_metrics"]
        self.assertEqual(region["records"], [])
        self.assertIn(region["status"], {"blocked", "deferred"})

    def test_23_quarantined_people_are_excluded(self) -> None:
        for detail in self.details.values():
            self.assertFalse(
                any(
                    person.get("quarantined")
                    or person.get("displayTier") == "quarantined"
                    for person in detail["people"]
                )
            )

    def test_24_no_handoff_dependency(self) -> None:
        generated_from = self.bundle["integration_diagnostics"]["generatedFrom"]
        self.assertFalse(any("handoff" in path.lower() for path in generated_from))

    def test_25_no_frontend_fixture_dependency(self) -> None:
        generated_from = self.bundle["integration_diagnostics"]["generatedFrom"]
        self.assertFalse(any("frontend" in path.lower() or "fixture" in path.lower() for path in generated_from))

    def test_26_enrollment_has_2019_warning(self) -> None:
        for detail in self.details.values():
            for scope in ("undergraduate", "graduate", "total"):
                field = _field(detail, "enrollment", scope)
                self.assertEqual(field["referenceYear"], 2019)
                self.assertIn("stale_reference_year", field["warnings"])

    def test_27_harvey_mudd_partial_enrollment(self) -> None:
        detail = self.details["candidate-v2:harvey-mudd-college"]
        self.assertIsNone(_field(detail, "enrollment", "graduate")["value"])
        self.assertIsNone(_field(detail, "enrollment", "total")["value"])

    def test_28_olin_partial_enrollment(self) -> None:
        detail = self.details["candidate-v2:olin-college-of-engineering"]
        self.assertIsNone(_field(detail, "enrollment", "graduate")["value"])
        self.assertIsNone(_field(detail, "enrollment", "total")["value"])

    def test_29_twelve_null_national_ranks_have_explicit_semantics(self) -> None:
        rows = [row for row in self.summaries if row["rankingSummary"]["nationalRank"] is None]
        self.assertEqual(len(rows), 12)
        self.assertTrue(
            all(
                row["rankingSummary"]["status"] == "not_in_current_national_scope"
                and row["rankingSummary"]["filterBehavior"] == "exclude_from_numeric_range"
                for row in rows
            )
        )

    def test_30_rank_zero_count_is_zero(self) -> None:
        self.assertFalse(
            any(row["rankingSummary"]["nationalRank"] == 0 for row in self.summaries)
        )

    def test_31_nine_sat_not_reported(self) -> None:
        self.assertEqual(
            sum(
                _field(detail, "admissions", "sat")["status"] == "not_reported"
                for detail in self.details.values()
            ),
            9,
        )

    def test_32_nine_act_not_reported(self) -> None:
        self.assertEqual(
            sum(
                _field(detail, "admissions", "act")["status"] == "not_reported"
                for detail in self.details.values()
            ),
            9,
        )

    def test_33_test_policy_all_pending(self) -> None:
        self.assertTrue(
            all(
                _field(detail, "admissions", "testPolicy")["status"]
                == "pending_external_access"
                for detail in self.details.values()
            )
        )

    def test_34_english_policy_all_pending(self) -> None:
        self.assertTrue(
            all(
                _field(detail, "admissions", "englishPolicy")["status"]
                == "pending_external_access"
                and _field(detail, "admissions", "englishPolicy")["value"] is None
                for detail in self.details.values()
            )
        )

    def test_35_sixteen_county_only_scopes(self) -> None:
        county_only = [
            detail
            for detail in self.details.values()
            if detail["geography"]["geographyScope"] == "county"
        ]
        self.assertEqual(len(county_only), 16)
        self.assertTrue(all(item["geography"]["place"]["value"] is None for item in county_only))

    def test_36_nearest_town_is_not_used_as_place(self) -> None:
        for detail in self.details.values():
            geography = detail["geography"]
            if geography["geographyScope"] == "county":
                nearest_names = {town["name"] for town in detail["nearbyTowns"]}
                self.assertNotIn(geography["place"]["value"], nearest_names)

    def test_37_program_people_gap_semantics(self) -> None:
        gaps = [
            gap
            for detail in self.details.values()
            for gap in detail["programPeopleGaps"]
        ]
        self.assertEqual(len(gaps), 130)
        self.assertTrue(
            all(
                gap["status"] == "source_review_not_completed"
                and gap["displayLabel"] == "数据补充中"
                and gap["displayAsNone"] is False
                for gap in gaps
            )
        )

    def test_38_all_source_ids_resolve(self) -> None:
        available = {
            row["sourceId"] for row in self.bundle["source_index"]["sources"]
        }
        referenced = _source_ids(self.summaries) | _source_ids(list(self.details.values()))
        self.assertTrue(referenced)
        self.assertEqual(referenced - available, set())

    def test_39_region_metrics_are_blocked(self) -> None:
        region = self.bundle["region_metrics"]
        self.assertEqual(region["status"], "blocked")
        self.assertEqual(region["records"], [])
        self.assertTrue(region["disabledReason"])

    def test_40_choropleth_is_disabled(self) -> None:
        self.assertFalse(self.bundle["region_metrics"]["choroplethEnabled"])
        self.assertFalse(
            self.bundle["feature_readiness"]["features"]["choropleth"]["previewEligibility"]
        )

    def test_41_ai_context_is_disabled(self) -> None:
        ai = self.bundle["feature_readiness"]["features"]["ai_context"]
        self.assertFalse(ai["previewEligibility"])
        self.assertEqual(ai["status"], "disabled")

    def test_42_production_eligibility_is_false(self) -> None:
        self.assertTrue(self.manifest["sourceLimited"])
        self.assertTrue(self.manifest["incomplete"])
        self.assertTrue(self.manifest["notFinal"])
        self.assertFalse(self.bundle["feature_readiness"]["productionEligibility"])

    def test_43_generated_from_excludes_raw_staging_and_cache_body(self) -> None:
        forbidden = ("/raw/", "/staging/", "/cache/", "cache-body", "cache_bodies")
        generated_from = self.bundle["integration_diagnostics"]["generatedFrom"]
        self.assertFalse(any(any(token in f"/{path.lower()}" for token in forbidden) for path in generated_from))

    def test_44_written_artifact_hashes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path = Path(first)
            second_path = Path(second)
            write_preview_bundle(self.bundle, first_path)
            write_preview_bundle(build_validated_preview_bundle(REPO_ROOT), second_path)
            self.assertEqual(_tree_hashes(first_path), _tree_hashes(second_path))
            self.assertEqual(
                set(_tree_hashes(first_path)),
                {
                    *ARTIFACT_FILES.values(),
                    *{
                        f"university-details/{university_id}.json"
                        for university_id in self.details
                    },
                },
            )

    def test_45_generation_succeeds_with_network_disabled(self) -> None:
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            regenerated = build_validated_preview_bundle(REPO_ROOT)
        validation = validate_preview_bundle(regenerated)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["checkCount"], 49)
        self.assertEqual(validation["passedCheckCount"], 49)
        self.assertEqual(len(EXPECTED_CHECK_IDS), 49)

    def test_46_detail_includes_reviewed_all_majors(self) -> None:
        self.assertTrue(
            all("allMajors" in detail for detail in self.details.values())
        )
        self.assertEqual(
            sum(len(detail["allMajors"]) for detail in self.details.values()),
            4693,
        )

    def test_47_source_index_has_no_synthetic_verified_placeholders(self) -> None:
        sources = self.bundle["source_index"]["sources"]
        self.assertFalse(
            any(source["publisher"] == "Frozen PathOS source" for source in sources)
        )
        self.assertFalse(
            any(source["sourceType"] == "frozen_verified_artifact" for source in sources)
        )

    def test_48_status_dictionary_covers_public_contract_states(self) -> None:
        statuses = set(self.bundle["status_dictionary"]["statuses"])
        self.assertTrue(
            {
                "verified",
                "not_reported",
                "pending_external_access",
                "deferred",
                "not_applicable",
                "source_review_not_completed",
                "quarantined",
                "source_limited",
                "incomplete",
                "not_final",
            }.issubset(statuses)
        )

    def test_49_region_metadata_preserves_blocked_reason(self) -> None:
        region = self.bundle["region_metrics"]
        self.assertEqual(region["status"], "blocked")
        self.assertFalse(region["choroplethEnabled"])
        self.assertTrue(region["disabledReason"])
        self.assertEqual(len(region["metricMetadata"]), 5)


if __name__ == "__main__":
    unittest.main()
