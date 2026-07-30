"""Deterministic human-readable Stage 4B reports."""

from __future__ import annotations

from typing import Any, Dict


def render_unified_report(bundle: Dict[str, Any]) -> str:
    summary = bundle["integration_summary"]
    return f"""# Stage 4B Unified Official Product Data Completion

Stage 4B is an independent verified enrichment overlay. It does not modify the
Candidate v2 universe, ranking memberships, people artifacts, or frontend.

## School and admissions

- Candidate schools: {summary["candidate_schools"]}
- School type: {summary["school_type_coverage"]}/62
- Undergraduate enrollment: {summary["undergraduate_enrollment_coverage"]}/62
- Graduate enrollment: {summary["graduate_enrollment_coverage"]}/62
- Total enrollment: {summary["total_enrollment_coverage"]}/62
- Acceptance rate: {summary["acceptance_rate_coverage"]}/62
- Graduation rate: {summary["graduation_rate_coverage"]}/62
- Retention rate: {summary["retention_rate_coverage"]}/62
- SAT middle-50 evidence: {summary["sat_coverage"]}/62
- ACT middle-50 evidence: {summary["act_coverage"]}/62
- Test-optional policy: {summary["test_optional_policy_coverage"]}/62
- TOEFL/English policy: {summary["toefl_policy_coverage"]}/62

## Geography and regional data

- County GEOID: {summary["county_geoid_coverage"]}/62
- Census place GEOID: {summary["census_place_geoid_coverage"]}/62
- CBSA: {summary["cbsa_coverage"]}/62
- Income/rent/density/Asian/Chinese ratio: deferred after official ACS intake required an unavailable credential
- Crime and safety index: deferred because no uniform jurisdiction/year exists in frozen inputs
- Cost-of-living index: deferred; no fabricated aggregate score was created
- Transport: {summary["transport_partial_coverage"]}/62 partial, using verified nearest-town distances only

## Product contracts

- Core marker contract: ready for a later preview-export stage
- Search contract: ready
- Filter/comparison contracts: partial; nulls are never coerced to zero
- Choropleth: not ready because regional metric intake is deferred
- AI context: contract ready; regional facts remain missing and quarantine is excluded

## Integrity

- Verified overlay records: {summary["verified_overlay_record_count"]}
- Source-policy violations: {summary["source_policy_violations"]}
- Ranking contamination: {summary["ranking_field_contamination"]}
- Program people preserved: {summary["program_people_identified"]}/310 identified, {summary["program_people_source_review_not_completed"]} gaps
- Final universe generated: {str(summary["final_universe_generated"]).lower()}
- Memberships generated: {str(summary["official_selection_memberships_generated"]).lower()}
- Frontend/preview/production export generated: false

Status: `{summary["readiness_status"]}`.
"""


def render_product_readiness_report(bundle: Dict[str, Any]) -> str:
    rows = bundle["product_data_coverage_matrix"]["fields"]
    grouped = {
        status: [row["field"] for row in rows if row["status"] == status]
        for status in ("ready", "partial", "missing", "blocked")
    }
    return f"""# Stage 4B Product Readiness

## Ready

{", ".join(grouped["ready"])}

## Partial

{", ".join(grouped["partial"]) or "None"}

## Missing

{", ".join(grouped["missing"]) or "None"}

## Blocked

{", ".join(grouped["blocked"]) or "None"}

Core map POI and school-detail preview contracts can be prepared in a later,
separately authorized export stage. Choropleth and region-dependent parent-mode
claims remain blocked. Production export remains prohibited.
"""


def render_source_gap_report(bundle: Dict[str, Any]) -> str:
    summary = bundle["integration_summary"]
    backlog = bundle["data_collection_backlog"]["items"]
    priorities = {
        priority: sum(row["priority"] == priority for row in backlog)
        for priority in ("P0", "P1", "P2")
    }
    return f"""# Stage 4B Source and Gap Report

Official frozen IPEDS and College Scorecard inputs produced verified school,
admissions, outcome, and test-score fields. Census Gazetteer and IPEDS produced
county/CBSA and 46 reviewed campus-place joins.

The Census geocoder request was rejected by the execution gateway, and the ACS
API required a credential not available to this task. These failures are
recorded in raw intake metadata. No values were guessed.

- Missing cache count: {summary["missing_cache_count"]}
- Quarantine count: {summary["quarantine_count"]}
- P0 backlog fields: {priorities["P0"]}
- P1 backlog fields: {priorities["P1"]}
- P2 backlog fields: {priorities["P2"]}
- Program-person gaps preserved: {summary["program_people_source_review_not_completed"]}

Regional demographics, rent, income, crime, safety, cost-of-living, and uniform
transport remain explicit pending/deferred work. Missing values must not be
rendered as zero, safe, cheap, or “none.”
"""


def write_reports(bundle: Dict[str, Any], report_dir: Any) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        "stage4b-unified-official-product-data-report.md": render_unified_report(bundle),
        "stage4b-product-readiness-report.md": render_product_readiness_report(bundle),
        "stage4b-source-and-gap-report.md": render_source_gap_report(bundle),
    }
    for filename, content in reports.items():
        (report_dir / filename).write_text(content, encoding="utf-8")
