"""Deterministic contract gates for the Stage 5 Preview bundle."""

from __future__ import annotations

from typing import Any, Dict, List

from .config import CONTRACT_VERSION, SOURCE_CHECKPOINT


EXPECTED_CHECK_IDS = tuple("stage5_{:02d}".format(number) for number in range(1, 50))


def _source_ids(value: Any) -> set[str]:
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


def validate_preview_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    manifest = bundle["manifest"]
    summaries = bundle["universities"]
    details = bundle["university_details"]
    region = bundle["region_metrics"]
    readiness = bundle["feature_readiness"]
    generated_from = bundle["integration_diagnostics"]["generatedFrom"]
    checks: List[tuple[str, bool]] = [
        ("contract version", manifest.get("contractVersion") == CONTRACT_VERSION),
        ("source checkpoint", manifest.get("sourceCheckpoint") == SOURCE_CHECKPOINT),
        ("preview view", manifest.get("view") == "preview"),
        ("summary count", len(summaries) == 62),
        ("detail count", len(details) == 62),
        ("unique IDs", len({row["id"] for row in summaries}) == 62),
        ("valid coordinates", all(-90 <= row["latitude"] <= 90 and -180 <= row["longitude"] <= 180 for row in summaries)),
        ("no null island", all((row["latitude"], row["longitude"]) != (0, 0) for row in summaries)),
        ("summary detail IDs", {row["id"] for row in summaries} == set(details)),
        ("English names", all(details[row["id"]]["name"] == row["name"] for row in summaries)),
        ("Chinese names", all(details[row["id"]]["nameZh"] == row["nameZh"] and row["nameZh"] for row in summaries)),
        ("locations", all((details[row["id"]]["city"], details[row["id"]]["state"]) == (row["city"], row["state"]) for row in summaries)),
        ("detail coordinates", all((details[row["id"]]["latitude"], details[row["id"]]["longitude"]) == (row["latitude"], row["longitude"]) for row in summaries)),
        ("rankings", all(details[row["id"]]["rankingSummary"] == row["rankingSummary"] for row in summaries)),
        ("acceptance", all(details[row["id"]]["admissions"]["acceptanceRate"]["value"] == row["acceptanceRate"]["value"] for row in summaries)),
        ("cost", all(details[row["id"]]["costSummary"] == row["costSummary"] for row in summaries)),
        ("ratios", all(details[row["id"]]["studentFacultyRatio"] == row["studentFacultyRatio"] for row in summaries)),
        ("school types", all(details[row["id"]]["schoolType"] == row["schoolType"] for row in summaries)),
        ("warnings", all(details[row["id"]]["warningSummary"] == row["warningSummary"] for row in summaries)),
        ("verified boundary", manifest.get("verifiedRecordCount") == 904),
        ("pending policies", all(detail["admissions"]["testPolicy"]["value"] is None for detail in details.values())),
        ("deferred regions", region.get("records") == []),
        ("no quarantined people", all(not any(person.get("quarantined") for person in detail["people"]) for detail in details.values())),
        ("no handoff", not any("handoff" in path.lower() for path in generated_from)),
        ("no fixture", not any("frontend" in path.lower() or "fixture" in path.lower() for path in generated_from)),
        ("2019 enrollment", all(all(detail["enrollment"][scope]["referenceYear"] == 2019 for scope in ("undergraduate", "graduate", "total")) for detail in details.values())),
        ("Harvey Mudd partial", details["candidate-v2:harvey-mudd-college"]["enrollment"]["graduate"]["value"] is None),
        ("Olin partial", details["candidate-v2:olin-college-of-engineering"]["enrollment"]["graduate"]["value"] is None),
        ("12 null ranks", sum(row["rankingSummary"]["nationalRank"] is None for row in summaries) == 12),
        ("no rank zero", all(row["rankingSummary"]["nationalRank"] != 0 for row in summaries)),
        ("9 SAT missing", sum(detail["admissions"]["sat"]["status"] == "not_reported" for detail in details.values()) == 9),
        ("9 ACT missing", sum(detail["admissions"]["act"]["status"] == "not_reported" for detail in details.values()) == 9),
        ("test policy pending", all(detail["admissions"]["testPolicy"]["status"] == "pending_external_access" for detail in details.values())),
        ("English policy pending", all(detail["admissions"]["englishPolicy"]["status"] == "pending_external_access" for detail in details.values())),
        ("16 county scopes", sum(detail["geography"]["geographyScope"] == "county" for detail in details.values()) == 16),
        ("nearest town distinct", all(detail["geography"]["geographyScope"] != "county" or detail["geography"]["place"]["value"] not in {town["name"] for town in detail["nearbyTowns"]} for detail in details.values())),
        ("130 people gaps", sum(len(detail["programPeopleGaps"]) for detail in details.values()) == 130),
        ("sources resolve", _source_ids(summaries) | _source_ids(details) <= {row["sourceId"] for row in bundle["source_index"]["sources"]}),
        ("regions blocked", region.get("status") == "blocked" and bool(region.get("disabledReason"))),
        ("choropleth disabled", not region.get("choroplethEnabled") and not readiness["features"]["choropleth"]["previewEligibility"]),
        ("AI disabled", readiness["features"]["ai_context"]["status"] == "disabled" and not readiness["features"]["ai_context"]["previewEligibility"]),
        ("production false", not readiness.get("productionEligibility") and manifest.get("sourceLimited") and manifest.get("incomplete") and manifest.get("notFinal")),
        ("approved input paths", not any(any(token in "/{}".format(path.lower()) for token in ("/raw/", "/staging/", "/cache/", "cache-body", "cache_bodies")) for path in generated_from)),
        ("deterministic marker", bundle["integration_diagnostics"].get("networkAccess") == "disabled"),
        ("mapping matrix", bundle["contract_mapping_matrix"].get("contractVersion") == CONTRACT_VERSION),
        ("all majors", sum(len(detail["allMajors"]) for detail in details.values()) == 4693),
        (
            "no synthetic source placeholders",
            all(
                source["publisher"] != "Frozen PathOS source"
                and source["sourceType"] != "frozen_verified_artifact"
                for source in bundle["source_index"]["sources"]
            ),
        ),
        (
            "complete status dictionary",
            {
                "deferred",
                "not_applicable",
                "source_review_not_completed",
                "quarantined",
                "source_limited",
                "incomplete",
                "not_final",
            }
            <= set(bundle["status_dictionary"]["statuses"]),
        ),
        ("region metric metadata", len(region.get("metricMetadata", [])) == 5),
    ]
    rows = [
        {"checkId": check_id, "label": label, "status": "pass" if passed else "fail"}
        for check_id, (label, passed) in zip(EXPECTED_CHECK_IDS, checks)
    ]
    passed = sum(row["status"] == "pass" for row in rows)
    return {
        "recordType": "stage5_preview_validation_result",
        "status": "pass" if passed == len(rows) else "fail",
        "checkCount": len(rows),
        "passedCheckCount": passed,
        "failedCheckCount": len(rows) - passed,
        "checks": rows,
        "sourceLimited": True,
        "incomplete": True,
        "notFinal": True,
        "deterministicRegeneration": True,
        "networkDisabledGeneration": True,
    }
