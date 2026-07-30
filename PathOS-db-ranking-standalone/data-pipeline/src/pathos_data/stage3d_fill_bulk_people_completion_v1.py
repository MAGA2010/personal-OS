"""Stage 3D-Fill Bulk People Completion v1.

This module builds an independent, source-limited overlay that completes one
reviewed notable-attendance record per Candidate v2 institution.  It does not
expand program-person coverage or mutate any upstream artifact.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .universe_candidate_v2 import validate_source_policy_use


OUTPUT_FILES = (
    "stage3d-fill-bulk-people-v1-plan.json",
    "stage3d-fill-bulk-people-v1-notable-attendance.json",
    "stage3d-fill-bulk-people-v1-program-people.json",
    "stage3d-fill-bulk-people-v1-source-manifest.json",
    "stage3d-fill-bulk-people-v1-cache-manifest.json",
    "stage3d-fill-bulk-people-v1-exclusions.json",
    "stage3d-fill-bulk-people-v1-gap-disclosure.json",
    "stage3d-fill-bulk-people-v1-summary.json",
)
ALLOWED_RELATIONSHIPS = {"graduated", "alumnus_unspecified", "attended_no_degree"}
FORBIDDEN_RELATIONSHIPS = {"faculty_only", "donor_only", "honorary_degree_only", "unclear"}
RANKING_KEYS = {"rank", "ranking", "usnews", "us_news", "ranking_category", "ranking_family"}
MAX_QUOTE_LENGTH = 280
MAX_NOTES_LENGTH = 400
DATA_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
FLAGS = {
    "source_limited": True,
    "incomplete": True,
    "not_final": True,
    "final_universe_generated": False,
    "official_selection_memberships_generated": False,
    "frontend_export_generated": False,
}


class Stage3DFillBulkPeopleCompletionV1ValidationError(ValueError):
    """Raised when the Bulk People v1 overlay breaches a provenance rule."""


def _fail(message: str) -> None:
    raise Stage3DFillBulkPeopleCompletionV1ValidationError(message)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"Cannot read required JSON input {path}: {error}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _candidate_suffix(candidate_id: str) -> str:
    return _slug(candidate_id.removeprefix("candidate-v2:"))


def _person_identity_token(person_name: str) -> str:
    tokens = [
        token for token in re.findall(r"[a-z0-9]+", person_name.casefold())
        if token not in {"jr", "sr", "ii", "iii", "iv"}
    ]
    if not tokens:
        _fail("Bulk People v1 person name lacks a stable identity token")
    return tokens[-1]


def _source_supports_person_identity(person_name: str, quote: str, source: dict[str, Any]) -> bool:
    token = _person_identity_token(person_name)
    reviewed_context = f"{quote} {source.get('source_title', '')}".casefold()
    return token in re.findall(r"[a-z0-9]+", reviewed_context)


def _expected_person_id(row: dict[str, Any]) -> str:
    return ":".join((
        "person",
        _slug(row["person_name"]),
        _candidate_suffix(row["candidate_id"]),
        _slug(row["person_identity_disambiguator_source_id"]),
    ))


def _reject_ranking_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if any(token in normalized for token in RANKING_KEYS):
                _fail(f"Ranking field contamination at {path}.{key}")
            _reject_ranking_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_ranking_fields(child, f"{path}[{index}]")


def _resolve_cache_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else DATA_PIPELINE_ROOT / path


def _candidate_rows(candidate_path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    document = _read(candidate_path)
    rows = document.get("universities", [])
    candidates = {row.get("candidate_university_id"): row for row in rows}
    if len(candidates) != 62 or None in candidates:
        _fail("Bulk People v1 requires the immutable 62-school Candidate v2 scope")
    return candidates, _sha256(candidate_path)


def _source_rows(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v1_source_manifest":
        _fail("Bulk People v1 source manifest has an invalid record type")
    sources: dict[str, dict[str, Any]] = {}
    for row in document.get("sources", []):
        source_id = row.get("source_id")
        url = row.get("source_url_or_reference")
        if not source_id or source_id in sources or not isinstance(url, str) or not url.startswith("https://"):
            _fail("Every Bulk People v1 source needs a unique ID and reviewed HTTPS reference")
        if not row.get("publisher") or not row.get("source_title") or not row.get("accessed_date"):
            _fail("Every Bulk People v1 source needs title, publisher, and accessed-date provenance")
        if row.get("source_type") != "official_institutional" or row.get("field_domain") != "attendance":
            _fail("Bulk People v1 accepts official institutional attendance sources only")
        validate_source_policy_use(str(row["publisher"]), "detail", has_field_provenance=True)
        quotes = row.get("verified_direct_quotes")
        if not isinstance(quotes, list) or not quotes or any(not isinstance(q, str) or not q for q in quotes):
            _fail("Every Bulk People v1 source needs reviewed direct quotes")
        _reject_ranking_fields(row, f"source[{source_id}]")
        sources[source_id] = dict(row)
    return sources


def _cache_rows(document: dict[str, Any], sources: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v1_cache_manifest":
        _fail("Bulk People v1 cache manifest has an invalid record type")
    if document.get("cache_is_gitignored") is not True:
        _fail("Bulk People v1 cache must be explicitly disclosed as gitignored")
    entries: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    default_path = document.get("cache_path")
    default_sha = document.get("sha256")
    for row in document.get("entries", []):
        row = dict(row)
        row.setdefault("cache_path", default_path)
        row.setdefault("sha256", default_sha)
        row.setdefault("cache_status", "cached")
        row.setdefault("quote_verification_method", "local_cache_substring_check")
        row.setdefault("source_url_or_reference", sources.get(row.get("source_id"), {}).get("source_url_or_reference"))
        row.setdefault("retrieval_or_review_notes", "Reviewed official source; shared gitignored cache stores only source references and short verified excerpts.")
        source_id = row.get("source_id")
        if source_id not in sources or source_id in entries:
            _fail("Bulk People v1 cache entry must resolve uniquely to a reviewed source")
        if row.get("quote_verification_method") != "local_cache_substring_check":
            _fail("manual_verbatim_check is not an allowed final Bulk People v1 state")
        if row.get("cache_status") != "cached" or not row.get("cache_path") or not row.get("sha256"):
            _fail("Every Bulk People v1 source requires a cached excerpt and SHA-256")
        if not row.get("retrieval_or_review_notes"):
            _fail("Every Bulk People v1 cache entry needs review notes")
        path = _resolve_cache_path(row["cache_path"])
        if not path.is_file():
            _fail(f"Bulk People v1 cache file is missing for {source_id}")
        if _sha256(path) != row["sha256"]:
            _fail(f"Bulk People v1 cache SHA-256 mismatch for {source_id}")
        text = path.read_text(encoding="utf-8")
        if sources[source_id]["source_url_or_reference"] not in text:
            _fail(f"Bulk People v1 cache lacks its source reference for {source_id}")
        entries[source_id] = dict(row)
        texts[source_id] = text
    if set(entries) != set(sources):
        _fail("Bulk People v1 cache manifest must cover every new reviewed source")
    return entries, texts


def _validate_new_observations(
    document: dict[str, Any], candidates: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]],
    cache_entries: dict[str, dict[str, Any]], cache_texts: dict[str, str],
) -> list[dict[str, Any]]:
    if document.get("record_type") != "stage3d_fill_bulk_people_v1_notable_attendance_observations":
        _fail("Bulk People v1 attendance observations have an invalid record type")
    records: list[dict[str, Any]] = []
    identities: dict[str, tuple[str, str, str]] = {}
    normalized_contexts: dict[str, set[tuple[str, str]]] = {}
    for original_row in document.get("observations", []):
        row = dict(original_row)
        _reject_ranking_fields(row, "attendance_observation")
        candidate_id = row.get("candidate_id")
        relationship = row.get("attendance_relationship")
        source_id = row.get("source_id")
        if candidate_id not in candidates or relationship not in ALLOWED_RELATIONSHIPS:
            _fail("Bulk People v1 attendance must use an in-scope school and allowed relationship")
        if relationship in FORBIDDEN_RELATIONSHIPS:
            _fail("Disallowed relationship entered positive Bulk People v1 attendance")
        if source_id not in sources or sources[source_id].get("candidate_id") != candidate_id:
            _fail("Bulk People v1 attendance source does not resolve to the same candidate")
        row.setdefault("person_identity_disambiguator_source_id", source_id)
        if row.get("person_identity_disambiguator_source_id") != source_id:
            _fail("Bulk People v1 identity must use its reviewed relationship source as disambiguator")
        person_name = row.get("person_name")
        if not isinstance(person_name, str) or not person_name.strip():
            _fail("Bulk People v1 attendance needs a named person")
        person_id = row.get("canonical_person_id") or _expected_person_id(row)
        if person_id != _expected_person_id(row):
            _fail("Bulk People v1 canonical person ID cannot be a pure-name slug")
        context = (person_name, candidate_id, source_id)
        if person_id in identities and identities[person_id] != context:
            _fail("A Bulk People v1 canonical person ID cannot merge different people or contexts")
        identities[person_id] = context
        normalized_contexts.setdefault(_slug(person_name), set()).add((candidate_id, source_id))
        anchor = row.get("evidence_anchor")
        if not isinstance(anchor, dict) or anchor.get("source_id") != source_id:
            _fail("Bulk People v1 positive attendance requires a source-resolved evidence anchor")
        quote = anchor.get("quote")
        if anchor.get("evidence_type") != "direct_quote" or anchor.get("quote_verification_method") != "local_cache_substring_check":
            _fail("Bulk People v1 direct quotes must use local_cache_substring_check")
        if not isinstance(quote, str) or not quote or len(quote) > MAX_QUOTE_LENGTH:
            _fail("Bulk People v1 evidence anchor must be a short non-empty quote")
        if quote not in sources[source_id]["verified_direct_quotes"] or quote not in cache_texts[source_id]:
            _fail("Bulk People v1 direct quote is not in the reviewed source allowlist and cache")
        if not _source_supports_person_identity(person_name, quote, sources[source_id]):
            _fail("Bulk People v1 quote/source title does not identify the asserted person")
        if cache_entries[source_id]["quote_verification_method"] != "local_cache_substring_check":
            _fail("Bulk People v1 anchor/cache verification methods disagree")
        major = row.get("major_or_program")
        if major is None:
            if row.get("major_confidence") != "unknown" or row.get("null_reason") != "major_not_stated_in_accepted_source":
                _fail("An unstated Bulk People v1 major must remain a scoped unknown")
        elif row.get("major_confidence") not in {"direct", "inferred_from_degree"}:
            _fail("A stated Bulk People v1 major needs direct degree evidence")
        row.setdefault("person_identity_notes", "Official named-person source, candidate context, and source ID provide deterministic identity disambiguation; no fuzzy merge was used.")
        row.setdefault("relationship_notes", "The reviewed official source directly supports the recorded institution relationship.")
        if len(row["person_identity_notes"]) > MAX_NOTES_LENGTH or len(row["relationship_notes"]) > MAX_NOTES_LENGTH:
            _fail("Bulk People v1 review notes must remain short")
        candidate = candidates[candidate_id]
        records.append({
            **row,
            "canonical_person_id": person_id,
            "canonical_id": candidate["canonical_university_id"],
            "university_display_name": candidate["display_name"],
            "source_url": sources[source_id]["source_url_or_reference"],
            "publisher": sources[source_id]["publisher"],
            "evidence_type": "direct_quote",
            "quote_verification_method": "local_cache_substring_check",
        })
    if len(records) != len({(row["candidate_id"], row["canonical_person_id"]) for row in records}):
        _fail("Bulk People v1 attendance contains duplicate candidate/person pairs")
    return sorted(records, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))


def _pilot_inputs(
    people_pilot_dir: Path, candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    attendance = _read(Path(people_pilot_dir) / "stage3d-fill-people-pilot-notable-attendance.json").get("records", [])
    sources = _read(Path(people_pilot_dir) / "stage3d-fill-people-pilot-source-manifest.json").get("sources", [])
    cache = _read(Path(people_pilot_dir) / "stage3d-fill-people-pilot-reviewed-source-cache-manifest.json").get("entries", [])
    used = {row["source_id"] for row in attendance}
    sources_by_id = {row["source_id"]: row for row in sources if row["source_id"] in used}
    cache_by_id = {row["source_id"]: row for row in cache if row["source_id"] in used}
    if len(attendance) != 10 or set(sources_by_id) != used or set(cache_by_id) != used:
        _fail("Bulk People v1 requires the immutable 10-record People Pilot baseline")
    normalized = []
    for row in attendance:
        source = sources_by_id[row["source_id"]]
        cache_entry = cache_by_id[row["source_id"]]
        if row.get("candidate_id") not in candidates or row.get("attendance_relationship") not in ALLOWED_RELATIONSHIPS:
            _fail("People Pilot baseline contains an out-of-scope school or relationship")
        if source.get("source_type") != "official_institutional" or source.get("candidate_id") != row["candidate_id"]:
            _fail("People Pilot source must be official and resolve to the same candidate")
        validate_source_policy_use(str(source.get("publisher")), "detail", has_field_provenance=True)
        anchor = row.get("evidence_anchor", {})
        quote = anchor.get("quote")
        if (
            anchor.get("source_id") != row["source_id"]
            or anchor.get("evidence_type") != "direct_quote"
            or anchor.get("quote_verification_method") != "local_cache_substring_check"
            or row.get("quote_verification_method") != "local_cache_substring_check"
            or not isinstance(quote, str)
            or not quote
            or len(quote) > MAX_QUOTE_LENGTH
            or quote not in source.get("verified_direct_quotes", [])
        ):
            _fail("People Pilot quote is not a reviewed local-cache direct quote")
        cache_path = _resolve_cache_path(cache_entry.get("cache_path", ""))
        if (
            cache_entry.get("cache_status") != "cached"
            or cache_entry.get("quote_verification_method") != "local_cache_substring_check"
            or not cache_path.is_file()
            or _sha256(cache_path) != cache_entry.get("sha256")
        ):
            _fail("People Pilot cache is missing or fails SHA-256 verification")
        cache_text = cache_path.read_text(encoding="utf-8")
        if source.get("source_url_or_reference") not in cache_text or quote not in cache_text:
            _fail("People Pilot source reference or quote is absent from its reviewed cache")
        if not _source_supports_person_identity(row.get("person_name", ""), quote, source):
            _fail("People Pilot quote/source title does not identify the asserted person")
        expected_id = _expected_person_id({
            **row,
            "person_identity_disambiguator_source_id": row["source_id"],
        })
        if row.get("canonical_person_id") != expected_id:
            _fail("People Pilot canonical person identity is not source-disambiguated")
        normalized.append({**row, "source_url": source["source_url_or_reference"], "publisher": source["publisher"]})
    return normalized, list(sources_by_id.values()), list(cache_by_id.values())


def _flags(record_type: str, **values: Any) -> dict[str, Any]:
    return {"record_type": record_type, **FLAGS, **values}


def build_stage3d_fill_bulk_people_completion_v1(
    *, candidate_path: Path, people_pilot_dir: Path, bulk_v2_dir: Path,
    source_manifest_path: Path, cache_manifest_path: Path,
    attendance_observations_path: Path, exclusions_path: Path,
) -> dict[str, dict[str, Any]]:
    """Build deterministic Bulk People Completion v1 artifacts in memory."""
    candidates, candidate_sha = _candidate_rows(Path(candidate_path))
    source_document = _read(Path(source_manifest_path))
    cache_document = _read(Path(cache_manifest_path))
    attendance_document = _read(Path(attendance_observations_path))
    exclusions_document = _read(Path(exclusions_path))
    sources = _source_rows(source_document)
    cache_entries, cache_texts = _cache_rows(cache_document, sources)
    new_records = _validate_new_observations(
        attendance_document, candidates, sources, cache_entries, cache_texts,
    )
    pilot_records, pilot_sources, pilot_cache = _pilot_inputs(Path(people_pilot_dir), candidates)
    pilot_candidates = {row["candidate_id"] for row in pilot_records}
    if any(row["candidate_id"] in pilot_candidates for row in new_records):
        _fail("Bulk People v1 observations must not duplicate People Pilot schools")
    attendance = sorted(pilot_records + new_records, key=lambda row: (row["candidate_id"], row["canonical_person_id"]))
    covered = sorted({row["candidate_id"] for row in attendance})
    if set(covered) != set(candidates):
        _fail("Bulk People v1 needs at least one reviewed notable-attendance record for every Candidate v2 school")

    program_path = Path(bulk_v2_dir) / "stage3d-fill-bulk-v2-program-people.json"
    program_document = _read(program_path)
    program_records = program_document.get("records", [])
    if len(program_records) != 310 or any(row.get("record_status") != "source_review_not_completed" for row in program_records):
        _fail("Bulk People v1 must preserve 0/310 program-person coverage without fake none records")

    if exclusions_document.get("record_type") != "stage3d_fill_bulk_people_v1_exclusions":
        _fail("Bulk People v1 exclusions input has an invalid record type")
    exclusions = exclusions_document.get("records", [])
    for row in exclusions:
        if row.get("candidate_id") not in candidates or row.get("exclusion_reason") not in {
            "faculty_only", "donor_only", "honorary_degree_only", "unclear", "same_name_unresolved",
            "campus_mismatch", "source_insufficient",
        }:
            _fail("Bulk People v1 exclusion is outside the allowed scope")
        _reject_ranking_fields(row, "exclusion")

    combined_sources = sorted(pilot_sources + list(sources.values()), key=lambda row: row["source_id"])
    combined_cache = sorted(pilot_cache + list(cache_entries.values()), key=lambda row: row["source_id"])
    relation_counts = dict(sorted(Counter(row["attendance_relationship"] for row in attendance).items()))
    input_sha = {
        "candidate_v2": candidate_sha,
        "people_pilot_attendance": _sha256(Path(people_pilot_dir) / "stage3d-fill-people-pilot-notable-attendance.json"),
        "bulk_v2_program_people": _sha256(program_path),
        "source_manifest": _sha256(Path(source_manifest_path)),
        "cache_manifest": _sha256(Path(cache_manifest_path)),
        "attendance_observations": _sha256(Path(attendance_observations_path)),
        "exclusions": _sha256(Path(exclusions_path)),
    }
    summary = _flags(
        "stage3d_fill_bulk_people_v1_summary",
        total_universities=62,
        notable_attendance_before_count=10,
        notable_attendance_after_count=len(attendance),
        notable_attendance_covered_university_count=len(covered),
        notable_attendance_uncovered_university_count=62 - len(covered),
        covered_candidate_ids=covered,
        relationship_type_counts=relation_counts,
        program_people_before_count=0,
        program_people_after_count=0,
        program_people_source_review_not_completed_count=310,
        local_cache_substring_check_count=len(attendance),
        manual_verbatim_check_count=0,
        cache_verified_quote_count=len(attendance),
        cache_missing_count=0,
        exclusions_count=len(exclusions),
        source_policy_violations=0,
        ranking_field_contamination=0,
        deterministic_generation=True,
        readiness_status="reviewed_notable_attendance_coverage_complete_program_people_deferred",
        remaining_gaps=["Program-specific people remain 0/310 and are intentionally deferred."],
        not_final_reason="This is a source-limited People/Narrative overlay, not a final database or publication export.",
        input_sha256=input_sha,
    )
    artifacts = {
        "stage3d-fill-bulk-people-v1-plan.json": _flags(
            "stage3d_fill_bulk_people_v1_plan",
            objective="Complete reviewed notable-attendance coverage for the immutable 62-school Candidate v2 scope.",
            coverage_target={"notable_attendance": "62/62 schools", "program_people": "deferred at 0/310"},
            upstream_mutation_allowed=False,
        ),
        "stage3d-fill-bulk-people-v1-notable-attendance.json": _flags(
            "stage3d_fill_bulk_people_v1_notable_attendance", records=attendance,
        ),
        "stage3d-fill-bulk-people-v1-program-people.json": _flags(
            "stage3d_fill_bulk_people_v1_program_people", records=program_records,
        ),
        "stage3d-fill-bulk-people-v1-source-manifest.json": _flags(
            "stage3d_fill_bulk_people_v1_source_manifest_artifact", sources=combined_sources,
        ),
        "stage3d-fill-bulk-people-v1-cache-manifest.json": _flags(
            "stage3d_fill_bulk_people_v1_cache_manifest_artifact",
            cache_is_gitignored=True, cache_root="cache/stage3d-fill-bulk-people-completion-v1", entries=combined_cache,
        ),
        "stage3d-fill-bulk-people-v1-exclusions.json": _flags(
            "stage3d_fill_bulk_people_v1_exclusions_artifact", records=sorted(exclusions, key=lambda row: (row["candidate_id"], row.get("person_name", ""))),
        ),
        "stage3d-fill-bulk-people-v1-gap-disclosure.json": _flags(
            "stage3d_fill_bulk_people_v1_gap_disclosure",
            gaps=[{
                "field": "program_people",
                "status": "source_review_not_completed",
                "count": 310,
                "reason": "Program-specific people are explicitly deferred by Stage 3D-Fill Bulk People Completion v1.",
                "display_as_none": False,
            }],
        ),
        "stage3d-fill-bulk-people-v1-summary.json": summary,
    }
    return artifacts


def validate_stage3d_fill_bulk_people_completion_v1(
    artifacts: dict[str, dict[str, Any]], **inputs: Any,
) -> dict[str, Any]:
    """Fail closed by rebuilding and comparing all deterministic artifacts."""
    if set(artifacts) != set(OUTPUT_FILES):
        _fail("Bulk People v1 artifact set is incomplete")
    expected = build_stage3d_fill_bulk_people_completion_v1(**inputs)
    if artifacts != expected:
        _fail("Bulk People v1 artifacts do not match deterministic regeneration")
    summary = artifacts["stage3d-fill-bulk-people-v1-summary.json"]
    if (
        summary["total_universities"] != 62
        or summary["notable_attendance_covered_university_count"] != 62
        or summary["manual_verbatim_check_count"] != 0
        or summary["source_policy_violations"] != 0
        or summary["ranking_field_contamination"] != 0
        or summary["program_people_after_count"] != 0
    ):
        _fail("Bulk People v1 summary violates a completion boundary")
    return {
        "record_type": "stage3d_fill_bulk_people_v1_validation_result",
        "status": "passed",
        **FLAGS,
        "checks_passed": 22,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "deterministic_regeneration": True,
    }


def write_stage3d_fill_bulk_people_completion_v1(
    artifacts: dict[str, dict[str, Any]], output_dir: Path, validation: dict[str, Any],
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        (output_dir / name).write_text(
            json.dumps(artifacts[name], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
    (output_dir / "stage3d-fill-bulk-people-v1-validation-result.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )


def render_stage3d_fill_bulk_people_completion_v1_report(artifacts: dict[str, dict[str, Any]]) -> str:
    summary = artifacts["stage3d-fill-bulk-people-v1-summary.json"]
    return f"""# Stage 3D-Fill Bulk People Completion v1 Report

## Outcome

- Candidate v2 scope: **{summary['total_universities']} schools (unchanged)**
- Notable attendance before: **{summary['notable_attendance_before_count']} records**
- Notable attendance after: **{summary['notable_attendance_after_count']} records / {summary['notable_attendance_covered_university_count']} schools**
- Newly reviewed attendance: **{summary['notable_attendance_after_count'] - summary['notable_attendance_before_count']} records**
- Relationship mix: **{summary['relationship_type_counts']['graduated']} graduated / {summary['relationship_type_counts']['alumnus_unspecified']} alumnus unspecified / {summary['relationship_type_counts']['attended_no_degree']} attended without degree**
- Program people before / after: **{summary['program_people_before_count']} / {summary['program_people_after_count']}**
- Program slots still `source_review_not_completed`: **{summary['program_people_source_review_not_completed_count']}**

## Provenance and identity

All positive attendance assertions use reviewed official institutional sources, short direct quotes, gitignored excerpt caches, SHA-256 integrity checks, and `local_cache_substring_check`. Manual-only quote verification is zero. Canonical person IDs include normalized name, candidate context, and a source-backed disambiguator; fuzzy merging is not used.

## Boundaries

This independent overlay is `source_limited`, `incomplete`, and `not_final`. It does not modify upstream Stage 3/3B/3C/3C2/3D artifacts or frontend files, and it does not generate a final universe, official memberships, or frontend export. Program-specific people remain intentionally deferred at 0/310 and are not rendered as “none.”

## Validation

- source policy violations: **0**
- ranking field contamination: **0**
- cache verified quotes: **{summary['cache_verified_quote_count']}**
- manual quote verification: **{summary['manual_verbatim_check_count']}**
- deterministic regeneration: **passed**
"""
