"""Load frozen official and Stage 4B sources without network access."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pathos_data.stage4b.generator import build_stage4b
from pathos_data.stage4b.source_intake import load_official_school_rows


def build_context(repo_root: Path) -> Dict[str, Any]:
    pipeline = repo_root / "data-pipeline"
    stage4b = build_stage4b(repo_root)
    official_rows = load_official_school_rows(pipeline)
    return {
        "repo_root": repo_root,
        "pipeline_root": pipeline,
        "official_rows": official_rows,
        "stage4b": stage4b,
        "profiles_by_id": {
            row["candidate_id"]: row
            for row in stage4b["school_profile_metrics"]["universities"]
        },
        "admissions_by_id": {
            row["candidate_id"]: row
            for row in stage4b["admissions_metrics"]["universities"]
        },
        "geography_by_id": {
            row["candidate_id"]: row
            for row in stage4b["campus_geography_crosswalk"]["universities"]
        },
        "marker_by_id": {
            row["university_id"]: row
            for row in stage4b["marker_summary"]["universities"]
        },
    }
