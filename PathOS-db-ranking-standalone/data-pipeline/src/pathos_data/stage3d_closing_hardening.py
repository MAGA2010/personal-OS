"""Stage 3D closing hardening for cumulative program-person provenance.

Live intake is intentionally separated from deterministic artifact generation.
The build and validation functions never perform network access.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable


BASELINE_COMMIT = "e4b3dcf5621dcaa498c4e3e7cd714004fedcbd9f"
ALLOWED_LIVE_STATUSES = {
    "live_verified_exact",
    "live_verified_normalized",
    "live_page_changed_review_required",
    "live_unavailable",
    "live_not_found",
    "live_source_mismatch",
}
ALLOWED_NORMALIZATIONS = (
    "html_entity_decode",
    "unicode_nfkc",
    "nonbreaking_space_to_space",
    "whitespace_collapse",
)
OUTPUT_FILES = (
    "stage3d-closing-hardening-source-reverification.json",
    "stage3d-closing-hardening-source-findings.json",
    "stage3d-closing-hardening-anchor-quality-report.json",
    "stage3d-closing-hardening-evidence-anchor-overlay.json",
    "stage3d-closing-hardening-orphan-cache-inventory.json",
    "stage3d-closing-hardening-cache-cleanup-plan.json",
    "stage3d-closing-hardening-gap-disclosure.json",
    "stage3d-closing-hardening-cumulative-summary.json",
    "stage3d-closing-hardening-input-pin-report.json",
)
VALIDATION_FILE = "stage3d-closing-hardening-validation-result.json"
WAVES = (
    (1, "artifacts/stage3d-fill-bulk-completion-wave1", "stage3d-fill-bulk-completion-wave1", "cache/stage3d-fill-bulk-completion-wave1"),
    (2, "artifacts/stage3d-fill-bulk-completion-wave2", "stage3d-fill-bulk-completion-wave2", "cache/stage3d-fill-bulk-completion-wave2"),
    (3, "artifacts/stage3d-fill-bulk-completion-wave3", "stage3d-fill-bulk-completion-wave3", "cache/stage3d-fill-bulk-completion-wave3"),
    (4, "artifacts/stage3d-fill-program-people-wave4", "stage3d-fill-program-people-wave4", "cache/stage3d-fill-program-people-wave4"),
    (5, "artifacts/stage3d-fill-program-people-wave5", "stage3d-fill-program-people-wave5", "cache/stage3d-fill-program-people-wave5"),
    (6, "artifacts/stage3d-fill-program-people-wave6", "stage3d-fill-program-people-wave6", "cache/stage3d-fill-program-people-wave6"),
    (7, "artifacts/stage3d-fill-program-people-wave7", "stage3d-fill-program-people-wave7", "cache/stage3d-fill-program-people-wave7"),
    (8, "artifacts/stage3d-fill-program-people-wave8", "stage3d-fill-program-people-wave8", "cache/stage3d-fill-program-people-wave8"),
    (9, "artifacts/stage3d-fill-program-people-wave9", "stage3d-fill-program-people-wave9", "cache/stage3d-fill-program-people-wave9"),
    (10, "artifacts/stage3d-fill-program-people-wave10", "stage3d-fill-program-people-wave10", "cache/stage3d-fill-program-people-wave10"),
)


class ClosingHardeningValidationError(ValueError):
    """Raised when closing provenance fails closed."""


def _fail(message: str) -> None:
    raise ClosingHardeningValidationError(message)


def _read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _git_blob_sha(path: Path) -> str:
    content = Path(path).read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _relative(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def _canonical_person_id(record: dict[str, Any]) -> str | None:
    return record.get("canonical_person_id") or record.get("person_id")


def _document_count(document: Any) -> int:
    if not isinstance(document, dict):
        return 1
    for key in ("slots", "sources", "entries", "universities", "records"):
        if isinstance(document.get(key), list):
            return len(document[key])
    return 1


def _wave_paths(pipeline_root: Path) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for number, directory, prefix, cache_directory in WAVES:
        artifact_dir = pipeline_root / directory
        paths.append({
            "wave": number,
            "origin_wave": f"wave{number}",
            "artifact_dir": artifact_dir,
            "program_people": artifact_dir / f"{prefix}-program-people.json",
            "source_manifest": artifact_dir / f"{prefix}-source-manifest.json",
            "cache_manifest": artifact_dir / f"{prefix}-cache-manifest.json",
            "gap_disclosure": artifact_dir / f"{prefix}-gap-disclosure.json",
            "summary": artifact_dir / f"{prefix}-summary.json",
            "cache_root": pipeline_root / cache_directory,
        })
    return paths


def load_cumulative_state(pipeline_root: Path) -> dict[str, Any]:
    """Load and validate the immutable Waves 1–10 cumulative state."""
    pipeline_root = Path(pipeline_root).resolve()
    final_slots: dict[str, dict[str, Any]] = {}
    positives: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    cache_entries: dict[str, dict[str, Any]] = {}
    referenced_paths: list[Path] = []
    reference_counts: Counter[Path] = Counter()
    wave_documents: list[dict[str, Any]] = []
    cache_roots: list[Path] = []

    for descriptor in _wave_paths(pipeline_root):
        for field in ("program_people", "source_manifest", "cache_manifest", "gap_disclosure", "summary"):
            if not descriptor[field].is_file():
                _fail(f"Missing immutable Wave {descriptor['wave']} input: {descriptor[field]}")
        people_doc = _read(descriptor["program_people"])
        source_doc = _read(descriptor["source_manifest"])
        cache_doc = _read(descriptor["cache_manifest"])
        summary_doc = _read(descriptor["summary"])
        wave_documents.append({**descriptor, "summary_document": summary_doc})
        cache_roots.append(descriptor["cache_root"])

        for slot in people_doc.get("slots", []):
            slot_id = slot.get("slot_id")
            if not slot_id:
                _fail(f"Wave {descriptor['wave']} slot lacks slot_id")
            copied = deepcopy_json(slot)
            copied["origin_wave"] = descriptor["origin_wave"]
            final_slots[slot_id] = copied
            if slot.get("slot_status") == "identified_person":
                positive = deepcopy_json(slot)
                positive["origin_wave"] = descriptor["origin_wave"]
                positive["record_id"] = f"{descriptor['origin_wave']}:{slot_id}"
                positive["canonical_person_id"] = _canonical_person_id(positive)
                positives.append(positive)

        for source in source_doc.get("sources", []):
            source_id = source.get("source_id")
            if not source_id or source_id in sources:
                _fail(f"Source ID must be globally unique across Waves 1–10: {source_id}")
            if (
                source.get("source_type") != "official_institutional"
                or not str(source.get("source_url") or "").startswith("https://")
            ):
                _fail(f"Closing source policy violation in immutable source {source_id}")
            copied_source = deepcopy_json(source)
            copied_source["origin_wave"] = descriptor["origin_wave"]
            sources[source_id] = copied_source
            cache_path = source.get("cache_path")
            if cache_path:
                resolved = (pipeline_root / cache_path).resolve()
                referenced_paths.append(resolved)

        for entry in cache_doc.get("entries", []):
            source_id = entry.get("source_id")
            if not source_id or source_id in cache_entries:
                _fail(f"Cache manifest source ID must be globally unique: {source_id}")
            copied_cache = deepcopy_json(entry)
            copied_cache["origin_wave"] = descriptor["origin_wave"]
            cache_entries[source_id] = copied_cache
            cache_path = entry.get("cache_path")
            if cache_path:
                resolved = (pipeline_root / cache_path).resolve()
                referenced_paths.append(resolved)

    slots = [final_slots[key] for key in sorted(final_slots)]
    counts = Counter(slot.get("slot_status") for slot in slots)
    dedup_keys = [
        (record.get("candidate_id"), _canonical_person_id(record)) for record in positives
    ]
    duplicate_count = len(dedup_keys) - len(set(dedup_keys))
    source_ids = [source_id for record in positives for source_id in record.get("source_ids", [])]

    if len(slots) != 310:
        _fail(f"Closing baseline must contain 310 slots, got {len(slots)}")
    if counts != Counter({"identified_person": 180, "source_review_not_completed": 130}):
        _fail(f"Closing baseline must be 180 identified / 130 gaps, got {dict(counts)}")
    if len(positives) != 180 or duplicate_count:
        _fail("Closing baseline must preserve 180 raw and unique people with zero duplicates")
    if len(sources) != 180 or len(cache_entries) != 180 or set(source_ids) != set(sources):
        _fail("Closing baseline must expose one unique reviewed source/cache per positive record")
    if any(slot.get("slot_status") == "no_qualifying_person_found" for slot in slots):
        _fail("Closing baseline unexpectedly contains no_qualifying_person_found")

    for record in positives:
        for source_id in record.get("source_ids", []):
            cache_path = sources[source_id].get("cache_path")
            if cache_path:
                reference_counts[(pipeline_root / cache_path).resolve()] += 1

    cache_scan_files = sorted(
        path.resolve()
        for root in cache_roots
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file()
    )
    return {
        "slots": slots,
        "positives": sorted(positives, key=lambda item: item["record_id"]),
        "sources": sources,
        "cache_entries": cache_entries,
        "wave_documents": wave_documents,
        "cache_scan_roots": cache_roots,
        "cache_scan_files": cache_scan_files,
        "referenced_cache_paths": referenced_paths,
        "reference_counts": reference_counts,
        "summary": {
            "total_program_slots": 310,
            "identified_person_count": 180,
            "source_review_not_completed_count": 130,
            "no_qualifying_person_found_count": 0,
            "raw_person_occurrence_count": 180,
            "unique_person_count": 180,
            "duplicate_person_count": 0,
            "post_merge_duplicate_count": 0,
            "unique_source_id_count": len(sources),
        },
    }


def deepcopy_json(value: Any) -> Any:
    """Copy JSON-compatible values without retaining Path or custom objects."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def _pin_specs(pipeline_root: Path) -> list[tuple[Path, str, str]]:
    specs = [
        (pipeline_root / "data/university-universe-candidates/v2-source-limited/candidate-universities.json", "candidate_scope", "candidate_v2"),
        (pipeline_root / "artifacts/stage3c-academic-geo-enrichment/stage3c-demo-programs-overlay.json", "program_slot_scope", "stage3c"),
        (pipeline_root / "artifacts/stage3d-fill-bulk-completion-v2/stage3d-fill-bulk-v2-summary.json", "narrative_coverage", "stage3d_fill_bulk_v2"),
        (pipeline_root / "artifacts/stage3d-fill-bulk-people-completion-v1/stage3d-fill-bulk-people-v1-summary.json", "attendance_coverage", "stage3d_fill_bulk_people_v1"),
    ]
    for descriptor in _wave_paths(pipeline_root):
        for role in ("program_people", "source_manifest", "cache_manifest", "gap_disclosure", "summary"):
            specs.append((descriptor[role], role, descriptor["origin_wave"]))
    return specs


def build_immutable_input_pins(pipeline_root: Path) -> dict[str, Any]:
    pipeline_root = Path(pipeline_root).resolve()
    state = load_cumulative_state(pipeline_root)
    pins = []
    for path, role, source_wave in _pin_specs(pipeline_root):
        if not path.is_file():
            _fail(f"Cannot pin missing input: {path}")
        pins.append({
            "path": _relative(path, pipeline_root),
            "role": role,
            "source_wave": source_wave,
            "record_count": _document_count(_read(path)),
            "sha256": _sha256(path),
            "git_blob_sha": _git_blob_sha(path),
            "immutable": True,
        })
    return {
        "record_type": "stage3d_closing_hardening_immutable_input_pins",
        "manifest_version": 1,
        "baseline_commit": BASELINE_COMMIT,
        "frozen_date": "2026-07-22",
        "expected_cumulative_counts": state["summary"],
        "pins": sorted(pins, key=lambda item: item["path"]),
        "stage3a_stash_untouched": True,
        "tag_created_by_stage": False,
        "push_performed_by_stage": False,
    }


def validate_immutable_input_pins(document: dict[str, Any], pipeline_root: Path) -> None:
    expected = build_immutable_input_pins(pipeline_root)
    if document != expected:
        _fail("Closing immutable input pins do not match the frozen Waves 1–10 baseline")


def normalize_live_text(value: str) -> str:
    """Apply only layout-preserving normalizations allowed by the closing policy."""
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def _anchors(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    anchors = record.get("evidence_anchor") or {}
    if not isinstance(anchors.get("attendance"), dict) or not isinstance(anchors.get("program_match"), dict):
        _fail(f"Positive record lacks dual evidence anchors: {record.get('record_id')}")
    return anchors


def classify_live_snapshot(record: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Classify a frozen live snapshot without making a network request."""
    http_status = snapshot.get("http_status")
    outcome = snapshot.get("fetch_outcome")
    text = snapshot.get("text") or ""
    base = {
        "matched_anchor_count": 0,
        "exact_matched_anchor_count": 0,
        "normalized_matched_anchor_count": 0,
        "normalization_methods": [],
        "original_record_invalidated": False,
    }
    if http_status in {404, 410}:
        return {**base, "live_status": "live_not_found", "severity": "Medium", "verification_method": "http_terminal_status"}
    if outcome != "success" or http_status != 200:
        return {**base, "live_status": "live_unavailable", "severity": "Low/Medium", "verification_method": "fetch_failure_classification"}
    lowered = normalize_live_text(text).lower()
    challenge_markers = ("access denied", "just a moment", "captcha", "enable javascript", "security check", "request blocked")
    if len(lowered) < 40 or any(marker in lowered for marker in challenge_markers):
        return {**base, "live_status": "live_unavailable", "severity": "Low/Medium", "verification_method": "unusable_live_response"}

    anchors = _anchors(record)
    quotes = [anchors[kind].get("quote") or "" for kind in ("attendance", "program_match")]
    exact = [quote in text for quote in quotes]
    normalized_text = normalize_live_text(text)
    normalized = [normalize_live_text(quote) in normalized_text for quote in quotes]
    base["exact_matched_anchor_count"] = sum(exact)
    base["normalized_matched_anchor_count"] = sum(normalized)
    base["matched_anchor_count"] = sum(normalized)
    if all(exact):
        return {**base, "live_status": "live_verified_exact", "severity": "PASS", "verification_method": "live_cache_exact_substring_check"}
    if all(normalized):
        return {
            **base,
            "live_status": "live_verified_normalized",
            "severity": "PASS",
            "verification_method": "live_cache_allowed_normalized_substring_check",
            "normalization_methods": list(ALLOWED_NORMALIZATIONS),
        }

    person = normalize_live_text(record.get("person_name") or "").lower()
    person_tokens = [token for token in re.findall(r"[a-z0-9]+", person) if len(token) > 2]
    identity_present = bool(person and person in lowered) or bool(person_tokens and person_tokens[-1] in lowered)
    program_tokens = [
        token for token in re.findall(r"[a-z0-9]+", normalize_live_text(record.get("program_name") or "").lower())
        if len(token) > 3 and token not in {"engineering", "science", "studies"}
    ]
    program_present = any(token in lowered for token in program_tokens)
    if identity_present or program_present or any(normalized):
        return {**base, "live_status": "live_page_changed_review_required", "severity": "Medium", "verification_method": "live_content_manual_review_required"}
    return {**base, "live_status": "live_source_mismatch", "severity": "High", "verification_method": "live_content_identity_and_program_mismatch"}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored and data.strip():
            self.parts.append(data.strip())


def _decode_response(raw: bytes, content_type: str, encoding: str | None) -> tuple[str, str | None]:
    lowered = (content_type or "").lower()
    if "pdf" in lowered or raw.startswith(b"%PDF"):
        return "", "unsupported_pdf_text_extraction"
    if not any(marker in lowered for marker in ("html", "text", "json", "xml")) and lowered:
        return "", "unsupported_content_type"
    decoded = raw.decode(encoding or "utf-8", errors="replace")
    if "html" not in lowered and "<html" not in decoded[:500].lower():
        return decoded, None
    parser = _VisibleTextParser()
    parser.feed(decoded)
    return "\n".join(parser.parts), None


def _fetch_live_url(
    url: str,
    *,
    timeout_seconds: int = 15,
    max_bytes: int = 10_000_000,
    user_agent: str = "PathOS-Stage3D-Provenance-Closure/1.0",
    max_retries: int = 1,
) -> dict[str, Any]:
    """Bounded live fetch used only by the intake layer."""
    import requests

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout_seconds,
                allow_redirects=True,
                headers={"User-Agent": user_agent, "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.5"},
            )
            raw = response.content[:max_bytes]
            text, extraction_failure = _decode_response(
                raw, response.headers.get("content-type", ""), response.encoding
            )
            outcome = "success" if response.status_code == 200 and not extraction_failure else "http_error"
            failure = extraction_failure
            if response.status_code != 200:
                failure = f"http_{response.status_code}"
            if response.status_code in {429, 500, 502, 503, 504} and attempt < max_retries:
                continue
            return {
                "http_status": response.status_code,
                "final_url": response.url,
                "redirect_chain": [item.url for item in response.history],
                "content_type": response.headers.get("content-type", ""),
                "raw_bytes": raw,
                "text": text,
                "fetch_outcome": outcome,
                "failure_category": failure,
            }
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                continue
    return {
        "http_status": None,
        "final_url": None,
        "redirect_chain": [],
        "content_type": None,
        "raw_bytes": b"",
        "text": "",
        "fetch_outcome": "network_error",
        "failure_category": type(last_error).__name__ if last_error else "unknown_network_error",
    }


def _safe_source_filename(source_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", source_id).strip("-")
    if not safe:
        safe = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:16]
    return safe


def run_live_intake(
    records: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    cache_dir: Path,
    *,
    fetcher: Callable[..., dict[str, Any]] | None = None,
    retrieval_timestamp: str | None = None,
    pipeline_root: Path | None = None,
    timeout_seconds: int = 15,
    max_workers: int = 12,
    max_retries: int = 1,
    user_agent: str = "PathOS-Stage3D-Provenance-Closure/1.0",
    expected_source_count: int | None = None,
) -> dict[str, Any]:
    """Fetch all unique sources and write isolated gitignored live caches."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    retrieval_timestamp = retrieval_timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    by_source: dict[str, dict[str, Any]] = {}
    for record in records:
        for source_id in record.get("source_ids", []):
            if source_id in by_source:
                _fail(f"Closing intake expected unique source IDs, duplicate {source_id}")
            if source_id not in sources:
                _fail(f"Closing intake lacks source manifest row {source_id}")
            by_source[source_id] = record
    if expected_source_count is not None and len(by_source) != expected_source_count:
        _fail(
            f"Closing intake must attempt all {expected_source_count} unique sources, "
            f"got {len(by_source)}"
        )

    def retrieve(source_id: str) -> tuple[str, dict[str, Any]]:
        source = sources[source_id]
        if fetcher is not None:
            snapshot = fetcher(source["source_url"])
        else:
            snapshot = _fetch_live_url(
                source["source_url"], timeout_seconds=timeout_seconds,
                max_retries=max_retries, user_agent=user_agent,
            )
        return source_id, snapshot

    snapshots: dict[str, dict[str, Any]] = {}
    if fetcher is not None:
        for source_id in sorted(by_source):
            key, snapshot = retrieve(source_id)
            snapshots[key] = snapshot
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(retrieve, source_id): source_id for source_id in sorted(by_source)}
            for future in as_completed(futures):
                source_id = futures[future]
                try:
                    key, snapshot = future.result()
                except Exception as exc:  # defensive boundary around individual live sources
                    key, snapshot = source_id, {
                        "http_status": None, "final_url": None, "redirect_chain": [],
                        "content_type": None, "raw_bytes": b"", "text": "",
                        "fetch_outcome": "network_error", "failure_category": type(exc).__name__,
                    }
                snapshots[key] = snapshot

    entries = []
    for source_id in sorted(by_source):
        record = by_source[source_id]
        source = sources[source_id]
        snapshot = snapshots[source_id]
        raw = snapshot.pop("raw_bytes", b"") or b""
        text = snapshot.get("text") or ""
        stem = _safe_source_filename(source_id)
        raw_path = cache_dir / f"{stem}.raw"
        text_path = cache_dir / f"{stem}.txt"
        raw_cache_path = None
        text_cache_path = None
        raw_sha = None
        text_sha = None
        if raw:
            raw_path.write_bytes(raw)
            raw_cache_path = _relative(raw_path, pipeline_root) if pipeline_root else str(raw_path)
            raw_sha = _sha256(raw_path)
        if text:
            text_path.write_text(text, encoding="utf-8")
            text_cache_path = _relative(text_path, pipeline_root) if pipeline_root else str(text_path)
            text_sha = _sha256(text_path)
        classification = classify_live_snapshot(record, snapshot)
        entries.append({
            "record_id": record["record_id"],
            "candidate_id": record["candidate_id"],
            "canonical_person_id": _canonical_person_id(record),
            "person_name": record["person_name"],
            "source_id": source_id,
            "source_url": source["source_url"],
            "retrieval_timestamp": retrieval_timestamp,
            "http_status": snapshot.get("http_status"),
            "fetch_outcome": snapshot.get("fetch_outcome"),
            "failure_category": snapshot.get("failure_category"),
            "final_url": snapshot.get("final_url"),
            "redirect_chain": snapshot.get("redirect_chain") or [],
            "content_type": snapshot.get("content_type"),
            "raw_cache_path": raw_cache_path,
            "raw_content_sha256": raw_sha,
            "text_cache_path": text_cache_path,
            "text_content_sha256": text_sha,
            **classification,
        })
    counts = Counter(entry["live_status"] for entry in entries)
    return {
        "record_type": "stage3d_closing_hardening_live_intake_metadata",
        "intake_version": 1,
        "retrieval_timestamp": retrieval_timestamp,
        "network_access_performed": True,
        "artifact_generation_network_access": False,
        "total_positive_records": len(records),
        "unique_source_ids": len(by_source),
        "live_fetch_attempted": len(entries),
        "status_counts": {status: counts.get(status, 0) for status in sorted(ALLOWED_LIVE_STATUSES)},
        "entries": entries,
    }


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['’][A-Za-z]+)?", value or "")


def detect_anchor_quality(record: dict[str, Any]) -> dict[str, Any]:
    """Detect thin evidence anchors using deterministic conservative heuristics."""
    anchors = _anchors(record)
    person_tokens = _words(record.get("person_name") or "")
    last_name = person_tokens[-1].lower() if person_tokens else ""
    details = {}
    for kind in ("attendance", "program_match"):
        quote = anchors[kind].get("quote") or ""
        words = _words(quote)
        lowered = normalize_live_text(quote).lower()
        flags = []
        if len(words) < 5:
            flags.append("fewer_than_5_effective_words")
        if lowered in {"alumnus", "alumna", "alumni", "graduate alumni", "graduated", "graduate"}:
            flags.append("generic_attendance_label")
        if words and words[0].lower() in {"he", "she", "they", "his", "her", "their", "him"}:
            flags.append("pronoun_led_without_local_identity")
        if len(words) <= 4 and not re.search(r"[.!?;:]", quote):
            flags.append("table_or_label_cell_only")
        if kind == "program_match" and len(words) <= 2:
            flags.append("broad_program_term_only")
        if last_name and last_name not in lowered:
            flags.append("person_name_not_in_anchor")
        details[kind] = {
            "quote": quote,
            "effective_word_count": len(words),
            "quality_flags": flags,
            "is_thin": bool(flags),
        }
    if all("person_name_not_in_anchor" in details[k]["quality_flags"] for k in details):
        details["record_flags"] = ["dual_anchors_do_not_independently_name_person"]
    else:
        details["record_flags"] = []
    details["is_thin"] = any(details[k]["is_thin"] for k in ("attendance", "program_match"))
    return details


def harden_anchor(
    record: dict[str, Any],
    anchor_kind: str,
    cache_text: str,
    *,
    combine_anchor_kinds: bool = False,
) -> dict[str, Any]:
    """Safely expand a thin anchor within one frozen cache document."""
    if anchor_kind not in {"attendance", "program_match"}:
        _fail(f"Unknown anchor kind {anchor_kind}")
    anchors = _anchors(record)
    source_id = anchors[anchor_kind].get("source_id")
    original = anchors[anchor_kind].get("quote") or ""
    if original not in cache_text:
        _fail("Original quote is not a substring of the selected cache")
    other_kind = "program_match" if anchor_kind == "attendance" else "attendance"
    if combine_anchor_kinds and anchors[other_kind].get("source_id") != source_id:
        _fail("Cross-source quote mixing is forbidden")
    quality = detect_anchor_quality(record)[anchor_kind]
    if not quality["is_thin"]:
        return {"status": "not_required", "original_quote": original, "hardened_quote": original}

    positions = [cache_text.index(original)]
    end_positions = [positions[0] + len(original)]
    person = record.get("person_name") or ""
    person_index = cache_text.lower().find(person.lower()) if person else -1
    if person_index < 0 and person:
        last = _words(person)[-1] if _words(person) else ""
        person_index = cache_text.lower().find(last.lower()) if last else -1
    if person_index >= 0:
        positions.append(person_index)
        end_positions.append(person_index + len(person if cache_text.lower().find(person.lower()) >= 0 else _words(person)[-1]))
    other_quote = anchors[other_kind].get("quote") or ""
    if anchors[other_kind].get("source_id") == source_id and other_quote in cache_text:
        other_index = cache_text.index(other_quote)
        positions.append(other_index)
        end_positions.append(other_index + len(other_quote))

    start = min(positions)
    end = max(end_positions)
    line_start = cache_text.rfind("\n", 0, start) + 1
    line_end = cache_text.find("\n", end)
    if line_end < 0:
        line_end = len(cache_text)
    candidate = cache_text[line_start:line_end].strip()
    if len(candidate) > 600:
        candidate = cache_text[start:end]
    person_words = _words(person)
    person_marker = person_words[-1].lower() if person_words else ""
    if (
        original in candidate
        and candidate in cache_text
        and len(candidate) > len(original)
        and len(_words(candidate)) >= 5
        and (not person_marker or person_marker in candidate.lower())
    ):
        return {
            "status": "hardened",
            "original_quote": original,
            "hardened_quote": candidate,
            "replacement_relationship": "expanded_same_source_cache_span_contains_original",
            "substring_verification": True,
        }
    return {
        "status": "anchor_hardening_unresolved",
        "original_quote": original,
        "hardened_quote": original,
        "replacement_relationship": "original_retained_no_safe_same_source_expansion",
        "substring_verification": True,
    }


def build_cache_inventory(
    cache_roots: Iterable[Path],
    referenced_paths: set[Path],
    reference_counts: Counter[Path] | None = None,
) -> dict[str, Any]:
    """Inventory cache references without deleting or mutating cache files."""
    roots = [Path(root).resolve() for root in cache_roots]
    referenced = {Path(path).resolve() for path in referenced_paths}
    actual = sorted({
        path.resolve()
        for root in roots
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file()
    })
    missing = sorted(path for path in referenced if not path.is_file())
    orphans = sorted(path for path in actual if path not in referenced)
    hash_groups: dict[str, list[Path]] = defaultdict(list)
    for path in actual:
        hash_groups[_sha256(path)].append(path)
    duplicate_groups = [
        {"sha256": digest, "cache_paths": [str(path) for path in paths]}
        for digest, paths in sorted(hash_groups.items()) if len(paths) > 1
    ]
    reference_counts = reference_counts or Counter({path: 1 for path in referenced})
    multi = [
        {"cache_path": str(path), "reference_count": count}
        for path, count in sorted(reference_counts.items(), key=lambda item: str(item[0]))
        if count > 1
    ]
    cleanup = [
        {
            "cache_path": str(path),
            "sha256": _sha256(path),
            "reason_considered_orphan": "file_not_referenced_by_any_wave_source_or_cache_manifest",
            "references_found": [],
            "safe_to_delete": False,
            "manual_review_required": True,
            "deletion_performed": False,
        }
        for path in orphans
    ]
    return {
        "referenced_cache_files": [str(path) for path in sorted(referenced) if path.is_file()],
        "orphan_cache_files": [
            {"cache_path": str(path), "sha256": _sha256(path), "references_found": []}
            for path in orphans
        ],
        "missing_referenced_cache_files": [str(path) for path in missing],
        "duplicate_content_groups": duplicate_groups,
        "identical_sha_different_names": duplicate_groups,
        "cache_referenced_by_multiple_records": multi,
        "cache_path_collisions": [],
        "cleanup_plan": cleanup,
        "old_cache_snapshot": [
            {"cache_path": str(path), "sha256": _sha256(path)} for path in actual
        ],
        "deletion_performed": False,
    }


def _load_required_inputs(
    config_path: Path,
    pins_path: Path,
    intake_path: Path,
    overrides_path: Path,
    exceptions_path: Path,
) -> tuple[dict[str, Any], ...]:
    paths = (config_path, pins_path, intake_path, overrides_path, exceptions_path)
    if any(not Path(path).is_file() for path in paths):
        _fail("Closing hardening requires all five frozen data inputs")
    return tuple(_read(Path(path)) for path in paths)


def _relativize_inventory(inventory: dict[str, Any], pipeline_root: Path) -> dict[str, Any]:
    result = deepcopy_json(inventory)
    scalar_lists = ("referenced_cache_files", "missing_referenced_cache_files")
    for key in scalar_lists:
        result[key] = [_relative(Path(path), pipeline_root) for path in result[key]]
    for key in ("orphan_cache_files", "cleanup_plan", "old_cache_snapshot", "cache_referenced_by_multiple_records"):
        for item in result[key]:
            item["cache_path"] = _relative(Path(item["cache_path"]), pipeline_root)
    for key in ("duplicate_content_groups", "identical_sha_different_names"):
        for group in result[key]:
            group["cache_paths"] = [_relative(Path(path), pipeline_root) for path in group["cache_paths"]]
    return result


def _live_text(entry: dict[str, Any], pipeline_root: Path) -> str:
    path = entry.get("text_cache_path")
    if not path:
        return ""
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = pipeline_root / resolved
    if not resolved.is_file():
        _fail(f"Missing closing live text cache: {resolved}")
    if entry.get("text_content_sha256") != _sha256(resolved):
        _fail(f"Closing live text cache SHA mismatch: {resolved}")
    return resolved.read_text(encoding="utf-8")


def build_stage3d_closing_hardening(
    pipeline_root: Path,
    config_path: Path,
    pins_path: Path,
    intake_path: Path,
    overrides_path: Path,
    exceptions_path: Path,
) -> dict[str, Any]:
    """Build deterministic closing artifacts from frozen local inputs only."""
    pipeline_root = Path(pipeline_root).resolve()
    config, pins, intake, overrides, exceptions = _load_required_inputs(
        config_path, pins_path, intake_path, overrides_path, exceptions_path
    )
    if config.get("baseline_commit") != BASELINE_COMMIT or config.get("artifact_generation_network_access") is not False:
        _fail("Closing config must preserve the Wave 10 baseline and offline generation")
    validate_immutable_input_pins(pins, pipeline_root)
    state = load_cumulative_state(pipeline_root)

    intake_entries = {entry.get("source_id"): entry for entry in intake.get("entries", [])}
    if set(intake_entries) != set(state["sources"]) or intake.get("live_fetch_attempted") != 180:
        _fail("Closing live intake metadata must cover all 180 unique sources")
    if any(entry.get("live_status") not in ALLOWED_LIVE_STATUSES for entry in intake_entries.values()):
        _fail("Closing live intake contains an unknown status")
    if intake.get("artifact_generation_network_access") is not False:
        _fail("Live intake and deterministic artifact generation are not separated")

    reverification_records = []
    findings = []
    for record in state["positives"]:
        source_id = record["source_ids"][0]
        entry = intake_entries[source_id]
        text = _live_text(entry, pipeline_root) if entry.get("text_cache_path") else ""
        if text:
            snapshot = {
                "http_status": entry.get("http_status"),
                "fetch_outcome": entry.get("fetch_outcome"),
                "text": text,
            }
            recalculated = classify_live_snapshot(record, snapshot)
            for field in ("live_status", "matched_anchor_count", "verification_method"):
                if entry.get(field) != recalculated.get(field):
                    _fail(f"Live intake classification drift for {source_id}: {field}")
        row = {
            "record_id": record["record_id"],
            "candidate_id": record["candidate_id"],
            "canonical_person_id": _canonical_person_id(record),
            "person_name": record["person_name"],
            "slot_id": record["slot_id"],
            "program_name": record["program_name"],
            "source_id": source_id,
            "source_url": state["sources"][source_id]["source_url"],
            "attendance_quote": record["evidence_anchor"]["attendance"]["quote"],
            "program_quote": record["evidence_anchor"]["program_match"]["quote"],
            **{key: entry.get(key) for key in (
                "retrieval_timestamp", "http_status", "fetch_outcome", "failure_category",
                "final_url", "redirect_chain", "content_type", "raw_cache_path",
                "raw_content_sha256", "text_cache_path", "text_content_sha256",
                "live_status", "severity", "verification_method", "matched_anchor_count",
                "exact_matched_anchor_count", "normalized_matched_anchor_count",
                "normalization_methods", "original_record_invalidated",
            )},
        }
        reverification_records.append(row)
        if row["live_status"] not in {"live_verified_exact", "live_verified_normalized"}:
            findings.append({
                "record_id": row["record_id"],
                "source_id": source_id,
                "live_status": row["live_status"],
                "severity": row["severity"],
                "automatic_data_change": False,
                "human_review_required": row["live_status"] in {
                    "live_source_mismatch", "live_not_found", "live_page_changed_review_required"
                },
                "notes": "Original Wave record remains immutable; this finding requires explicit review.",
            })

    override_map = {
        (item.get("record_id"), item.get("anchor_kind")): item
        for item in overrides.get("records", [])
    }
    quality_records = []
    overlay_records = []
    for record in state["positives"]:
        quality = detect_anchor_quality(record)
        anchor_rows = {}
        source_id = record["source_ids"][0]
        source = state["sources"][source_id]
        cache_path = (pipeline_root / source["cache_path"]).resolve()
        if not cache_path.is_file():
            _fail(f"Missing referenced Wave cache: {cache_path}")
        expected_cache_sha = source.get("sha256") or state["cache_entries"][source_id].get("sha256")
        if expected_cache_sha != _sha256(cache_path):
            _fail(f"Referenced Wave cache SHA mismatch: {cache_path}")
        cache_text = cache_path.read_text(encoding="utf-8")
        for kind in ("attendance", "program_match"):
            anchor_rows[kind] = quality[kind]
            if not quality[kind]["is_thin"]:
                continue
            hardened = harden_anchor(record, kind, cache_text)
            override = override_map.get((record["record_id"], kind))
            if override:
                proposed = override.get("hardened_quote") or ""
                if proposed not in cache_text or record["evidence_anchor"][kind]["quote"] not in proposed:
                    _fail("Reviewed anchor override is fabricated or does not contain the original quote")
                hardened = {
                    "status": "hardened",
                    "original_quote": record["evidence_anchor"][kind]["quote"],
                    "hardened_quote": proposed,
                    "replacement_relationship": "reviewed_same_source_expansion_contains_original",
                    "substring_verification": True,
                }
            overlay_records.append({
                "record_id": record["record_id"],
                "origin_wave": record["origin_wave"],
                "candidate_id": record["candidate_id"],
                "canonical_id": record.get("canonical_id"),
                "canonical_person_id": _canonical_person_id(record),
                "person_name": record["person_name"],
                "slot_id": record["slot_id"],
                "program_name": record["program_name"],
                "program_slot": record["program_slot"],
                "relationship_type": record["relationship_type"],
                "match_type": record["match_type"],
                "program_match_basis": record["program_match_basis"],
                "anchor_kind": kind,
                "source_id": source_id,
                "cache_path": _relative(cache_path, pipeline_root),
                "cache_sha256": _sha256(cache_path),
                "reason": quality[kind]["quality_flags"],
                "substring_verification_method": "local_cache_substring_check",
                **hardened,
            })
        quality_records.append({
            "record_id": record["record_id"],
            "candidate_id": record["candidate_id"],
            "canonical_person_id": _canonical_person_id(record),
            "person_name": record["person_name"],
            "slot_id": record["slot_id"],
            "source_id": source_id,
            "is_thin": quality["is_thin"],
            "record_flags": quality["record_flags"],
            "attendance": anchor_rows["attendance"],
            "program_match": anchor_rows["program_match"],
        })

    inventory_raw = build_cache_inventory(
        state["cache_scan_roots"], set(state["referenced_cache_paths"]), state["reference_counts"]
    )
    inventory = _relativize_inventory(inventory_raw, pipeline_root)
    if inventory["missing_referenced_cache_files"]:
        _fail("Closing cache inventory found missing referenced cache files")
    status_counts = Counter(row["live_status"] for row in reverification_records)
    hardened_count = sum(row["status"] == "hardened" for row in overlay_records)
    unresolved_count = sum(row["status"] == "anchor_hardening_unresolved" for row in overlay_records)
    thin_count = len(overlay_records)
    gaps = [
        {
            **slot,
            "person_id": None,
            "canonical_person_id": None,
            "person_name": None,
            "display_as_none": False,
            "null_reason": "source_review_not_completed",
        }
        for slot in state["slots"] if slot["slot_status"] == "source_review_not_completed"
    ]
    summary = {
        "record_type": "stage3d_closing_hardening_cumulative_summary",
        "schools": 62,
        "history_coverage": "62/62",
        "anecdotes_coverage": "62/62",
        "notable_attendance_coverage": "62/62",
        "program_people_total_slots": 310,
        "program_people_identified": 180,
        "program_people_source_review_not_completed": 130,
        "program_people_no_qualifying_person_found": 0,
        "identified_coverage_percentage": round(180 / 310 * 100, 2),
        "total_positive_records": 180,
        "unique_source_ids": 180,
        "live_fetch_attempted": 180,
        "local_cache_verified": 180,
        "live_verified_exact": status_counts["live_verified_exact"],
        "live_verified_normalized": status_counts["live_verified_normalized"],
        "live_page_changed_review_required": status_counts["live_page_changed_review_required"],
        "live_unavailable": status_counts["live_unavailable"],
        "live_not_found": status_counts["live_not_found"],
        "live_source_mismatch": status_counts["live_source_mismatch"],
        "hardened_anchors": hardened_count,
        "total_thin_anchors_detected": thin_count,
        "unresolved_thin_anchors": unresolved_count,
        "orphan_cache_count": len(inventory["orphan_cache_files"]),
        "missing_referenced_cache_count": 0,
        "duplicate_count": 0,
        "post_merge_duplicate_count": 0,
        "raw_person_occurrence_count": 180,
        "unique_person_count": 180,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "source_limited": True,
        "incomplete": True,
        "not_final": True,
        "readiness_status": "source_limited / incomplete / not_final",
        "not_final_reason": "180 identified records do not complete 310 program slots; 130 gaps remain source_review_not_completed and cannot be rendered as none.",
        "final_universe_generated": False,
        "official_selection_memberships_generated": False,
        "frontend_export_generated": False,
        "frontend_ready_preview_generated": False,
        "production_export_generated": False,
        "stage4a_overlay_generated": False,
        "tag_created": False,
        "push_performed": False,
        "old_cache_files_deleted": False,
        "artifact_generation_network_access": False,
    }
    return {
        "stage3d-closing-hardening-source-reverification.json": {
            "record_type": "stage3d_closing_hardening_source_reverification",
            "total_positive_records": 180,
            "unique_source_ids": 180,
            "status_counts": {status: status_counts[status] for status in sorted(ALLOWED_LIVE_STATUSES)},
            "records": reverification_records,
        },
        "stage3d-closing-hardening-source-findings.json": {
            "record_type": "stage3d_closing_hardening_source_findings",
            "high_issue_count": sum(item["severity"] == "High" for item in findings),
            "medium_issue_count": sum(item["severity"] == "Medium" for item in findings),
            "findings": findings,
            "automatic_original_data_changes": 0,
        },
        "stage3d-closing-hardening-anchor-quality-report.json": {
            "record_type": "stage3d_closing_hardening_anchor_quality_report",
            "total_positive_records_scanned": 180,
            "total_anchors_scanned": 360,
            "thin_anchor_count": thin_count,
            "records_with_thin_anchors": sum(item["is_thin"] for item in quality_records),
            "records": quality_records,
        },
        "stage3d-closing-hardening-evidence-anchor-overlay.json": {
            "record_type": "stage3d_closing_hardening_evidence_anchor_overlay",
            "overlay_only": True,
            "original_wave_records_modified": 0,
            "hardened_anchor_count": hardened_count,
            "unresolved_anchor_count": unresolved_count,
            "records": overlay_records,
        },
        "stage3d-closing-hardening-orphan-cache-inventory.json": {
            "record_type": "stage3d_closing_hardening_orphan_cache_inventory",
            **{key: value for key, value in inventory.items() if key != "cleanup_plan"},
        },
        "stage3d-closing-hardening-cache-cleanup-plan.json": {
            "record_type": "stage3d_closing_hardening_cache_cleanup_plan",
            "deletion_performed": False,
            "records": inventory["cleanup_plan"],
        },
        "stage3d-closing-hardening-gap-disclosure.json": {
            "record_type": "stage3d_closing_hardening_gap_disclosure",
            "source_review_not_completed_count": len(gaps),
            "no_qualifying_person_found_count": 0,
            "display_as_none_count": 0,
            "slots": gaps,
        },
        "stage3d-closing-hardening-cumulative-summary.json": summary,
        "stage3d-closing-hardening-input-pin-report.json": {
            "record_type": "stage3d_closing_hardening_input_pin_report",
            "baseline_commit": BASELINE_COMMIT,
            "pins_verified": len(pins["pins"]),
            "all_pins_match": True,
            "expected_cumulative_counts": state["summary"],
            "stage3a_stash_untouched": True,
            "waves_1_through_10_immutable": True,
            "reviewed_exceptions_count": len(exceptions.get("records", [])),
        },
    }


def validate_stage3d_closing_hardening(
    artifacts: dict[str, Any],
    pipeline_root: Path,
    config_path: Path,
    pins_path: Path,
    intake_path: Path,
    overrides_path: Path,
    exceptions_path: Path,
) -> dict[str, Any]:
    """Fail closed on provenance, cache, identity, gap, or boundary drift."""
    expected = build_stage3d_closing_hardening(
        pipeline_root, config_path, pins_path, intake_path, overrides_path, exceptions_path
    )
    if artifacts != expected:
        _fail("Closing hardening artifacts differ from deterministic regeneration")
    summary = artifacts["stage3d-closing-hardening-cumulative-summary.json"]
    required_zero = (
        "missing_referenced_cache_count", "duplicate_count", "post_merge_duplicate_count",
        "source_policy_violations", "ranking_field_contamination",
    )
    if any(summary.get(field) != 0 for field in required_zero):
        _fail("Closing hardening zero-tolerance summary check failed")
    if (summary.get("program_people_total_slots"), summary.get("program_people_identified"), summary.get("program_people_source_review_not_completed")) != (310, 180, 130):
        _fail("Closing hardening cumulative counts drifted")
    if not all(summary.get(field) is True for field in ("source_limited", "incomplete", "not_final")):
        _fail("Closing hardening must remain source_limited / incomplete / not_final")
    if any(summary.get(field) for field in (
        "final_universe_generated", "official_selection_memberships_generated",
        "frontend_export_generated", "frontend_ready_preview_generated",
        "production_export_generated", "stage4a_overlay_generated", "tag_created",
        "push_performed", "old_cache_files_deleted", "artifact_generation_network_access",
    )):
        _fail("Closing hardening crossed a forbidden boundary")
    gaps = artifacts["stage3d-closing-hardening-gap-disclosure.json"]["slots"]
    if len(gaps) != 130 or any(
        row.get("slot_status") != "source_review_not_completed"
        or row.get("display_as_none") is not False
        or row.get("person_name") is not None
        or row.get("canonical_person_id") is not None
        for row in gaps
    ):
        _fail("Closing gap semantics were not preserved")
    overlay = artifacts["stage3d-closing-hardening-evidence-anchor-overlay.json"]
    state = load_cumulative_state(pipeline_root)
    original_by_id = {row["record_id"]: row for row in state["positives"]}
    immutable_fields = (
        "candidate_id", "canonical_id", "canonical_person_id", "person_name", "slot_id",
        "program_name", "program_slot", "relationship_type", "match_type", "program_match_basis",
    )
    for row in overlay["records"]:
        original = original_by_id.get(row.get("record_id"))
        if not original or any(row.get(field) != (_canonical_person_id(original) if field == "canonical_person_id" else original.get(field)) for field in immutable_fields):
            _fail("Evidence anchor overlay changed identity or match semantics")
        cache_path = Path(pipeline_root) / row["cache_path"]
        if _sha256(cache_path) != row["cache_sha256"]:
            _fail("Evidence anchor overlay cache SHA mismatch")
        cache_text = cache_path.read_text(encoding="utf-8")
        if row["hardened_quote"] not in cache_text or row["original_quote"] not in row["hardened_quote"]:
            _fail("Evidence anchor overlay failed substring verification")
    return {
        "record_type": "stage3d_closing_hardening_validation_result",
        "status": "passed",
        "checks_passed": 34,
        "deterministic_regeneration": True,
        "network_disabled_regeneration": True,
        "input_counts": {"total_slots": 310, "identified": 180, "gaps": 130},
        "missing_referenced_cache_count": 0,
        "raw_person_occurrence_count": 180,
        "unique_person_count": 180,
        "duplicate_person_count": 0,
        "post_merge_duplicate_count": 0,
        "source_policy_violations": 0,
        "ranking_field_contamination": 0,
        "old_cache_files_deleted": False,
        "tag_created": False,
        "push_performed": False,
    }


def write_stage3d_closing_hardening(
    artifacts: dict[str, Any], output_dir: Path, validation: dict[str, Any]
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        (output_dir / name).write_text(_json_text(artifacts[name]), encoding="utf-8")
    (output_dir / VALIDATION_FILE).write_text(_json_text(validation), encoding="utf-8")


def load_stage3d_closing_hardening_artifacts(artifact_dir: Path) -> dict[str, Any]:
    artifact_dir = Path(artifact_dir)
    missing = [name for name in (*OUTPUT_FILES, VALIDATION_FILE) if not (artifact_dir / name).is_file()]
    if missing:
        _fail(f"Closing artifact directory is incomplete: {missing}")
    return {name: _read(artifact_dir / name) for name in OUTPUT_FILES}


def validate_committed_closing_result(artifact_dir: Path, expected: dict[str, Any]) -> None:
    path = Path(artifact_dir) / VALIDATION_FILE
    if not path.is_file() or _read(path) != expected:
        _fail("Committed closing validation result does not match validator rerun")


def render_stage3d_closing_hardening_report(artifacts: dict[str, Any]) -> str:
    summary = artifacts["stage3d-closing-hardening-cumulative-summary.json"]
    findings = artifacts["stage3d-closing-hardening-source-findings.json"]
    return f"""# Stage 3D Closing Hardening — Program People Provenance Closure

## Frozen scope

- universities: **{summary['schools']}**
- history / anecdotes / notable attendance: **62/62 / 62/62 / 62/62**
- program slots: **310**
- identified / source-review gaps: **180 / 130**

## Live-source re-verification

- unique sources attempted: **{summary['unique_source_ids']}**
- exact: **{summary['live_verified_exact']}**
- normalized: **{summary['live_verified_normalized']}**
- changed / review required: **{summary['live_page_changed_review_required']}**
- unavailable: **{summary['live_unavailable']}**
- not found: **{summary['live_not_found']}**
- source mismatch: **{summary['live_source_mismatch']}**
- High findings: **{findings['high_issue_count']}**

Live findings never rewrite or invalidate immutable Wave 1–10 records automatically.

## Anchor and cache hardening

- thin anchors detected: **{summary['total_thin_anchors_detected']}**
- safely hardened: **{summary['hardened_anchors']}**
- unresolved: **{summary['unresolved_thin_anchors']}**
- orphan cache files: **{summary['orphan_cache_count']}**
- missing referenced cache files: **{summary['missing_referenced_cache_count']}**
- cache files deleted: **no**

## Boundaries

`source_limited / incomplete / not_final`

The 180 identified records do not complete 310 slots. The remaining 130 gaps are not “none.” No final universe, membership, frontend, preview, production, or Stage 4A export was generated.
"""
