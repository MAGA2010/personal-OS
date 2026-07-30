"""Pure transformations from frozen Stage 3/4 records to the Preview contract."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Set

from .config import (
    CONTRACT_VERSION,
    DATASET_VERSION,
    DISABLED_FEATURES,
    ENABLED_FEATURES,
    SOURCE_CHECKPOINT,
    SOURCE_CHECKPOINT_TIME,
)


def _camel_field(raw: Mapping[str, Any], *, warnings: Iterable[str] = ()) -> Dict[str, Any]:
    status = raw.get("status") or raw.get("verification_status") or raw.get(
        "availability_status"
    )
    return {
        "value": raw.get("value"),
        "status": status or ("verified" if raw.get("value") is not None else "unavailable"),
        "referenceYear": raw.get("reference_year"),
        "scope": raw.get("scope"),
        "unit": raw.get("unit"),
        "sourceIds": list(raw.get("source_ids") or []),
        "warnings": sorted(set(list(raw.get("warnings") or []) + list(warnings))),
        "nullReason": raw.get("null_reason") or raw.get("missing_reason"),
    }


def _pending_field(raw: Mapping[str, Any], unit: str = "policy") -> Dict[str, Any]:
    return {
        "value": None,
        "status": "pending_external_access",
        "referenceYear": raw.get("reference_year") or raw.get("reference_cycle"),
        "scope": raw.get("applicant_scope"),
        "unit": unit,
        "sourceIds": [],
        "warnings": ["pending_data_not_a_verified_fact"],
        "nullReason": raw.get("gap_reason"),
    }


def _ranking_summary(raw: Mapping[str, Any]) -> Dict[str, Any]:
    rank = raw.get("national_rank")
    status = raw.get("ranking_status")
    return {
        "nationalRank": rank,
        "rankingTier": "national_top_50" if rank is not None else "outside_numeric_scope",
        "rankingLabel": raw.get("display_label"),
        "status": status,
        "filterBehavior": raw.get("filter_behavior"),
        "sourceIds": list(raw.get("source_ids") or []),
    }


def _cost_summary(marker: Mapping[str, Any]) -> Dict[str, Any]:
    raw = marker["tuition_summary"]
    minimum = raw.get("minimum")
    maximum = raw.get("maximum")
    if minimum == maximum:
        label = "${:,.0f}".format(minimum) if minimum is not None else "Not available"
    else:
        label = "${:,.0f}–${:,.0f}".format(minimum, maximum)
    warnings = [raw["comparison_warning"]] if raw.get("comparison_warning") else []
    return {
        "minimumUsd": minimum,
        "maximumUsd": maximum,
        "displayLabel": label,
        "comparisonSafe": len(raw.get("scopes") or []) <= 1,
        "currency": raw.get("currency"),
        "academicYear": raw.get("academic_year"),
        "scopes": list(raw.get("scopes") or []),
        "sourceIds": list(raw.get("source_ids") or []),
        "warnings": warnings,
    }


def _warning_summary(codes: Iterable[str]) -> Dict[str, Any]:
    values = sorted(set(code for code in codes if code))
    return {"count": len(values), "codes": values, "hasWarnings": bool(values)}


def _people_by_school(inputs: Mapping[str, Any]) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
    reverify = {
        row["source_id"]: row["live_status"]
        for row in inputs["documents"]["people_reverification"]["records"]
    }
    people: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    gaps: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for slot in inputs["people_state"]["slots"]:
        candidate_id = slot["candidate_id"]
        if slot.get("slot_status") != "identified_person":
            gaps[candidate_id].append(
                {
                    "slotId": slot["slot_id"],
                    "programName": slot["program_name"],
                    "status": "source_review_not_completed",
                    "displayLabel": "数据补充中",
                    "displayAsNone": False,
                }
            )
            continue
        live_status = reverify.get(slot.get("source_id"))
        if live_status not in {"live_verified_exact", "live_verified_normalized"}:
            continue
        people[candidate_id].append(
            {
                "id": slot.get("canonical_person_id") or slot.get("person_id"),
                "name": slot["person_name"],
                "programName": slot["program_name"],
                "relationshipType": slot.get("relationship_type"),
                "verificationStatus": live_status,
                "sourceIds": list(slot.get("source_ids") or [slot["source_id"]]),
                "displayTier": "verified",
                "quarantined": False,
            }
        )
    return people, gaps


def _narrative_sources(inputs: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    notable: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in inputs["documents"]["narrative_notable"].get("records", []):
        notable[row["candidate_id"]].append(
            {
                "personName": row["person_name"],
                "relationship": row.get("attendance_relationship"),
                "program": row.get("major_or_program") or row.get("degree_or_program"),
                "sourceIds": [row["source_id"]],
            }
        )
    return notable


def _source_rows(inputs: Mapping[str, Any], referenced: Set[str]) -> List[Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}

    def add(row: Mapping[str, Any]) -> None:
        source_id = row.get("source_id") or row.get("sourceId")
        if not source_id:
            return
        url = row.get("source_url") or row.get("url") or row.get(
            "source_url_or_reference"
        )
        publisher = row.get("publisher") or row.get("source_publisher")
        source_type = row.get("source_type") or row.get("source_access_type")
        if not publisher or not source_type:
            return
        candidate = {
            "sourceId": source_id,
            "publisher": publisher,
            "sourceType": source_type,
            "url": url if isinstance(url, str) and url.startswith(("http://", "https://")) else None,
            "referenceYear": row.get("reference_year"),
            "scope": row.get("field_scope") or row.get("supports_streams") or row.get("source_role") or [],
            "status": row.get("availability_status") or row.get("source_confidence") or "verified",
        }
        previous = candidates.get(source_id)
        if previous is None or sum(value not in (None, [], "") for value in candidate.values()) > sum(
            value not in (None, [], "") for value in previous.values()
        ):
            candidates[source_id] = candidate

    for name in (
        "stage3c_source_manifest",
        "stage4b_source_manifest",
        "stage4c_source_manifest",
        "narrative_sources",
    ):
        document = inputs["documents"][name]
        for row in document.get("sources", document.get("records", [])):
            add(row)
    candidate_names = {
        row["candidate_university_id"]: row["display_name"]
        for row in inputs["documents"]["candidate_identities"]["universities"]
    }
    for row in inputs["documents"]["stage3b_program_sources"]["observations"]:
        add(
            {
                **row,
                "publisher": candidate_names[row["candidate_id"]],
                "field_scope": ["top_programs"],
                "availability_status": "verified",
            }
        )
    if any(
        major.get("source_id") == "source_ipeds_c2023_completions"
        for school in inputs["documents"]["stage3c_all_majors"]["universities"]
        for major in school.get("all_undergraduate_majors", [])
    ):
        add(
            {
                "source_id": "source_ipeds_c2023_completions",
                "publisher": "National Center for Education Statistics",
                "source_type": "ipeds_federal",
                "source_url_or_reference": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx",
                "reference_year": "2022-23",
                "field_scope": ["bachelor_degree_award_areas"],
                "availability_status": "source_limited",
            }
        )
    for item in inputs["ranking_source_manifests"]:
        document = item["document"]
        for row in document.get("sources", document.get("records", [])):
            add(row)
    for row in inputs["people_state"]["sources"].values():
        add(row)

    missing = sorted(referenced - set(candidates))
    if missing:
        raise ValueError("Unresolved Preview source metadata: {}".format(", ".join(missing)))
    return [candidates[source_id] for source_id in sorted(referenced)]


def _collect_source_ids(value: Any, found: Set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "sourceIds" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            else:
                _collect_source_ids(child, found)
    elif isinstance(value, list):
        for child in value:
            _collect_source_ids(child, found)


def build_preview_contract(inputs: Mapping[str, Any]) -> Dict[str, Any]:
    indexes = inputs["indexes"]
    documents = inputs["documents"]
    people_by_school, gaps_by_school = _people_by_school(inputs)
    notable_by_school = _narrative_sources(inputs)
    summaries: List[Dict[str, Any]] = []
    details: Dict[str, Dict[str, Any]] = {}

    comparison_index = indexes["comparison"]
    for candidate_id in sorted(indexes["candidates"]):
        candidate = indexes["candidates"][candidate_id]
        marker = indexes["marker"][candidate_id]
        profile = indexes["profiles"][candidate_id]
        admissions = indexes["admissions"][candidate_id]
        enrollment = indexes["enrollment"][candidate_id]
        sat_act = indexes["sat_act"][candidate_id]
        ranking = _ranking_summary(indexes["rankings"][candidate_id])
        chinese = indexes["chinese_names"][candidate_id]
        place = indexes["places"][candidate_id]
        geography4b = indexes["geography4b"][candidate_id]
        stage3b = indexes["stage3b_universities"][candidate_id]
        all_majors = indexes["all_majors"][candidate_id]
        comparison = comparison_index[candidate_id]

        warnings = list(marker.get("warnings") or [])
        warnings.extend(["stale_reference_year"])
        if sat_act["sat"].get("status") == "not_reported":
            warnings.append("sat_not_reported")
        if sat_act["act"].get("status") == "not_reported":
            warnings.append("act_not_reported")
        warnings.extend(
            [
                "test_policy_pending_external_access",
                "english_policy_pending_external_access",
            ]
        )
        if enrollment["graduate"].get("value") is None:
            warnings.append("graduate_enrollment_not_reported")
        if enrollment["total"].get("value") is None:
            warnings.append("total_enrollment_not_reported")
        if ranking["nationalRank"] is None:
            warnings.append("not_in_current_national_scope")
        if place.get("resolution_status") != "verified_place":
            warnings.append("county_scope_only")
        warning_summary = _warning_summary(warnings)
        cost_summary = _cost_summary(marker)
        undergraduate = _camel_field(
            enrollment["undergraduate"], warnings=("stale_reference_year",)
        )
        summary = {
            "id": candidate_id,
            "name": marker["name"],
            "nameZh": chinese["display_name_zh"],
            "chineseName": chinese["display_name_zh"],
            "aliases": sorted(set(candidate.get("aliases") or [marker["name"]])),
            "city": marker["city"],
            "state": marker["state"],
            "region": stage3b.get("region"),
            "country": stage3b.get("country") or "US",
            "latitude": marker["coordinates"]["latitude"],
            "longitude": marker["coordinates"]["longitude"],
            "schoolType": marker["school_type"],
            "rankingSummary": ranking,
            "rankingTier": ranking["rankingTier"],
            "rankingBand": ranking["rankingTier"],
            "nationalRanking": ranking["nationalRank"],
            "rankingYear": None,
            "costSummary": cost_summary,
            "undergraduateEnrollment": undergraduate,
            "acceptanceRate": _camel_field(admissions["acceptance_rate"]),
            "studentFacultyRatio": marker.get("student_faculty_ratio"),
            "topPrograms": [
                row["program_name"] for row in stage3b.get("top_5_programs_for_demo", [])
            ],
            "qualitySummary": {
                "status": "warning" if warning_summary["count"] else "verified",
                "warningCodes": warning_summary["codes"],
                "sourceLimited": True,
            },
            "warningSummary": warning_summary,
            "sourceStatus": "verified_frozen_with_warnings",
            "displayTier": "preview",
            "previewOnly": True,
            "datasetVersion": DATASET_VERSION,
            "sourceCommit": SOURCE_CHECKPOINT,
        }

        sat = _camel_field(sat_act["sat"])
        act = _camel_field(sat_act["act"])
        enrollment_fields = {
            scope: _camel_field(enrollment[scope], warnings=("stale_reference_year",))
            for scope in ("undergraduate", "graduate", "total")
        }
        geography_scope = "place" if place.get("resolution_status") == "verified_place" else "county"
        detail = dict(summary)
        detail.update(
            {
                "programs": [
                    {
                        "id": "{}:program:{}".format(candidate_id, index + 1),
                        "name": row["program_name"],
                        "rank": row.get("usnews_rank"),
                        "rankingFamily": row.get("source_basis"),
                        "sourceIds": [row["source_id"]] if row.get("source_id") else [],
                    }
                    for index, row in enumerate(stage3b.get("top_5_programs_for_demo", []))
                ],
                "allMajors": [
                    {
                        "name": row["normalized_major_name"] or row["major_name"],
                        "displayName": row["major_name"],
                        "degreeType": row.get("degree_type"),
                        "listType": row.get("list_type"),
                        "sourceIds": [row["source_id"]],
                        "status": "source_limited",
                        "warnings": [row["data_limitation"]]
                        if row.get("data_limitation")
                        else [],
                    }
                    for row in all_majors.get("all_undergraduate_majors", [])
                ],
                "allMajorsStatus": {
                    "status": "source_limited"
                    if all_majors.get("all_undergraduate_majors")
                    else "not_reported",
                    "nullReason": all_majors.get("major_list_gap_reason"),
                },
                "enrollment": enrollment_fields,
                "admissions": {
                    "acceptanceRate": _camel_field(admissions["acceptance_rate"]),
                    "graduationRate": _camel_field(admissions["graduation_rate"]),
                    "retentionRate": _camel_field(admissions["retention_rate"]),
                    "sat": sat,
                    "act": act,
                    "testPolicy": _pending_field(indexes["test_policy"][candidate_id]),
                    "englishPolicy": _pending_field(indexes["english_policy"][candidate_id]),
                },
                "geography": {
                    "geographyScope": geography_scope,
                    "place": {
                        "value": place.get("place_name") if geography_scope == "place" else None,
                        "status": place.get("resolution_status"),
                        "referenceYear": 2024,
                        "scope": "census_place",
                        "unit": "name",
                        "sourceIds": list(
                            geography4b.get("census_place", {}).get("source_ids") or []
                        ),
                        "warnings": [],
                    },
                    "county": {
                        "value": geography4b.get("county", {}).get("name"),
                        "status": geography4b.get("county", {}).get("availability_status"),
                        "referenceYear": geography4b.get("county", {}).get("reference_year"),
                        "scope": "county",
                        "unit": "name",
                        "sourceIds": list(
                            geography4b.get("county", {}).get("source_ids") or []
                        ),
                        "warnings": [],
                    },
                    "cbsa": geography4b.get("cbsa"),
                },
                "nearbyTowns": list(comparison.get("nearest_towns", {}).get("values") or []),
                "history": {
                    "value": indexes["history"][candidate_id].get("history_summary"),
                    "status": "verified",
                    "sourceIds": [indexes["history"][candidate_id]["source_id"]],
                },
                "anecdotes": [
                    {
                        "text": indexes["anecdotes"][candidate_id].get("anecdote_text"),
                        "type": indexes["anecdotes"][candidate_id].get("anecdote_type"),
                        "sourceIds": [indexes["anecdotes"][candidate_id]["source_id"]],
                    }
                ],
                "notableAttendance": notable_by_school.get(candidate_id, []),
                "people": sorted(
                    people_by_school.get(candidate_id, []),
                    key=lambda row: (row["programName"], row["name"], row["id"]),
                ),
                "programPeopleGaps": sorted(
                    gaps_by_school.get(candidate_id, []), key=lambda row: row["slotId"]
                ),
                "rawCostRecords": [
                    {
                        "amountUsd": value,
                        "currency": cost_summary["currency"],
                        "scope": scope,
                        "academicYear": cost_summary["academicYear"],
                        "sourceIds": cost_summary["sourceIds"],
                    }
                    for scope, value in zip(cost_summary["scopes"], marker["tuition_summary"]["values"])
                ],
            }
        )
        summaries.append(summary)
        details[candidate_id] = detail

    referenced: Set[str] = set()
    _collect_source_ids(summaries, referenced)
    _collect_source_ids(details, referenced)
    source_index = {"contractVersion": CONTRACT_VERSION, "sources": _source_rows(inputs, referenced)}
    features: MutableMapping[str, Dict[str, Any]] = {}
    for feature in ENABLED_FEATURES:
        features[feature] = {"status": "ready_with_warnings", "previewEligibility": True}
    for feature in DISABLED_FEATURES:
        features[feature] = {
            "status": "disabled" if feature == "ai_context" else "blocked",
            "previewEligibility": False,
        }

    region_metrics = {
        "contractVersion": CONTRACT_VERSION,
        "status": "blocked",
        "records": [],
        "choroplethEnabled": False,
        "disabledReason": "Credentialed official regional intake is unavailable.",
        "metricMetadata": [
            {"metricId": metric_id, "status": "deferred", "unit": None}
            for metric_id in (
                "income",
                "safety",
                "employment",
                "cost",
                "chinese_population",
            )
        ],
        "warnings": ["deferred_regional_data_not_a_verified_fact"],
    }
    feature_readiness = {
        "contractVersion": CONTRACT_VERSION,
        "productionEligibility": False,
        "features": features,
    }
    manifest = {
        "contractVersion": CONTRACT_VERSION,
        "schemaVersion": CONTRACT_VERSION,
        "datasetVersion": DATASET_VERSION,
        "view": "preview",
        "sourceCheckpoint": SOURCE_CHECKPOINT,
        "sourceCommit": SOURCE_CHECKPOINT,
        "generatedAt": SOURCE_CHECKPOINT_TIME,
        "schoolCount": 62,
        "summaryCount": len(summaries),
        "detailCount": len(details),
        "verifiedRecordCount": 904,
        "sourceLimited": True,
        "incomplete": True,
        "notFinal": True,
        "previewOnly": True,
        "enabledFeatures": list(ENABLED_FEATURES),
        "disabledFeatures": list(DISABLED_FEATURES),
        "warningCodes": sorted(
            {
                code
                for summary in summaries
                for code in summary["warningSummary"]["codes"]
            }
        ),
        "generatedFrom": list(inputs["generated_from"]),
        "counts": {"universities": 62, "regionMetrics": 0, "news": 0},
    }
    diagnostics = {
        "contractVersion": CONTRACT_VERSION,
        "sourceCheckpoint": SOURCE_CHECKPOINT,
        "generatedFrom": list(inputs["generated_from"]),
        "networkAccess": "disabled",
        "handoffDependency": False,
        "fixtureDependency": False,
        "stage4bValidator": "60/60",
        "stage4cValidator": "86/86",
        "cumulativeVerifiedRecords": 904,
        "programPeopleInput": 180,
        "programPeoplePublished": sum(len(rows) for rows in people_by_school.values()),
        "programPeopleGaps": sum(len(rows) for rows in gaps_by_school.values()),
    }
    return {
        "manifest": manifest,
        "universities": summaries,
        "university_details": details,
        "region_metrics": region_metrics,
        "source_index": source_index,
        "status_dictionary": {
            "contractVersion": CONTRACT_VERSION,
            "statuses": {
                "verified": "Frozen verified fact",
                "not_reported": "Official source did not report a value",
                "pending_external_access": "Not a fact; external review remains pending",
                "deferred": "Prerequisite data is deferred and no fact is available",
                "not_applicable": "The field does not apply to this record",
                "source_review_not_completed": "数据补充中",
                "quarantined": "The record is excluded from public Preview output",
                "source_limited": "The Preview is limited to approved frozen sources",
                "incomplete": "The Preview contract is incomplete",
                "not_final": "The Preview contract is not final",
                "blocked": "Feature is disabled because prerequisites are unavailable",
                "not_in_current_national_scope": "Excluded from numeric rank filters",
            },
        },
        "feature_readiness": feature_readiness,
        "integration_diagnostics": diagnostics,
        "contract_mapping_matrix": documents["mapping_matrix"],
    }
