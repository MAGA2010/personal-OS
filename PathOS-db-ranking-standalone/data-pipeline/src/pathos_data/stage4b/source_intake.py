"""Read frozen official IPEDS and College Scorecard cache inputs."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import fail, read_json


SCORECARD_SOURCE_ID = "source_stage4b_college_scorecard_2025_05_19"
IPEDS_HD_SOURCE_ID = "source_stage4b_ipeds_hd2024"
SCORECARD_RELEASE_YEAR = 2025
IPEDS_REFERENCE_YEAR = 2024
MISSING = {"", "NA", "NULL", "PrivacySuppressed", None}


def _zip_csv_rows(path: Path) -> List[Dict[str, str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".csv")
            ]
            if len(names) != 1:
                fail(f"Expected exactly one CSV in official cache: {path}")
            with archive.open(names[0]) as raw:
                return list(
                    csv.DictReader(line.decode("utf-8-sig") for line in raw)
                )
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        fail(f"Unable to read official cache {path}: {error}")


def parse_int(value: Any) -> Any:
    if value in MISSING:
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        fail(f"Official integer field has invalid value: {value!r}")


def parse_float(value: Any) -> Any:
    if value in MISSING:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        fail(f"Official numeric field has invalid value: {value!r}")


def load_official_school_rows(pipeline_root: Path) -> List[Dict[str, Any]]:
    stage3b_path = (
        pipeline_root
        / "artifacts/stage3b-demo-critical-gap-fill/stage3b-mvp-universities.json"
    )
    universities = read_json(stage3b_path).get("universities")
    if not isinstance(universities, list) or len(universities) != 62:
        fail("Stage 4B requires exactly 62 Stage 3B identity rows")
    scorecard_path = (
        pipeline_root
        / "cache/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip"
    )
    ipeds_path = pipeline_root / "cache/stage3-ipeds/HD2024.zip"
    scorecard = {
        row.get("UNITID"): row for row in _zip_csv_rows(scorecard_path)
        if row.get("UNITID")
    }
    ipeds = {
        row.get("UNITID"): row for row in _zip_csv_rows(ipeds_path)
        if row.get("UNITID")
    }
    output: List[Dict[str, Any]] = []
    for university in universities:
        unitid = str(university.get("unitid") or "")
        if not unitid or unitid not in scorecard or unitid not in ipeds:
            fail(
                f"Official Stage 4B identity join failed for "
                f"{university.get('candidate_id')}"
            )
        score_row = scorecard[unitid]
        hd_row = ipeds[unitid]
        identity_name_variation = (
            score_row.get("INSTNM") != hd_row.get("INSTNM")
        )
        output.append(
            {
                "candidate_id": university["candidate_id"],
                "canonical_id": university["canonical_id"],
                "university_display_name": university["display_name"],
                "known_aliases": university.get("known_aliases", []),
                "unitid": unitid,
                "official_homepage": university.get("official_homepage"),
                "city": university.get("city"),
                "state": university.get("state"),
                "region": university.get("region"),
                "top_5_programs_for_demo": university.get(
                    "top_5_programs_for_demo", []
                ),
                "identity_join": {
                    "method": "reviewed_unitid_exact_join",
                    "confidence": "high",
                    "source_name_variation": identity_name_variation,
                    "scorecard_name": score_row.get("INSTNM"),
                    "ipeds_name": hd_row.get("INSTNM"),
                },
                "scorecard": score_row,
                "ipeds_hd": hd_row,
            }
        )
    if len({row["candidate_id"] for row in output}) != 62:
        fail("Stage 4B official source join produced duplicate candidates")
    return sorted(output, key=lambda row: row["candidate_id"])
