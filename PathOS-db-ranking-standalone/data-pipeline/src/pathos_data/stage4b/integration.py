"""Stage 4B source manifests, backend context, coverage, and gap assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .config import read_json, sha256_file
from .source_intake import (
    IPEDS_HD_SOURCE_ID,
    SCORECARD_SOURCE_ID,
)


SOURCE_DEFINITIONS = (
    {
        "source_id": IPEDS_HD_SOURCE_ID,
        "publisher": "National Center for Education Statistics",
        "source_type": "official_federal_dataset",
        "source_url": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx",
        "reference_year": 2024,
        "path": "data-pipeline/cache/stage3-ipeds/HD2024.zip",
        "cache_id": "cache_stage4b_ipeds_hd2024",
        "field_scope": ["institution", "county", "cbsa", "campus_setting"],
        "availability_status": "verified",
    },
    {
        "source_id": SCORECARD_SOURCE_ID,
        "publisher": "United States Department of Education",
        "source_type": "official_federal_dataset",
        "source_url": (
            "https://ed-public-download.scorecard.network/downloads/"
            "Most-Recent-Cohorts-Institution_05192025.zip"
        ),
        "reference_year": 2025,
        "path": (
            "data-pipeline/cache/stage3b-official/"
            "Most-Recent-Cohorts-Institution_05192025.zip"
        ),
        "cache_id": "cache_stage4b_college_scorecard_2025_05_19",
        "field_scope": [
            "undergraduate_enrollment",
            "acceptance_rate",
            "graduation_rate",
            "retention_rate",
            "sat",
            "act",
        ],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_census_2024_places_gazetteer",
        "publisher": "United States Census Bureau",
        "source_type": "official_federal_dataset",
        "source_url": (
            "https://www.census.gov/geographies/reference-files/time-series/"
            "geo/gazetteer-files.2024.html"
        ),
        "reference_year": 2024,
        "path": "data-pipeline/cache/stage3c2-geography/2024_Gaz_place_national.zip",
        "cache_id": "cache_stage4b_census_2024_places_gazetteer",
        "field_scope": ["census_place", "nearest_towns"],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_national_ranking_existing",
        "publisher": "PathOS verified Stage 2 ranking layer",
        "source_type": "verified_existing_backend_artifact",
        "source_url": "input://stage2-national-top50",
        "reference_year": 2026,
        "path": (
            "data-pipeline/data/ranking-seeds/2026-best-colleges/"
            "completion-national/national-universities-top-50.json"
        ),
        "cache_id": "input_stage4b_national_ranking_top50",
        "field_scope": ["national_ranking"],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_tuition_existing",
        "publisher": "PathOS verified Stage 3B IPEDS overlay",
        "source_type": "verified_existing_backend_artifact",
        "source_url": "input://stage3b-tuition-gap-fill",
        "reference_year": 2023,
        "path": (
            "data-pipeline/artifacts/stage3b-demo-critical-gap-fill/"
            "stage3b-tuition-gap-fill.json"
        ),
        "cache_id": "input_stage4b_stage3b_tuition",
        "field_scope": ["tuition"],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_ratio_existing",
        "publisher": "PathOS verified Stage 3B College Scorecard overlay",
        "source_type": "verified_existing_backend_artifact",
        "source_url": "input://stage3b-student-faculty",
        "reference_year": 2025,
        "path": (
            "data-pipeline/artifacts/stage3b-demo-critical-gap-fill/"
            "stage3b-student-faculty.json"
        ),
        "cache_id": "input_stage4b_stage3b_ratio",
        "field_scope": ["student_faculty_ratio"],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_stage3c2_nearest_towns",
        "publisher": "PathOS verified Stage 3C2 Census Gazetteer overlay",
        "source_type": "verified_existing_backend_artifact",
        "source_url": "input://stage3c2-nearest-towns",
        "reference_year": 2024,
        "path": (
            "data-pipeline/artifacts/stage3c2-nearest-towns-gap-repair/"
            "stage3c2-nearest-towns.json"
        ),
        "cache_id": "input_stage4b_stage3c2_nearest_towns",
        "field_scope": ["nearest_towns", "transport_context"],
        "availability_status": "verified",
    },
    {
        "source_id": "source_stage4b_acs5_2023_intake_deferred",
        "publisher": "United States Census Bureau",
        "source_type": "official_federal_api",
        "source_url": "https://api.census.gov/data/2023/acs/acs5",
        "reference_year": 2023,
        "path": None,
        "cache_id": None,
        "field_scope": ["demographics", "housing", "income"],
        "availability_status": "deferred",
        "failure_category": "api_key_required",
    },
)


def build_source_and_cache_manifests(
    repo_root: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    sources = []
    caches = []
    for definition in SOURCE_DEFINITIONS:
        source = {
            key: value
            for key, value in definition.items()
            if key not in {"path"}
        }
        source.update(
            {
                "accessed_date": "2026-07-24",
                "license_or_usage_notes": "Official public data or frozen verified PathOS input",
                "query_parameters": {},
            }
        )
        sources.append(source)
        relative = definition.get("path")
        if relative:
            path = repo_root / relative
            caches.append(
                {
                    "cache_id": definition["cache_id"],
                    "cache_path": relative,
                    "sha256": sha256_file(path),
                    "exists": path.is_file(),
                    "cache_class": (
                        "gitignored_official_cache"
                        if "/cache/" in f"/{relative}"
                        else "committed_verified_input_artifact"
                    ),
                    "git_tracked": "/cache/" not in f"/{relative}",
                    "gitignored": "/cache/" in f"/{relative}",
                    "source_ids": [definition["source_id"]],
                    "reference_year": definition["reference_year"],
                }
            )
    return (
        {
            "record_type": "stage4b_source_manifest",
            "sources": sorted(sources, key=lambda row: row["source_id"]),
        },
        {
            "record_type": "stage4b_cache_manifest",
            "caches": sorted(caches, key=lambda row: row["cache_id"]),
            "cache_bodies_committed_by_stage4b": 0,
        },
    )


def _tuition_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    records = row.get("tuition_records", [])
    values = [
        value
        for record in records
        for value in [record.get("total_tuition_and_required_fees")]
        if isinstance(value, (int, float))
    ]
    scopes = sorted(
        {
            record.get("residency_scope")
            for record in records
            if record.get("residency_scope")
        }
    )
    years = sorted(
        {record.get("academic_year") for record in records if record.get("academic_year")}
    )
    return {
        "values": values,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "currency": "USD",
        "academic_year": years[-1] if years else None,
        "scopes": scopes,
        "source_ids": sorted(
            {record.get("source_id") for record in records if record.get("source_id")}
        ),
        "comparison_warning": (
            "Public in-state and out-of-state tuition are separate scopes."
            if len(values) > 1
            else None
        ),
    }


def build_backend_context(
    repo_root: Path,
    official_rows: Iterable[Dict[str, Any]],
    profiles: Iterable[Dict[str, Any]],
    admissions: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    pipeline = repo_root / "data-pipeline"
    stage3c = read_json(
        pipeline
        / "artifacts/stage3c-academic-geo-enrichment/stage3c-universities.json"
    )["universities"]
    stage3c_by_id = {row["candidate_id"]: row for row in stage3c}
    universities = {}
    for row in official_rows:
        location = stage3c_by_id[row["candidate_id"]]
        universities[row["candidate_id"]] = {
            **row,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "city": location["city"],
            "state": location["state"],
            "region": location["region"],
        }
    alias_to_candidate = {
        name.casefold(): row["candidate_id"]
        for row in universities.values()
        for name in [
            row["university_display_name"],
            *row.get("known_aliases", []),
        ]
    }
    rankings = {}
    for record in read_json(
        pipeline
        / "data/ranking-seeds/2026-best-colleges/completion-national/"
        "national-universities-top-50.json"
    )["records"]:
        candidate_id = alias_to_candidate[record["school_display_name"].casefold()]
        rankings[candidate_id] = record
    tuition_rows = read_json(
        pipeline
        / "artifacts/stage3-program-mvp-detail-pack/program-mvp-tuition.json"
    )["universities"]
    tuition_gap_rows = read_json(
        pipeline
        / "artifacts/stage3b-demo-critical-gap-fill/stage3b-tuition-gap-fill.json"
    )["universities"]
    tuition_by_id = {row["candidate_id"]: row for row in tuition_rows}
    tuition_by_id.update(
        {
            row["candidate_id"]: row
            for row in tuition_gap_rows
            if row.get("resolved") is True
        }
    )
    ratios = read_json(
        pipeline
        / "artifacts/stage3b-demo-critical-gap-fill/stage3b-student-faculty.json"
    )["universities"]
    majors = read_json(
        pipeline
        / "artifacts/stage3c-academic-geo-enrichment/stage3c-official-majors.json"
    )["universities"]
    nearest = read_json(
        pipeline
        / "artifacts/stage3c2-nearest-towns-gap-repair/stage3c2-nearest-towns.json"
    )["universities"]
    return {
        "universities": universities,
        "profiles": {row["candidate_id"]: row for row in profiles},
        "admissions": {row["candidate_id"]: row for row in admissions},
        "rankings": rankings,
        "tuition": {
            candidate_id: _tuition_summary(row)
            for candidate_id, row in tuition_by_id.items()
        },
        "ratios": {row["candidate_id"]: row for row in ratios},
        "majors": {
            row["candidate_id"]: [
                major.get("major_name") or major.get("program_name") or str(major)
                for major in row.get("majors", [])
            ]
            for row in majors
        },
        "nearest": {row["candidate_id"]: row for row in nearest},
    }


def build_comparison_records(
    context: Dict[str, Any],
    geography: Iterable[Dict[str, Any]],
    housing: Iterable[Dict[str, Any]],
    demographics: Iterable[Dict[str, Any]],
    crime: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    geo = {row["candidate_id"]: row for row in geography}
    housing_by_id = {row["candidate_id"]: row for row in housing}
    demographic_by_id = {row["candidate_id"]: row for row in demographics}
    crime_by_id = {row["candidate_id"]: row for row in crime}
    output = []
    for candidate_id, university in context["universities"].items():
        admission = context["admissions"][candidate_id]
        profile = context["profiles"][candidate_id]
        rank = context["rankings"].get(candidate_id)
        towns = context["nearest"][candidate_id]["nearest_towns"]
        output.append(
            {
                "university_id": candidate_id,
                "national_ranking": {
                    "value": rank["numeric_rank"] if rank else None,
                    "unit": "rank",
                    "reference_year": 2026 if rank else None,
                    "null_semantics": (
                        None
                        if rank
                        else "explicit_not_applicable_or_not_in_national_scope"
                    ),
                },
                "top_programs": [
                    item["program_name"]
                    for item in university["top_5_programs_for_demo"]
                ],
                "tuition": context["tuition"][candidate_id],
                "acceptance_rate": {
                    "value": admission["acceptance_rate"]["value"],
                    "unit": "ratio",
                    "scope": admission["acceptance_rate"]["scope"],
                    "reference_year": admission["acceptance_rate"]["reference_year"],
                },
                "student_faculty_ratio": {
                    "value": context["ratios"][candidate_id][
                        "student_faculty_ratio"
                    ],
                    "unit": "students_per_faculty",
                    "reference_year": 2025,
                },
                "undergraduate_enrollment": {
                    "value": profile["enrollment"]["undergraduate"]["value"],
                    "unit": "students",
                    "scope": "undergraduate_degree_seeking",
                    "reference_year": 2025,
                },
                "school_type": profile["school_type"]["value"],
                "nearest_towns": {
                    "values": [
                        {
                            "name": town["town_name"],
                            "distance": town["distance_km"],
                        }
                        for town in towns
                    ],
                    "distance_unit": "km",
                    "distance_method": "haversine_straight_line",
                },
                "regional_geography": {
                    "geography_id": geo[candidate_id]["primary_region_for_map"][
                        "geography_id"
                    ],
                    "geography_type": geo[candidate_id]["primary_region_for_map"][
                        "geography_type"
                    ],
                },
                "income_rent": housing_by_id[candidate_id]["metrics"],
                "population_ratios": demographic_by_id[candidate_id]["metrics"],
                "crime_safety": crime_by_id[candidate_id],
                "warnings": [
                    "Regional metrics are unavailable until credentialed official intake.",
                    "Different reference years and scopes must be shown in comparison UI.",
                ],
            }
        )
    return sorted(output, key=lambda row: row["university_id"])


def coverage_row(
    field: str,
    *,
    expected: int,
    available: int,
    verified: int,
    product_area: str,
    scope: str = "school",
    required_for_mvp: bool = False,
    blocked: bool = False,
    source_quality: str = "official_or_verified_backend",
    priority: str = "P1",
) -> Dict[str, Any]:
    status = (
        "blocked"
        if blocked
        else "ready"
        if verified == expected
        else "partial"
        if available
        else "missing"
    )
    return {
        "product_area": product_area,
        "field": field,
        "scope": scope,
        "required_for_mvp": required_for_mvp,
        "backend_path": f"stage4b.{field}",
        "coverage": {
            "expected_records": expected,
            "available_records": available,
            "verified_records": verified,
            "pending_records": max(available - verified, 0),
            "missing_records": expected - available,
            "coverage_percent": round(available / expected * 100, 2),
        },
        "status": status,
        "source_quality": source_quality,
        "remaining_gap_reason": None if status == "ready" else "official_uniform_data_incomplete",
        "next_collection_action": (
            "none"
            if status == "ready"
            else "credentialed_official_source_intake_or_review"
        ),
        "priority": priority,
    }


def build_coverage_matrix(
    *,
    place_count: int,
    cbsa_count: int,
    sat_count: int,
    act_count: int,
) -> List[Dict[str, Any]]:
    specs = [
        ("identity", 62, 62, "map", True, False, "P0"),
        ("coordinates", 62, 62, "map", True, False, "P0"),
        ("school_type", 62, 62, "detail", True, False, "P0"),
        ("undergraduate_enrollment", 62, 62, "detail", True, False, "P0"),
        ("graduate_enrollment", 0, 0, "detail", False, False, "P1"),
        ("total_enrollment", 0, 0, "detail", False, False, "P1"),
        ("chinese_display_name", 0, 0, "detail", False, False, "P1"),
        ("acceptance_rate", 62, 62, "detail", True, False, "P0"),
        ("graduation_rate", 62, 62, "detail", False, False, "P1"),
        ("retention_rate", 62, 62, "detail", False, False, "P1"),
        ("sat", sat_count, sat_count, "detail", False, False, "P1"),
        ("act", act_count, act_count, "detail", False, False, "P2"),
        ("test_optional_policy", 0, 0, "detail", False, False, "P1"),
        ("toefl_policy", 0, 0, "detail", False, False, "P1"),
        ("national_ranking", 50, 50, "filter", False, False, "P0"),
        ("top_five_programs", 62, 62, "detail", True, False, "P0"),
        ("tuition", 62, 62, "comparison", True, False, "P0"),
        ("student_faculty_ratio", 62, 62, "comparison", True, False, "P0"),
        ("nearest_towns", 62, 62, "detail", False, False, "P1"),
        ("county_geoid", 62, 62, "map", True, False, "P0"),
        ("census_place_geoid", place_count, place_count, "map", False, False, "P1"),
        ("cbsa_geoid", cbsa_count, cbsa_count, "map", False, False, "P1"),
        ("median_household_income", 0, 0, "map", False, False, "P1"),
        ("median_gross_rent", 0, 0, "comparison", False, False, "P1"),
        ("population_density", 0, 0, "map", False, False, "P1"),
        ("asian_population_ratio", 0, 0, "map", False, False, "P1"),
        ("chinese_population_ratio", 0, 0, "map", False, False, "P1"),
        ("crime_rate", 0, 0, "map", False, False, "P1"),
        ("safety_index", 0, 0, "map", False, False, "P1"),
        ("cost_of_living_index", 0, 0, "comparison", False, False, "P1"),
        ("transport_accessibility", 62, 0, "detail", False, False, "P2"),
        ("history", 62, 62, "detail", False, False, "P1"),
        ("anecdotes", 62, 62, "detail", False, False, "P1"),
        ("notable_attendance", 62, 62, "detail", False, False, "P1"),
        ("program_people", 180, 180, "detail", False, False, "P2"),
        ("marker_summary_readiness", 62, 62, "map", True, False, "P0"),
        ("search_readiness", 62, 62, "filter", True, False, "P0"),
        ("filter_readiness", 62, 62, "filter", True, False, "P0"),
        ("comparison_readiness", 62, 62, "comparison", False, False, "P1"),
        ("parent_mode_readiness", 0, 0, "mode", False, True, "P1"),
        ("student_mode_readiness", 62, 62, "mode", False, False, "P1"),
        ("ai_context_readiness", 62, 0, "ai", False, False, "P1"),
        ("source_panel_readiness", 62, 62, "detail", True, False, "P0"),
        ("map_choropleth_readiness", 0, 0, "map", False, True, "P1"),
    ]
    rows = []
    for field, available, verified, area, mvp, blocked, priority in specs:
        expected = 310 if field == "program_people" else 62
        rows.append(
            coverage_row(
                field,
                expected=expected,
                available=available,
                verified=verified,
                product_area=area,
                required_for_mvp=mvp,
                blocked=blocked,
                priority=priority,
            )
        )
    return rows


def build_backlog(matrix: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "field": row["field"],
            "priority": row["priority"],
            "records_affected": row["coverage"]["missing_records"],
            "recommended_source": (
                "official university policy page"
                if row["field"] in {"test_optional_policy", "toefl_policy"}
                else "credentialed federal/state/local official dataset"
            ),
            "estimated_difficulty": "medium" if row["priority"] == "P0" else "high",
            "validation_rule": "scope, year, unit, source, and cache provenance required",
            "dependency": row["remaining_gap_reason"],
            "frontend_feature_unlocked": row["product_area"],
        }
        for row in matrix
        if row["status"] in {"partial", "missing", "blocked"}
    ]
