"""TDD contracts for Stage 3D People/Narrative closing hardening."""

import json
import os
import socket
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

try:
    from pathos_data.stage3d_closing_hardening import (
        ALLOWED_LIVE_STATUSES,
        ClosingHardeningValidationError,
        build_cache_inventory,
        build_immutable_input_pins,
        build_stage3d_closing_hardening,
        classify_live_snapshot,
        detect_anchor_quality,
        harden_anchor,
        load_cumulative_state,
        normalize_live_text,
        run_live_intake,
        validate_immutable_input_pins,
        validate_stage3d_closing_hardening,
    )
except ImportError:
    ALLOWED_LIVE_STATUSES = set()
    ClosingHardeningValidationError = ValueError
    build_cache_inventory = None
    build_immutable_input_pins = None
    build_stage3d_closing_hardening = None
    classify_live_snapshot = None
    detect_anchor_quality = None
    harden_anchor = None
    load_cumulative_state = None
    normalize_live_text = None
    run_live_intake = None
    validate_immutable_input_pins = None
    validate_stage3d_closing_hardening = None


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3d-closing-hardening"
CONFIG = DATA / "stage3d-closing-hardening-config.json"
PINS = DATA / "stage3d-closing-hardening-immutable-input-pins.json"
INTAKE = DATA / "stage3d-closing-hardening-live-intake-metadata.json"
OVERRIDES = DATA / "stage3d-closing-hardening-anchor-overrides.json"
EXCEPTIONS = DATA / "stage3d-closing-hardening-reviewed-exceptions.json"


def _record(**overrides):
    value = {
        "record_id": "wave-test:candidate-v2:test:slot-1",
        "origin_wave": "wave-test",
        "candidate_id": "candidate-v2:test-university",
        "canonical_id": "institution:test-university",
        "university_name": "Test University",
        "slot_id": "candidate-v2:test-university:slot-1",
        "program_name": "Computer Science",
        "program_slot": 1,
        "person_name": "Alex Example",
        "canonical_person_id": "person:alex-example:test-university:test-source",
        "relationship_type": "graduated",
        "match_type": "direct_program_match",
        "program_match_basis": "source_stated_exact_program",
        "source_ids": ["test-source"],
        "evidence_anchor": {
            "attendance": {
                "source_id": "test-source",
                "quote": "Alex Example graduated from Test University in 2010.",
                "quote_verification_method": "local_cache_substring_check",
            },
            "program_match": {
                "source_id": "test-source",
                "quote": "Alex Example earned a degree in Computer Science.",
                "quote_verification_method": "local_cache_substring_check",
            },
        },
    }
    value.update(overrides)
    return value


class Stage3DClosingHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.temp = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_cumulative_input_counts_and_dedup_are_frozen(self):
        state = load_cumulative_state(ROOT)
        self.assertEqual(state["summary"]["total_program_slots"], 310)
        self.assertEqual(state["summary"]["identified_person_count"], 180)
        self.assertEqual(state["summary"]["source_review_not_completed_count"], 130)
        self.assertEqual(state["summary"]["no_qualifying_person_found_count"], 0)
        self.assertEqual(state["summary"]["raw_person_occurrence_count"], 180)
        self.assertEqual(state["summary"]["unique_person_count"], 180)
        self.assertEqual(state["summary"]["duplicate_person_count"], 0)

    def test_immutable_input_pin_mismatch_is_rejected(self):
        pins = build_immutable_input_pins(ROOT)
        validate_immutable_input_pins(pins, ROOT)
        invalid = deepcopy(pins)
        invalid["pins"][0]["sha256"] = "0" * 64
        with self.assertRaises(ClosingHardeningValidationError):
            validate_immutable_input_pins(invalid, ROOT)

    def test_live_exact_and_allowed_normalized_verification(self):
        record = _record()
        exact = classify_live_snapshot(
            record,
            {"http_status": 200, "fetch_outcome": "success", "text": (
                "Alex Example graduated from Test University in 2010. "
                "Alex Example earned a degree in Computer Science."
            )},
        )
        self.assertEqual(exact["live_status"], "live_verified_exact")
        normalized = classify_live_snapshot(
            record,
            {"http_status": 200, "fetch_outcome": "success", "text": (
                "Alex Example\u00a0graduated from Test University in 2010.\n"
                "Alex Example earned a degree in Computer Science."
            )},
        )
        self.assertEqual(normalized["live_status"], "live_verified_normalized")
        self.assertEqual(
            normalize_live_text("A&amp;B\u00a0 C"), normalize_live_text("A&B C")
        )

    def test_quote_mismatch_requires_review_and_source_mismatch_is_high(self):
        record = _record()
        changed = classify_live_snapshot(
            record,
            {"http_status": 200, "fetch_outcome": "success", "text": (
                "Alex Example is profiled by Test University. "
                "The biography now describes a Computer Science degree differently."
            )},
        )
        self.assertEqual(changed["live_status"], "live_page_changed_review_required")
        mismatch = classify_live_snapshot(
            record,
            {"http_status": 200, "fetch_outcome": "success", "text": (
                "This page is about an unrelated campus announcement and another person."
            )},
        )
        self.assertEqual(mismatch["live_status"], "live_source_mismatch")
        self.assertEqual(mismatch["severity"], "High")

    def test_unavailable_and_not_found_do_not_invalidate_records(self):
        record = _record()
        unavailable = classify_live_snapshot(
            record,
            {"http_status": 403, "fetch_outcome": "http_error", "text": ""},
        )
        self.assertEqual(unavailable["live_status"], "live_unavailable")
        self.assertFalse(unavailable["original_record_invalidated"])
        not_found = classify_live_snapshot(
            record,
            {"http_status": 404, "fetch_outcome": "http_error", "text": ""},
        )
        self.assertEqual(not_found["live_status"], "live_not_found")
        self.assertFalse(not_found["original_record_invalidated"])

    def test_live_status_enum_is_closed(self):
        self.assertEqual(ALLOWED_LIVE_STATUSES, {
            "live_verified_exact", "live_verified_normalized",
            "live_page_changed_review_required", "live_unavailable",
            "live_not_found", "live_source_mismatch",
        })

    def test_live_intake_writes_separate_cache_and_metadata(self):
        record = _record()
        source = {"source_id": "test-source", "source_url": "https://example.edu/person"}

        def fetcher(url, **_kwargs):
            self.assertEqual(url, source["source_url"])
            return {
                "http_status": 200,
                "final_url": url,
                "redirect_chain": [],
                "content_type": "text/html",
                "raw_bytes": b"Alex Example graduated from Test University in 2010. "
                b"Alex Example earned a degree in Computer Science.",
                "text": "Alex Example graduated from Test University in 2010. "
                "Alex Example earned a degree in Computer Science.",
                "fetch_outcome": "success",
                "failure_category": None,
            }

        metadata = run_live_intake(
            [record], {"test-source": source}, self.temp / "cache", fetcher=fetcher,
            retrieval_timestamp="2026-07-22T00:00:00Z",
        )
        entry = metadata["entries"][0]
        self.assertEqual(entry["live_status"], "live_verified_exact")
        self.assertTrue((self.temp / "cache/test-source.raw").is_file())
        self.assertTrue((self.temp / "cache/test-source.txt").is_file())
        self.assertEqual(entry["matched_anchor_count"], 2)

    def test_thin_anchor_detection_and_safe_expansion(self):
        record = _record(
            evidence_anchor={
                "attendance": {"source_id": "test-source", "quote": "Graduate Alumni"},
                "program_match": {"source_id": "test-source", "quote": "Psychology"},
            }
        )
        quality = detect_anchor_quality(record)
        self.assertTrue(quality["is_thin"])
        cache = (
            "Alex Example is listed among Graduate Alumni.\n"
            "Alex Example earned a Bachelor of Arts in Psychology from Test University."
        )
        hardened = harden_anchor(record, "attendance", cache)
        self.assertEqual(hardened["status"], "hardened")
        self.assertIn("Graduate Alumni", hardened["hardened_quote"])
        self.assertIn("Alex Example", hardened["hardened_quote"])
        self.assertIn(hardened["hardened_quote"], cache)

    def test_fabricated_or_cross_source_anchor_is_rejected(self):
        record = _record()
        with self.assertRaises(ClosingHardeningValidationError):
            harden_anchor(record, "attendance", "An unrelated cache text.")
        mixed = deepcopy(record)
        mixed["evidence_anchor"]["program_match"]["source_id"] = "other-source"
        with self.assertRaises(ClosingHardeningValidationError):
            harden_anchor(mixed, "attendance", (
                "Alex Example graduated from Test University in 2010. "
                "Alex Example earned a degree in Computer Science."
            ), combine_anchor_kinds=True)

    def test_anchor_overlay_cannot_change_identity_or_match_semantics(self):
        artifacts = build_stage3d_closing_hardening(
            ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        invalid = deepcopy(artifacts)
        overlay = invalid["stage3d-closing-hardening-evidence-anchor-overlay.json"]
        if overlay["records"]:
            overlay["records"][0]["candidate_id"] = "candidate-v2:other"
            with self.assertRaises(ClosingHardeningValidationError):
                validate_stage3d_closing_hardening(
                    invalid, ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
                )

    def test_orphan_inventory_and_missing_reference_gate(self):
        cache = self.temp / "cache"
        cache.mkdir()
        referenced = cache / "referenced.txt"
        orphan = cache / "orphan.txt"
        referenced.write_text("same", encoding="utf-8")
        orphan.write_text("same", encoding="utf-8")
        inventory = build_cache_inventory([cache], {referenced.resolve()})
        self.assertEqual(len(inventory["orphan_cache_files"]), 1)
        self.assertFalse(inventory["cleanup_plan"][0]["safe_to_delete"])
        self.assertTrue(inventory["cleanup_plan"][0]["manual_review_required"])
        self.assertEqual(len(inventory["duplicate_content_groups"]), 1)
        referenced.unlink()
        missing = build_cache_inventory([cache], {referenced.resolve()})
        self.assertEqual(len(missing["missing_referenced_cache_files"]), 1)

    def test_actual_orphan_scan_finds_known_candidates_without_deleting(self):
        state = load_cumulative_state(ROOT)
        before = {path: path.stat().st_mtime_ns for path in state["cache_scan_files"]}
        inventory = build_cache_inventory(
            state["cache_scan_roots"], set(state["referenced_cache_paths"])
        )
        orphan_names = {Path(item["cache_path"]).name for item in inventory["orphan_cache_files"]}
        self.assertTrue(any(name.startswith("wave5-mit-") for name in orphan_names))
        self.assertIn("georgia-tech-blair-evanchec.txt", orphan_names)
        after = {path: path.stat().st_mtime_ns for path in state["cache_scan_files"]}
        self.assertEqual(before, after)

    def test_gap_semantics_and_cumulative_dashboard_are_preserved(self):
        artifacts = build_stage3d_closing_hardening(
            ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        gaps = artifacts["stage3d-closing-hardening-gap-disclosure.json"]["slots"]
        self.assertEqual(len(gaps), 130)
        self.assertTrue(all(item["slot_status"] == "source_review_not_completed" for item in gaps))
        self.assertTrue(all(item["display_as_none"] is False for item in gaps))
        self.assertTrue(all(item["person_name"] is None for item in gaps))
        summary = artifacts["stage3d-closing-hardening-cumulative-summary.json"]
        self.assertEqual(summary["schools"], 62)
        self.assertEqual(summary["history_coverage"], "62/62")
        self.assertEqual(summary["anecdotes_coverage"], "62/62")
        self.assertEqual(summary["notable_attendance_coverage"], "62/62")
        self.assertEqual(summary["program_people_identified"], 180)
        self.assertEqual(summary["program_people_source_review_not_completed"], 130)
        self.assertTrue(summary["source_limited"])
        self.assertTrue(summary["incomplete"])
        self.assertTrue(summary["not_final"])

    def test_validator_rejects_missing_cache_ranking_and_policy_contamination(self):
        artifacts = build_stage3d_closing_hardening(
            ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        validate_stage3d_closing_hardening(
            artifacts, ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        for field in ("missing_referenced_cache_count", "ranking_field_contamination", "source_policy_violations"):
            invalid = deepcopy(artifacts)
            invalid["stage3d-closing-hardening-cumulative-summary.json"][field] = 1
            with self.assertRaises(ClosingHardeningValidationError):
                validate_stage3d_closing_hardening(
                    invalid, ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
                )

    def test_regeneration_is_deterministic_and_network_disabled(self):
        first = build_stage3d_closing_hardening(
            ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        with patch.object(socket, "create_connection", side_effect=AssertionError("network used")):
            second = build_stage3d_closing_hardening(
                ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
            )
        self.assertEqual(first, second)
        result = validate_stage3d_closing_hardening(
            first, ROOT, CONFIG, PINS, INTAKE, OVERRIDES, EXCEPTIONS
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["network_disabled_regeneration"])

    def test_cli_generates_and_validates_without_network(self):
        output = self.temp / "artifacts"
        report = self.temp / "report.md"
        result = self.temp / "validation.json"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        shared = [
            "--pipeline-root", str(ROOT), "--config", str(CONFIG), "--pins", str(PINS),
            "--intake-metadata", str(INTAKE), "--anchor-overrides", str(OVERRIDES),
            "--reviewed-exceptions", str(EXCEPTIONS),
        ]
        generated = subprocess.run([
            sys.executable, "-m", "pathos_data", "stage3d-closing-hardening",
            "--mode", "generate", *shared, "--output", str(output),
            "--report-output", str(report),
        ], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        validated = subprocess.run([
            sys.executable, "-m", "pathos_data", "stage3d-closing-hardening",
            "--mode", "validate", *shared, "--artifact-dir", str(output),
            "--result-output", str(result),
        ], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(result.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
