"""Build and formally validate the Stage 2D source-limited candidate."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple


class CandidateValidationError(ValueError):
    """Raised when a candidate violates its non-canonical contract."""


def _anchor_references(record: Dict[str, Any]) -> list[Dict[str, str]]:
    return [
        {
            "record_id": record["record_id"],
            "field": anchor["field"],
            "source_id": anchor["source_id"],
        }
        for anchor in record["evidence_anchors"]
    ]


def _candidate_identity(identity: Dict[str, Any]) -> Dict[str, Any]:
    canonical_identity_id = identity["canonical_identity_id"]
    return {
        "candidate_university_id": (
            f"candidate:{canonical_identity_id.removeprefix('institution:')}"
        ),
        "canonical_identity_id": canonical_identity_id,
        "official_or_normalized_name": identity["official_institution_name"],
        "source_display_names": [],
        "identity_confidence": identity["identity_confidence"],
        "unitid": None,
        "supporting_ranking_records": [],
        "supporting_streams": [],
        "source_ids": [],
        "evidence_anchor_references": [],
        "gap_notes": ["Source-limited and incomplete; not a final universe."],
        "candidate_status": "source_limited_incomplete",
    }


def build_candidate(corpus: Dict[str, Any]) -> Dict[str, Any]:
    """Derive candidates exclusively from verified records in a ready corpus."""
    readiness = corpus.get("readiness", {})
    if readiness.get("universe_candidate_ready") is not True:
        raise CandidateValidationError("Corpus is not ready for candidate generation")
    if readiness.get("universe_generated") is not False:
        raise CandidateValidationError("Candidate input cannot already be a universe")

    mappings = {
        item["record_id"]: item
        for document in corpus["identity_documents"]
        for item in document["mappings"]
    }
    universities: Dict[str, Dict[str, Any]] = {}
    membership_support: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for seed in corpus["seed_batches"]:
        stream = seed["stream"]
        for record in seed["records"]:
            if record["verification_status"] != "verified":
                raise CandidateValidationError("Non-verified record cannot create candidate")
            identity = mappings[record["record_id"]]
            canonical_identity_id = identity["canonical_identity_id"]
            university = universities.setdefault(
                canonical_identity_id, _candidate_identity(identity)
            )
            anchors = _anchor_references(record)
            university["source_display_names"].append(record["school_display_name"])
            university["supporting_ranking_records"].append(record["record_id"])
            university["supporting_streams"].append(stream["stream_id"])
            university["source_ids"].append(record["source"]["source_id"])
            university["evidence_anchor_references"].extend(anchors)

            reason = (
                "national_top_50_candidate"
                if record["ranking_family"] == "national_universities"
                else "program_top_20_candidate"
            )
            key = (canonical_identity_id, reason)
            membership = membership_support.setdefault(
                key,
                {
                    "candidate_university_id": university["candidate_university_id"],
                    "canonical_identity_id": canonical_identity_id,
                    "membership_reason": reason,
                    "supporting_ranking_records": [],
                    "supporting_streams": [],
                    "source_ids": [],
                    "evidence_anchor_references": [],
                },
            )
            membership["supporting_ranking_records"].append(record["record_id"])
            membership["supporting_streams"].append(stream["stream_id"])
            membership["source_ids"].append(record["source"]["source_id"])
            membership["evidence_anchor_references"].extend(anchors)

    for item in [*universities.values(), *membership_support.values()]:
        for key in (
            "source_display_names",
            "supporting_ranking_records",
            "supporting_streams",
            "source_ids",
        ):
            if key in item:
                item[key] = sorted(set(item[key]))

    return {
        "metadata": {
            "record_type": "university_universe_candidate",
            "edition": "2026 Best Colleges",
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
            "final_universe": False,
            "frontend_export": False,
            "selection_memberships": False,
            "frontend_export_generated": False,
            "selection_memberships_generated": False,
        },
        "universities": sorted(
            universities.values(), key=lambda item: item["candidate_university_id"]
        ),
        "memberships": sorted(
            membership_support.values(),
            key=lambda item: (item["candidate_university_id"], item["membership_reason"]),
        ),
        "gap_disclosure": {
            "source_limited": True,
            "incomplete": True,
            "not_final": True,
            "national_top50_incomplete": True,
            "all_streams_incomplete": True,
            "no_verified_stream_count": corpus["gaps"]["no_verified_stream_count"],
            "candidate_university_count": len(universities),
            "frontend_export_allowed": False,
            "final_universe_allowed": False,
            "selection_memberships_allowed": False,
            "national_universities_coverage": "Top-3 pilot only; not Top-50.",
            "not_for_final_product_or_frontend": True,
        },
    }


def _validate_candidate_structure(candidate: Dict[str, Any]) -> None:
    """Low-level structural validation for unit tests; no provenance decision."""
    metadata = candidate.get("metadata", {})
    if any(metadata.get(field) is not True for field in (
        "source_limited", "incomplete", "not_final"
    )):
        raise CandidateValidationError("Candidate metadata lacks truthful scope flags")
    if any(metadata.get(field) is not False for field in (
        "final_universe", "frontend_export", "selection_memberships",
        "frontend_export_generated", "selection_memberships_generated",
    )):
        raise CandidateValidationError("Candidate must not create final outputs")

    universities = candidate.get("universities", [])
    gap = candidate.get("gap_disclosure")
    if not isinstance(gap, dict):
        raise CandidateValidationError("Candidate requires gap disclosure")
    if any(gap.get(field) is not True for field in (
        "source_limited", "incomplete", "not_final", "national_top50_incomplete",
        "all_streams_incomplete",
    )):
        raise CandidateValidationError("Gap disclosure lacks required truthful flags")
    if not isinstance(gap.get("no_verified_stream_count"), int) or gap["no_verified_stream_count"] < 0:
        raise CandidateValidationError("Gap disclosure needs non-negative no-verified count")
    if gap.get("candidate_university_count") != len(universities):
        raise CandidateValidationError("Gap disclosure candidate count mismatch")
    if any(gap.get(field) is not False for field in (
        "frontend_export_allowed", "final_universe_allowed",
        "selection_memberships_allowed",
    )):
        raise CandidateValidationError("Gap disclosure must prohibit final outputs")

    candidate_ids = {item["candidate_university_id"] for item in universities}
    if len(candidate_ids) != len(universities):
        raise CandidateValidationError("Duplicate candidate identity")
    support_by_candidate = {}
    for university in universities:
        required = (
            university.get("supporting_ranking_records"),
            university.get("source_ids"),
            university.get("evidence_anchor_references"),
        )
        if university.get("unitid") is not None or not all(required):
            raise CandidateValidationError("Candidate lacks verified support or guesses UNITID")
        support_by_candidate[university["candidate_university_id"]] = set(
            university["supporting_ranking_records"]
        )

    allowed_reasons = {"national_top_50_candidate", "program_top_20_candidate"}
    for membership in candidate.get("memberships", []):
        candidate_id = membership["candidate_university_id"]
        if candidate_id not in candidate_ids:
            raise CandidateValidationError("Candidate membership has unknown identity")
        if membership["membership_reason"] not in allowed_reasons:
            raise CandidateValidationError("Invalid candidate membership reason")
        required = (
            membership.get("supporting_ranking_records"),
            membership.get("source_ids"),
            membership.get("evidence_anchor_references"),
        )
        if not all(required):
            raise CandidateValidationError("Membership lacks provenance")
        if not set(membership["supporting_ranking_records"]).issubset(
            support_by_candidate[candidate_id]
        ):
            raise CandidateValidationError("Membership cites unsupported ranking record")


def _accepted_corpus_records(corpus: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if corpus.get("readiness", {}).get("universe_candidate_ready") is not True:
        raise CandidateValidationError("Formal validation requires a ready corpus")
    records = {
        record["record_id"]: record
        for seed in corpus["seed_batches"]
        for record in seed["records"]
        if record.get("verification_status") == "verified"
    }
    if not records:
        raise CandidateValidationError("Corpus has no accepted verified records")
    return records


def _validate_corpus_result(
    corpus: Dict[str, Any], corpus_validation_result: Dict[str, Any]
) -> None:
    if not isinstance(corpus_validation_result, dict):
        raise CandidateValidationError("Formal validation requires corpus validation result")
    for key in ("counts", "gaps", "readiness"):
        if corpus_validation_result.get(key) != corpus.get(key):
            raise CandidateValidationError("Corpus validation result does not match revalidated corpus")


def _validate_provenance_rows(
    row: Dict[str, Any],
    accepted_records: Dict[str, Dict[str, Any]],
    expected_identity_id: str,
    expected_reason: str = "",
) -> None:
    record_ids = set(row["supporting_ranking_records"])
    if not record_ids.issubset(accepted_records):
        raise CandidateValidationError("Candidate references non-accepted corpus record")
    for record_id in record_ids:
        record = accepted_records[record_id]
        if expected_identity_id and record["record_id"] != record_id:
            raise CandidateValidationError("Invalid accepted record")
        if expected_reason:
            actual_reason = (
                "national_top_50_candidate"
                if record["ranking_family"] == "national_universities"
                else "program_top_20_candidate"
            )
            if actual_reason != expected_reason:
                raise CandidateValidationError("Membership reason conflicts with corpus record")
    valid_sources = {accepted_records[record_id]["source"]["source_id"] for record_id in record_ids}
    if not set(row["source_ids"]).issubset(valid_sources):
        raise CandidateValidationError("Candidate source ID is not supported by corpus record")
    valid_anchors = {
        (record_id, anchor["field"], anchor["source_id"])
        for record_id in record_ids
        for anchor in accepted_records[record_id]["evidence_anchors"]
    }
    supplied_anchors = {
        (anchor["record_id"], anchor["field"], anchor["source_id"])
        for anchor in row["evidence_anchor_references"]
    }
    if not supplied_anchors.issubset(valid_anchors):
        raise CandidateValidationError("Evidence anchor does not match accepted corpus record")


def validate_candidate(
    candidate: Dict[str, Any],
    corpus: Dict[str, Any],
    corpus_validation_result: Dict[str, Any],
) -> None:
    """Formal, fail-closed candidate validation against a revalidated corpus."""
    _validate_candidate_structure(candidate)
    _validate_corpus_result(corpus, corpus_validation_result)
    if candidate != build_candidate(corpus):
        raise CandidateValidationError(
            "Candidate artifact does not match deterministic corpus generation"
        )
    accepted_records = _accepted_corpus_records(corpus)
    identities = {
        item["record_id"]: item["canonical_identity_id"]
        for document in corpus["identity_documents"]
        for item in document["mappings"]
    }
    for university in candidate["universities"]:
        _validate_provenance_rows(
            university, accepted_records, university["canonical_identity_id"]
        )
        if any(
            identities[record_id] != university["canonical_identity_id"]
            for record_id in university["supporting_ranking_records"]
        ):
            raise CandidateValidationError("Candidate identity conflicts with corpus mapping")
    for membership in candidate["memberships"]:
        _validate_provenance_rows(
            membership,
            accepted_records,
            membership["canonical_identity_id"],
            membership["membership_reason"],
        )
        if any(
            identities[record_id] != membership["canonical_identity_id"]
            for record_id in membership["supporting_ranking_records"]
        ):
            raise CandidateValidationError("Membership identity conflicts with corpus mapping")


def _validation_result(candidate: Dict[str, Any], corpus: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "valid": True,
        "formal_corpus_validation": True,
        "candidate_count": len(candidate["universities"]),
        "membership_count": len(candidate["memberships"]),
        "corpus_verified_record_count": corpus["counts"]["verified_records"],
        "final_universe_generated": False,
        "frontend_export_generated": False,
    }


def write_candidate(
    candidate: Dict[str, Any],
    output: Path,
    corpus: Dict[str, Any],
    corpus_validation_result: Dict[str, Any],
) -> None:
    """Write only after formal corpus-backed validation succeeds."""
    validate_candidate(candidate, corpus, corpus_validation_result)
    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "university-universe-candidate.json": candidate,
        "membership-candidates.json": {"memberships": candidate["memberships"]},
        "candidate-source-map.json": {
            "universities": [
                {
                    "candidate_university_id": item["candidate_university_id"],
                    "source_ids": item["source_ids"],
                    "evidence_anchor_references": item["evidence_anchor_references"],
                }
                for item in candidate["universities"]
            ]
        },
        "candidate-gap-disclosure.json": candidate["gap_disclosure"],
        "candidate-validation-result.json": _validation_result(candidate, corpus),
    }
    for name, payload in payloads.items():
        (output / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def write_candidate_validation_result(
    candidate: Dict[str, Any],
    corpus: Dict[str, Any],
    corpus_validation_result: Dict[str, Any],
    output: Path,
) -> None:
    """Validate an existing artifact and write a formal validation receipt."""
    validate_candidate(candidate, corpus, corpus_validation_result)
    output.write_text(
        json.dumps(_validation_result(candidate, corpus), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
