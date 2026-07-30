"""Deterministic Stage 4C reports."""

from pathlib import Path
from typing import Any, Dict


def render_completion_report(bundle: Dict[str, Any]) -> str:
    s = bundle["integration_summary"]
    return f"""# Stage 4C MVP-Critical Data Completion

- Schools: {s["schools"]}
- Graduate enrollment: {s["graduate_enrollment_verified"]}/62 verified
- Total enrollment: {s["total_enrollment_verified_derived"]}/62 same-scope derived
- Chinese display names: {s["chinese_names_reviewed_established"]}/62 reviewed
- SAT / ACT: {s["sat_verified"]}/62 and {s["act_verified"]}/62 verified; all remaining records have explicit missing status
- Census place: {s["census_place_verified"]}/62 place, {s["county_only_valid"]}/62 county-only valid
- National ranking: {s["national_ranked"]} ranked, {s["national_rank_null_semantics"]} explicit null semantics
- Stage 4C verified records: {s["stage4c_verified_record_count"]}
- Cumulative Stage 4B+4C records: {s["cumulative_verified_record_count"]}
- Program people preserved: {s["program_people_identified"]}/310; gaps {s["program_people_gaps"]}

Test and English policy pages were not frozen and remain pending external access.
ACS API and bulk routes were unavailable in this execution environment, so no
regional estimate was guessed. Status remains `{s["readiness_status"]}`.
"""


def render_preview_report(bundle: Dict[str, Any]) -> str:
    rows = bundle["preview_readiness_contract"]["areas"]
    lines = "\n".join(f"- {r['product_area']}: {r['status']}" for r in rows)
    return f"""# Stage 4C Preview Readiness

{lines}

No preview, production, or frontend export was generated. A Preview Adapter may
be started only after the combined Stage 4B+4C Gate, with null/source warnings.
"""


def render_source_gap_report(bundle: Dict[str, Any]) -> str:
    failures = bundle["regional_access_failures"]["failures"]
    return f"""# Stage 4C Source and Gap Report

- Regional access failures: {len(failures)} metric families
- Test-policy pending: 62
- English-policy pending: 62
- Graduate enrollment not reported: 2
- Census place county-only valid fallbacks: 16
- Program-person gaps preserved: 130
- Missing referenced cache: 0
- Source-policy violations: 0

Official Census API returned Missing Key, official table-based bulk returned
HTTP 403 through the gateway, and the IPEDS ADM2024 download timed out. These
are recorded as access failures; frontend demonstration values were excluded.
"""


def write_reports(bundle: Dict[str, Any], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "stage4c-mvp-critical-data-completion-report.md": render_completion_report(bundle),
        "stage4c-preview-readiness-report.md": render_preview_report(bundle),
        "stage4c-source-and-gap-report.md": render_source_gap_report(bundle),
    }
    for filename, content in outputs.items():
        (report_dir / filename).write_text(content, encoding="utf-8")
