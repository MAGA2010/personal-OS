"""Read-only loader for the explicit Stage 5 frozen-input allowlist."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from pathos_data.stage3d_closing_hardening import load_cumulative_state

from .config import INPUT_PATHS, Stage5ContractError, index_by, read_json


def _read_required(repo_root: Path, relative_path: str) -> Any:
    path = repo_root / relative_path
    if not path.is_file():
        raise Stage5ContractError("Missing frozen Stage 5 input: {}".format(relative_path))
    return read_json(path)


def _university_index(document: Dict[str, Any], key: str = "candidate_id") -> Dict[str, Dict[str, Any]]:
    return index_by(document.get("universities", []), key)


def _ranking_source_manifests(repo_root: Path) -> List[Dict[str, Any]]:
    root = repo_root / "data-pipeline/data/ranking-seeds"
    documents = []
    if root.is_dir():
        for path in sorted(root.rglob("source-manifest.json")):
            relative = path.relative_to(repo_root).as_posix()
            documents.append({"path": relative, "document": read_json(path)})
    return documents


def _people_input_paths(repo_root: Path) -> List[str]:
    pipeline = repo_root / "data-pipeline"
    paths = []
    for number, directory, prefix in (
        (1, "stage3d-fill-bulk-completion-wave1", "stage3d-fill-bulk-completion-wave1"),
        (2, "stage3d-fill-bulk-completion-wave2", "stage3d-fill-bulk-completion-wave2"),
        (3, "stage3d-fill-bulk-completion-wave3", "stage3d-fill-bulk-completion-wave3"),
        (4, "stage3d-fill-program-people-wave4", "stage3d-fill-program-people-wave4"),
        (5, "stage3d-fill-program-people-wave5", "stage3d-fill-program-people-wave5"),
        (6, "stage3d-fill-program-people-wave6", "stage3d-fill-program-people-wave6"),
        (7, "stage3d-fill-program-people-wave7", "stage3d-fill-program-people-wave7"),
        (8, "stage3d-fill-program-people-wave8", "stage3d-fill-program-people-wave8"),
        (9, "stage3d-fill-program-people-wave9", "stage3d-fill-program-people-wave9"),
        (10, "stage3d-fill-program-people-wave10", "stage3d-fill-program-people-wave10"),
    ):
        del number
        base = pipeline / "artifacts" / directory
        for suffix in ("program-people", "source-manifest", "gap-disclosure", "summary"):
            path = base / "{}-{}.json".format(prefix, suffix)
            if not path.is_file():
                raise Stage5ContractError("Missing approved Stage 3D people input: {}".format(path))
            paths.append(path.relative_to(repo_root).as_posix())
    return sorted(paths)


def load_stage5_inputs(repo_root: Path) -> Dict[str, Any]:
    """Load only committed, deterministic artifacts; never cache bodies or handoff."""
    repo_root = Path(repo_root).resolve()
    documents = {
        name: _read_required(repo_root, relative_path)
        for name, relative_path in INPUT_PATHS.items()
    }
    people_state = load_cumulative_state(repo_root / "data-pipeline")
    ranking_manifests = _ranking_source_manifests(repo_root)
    people_paths = _people_input_paths(repo_root)

    generated_from = sorted(
        list(INPUT_PATHS.values())
        + people_paths
        + [item["path"] for item in ranking_manifests]
    )
    forbidden = ("/raw/", "/staging/", "/handoff/", "/cache/", "frontend", "fixture")
    for relative_path in generated_from:
        lowered = "/{}/".format(relative_path.lower().strip("/"))
        if any(token in lowered for token in forbidden):
            raise Stage5ContractError(
                "Forbidden Stage 5 generation dependency: {}".format(relative_path)
            )

    stage4b_validation = documents["stage4b_validation"]
    stage4c_validation = documents["stage4c_validation"]
    stage4c_summary = documents["stage4c_summary"]
    if (
        stage4b_validation.get("passed_check_count") != 60
        or stage4b_validation.get("failed_check_count") != 0
    ):
        raise Stage5ContractError("Stage 4B checkpoint is not 60/60 PASS")
    if (
        stage4c_validation.get("passed_check_count") != 86
        or stage4c_validation.get("failed_check_count") != 0
    ):
        raise Stage5ContractError("Stage 4C checkpoint is not 86/86 PASS")
    if stage4c_summary.get("schools") != 62:
        raise Stage5ContractError("Stage 4C school scope is not 62")
    if stage4c_summary.get("cumulative_verified_record_count") != 904:
        raise Stage5ContractError("Stage 4C cumulative verified boundary is not 904")

    candidates = index_by(
        documents["candidate_identities"].get("universities", []),
        "candidate_university_id",
    )
    marker = _university_index(documents["stage4b_marker"], "university_id")
    expected_ids = set(candidates)
    if set(marker) != expected_ids or len(expected_ids) != 62:
        raise Stage5ContractError("Candidate v2 and Stage 4B marker identities differ")

    return {
        "repo_root": repo_root,
        "documents": documents,
        "generated_from": generated_from,
        "ranking_source_manifests": ranking_manifests,
        "people_state": people_state,
        "indexes": {
            "candidates": candidates,
            "stage3b_universities": _university_index(documents["stage3b_universities"]),
            "all_majors": _university_index(documents["stage3c_all_majors"]),
            "marker": marker,
            "profiles": _university_index(documents["stage4b_profiles"]),
            "admissions": _university_index(documents["stage4b_admissions"]),
            "geography4b": _university_index(documents["stage4b_geography"]),
            "comparison": _university_index(documents["stage4b_comparison"], "university_id"),
            "enrollment": _university_index(documents["stage4c_enrollment"]),
            "test_policy": _university_index(documents["stage4c_test_policy"]),
            "english_policy": _university_index(documents["stage4c_english_policy"]),
            "sat_act": _university_index(documents["stage4c_sat_act"]),
            "chinese_names": _university_index(documents["stage4c_chinese_names"]),
            "places": _university_index(documents["stage4c_places"]),
            "rankings": _university_index(documents["stage4c_rankings"]),
            "history": _university_index(documents["narrative_history"]),
            "anecdotes": _university_index(documents["narrative_anecdotes"]),
        },
    }
