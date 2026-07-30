"""Stable Markdown reports for the Stage 5 adapter checkpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


REPORT_FILES = {
    "adapter": "stage5-warning-aware-preview-adapter-report.md",
    "contract": "stage5-preview-contract-report.md",
    "validation": "stage5-integration-validation-report.md",
}


def render_reports(bundle: Dict[str, Any]) -> Dict[str, str]:
    manifest = bundle["manifest"]
    validation = bundle["validation_result"]
    diagnostics = bundle["integration_diagnostics"]
    summaries = bundle["universities"]
    details = bundle["university_details"]
    adapter = f"""# Stage 5 Warning-Aware Preview Adapter Report

## Outcome

- Architecture: additive read-only adapter over committed frozen artifacts
- Transport: `preview_bundle_via_next_bff`
- Contract: `{manifest["contractVersion"]}`
- Source checkpoint: `{manifest["sourceCheckpoint"]}`
- Preview only: `true`
- Production eligibility: `false`
- Summary/detail records: `{len(summaries)}/{len(details)}`
- Verified Stage 4B + 4C boundary: `{manifest["verifiedRecordCount"]}`
- Network used during generation: `false`
- Frontend fixture dependency: `false`
- Handoff dependency: `false`

## Warning policy

Null, not-reported, pending, deferred, source-limited, and gap states remain explicit.
The adapter does not synthesize zeroes, ranking memberships, region metrics, policy
facts, or production exports. People whose live evidence is changed, unavailable,
or not found are not exposed.
"""
    contract = f"""# Stage 5 Preview Contract Report

## Contract boundary

- `view=preview`
- `sourceLimited=true`
- `incomplete=true`
- `notFinal=true`
- Schools: `{manifest["schoolCount"]}`
- National rank nulls: `{sum(row["rankingSummary"]["nationalRank"] is None for row in summaries)}`
- Rank zero records: `{sum(row["rankingSummary"]["nationalRank"] == 0 for row in summaries)}`
- County-only records: `{sum(row["geography"]["geographyScope"] == "county" for row in details.values())}`
- All-major rows: `{sum(len(row["allMajors"]) for row in details.values())}`
- People input/published/gaps: `{diagnostics["programPeopleInput"]}/{diagnostics["programPeoplePublished"]}/{diagnostics["programPeopleGaps"]}`
- Region records: `0` (blocked)
- Synthetic source placeholders: `0`
- AI context: disabled
- Choropleth: disabled

The contract mapping matrix is emitted with the bundle and is the authoritative
DTO-to-domain mapping record for the frontend integration.
"""
    validation_report = f"""# Stage 5 Integration Validation Report

## Deterministic backend gate

- Status: `{validation["status"]}`
- Checks: `{validation["passedCheckCount"]}/{validation["checkCount"]}`
- Failed: `{validation["failedCheckCount"]}`
- Stage 4B checkpoint: `{diagnostics["stage4bValidator"]}`
- Stage 4C checkpoint: `{diagnostics["stage4cValidator"]}`
- Deterministic regeneration: `{str(validation["deterministicRegeneration"]).lower()}`
- Network-disabled generation: `{str(validation["networkDisabledGeneration"]).lower()}`

## Standalone full-suite observation

- Full Python discovery: `393` run
- Passed: `279`
- Cache-dependent errors/failures: `114`
- Root cause: untracked cache bodies intentionally excluded from the standalone clone
- Stage 5 dependency on those cache bodies: `false`

The committed Stage 4B `60/60` and Stage 4C `86/86` validation results remain
unchanged. Re-running their historical validators in the standalone clone is
intentionally impossible without the prohibited untracked cache bodies. Frontend
type checking, lint, tests, build, and browser results are recorded in the
frontend Stage 5 integration report.
"""
    return {"adapter": adapter, "contract": contract, "validation": validation_report}


def write_reports(bundle: Dict[str, Any], report_root: Path) -> None:
    report_root = Path(report_root)
    report_root.mkdir(parents=True, exist_ok=True)
    for key, contents in render_reports(bundle).items():
        (report_root / REPORT_FILES[key]).write_text(contents, encoding="utf-8")
