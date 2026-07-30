"""CLI skeleton. Network collection commands are intentionally dry-run only."""

import argparse
import json
from pathlib import Path

from .exporter import write_formal_frontend_export
from .migration_audit import audit_migrations
from .pipeline import normalize_staged, stage_raw
from .ranking_discovery import (
    stage_manual_seed_batch,
    validate_category_inventory,
    validate_manual_seed_batch,
    validate_ranking_family_inventory,
)
from .ranking_collection import stage_verified_pilot_stream, validate_pilot_artifacts, write_pilot_validation_result
from .ranking_corpus import validate_corpus, write_corpus_artifacts
from .universe_candidate import (
    build_candidate,
    validate_candidate,
    write_candidate,
    write_candidate_validation_result,
)
from .universe_completion import validate_universe_completion_plan
from .national_completion import (
    build_national_manual_seed_bundle,
    validate_national_completion_artifacts,
    write_national_manual_seed_bundle,
    write_national_completion_validation_result,
)
from .priority_program_batch import (
    build_priority_program_batch_bundle,
    validate_priority_program_batch_artifacts,
    write_priority_program_batch_bundle,
    write_priority_program_batch_validation_result,
)
from .official_program_sweep import (
    build_official_program_sweep_bundle,
    validate_official_program_sweep_artifacts,
    write_official_program_sweep_bundle,
    write_official_program_sweep_validation_result,
)
from .program_gap_repair import (
    build_program_gap_repair_bundle,
    validate_program_gap_repair_artifacts,
    write_program_gap_repair_bundle,
    write_program_gap_repair_validation_result,
)
from .program_top20_completion import (
    build_program_top20_completion_attempt_bundle,
    validate_program_top20_completion_attempt_artifacts,
    write_program_top20_completion_attempt_bundle,
    write_program_top20_completion_attempt_validation_result,
)
from .universe_candidate_v2 import (
    build_candidate_v2,
    validate_candidate_v2_artifacts,
    write_candidate_v2_bundle,
)
from .stage3_program_mvp import (
    build_stage3_program_mvp,
    validate_stage3_program_mvp,
    write_stage3_program_mvp,
)
from .stage3b_gap_fill import (
    build_stage3b_gap_fill,
    validate_stage3b_gap_fill,
    write_stage3b_gap_fill,
)
from .stage3c_academic_geo import (
    build_stage3c_academic_geo,
    validate_stage3c_academic_geo,
    write_stage3c_academic_geo,
)
from .stage3c2_nearest_towns import (
    build_stage3c2_nearest_towns,
    render_stage3c2_report,
    validate_stage3c2_nearest_towns,
    write_stage3c2_artifacts,
)
from .stage3d_people_narrative import (
    build_stage3d_people_narrative,
    render_stage3d_report,
    validate_stage3d_people_narrative,
    write_stage3d_artifacts,
)
from .stage3d_fill_people_narrative import (
    build_stage3d_fill,
    render_stage3d_fill_report,
    validate_stage3d_fill,
    write_stage3d_fill,
)
from .stage3d_fill_batch1_history_anecdotes import (
    build_stage3d_fill_batch1,
    render_stage3d_fill_batch1_report,
    validate_stage3d_fill_batch1,
    write_stage3d_fill_batch1,
)
from .stage3d_fill_batch2_history_anecdotes import (
    build_stage3d_fill_batch2,
    render_stage3d_fill_batch2_report,
    validate_stage3d_fill_batch2,
    write_stage3d_fill_batch2,
)
from .stage3d_fill_people_pilot_notable_attendance import (
    build_stage3d_fill_people_pilot,
    render_stage3d_fill_people_pilot_report,
    validate_stage3d_fill_people_pilot,
    write_stage3d_fill_people_pilot,
)
from .stage3d_fill_bulk_completion_v2 import (
    build_stage3d_fill_bulk_completion_v2,
    render_stage3d_fill_bulk_completion_v2_report,
    validate_stage3d_fill_bulk_completion_v2,
    write_stage3d_fill_bulk_completion_v2,
)
from .stage3d_fill_bulk_people_completion_v1 import (
    build_stage3d_fill_bulk_people_completion_v1,
    render_stage3d_fill_bulk_people_completion_v1_report,
    validate_stage3d_fill_bulk_people_completion_v1,
    write_stage3d_fill_bulk_people_completion_v1,
)
from .stage3d_fill_bulk_people_v2 import (
    build_stage3d_fill_bulk_people_v2,
    render_stage3d_fill_bulk_people_v2_report,
    validate_stage3d_fill_bulk_people_v2,
    write_stage3d_fill_bulk_people_v2,
)
from .stage3d_fill_bulk_people_v2_batch_a import (
    build_stage3d_fill_bulk_people_v2_batch_a,
    render_stage3d_fill_bulk_people_v2_batch_a_report,
    validate_stage3d_fill_bulk_people_v2_batch_a,
    write_stage3d_fill_bulk_people_v2_batch_a,
)
from .stage3d_fill_bulk_people_v2_batch_b import (
    build_stage3d_fill_bulk_people_v2_batch_b,
    render_stage3d_fill_bulk_people_v2_batch_b_report,
    validate_stage3d_fill_bulk_people_v2_batch_b,
    write_stage3d_fill_bulk_people_v2_batch_b,
)
from .stage3d_fill_bulk_people_v2_combined_dedup import (
    build_stage3d_fill_bulk_people_v2_combined_dedup,
    render_stage3d_fill_bulk_people_v2_combined_dedup_report,
    validate_stage3d_fill_bulk_people_v2_combined_dedup,
    write_stage3d_fill_bulk_people_v2_combined_dedup,
)
from .stage3d_fill_bulk_completion_wave1 import (
    OUTPUT_FILES as STAGE3D_FILL_BULK_COMPLETION_WAVE1_OUTPUT_FILES,
    build_stage3d_fill_bulk_completion_wave1,
    render_stage3d_fill_bulk_completion_wave1_report,
    validate_stage3d_fill_bulk_completion_wave1,
    write_stage3d_fill_bulk_completion_wave1,
)
from .stage3d_fill_bulk_completion_wave2 import (
    OUTPUT_FILES as STAGE3D_FILL_BULK_COMPLETION_WAVE2_OUTPUT_FILES,
    build_stage3d_fill_bulk_completion_wave2,
    render_stage3d_fill_bulk_completion_wave2_report,
    validate_stage3d_fill_bulk_completion_wave2,
    write_stage3d_fill_bulk_completion_wave2,
)
from .stage3d_fill_bulk_completion_wave3 import (
    OUTPUT_FILES as STAGE3D_FILL_BULK_COMPLETION_WAVE3_OUTPUT_FILES,
    build_stage3d_fill_bulk_completion_wave3,
    render_stage3d_fill_bulk_completion_wave3_report,
    validate_stage3d_fill_bulk_completion_wave3,
    write_stage3d_fill_bulk_completion_wave3,
)
from .stage3d_fill_program_people_wave4 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE4_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave4,
    render_stage3d_fill_program_people_wave4_report,
    validate_stage3d_fill_program_people_wave4,
    write_stage3d_fill_program_people_wave4,
)
from .stage3d_fill_program_people_wave5 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE5_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave5,
    render_stage3d_fill_program_people_wave5_report,
    validate_stage3d_fill_program_people_wave5,
    write_stage3d_fill_program_people_wave5,
)
from .stage3d_fill_program_people_wave6 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE6_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave6,
    render_stage3d_fill_program_people_wave6_report,
    validate_stage3d_fill_program_people_wave6,
    write_stage3d_fill_program_people_wave6,
)
from .stage3d_fill_program_people_wave7 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE7_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave7,
    render_stage3d_fill_program_people_wave7_report,
    validate_stage3d_fill_program_people_wave7_artifact_directory,
    validate_stage3d_fill_program_people_wave7_committed_result,
    validate_stage3d_fill_program_people_wave7_output_path,
    validate_stage3d_fill_program_people_wave7,
    write_stage3d_fill_program_people_wave7,
)
from .stage3d_fill_program_people_wave8 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE8_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave8,
    render_stage3d_fill_program_people_wave8_report,
    validate_stage3d_fill_program_people_wave8_artifact_directory,
    validate_stage3d_fill_program_people_wave8_committed_result,
    validate_stage3d_fill_program_people_wave8_output_path,
    validate_stage3d_fill_program_people_wave8,
    write_stage3d_fill_program_people_wave8,
)
from .stage3d_fill_program_people_wave9 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE9_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave9,
    render_stage3d_fill_program_people_wave9_report,
    validate_stage3d_fill_program_people_wave9_artifact_directory,
    validate_stage3d_fill_program_people_wave9_committed_result,
    validate_stage3d_fill_program_people_wave9_output_path,
    validate_stage3d_fill_program_people_wave9,
    write_stage3d_fill_program_people_wave9,
)
from .stage3d_fill_program_people_wave10 import (
    OUTPUT_FILES as STAGE3D_FILL_PROGRAM_PEOPLE_WAVE10_OUTPUT_FILES,
    build_stage3d_fill_program_people_wave10,
    render_stage3d_fill_program_people_wave10_report,
    validate_stage3d_fill_program_people_wave10_artifact_directory,
    validate_stage3d_fill_program_people_wave10_committed_result,
    validate_stage3d_fill_program_people_wave10_output_path,
    validate_stage3d_fill_program_people_wave10,
    write_stage3d_fill_program_people_wave10,
)
from .stage3d_closing_hardening import (
    build_immutable_input_pins as build_stage3d_closing_hardening_pins,
    build_stage3d_closing_hardening,
    load_cumulative_state as load_stage3d_closing_cumulative_state,
    load_stage3d_closing_hardening_artifacts,
    render_stage3d_closing_hardening_report,
    run_live_intake as run_stage3d_closing_live_intake,
    validate_committed_closing_result,
    validate_immutable_input_pins as validate_stage3d_closing_input_pins,
    validate_stage3d_closing_hardening,
    write_stage3d_closing_hardening,
)
from .stage4b.config import canonical_json as stage4b_canonical_json
from .stage4b.generator import write_artifacts as write_stage4b_artifacts
from .stage4b.reports import write_reports as write_stage4b_reports
from .stage4b.validator import (
    build_validated_stage4b,
    validate_committed_stage4b,
)
from .stage4c.config import canonical_json as stage4c_canonical_json
from .stage4c.generator import write_artifacts as write_stage4c_artifacts
from .stage4c.reports import write_reports as write_stage4c_reports
from .stage4c.validator import (
    build_validated_stage4c,
    validate_committed_stage4c,
)
from .schema_validation import load_schema, validate_instance, validate_schema_documents


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="pathos_data")
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate = subcommands.add_parser("validate")
    validate.add_argument("--fixture", type=Path)
    export = subcommands.add_parser("export-frontend")
    export.add_argument("--input", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    normalize = subcommands.add_parser("normalize")
    normalize.add_argument("--input", type=Path, required=True)
    normalize.add_argument("--dry-run", action="store_true")
    collect = subcommands.add_parser("collect")
    collect.add_argument("--university")
    collect.add_argument("--batch-size", type=int)
    subcommands.add_parser("discover-rankings")
    subcommands.add_parser("report")
    discovery = subcommands.add_parser("validate-ranking-discovery")
    discovery.add_argument("--family-inventory", type=Path, required=True)
    discovery.add_argument("--category-inventory", type=Path, required=True)
    discovery.add_argument("--manual-seed", type=Path)
    pilot = subcommands.add_parser("validate-ranking-pilot")
    pilot.add_argument("--seed-batch", type=Path, required=True, action="append")
    pilot.add_argument("--identity-mappings", type=Path, required=True)
    pilot.add_argument("--candidate-observations", type=Path, required=True)
    pilot.add_argument("--coverage-matrix", type=Path, required=True)
    pilot.add_argument("--source-manifest", type=Path, required=True)
    pilot.add_argument("--result-output", type=Path, required=True)
    corpus = subcommands.add_parser("validate-ranking-corpus")
    corpus.add_argument("--root", type=Path, required=True)
    corpus.add_argument("--output", type=Path, required=True)
    candidate = subcommands.add_parser("generate-universe-candidate")
    candidate.add_argument("--corpus-root", type=Path, required=True)
    candidate.add_argument("--corpus-validation-result", type=Path, required=True)
    candidate.add_argument("--output", type=Path, required=True)
    candidate_validation = subcommands.add_parser("validate-universe-candidate")
    candidate_validation.add_argument("--candidate", type=Path, required=True)
    candidate_validation.add_argument("--corpus-root", type=Path, required=True)
    candidate_validation.add_argument("--corpus-validation-result", type=Path, required=True)
    candidate_validation.add_argument("--result-output", type=Path, required=True)
    completion = subcommands.add_parser("validate-universe-completion-plan")
    completion.add_argument("--plan", type=Path, required=True)
    completion.add_argument("--category-inventory", type=Path, required=True)
    completion.add_argument("--corpus-validation-result", type=Path, required=True)
    national_completion = subcommands.add_parser("validate-national-completion")
    national_completion.add_argument("--seed-batch", type=Path, required=True, action="append")
    national_completion.add_argument("--identity-mappings", type=Path, required=True)
    national_completion.add_argument("--candidate-observations", type=Path, required=True)
    national_completion.add_argument("--coverage-matrix", type=Path, required=True)
    national_completion.add_argument("--source-manifest", type=Path, required=True)
    national_completion.add_argument("--excluded-entries", type=Path, required=True)
    national_completion.add_argument("--result-output", type=Path, required=True)
    national_import = subcommands.add_parser("prepare-national-manual-seed")
    national_import.add_argument("--input", type=Path, required=True)
    national_import.add_argument("--output", type=Path, required=True)
    priority_batch = subcommands.add_parser("validate-priority-program-batch")
    priority_batch.add_argument("--seed-batch", type=Path, required=True, action="append")
    priority_batch.add_argument("--identity-mappings", type=Path, required=True)
    priority_batch.add_argument("--candidate-observations", type=Path, required=True)
    priority_batch.add_argument("--coverage-matrix", type=Path, required=True)
    priority_batch.add_argument("--source-manifest", type=Path, required=True)
    priority_batch.add_argument("--gap-report", type=Path, required=True)
    priority_batch.add_argument("--result-output", type=Path, required=True)
    priority_import = subcommands.add_parser("prepare-priority-program-batch")
    priority_import.add_argument("--input", type=Path, required=True)
    priority_import.add_argument("--output", type=Path, required=True)
    official_sweep = subcommands.add_parser("validate-official-program-sweep")
    official_sweep.add_argument("--seed-batch", type=Path, required=True, action="append")
    official_sweep.add_argument("--identity-mappings", type=Path, required=True)
    official_sweep.add_argument("--candidate-observations", type=Path, required=True)
    official_sweep.add_argument("--coverage-matrix", type=Path, required=True)
    official_sweep.add_argument("--source-manifest", type=Path, required=True)
    official_sweep.add_argument("--gap-report", type=Path, required=True)
    official_sweep.add_argument("--duplicate-dedupe-report", type=Path, required=True)
    official_sweep.add_argument("--existing-root", type=Path, required=True)
    official_sweep.add_argument("--result-output", type=Path, required=True)
    official_sweep_import = subcommands.add_parser("prepare-official-program-sweep")
    official_sweep_import.add_argument("--input", type=Path, required=True)
    official_sweep_import.add_argument("--existing-root", type=Path, required=True)
    official_sweep_import.add_argument("--output", type=Path, required=True)
    gap_repair = subcommands.add_parser("validate-program-gap-repair")
    gap_repair.add_argument("--seed-batch", type=Path, required=True, action="append")
    gap_repair.add_argument("--identity-mappings", type=Path, required=True)
    gap_repair.add_argument("--candidate-observations", type=Path, required=True)
    gap_repair.add_argument("--coverage-matrix", type=Path, required=True)
    gap_repair.add_argument("--source-manifest", type=Path, required=True)
    gap_repair.add_argument("--gap-repair-report", type=Path, required=True)
    gap_repair.add_argument("--duplicate-dedupe-report", type=Path, required=True)
    gap_repair.add_argument("--existing-root", type=Path, required=True)
    gap_repair.add_argument("--result-output", type=Path, required=True)
    gap_import = subcommands.add_parser("prepare-program-gap-repair")
    gap_import.add_argument("--input", type=Path, required=True)
    gap_import.add_argument("--existing-root", type=Path, required=True)
    gap_import.add_argument("--output", type=Path, required=True)
    top20_attempt = subcommands.add_parser("validate-program-top20-completion-attempt")
    top20_attempt.add_argument("--seed-batches", type=Path, required=True)
    top20_attempt.add_argument("--identity-mappings", type=Path, required=True)
    top20_attempt.add_argument("--candidate-observations", type=Path, required=True)
    top20_attempt.add_argument("--coverage-matrix", type=Path, required=True)
    top20_attempt.add_argument("--source-manifest", type=Path, required=True)
    top20_attempt.add_argument("--gap-report", type=Path, required=True)
    top20_attempt.add_argument("--duplicate-dedupe-report", type=Path, required=True)
    top20_attempt.add_argument("--manual-seed-needed-report", type=Path, required=True)
    top20_attempt.add_argument("--completion-readiness-summary", type=Path, required=True)
    top20_attempt.add_argument("--existing-root", type=Path, required=True)
    top20_attempt.add_argument("--result-output", type=Path, required=True)
    top20_import = subcommands.add_parser("prepare-program-top20-completion-attempt")
    top20_import.add_argument("--existing-root", type=Path, required=True)
    top20_import.add_argument("--output", type=Path, required=True)
    candidate_v2 = subcommands.add_parser("validate-universe-candidate-v2")
    candidate_v2.add_argument("--ranking-root", type=Path, required=True)
    candidate_v2.add_argument("--stage2h-summary", type=Path, required=True)
    candidate_v2.add_argument("--source-policy", type=Path, required=True)
    candidate_v2.add_argument("--candidate-universities", type=Path, required=True)
    candidate_v2.add_argument("--candidate-memberships", type=Path, required=True)
    candidate_v2.add_argument("--candidate-source-manifest", type=Path, required=True)
    candidate_v2.add_argument("--candidate-identity-mappings", type=Path, required=True)
    candidate_v2.add_argument("--candidate-gap-disclosure", type=Path, required=True)
    candidate_v2.add_argument("--candidate-generation-summary", type=Path, required=True)
    candidate_v2.add_argument("--candidate-dedupe-report", type=Path, required=True)
    candidate_v2.add_argument("--result-output", type=Path, required=True)
    candidate_v2_generate = subcommands.add_parser("generate-universe-candidate-v2")
    candidate_v2_generate.add_argument("--ranking-root", type=Path, required=True)
    candidate_v2_generate.add_argument("--stage2h-summary", type=Path, required=True)
    candidate_v2_generate.add_argument("--source-policy", type=Path, required=True)
    candidate_v2_generate.add_argument("--output", type=Path, required=True)
    stage3 = subcommands.add_parser("generate-stage3-program-mvp")
    stage3.add_argument("--candidate-v2", type=Path, required=True)
    stage3.add_argument("--ranking-root", type=Path, required=True)
    stage3.add_argument("--ipeds-cache", type=Path, required=True)
    stage3.add_argument("--output", type=Path, required=True)
    stage3_validate = subcommands.add_parser("validate-stage3-program-mvp")
    stage3_validate.add_argument("--candidate-v2", type=Path, required=True)
    stage3_validate.add_argument("--ranking-root", type=Path, required=True)
    stage3_validate.add_argument("--ipeds-cache", type=Path, required=True)
    stage3_validate.add_argument("--universities", type=Path, required=True)
    stage3_validate.add_argument("--programs", type=Path, required=True)
    stage3_validate.add_argument("--tuition", type=Path, required=True)
    stage3_validate.add_argument("--student-faculty", type=Path, required=True)
    stage3_validate.add_argument("--majors", type=Path, required=True)
    stage3_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3_validate.add_argument("--summary", type=Path, required=True)
    stage3_validate.add_argument("--result-output", type=Path, required=True)
    stage3b = subcommands.add_parser("generate-stage3b-gap-fill")
    stage3b.add_argument("--candidate-v2", type=Path, required=True)
    stage3b.add_argument("--stage3-dir", type=Path, required=True)
    stage3b.add_argument("--ipeds-cache", type=Path, required=True)
    stage3b.add_argument("--official-cache", type=Path, required=True)
    stage3b.add_argument("--alias-mappings", type=Path, required=True)
    stage3b.add_argument("--program-observations", type=Path, required=True)
    stage3b.add_argument("--output", type=Path, required=True)
    stage3b_validate = subcommands.add_parser("validate-stage3b-gap-fill")
    stage3b_validate.add_argument("--candidate-v2", type=Path, required=True)
    stage3b_validate.add_argument("--stage3-dir", type=Path, required=True)
    stage3b_validate.add_argument("--ipeds-cache", type=Path, required=True)
    stage3b_validate.add_argument("--official-cache", type=Path, required=True)
    stage3b_validate.add_argument("--alias-mappings", type=Path, required=True)
    stage3b_validate.add_argument("--program-observations", type=Path, required=True)
    stage3b_validate.add_argument("--universities", type=Path, required=True)
    stage3b_validate.add_argument("--student-faculty", type=Path, required=True)
    stage3b_validate.add_argument("--identity-gap-fill", type=Path, required=True)
    stage3b_validate.add_argument("--tuition-gap-fill", type=Path, required=True)
    stage3b_validate.add_argument("--majors-gap-fill", type=Path, required=True)
    stage3b_validate.add_argument("--program-gap-fill", type=Path, required=True)
    stage3b_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3b_validate.add_argument("--summary", type=Path, required=True)
    stage3b_validate.add_argument("--result-output", type=Path, required=True)
    stage3c = subcommands.add_parser("generate-stage3c-academic-geo-enrichment")
    for command in (stage3c,):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3-dir", type=Path, required=True)
        command.add_argument("--stage3b-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--major-observations", type=Path, required=True)
        command.add_argument("--tuition-observations", type=Path, required=True)
        command.add_argument("--region-mapping", type=Path, required=True)
        command.add_argument("--town-manifest", type=Path, required=True)
        command.add_argument("--town-cache", type=Path, required=True)
        command.add_argument("--report", type=Path, required=True)
    stage3c.add_argument("--output", type=Path, required=True)
    stage3c_validate = subcommands.add_parser("validate-stage3c-academic-geo-enrichment")
    for command in (stage3c_validate,):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3-dir", type=Path, required=True)
        command.add_argument("--stage3b-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--major-observations", type=Path, required=True)
        command.add_argument("--tuition-observations", type=Path, required=True)
        command.add_argument("--region-mapping", type=Path, required=True)
        command.add_argument("--town-manifest", type=Path, required=True)
        command.add_argument("--town-cache", type=Path, required=True)
        command.add_argument("--report", type=Path, required=True)
    stage3c_validate.add_argument("--universities", type=Path, required=True)
    stage3c_validate.add_argument("--official-major-sources", type=Path, required=True)
    stage3c_validate.add_argument("--official-majors", type=Path, required=True)
    stage3c_validate.add_argument("--demo-programs-overlay", type=Path, required=True)
    stage3c_validate.add_argument("--tuition-deepening", type=Path, required=True)
    stage3c_validate.add_argument("--highest-lowest-tuition", type=Path, required=True)
    stage3c_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3c_validate.add_argument("--summary", type=Path, required=True)
    stage3c_validate.add_argument("--result-output", type=Path, required=True)
    stage3c2 = subcommands.add_parser("generate-stage3c2-nearest-towns")
    for command in (stage3c2,):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--place-source-manifest", type=Path, required=True)
        command.add_argument("--cache-dir", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--report-output", type=Path, required=True)
    stage3c2_validate = subcommands.add_parser("validate-stage3c2-nearest-towns")
    for command in (stage3c2_validate,):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--place-source-manifest", type=Path, required=True)
        command.add_argument("--cache-dir", type=Path, required=True)
        command.add_argument("--report", type=Path, required=True)
    stage3c2_validate.add_argument("--nearest-towns", type=Path, required=True)
    stage3c2_validate.add_argument("--place-source", type=Path, required=True)
    stage3c2_validate.add_argument("--place-observations", type=Path, required=True)
    stage3c2_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3c2_validate.add_argument("--summary", type=Path, required=True)
    stage3c2_validate.add_argument("--result-output", type=Path, required=True)
    stage3d = subcommands.add_parser("generate-stage3d-people-narrative")
    stage3d_validate = subcommands.add_parser("validate-stage3d-people-narrative")
    for command in (stage3d, stage3d_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3-dir", type=Path, required=True)
        command.add_argument("--stage3b-dir", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--stage3c2-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--person-mappings", type=Path, required=True)
        command.add_argument("--program-alias-mappings", type=Path, required=True)
        command.add_argument("--top-program-observations", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--history-observations", type=Path, required=True)
        command.add_argument("--interesting-fact-observations", type=Path, required=True)
    stage3d.add_argument("--output", type=Path, required=True)
    stage3d.add_argument("--report-output", type=Path, required=True)
    stage3d_validate.add_argument("--universities", type=Path, required=True)
    stage3d_validate.add_argument("--source-manifest-output", type=Path, required=True)
    stage3d_validate.add_argument("--person-mappings-output", type=Path, required=True)
    stage3d_validate.add_argument("--top-program-students", type=Path, required=True)
    stage3d_validate.add_argument("--notable-attendance", type=Path, required=True)
    stage3d_validate.add_argument("--history", type=Path, required=True)
    stage3d_validate.add_argument("--interesting-facts", type=Path, required=True)
    stage3d_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3d_validate.add_argument("--summary", type=Path, required=True)
    stage3d_validate.add_argument("--report", type=Path, required=True)
    stage3d_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_fill = subcommands.add_parser("generate-stage3d-fill-reviewed-people-narrative")
    stage3d_fill_validate = subcommands.add_parser("validate-stage3d-fill-reviewed-people-narrative")
    for command in (stage3d_fill, stage3d_fill_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--stage3d-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--person-mappings", type=Path, required=True)
        command.add_argument("--program-observations", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--history-observations", type=Path, required=True)
        command.add_argument("--anecdote-observations", type=Path, required=True)
    stage3d_fill.add_argument("--output", type=Path, required=True)
    stage3d_fill.add_argument("--report-output", type=Path, required=True)
    stage3d_fill_validate.add_argument("--program-people", type=Path, required=True)
    stage3d_fill_validate.add_argument("--notable-attendance", type=Path, required=True)
    stage3d_fill_validate.add_argument("--history", type=Path, required=True)
    stage3d_fill_validate.add_argument("--anecdotes", type=Path, required=True)
    stage3d_fill_validate.add_argument("--exclusions", type=Path, required=True)
    stage3d_fill_validate.add_argument("--source-manifest-output", type=Path, required=True)
    stage3d_fill_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3d_fill_validate.add_argument("--summary", type=Path, required=True)
    stage3d_fill_validate.add_argument("--report", type=Path, required=True)
    stage3d_fill_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_fill_batch1 = subcommands.add_parser("generate-stage3d-fill-batch1-history-anecdotes")
    stage3d_fill_batch1_validate = subcommands.add_parser("validate-stage3d-fill-batch1-history-anecdotes")
    for command in (stage3d_fill_batch1, stage3d_fill_batch1_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--stage3d-fill-seed-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--history-observations", type=Path, required=True)
        command.add_argument("--anecdote-observations", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--program-people-observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_fill_batch1.add_argument("--output", type=Path, required=True)
    stage3d_fill_batch1.add_argument("--report-output", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--history", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--anecdotes", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--notable-attendance", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--program-people", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--source-manifest-output", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--exclusions-output", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--summary", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--report", type=Path, required=True)
    stage3d_fill_batch1_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_fill_batch2 = subcommands.add_parser("generate-stage3d-fill-batch2-history-anecdotes")
    stage3d_fill_batch2_validate = subcommands.add_parser("validate-stage3d-fill-batch2-history-anecdotes")
    for command in (stage3d_fill_batch2, stage3d_fill_batch2_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--stage3d-fill-seed-dir", type=Path, required=True)
        command.add_argument("--batch1-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--history-observations", type=Path, required=True)
        command.add_argument("--anecdote-observations", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--program-people-observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_fill_batch2.add_argument("--output", type=Path, required=True)
    stage3d_fill_batch2.add_argument("--report-output", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--history", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--anecdotes", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--notable-attendance", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--program-people", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--source-manifest-output", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--exclusions-output", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--summary", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--report", type=Path, required=True)
    stage3d_fill_batch2_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_people_pilot = subcommands.add_parser("generate-stage3d-fill-people-pilot-notable-attendance")
    stage3d_people_pilot_validate = subcommands.add_parser("validate-stage3d-fill-people-pilot-notable-attendance")
    for command in (stage3d_people_pilot, stage3d_people_pilot_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--stage3d-fill-seed-dir", type=Path, required=True)
        command.add_argument("--batch1-dir", type=Path, required=True)
        command.add_argument("--batch2-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--program-people-observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_people_pilot.add_argument("--output", type=Path, required=True)
    stage3d_people_pilot.add_argument("--report-output", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--notable-attendance", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--program-people", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--exclusions-output", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--source-manifest-output", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--cache-manifest-output", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--gap-disclosure", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--summary", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--report", type=Path, required=True)
    stage3d_people_pilot_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_bulk = subcommands.add_parser("generate-stage3d-fill-bulk-completion-v2")
    stage3d_bulk_validate = subcommands.add_parser("validate-stage3d-fill-bulk-completion-v2")
    for command in (stage3d_bulk, stage3d_bulk_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-dir", type=Path, required=True)
        command.add_argument("--batch1-dir", type=Path, required=True)
        command.add_argument("--batch2-dir", type=Path, required=True)
        command.add_argument("--people-pilot-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--history-observations", type=Path, required=True)
        command.add_argument("--anecdote-observations", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--program-people-observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk.add_argument("--output", type=Path, required=True)
    stage3d_bulk.add_argument("--report-output", type=Path, required=True)
    for name in ("plan", "history", "anecdotes", "notable-attendance", "program-people", "exclusions-output", "source-manifest-output", "cache-manifest-output", "gap-disclosure", "summary"):
        stage3d_bulk_validate.add_argument(f"--{name}", type=Path, required=True)
    stage3d_bulk_validate.add_argument("--report", type=Path, required=True)
    stage3d_bulk_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_bulk_people = subcommands.add_parser("generate-stage3d-fill-bulk-people-completion-v1")
    stage3d_bulk_people_validate = subcommands.add_parser("validate-stage3d-fill-bulk-people-completion-v1")
    for command in (stage3d_bulk_people, stage3d_bulk_people_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--people-pilot-dir", type=Path, required=True)
        command.add_argument("--bulk-v2-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--attendance-observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_people.add_argument("--output", type=Path, required=True)
    stage3d_bulk_people.add_argument("--report-output", type=Path, required=True)
    for name in (
        "plan", "notable-attendance", "program-people", "source-manifest-output",
        "cache-manifest-output", "exclusions-output", "gap-disclosure", "summary",
    ):
        stage3d_bulk_people_validate.add_argument(f"--{name}", type=Path, required=True)
    stage3d_bulk_people_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_bulk_people_v2 = subcommands.add_parser("generate-stage3d-fill-bulk-people-v2")
    stage3d_bulk_people_v2_validate = subcommands.add_parser("validate-stage3d-fill-bulk-people-v2")
    for command in (stage3d_bulk_people_v2, stage3d_bulk_people_v2_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--stage3c-programs", type=Path, required=True)
        command.add_argument("--bulk-people-v1-dir", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_people_v2.add_argument("--output", type=Path, required=True)
    stage3d_bulk_people_v2.add_argument("--report-output", type=Path, required=True)
    for name in (
        "plan", "slot-inventory", "people-observations", "program-person-matches",
        "source-manifest-output", "cache-manifest-output", "exclusions-output",
        "gap-disclosure", "summary",
    ):
        stage3d_bulk_people_v2_validate.add_argument(f"--{name}", type=Path, required=True)
    stage3d_bulk_people_v2_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_bulk_people_v2_batch_a = subcommands.add_parser(
        "generate-stage3d-fill-bulk-people-v2-batch-a"
    )
    stage3d_bulk_people_v2_batch_a_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-people-v2-batch-a"
    )
    for command in (stage3d_bulk_people_v2_batch_a, stage3d_bulk_people_v2_batch_a_validate):
        command.add_argument("--pipeline-v2-dir", type=Path, required=True)
        command.add_argument("--bulk-people-v1-dir", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
    stage3d_bulk_people_v2_batch_a.add_argument("--output", type=Path, required=True)
    stage3d_bulk_people_v2_batch_a.add_argument("--report-output", type=Path, required=True)
    for name in (
        "plan", "notable-attendance", "slot-inventory", "people-observations",
        "program-person-matches", "source-manifest", "cache-manifest", "exclusions",
        "gap-disclosure", "summary",
    ):
        stage3d_bulk_people_v2_batch_a_validate.add_argument(
            f"--{name}", type=Path, required=True
        )
    stage3d_bulk_people_v2_batch_a_validate.add_argument(
        "--result-output", type=Path, required=True
    )
    stage3d_bulk_people_v2_batch_b = subcommands.add_parser(
        "generate-stage3d-fill-bulk-people-v2-batch-b"
    )
    stage3d_bulk_people_v2_batch_b_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-people-v2-batch-b"
    )
    for command in (stage3d_bulk_people_v2_batch_b, stage3d_bulk_people_v2_batch_b_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--pipeline-v2-dir", type=Path, required=True)
        command.add_argument("--bulk-people-v1-dir", type=Path, required=True)
        command.add_argument("--batch-a-dir", type=Path, required=True)
        command.add_argument("--school-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_people_v2_batch_b.add_argument("--output", type=Path, required=True)
    stage3d_bulk_people_v2_batch_b.add_argument("--report-output", type=Path, required=True)
    for name in (
        "plan", "notable-attendance", "program-people", "exclusions-output",
        "source-manifest-output", "cache-manifest-output", "gap-disclosure", "summary",
    ):
        stage3d_bulk_people_v2_batch_b_validate.add_argument(
            f"--{name}", type=Path, required=True
        )
    stage3d_bulk_people_v2_batch_b_validate.add_argument(
        "--result-output", type=Path, required=True
    )
    stage3d_bulk_people_v2_combined = subcommands.add_parser(
        "generate-stage3d-fill-bulk-people-v2-combined-dedup"
    )
    stage3d_bulk_people_v2_combined_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-people-v2-combined-dedup"
    )
    for command in (
        stage3d_bulk_people_v2_combined,
        stage3d_bulk_people_v2_combined_validate,
    ):
        command.add_argument("--batch-dir", type=Path, action="append", required=True)
        command.add_argument("--pin-manifest", type=Path, required=True)
    stage3d_bulk_people_v2_combined.add_argument("--output", type=Path, required=True)
    stage3d_bulk_people_v2_combined.add_argument(
        "--report-output", type=Path, required=True
    )
    stage3d_bulk_people_v2_combined_validate.add_argument(
        "--combined-attendance", type=Path, required=True
    )
    stage3d_bulk_people_v2_combined_validate.add_argument(
        "--duplicate-records", type=Path, required=True
    )
    stage3d_bulk_people_v2_combined_validate.add_argument(
        "--summary", type=Path, required=True
    )
    stage3d_bulk_people_v2_combined_validate.add_argument(
        "--result-output", type=Path, required=True
    )
    stage3d_bulk_completion_wave1 = subcommands.add_parser(
        "generate-stage3d-fill-bulk-completion-wave1"
    )
    stage3d_bulk_completion_wave1_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-completion-wave1"
    )
    for command in (stage3d_bulk_completion_wave1, stage3d_bulk_completion_wave1_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--school-manifest", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_completion_wave2 = subcommands.add_parser(
        "generate-stage3d-fill-bulk-completion-wave2"
    )
    stage3d_bulk_completion_wave2_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-completion-wave2"
    )
    for command in (stage3d_bulk_completion_wave2, stage3d_bulk_completion_wave2_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--school-manifest", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_completion_wave2.add_argument("--output", type=Path, required=True)
    stage3d_bulk_completion_wave2.add_argument("--report-output", type=Path, required=True)
    stage3d_bulk_completion_wave2_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_bulk_completion_wave2_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_bulk_completion_wave3 = subcommands.add_parser(
        "generate-stage3d-fill-bulk-completion-wave3"
    )
    stage3d_bulk_completion_wave3_validate = subcommands.add_parser(
        "validate-stage3d-fill-bulk-completion-wave3"
    )
    for command in (stage3d_bulk_completion_wave3, stage3d_bulk_completion_wave3_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_bulk_completion_wave3.add_argument("--output", type=Path, required=True)
    stage3d_bulk_completion_wave3.add_argument("--report-output", type=Path, required=True)
    stage3d_bulk_completion_wave3_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_bulk_completion_wave3_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave4 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave4"
    )
    stage3d_program_people_wave4_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave4"
    )
    for command in (stage3d_program_people_wave4, stage3d_program_people_wave4_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave4.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave4.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave4_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave4_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave5 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave5"
    )
    stage3d_program_people_wave5_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave5"
    )
    for command in (stage3d_program_people_wave5, stage3d_program_people_wave5_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave5.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave5.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave5_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave5_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave6 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave6"
    )
    stage3d_program_people_wave6_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave6"
    )
    for command in (stage3d_program_people_wave6, stage3d_program_people_wave6_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave6.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave6.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave6_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave6_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave7 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave7"
    )
    stage3d_program_people_wave7_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave7"
    )
    for command in (stage3d_program_people_wave7, stage3d_program_people_wave7_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave7.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave7.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave7_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave7_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave8 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave8"
    )
    stage3d_program_people_wave8_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave8"
    )
    for command in (stage3d_program_people_wave8, stage3d_program_people_wave8_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave8.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave8.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave8_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave8_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave9 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave9"
    )
    stage3d_program_people_wave9_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave9"
    )
    for command in (stage3d_program_people_wave9, stage3d_program_people_wave9_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave9.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave9.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave9_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave9_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_program_people_wave10 = subcommands.add_parser(
        "generate-stage3d-fill-program-people-wave10"
    )
    stage3d_program_people_wave10_validate = subcommands.add_parser(
        "validate-stage3d-fill-program-people-wave10"
    )
    for command in (stage3d_program_people_wave10, stage3d_program_people_wave10_validate):
        command.add_argument("--candidate-v2", type=Path, required=True)
        command.add_argument("--programs", type=Path, required=True)
        command.add_argument("--input-pin-manifest", type=Path, required=True)
        command.add_argument("--source-manifest", type=Path, required=True)
        command.add_argument("--cache-manifest", type=Path, required=True)
        command.add_argument("--observations", type=Path, required=True)
        command.add_argument("--exclusions", type=Path, required=True)
    stage3d_program_people_wave10.add_argument("--output", type=Path, required=True)
    stage3d_program_people_wave10.add_argument("--report-output", type=Path, required=True)
    stage3d_program_people_wave10_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_program_people_wave10_validate.add_argument("--result-output", type=Path, required=True)
    stage3d_closing_hardening = subcommands.add_parser("stage3d-closing-hardening")
    stage3d_closing_hardening.add_argument(
        "--mode", choices=("freeze", "intake", "generate", "validate"), required=True
    )
    stage3d_closing_hardening.add_argument("--pipeline-root", type=Path, required=True)
    stage3d_closing_hardening.add_argument("--config", type=Path, required=True)
    stage3d_closing_hardening.add_argument("--pins", type=Path, required=True)
    stage3d_closing_hardening.add_argument("--intake-metadata", type=Path)
    stage3d_closing_hardening.add_argument("--anchor-overrides", type=Path)
    stage3d_closing_hardening.add_argument("--reviewed-exceptions", type=Path)
    stage3d_closing_hardening.add_argument("--output", type=Path)
    stage3d_closing_hardening.add_argument("--report-output", type=Path)
    stage3d_closing_hardening.add_argument("--artifact-dir", type=Path)
    stage3d_closing_hardening.add_argument("--result-output", type=Path)
    stage4b = subcommands.add_parser("stage4b-unified-official-product-data")
    stage4b.add_argument("--mode", choices=("generate", "validate"), required=True)
    stage4b.add_argument("--repo-root", type=Path, required=True)
    stage4b.add_argument("--output", type=Path)
    stage4b.add_argument("--report-output", type=Path)
    stage4b.add_argument("--artifact-dir", type=Path)
    stage4b.add_argument("--result-output", type=Path)
    stage4c = subcommands.add_parser("stage4c-mvp-critical-data-completion")
    stage4c.add_argument("--mode", choices=("generate", "validate"), required=True)
    stage4c.add_argument("--repo-root", type=Path, required=True)
    stage4c.add_argument("--output", type=Path)
    stage4c.add_argument("--report-output", type=Path)
    stage4c.add_argument("--artifact-dir", type=Path)
    stage4c.add_argument("--result-output", type=Path)
    stage3d_bulk_completion_wave1.add_argument("--output", type=Path, required=True)
    stage3d_bulk_completion_wave1.add_argument("--report-output", type=Path, required=True)
    stage3d_bulk_completion_wave1_validate.add_argument("--artifact-dir", type=Path, required=True)
    stage3d_bulk_completion_wave1_validate.add_argument("--result-output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "validate":
        validate_schema_documents()
        audit_migrations()
        if args.fixture:
            raw = _load_json(args.fixture)
            validate_instance(raw, load_schema("raw-university.json"))
            validate_instance(stage_raw(raw), load_schema("staging-university.json"))
            validate_instance(normalize_staged(stage_raw(raw)), load_schema("canonical-university.json"))
        print("Schema and migration validation passed")
        return 0

    if args.command == "normalize":
        canonical = normalize_staged(stage_raw(_load_json(args.input)))
        print(json.dumps(canonical, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-frontend":
        records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
        write_formal_frontend_export(records, args.output)
        print(f"Wrote canonical-only frontend export to {args.output}")
        return 0

    if args.command == "validate-ranking-discovery":
        validate_ranking_family_inventory(_load_json(args.family_inventory))
        validate_category_inventory(_load_json(args.category_inventory))
        if args.manual_seed:
            stage_manual_seed_batch(_load_json(args.manual_seed))
        print("Ranking discovery validation passed")
        return 0

    if args.command == "validate-ranking-pilot":
        batches = [_load_json(path) for path in args.seed_batch]
        identities = _load_json(args.identity_mappings)
        result = validate_pilot_artifacts(
            batches, identities, _load_json(args.candidate_observations),
            _load_json(args.coverage_matrix), _load_json(args.source_manifest),
        )
        write_pilot_validation_result(result, args.result_output, " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-ranking-pilot"]))
        print("Ranking collection pilot validation passed")
        return 0

    if args.command == "validate-ranking-corpus":
        result = validate_corpus(args.root)
        write_corpus_artifacts(result, args.output)
        print("Ranking corpus validation passed")
        return 0

    if args.command == "generate-universe-candidate":
        corpus_result = validate_corpus(args.corpus_root, materialize=True)
        candidate = build_candidate(corpus_result)
        write_candidate(
            candidate,
            args.output,
            corpus_result,
            _load_json(args.corpus_validation_result),
        )
        print("Universe candidate generation passed")
        return 0

    if args.command == "validate-universe-candidate":
        corpus_result = validate_corpus(args.corpus_root, materialize=True)
        candidate_document = _load_json(args.candidate)
        validate_candidate(
            candidate_document,
            corpus_result,
            _load_json(args.corpus_validation_result),
        )
        write_candidate_validation_result(
            candidate_document,
            corpus_result,
            _load_json(args.corpus_validation_result),
            args.result_output,
        )
        print("Universe candidate validation passed")
        return 0

    if args.command == "validate-universe-completion-plan":
        validate_universe_completion_plan(
            _load_json(args.plan),
            _load_json(args.category_inventory),
            _load_json(args.corpus_validation_result),
        )
        print("Universe completion plan validation passed")
        return 0

    if args.command == "validate-national-completion":
        result = validate_national_completion_artifacts(
            [_load_json(path) for path in args.seed_batch],
            _load_json(args.identity_mappings),
            _load_json(args.candidate_observations),
            _load_json(args.coverage_matrix),
            _load_json(args.source_manifest),
            _load_json(args.excluded_entries),
        )
        write_national_completion_validation_result(
            result,
            args.result_output,
            " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-national-completion"]),
        )
        print("National completion validation passed")
        return 0

    if args.command == "prepare-national-manual-seed":
        write_national_manual_seed_bundle(
            build_national_manual_seed_bundle(_load_json(args.input)),
            args.output,
        )
        print("National manual seed bundle prepared")
        return 0

    if args.command == "validate-priority-program-batch":
        result = validate_priority_program_batch_artifacts(
            [_load_json(path) for path in args.seed_batch],
            _load_json(args.identity_mappings),
            _load_json(args.candidate_observations),
            _load_json(args.coverage_matrix),
            _load_json(args.source_manifest),
            _load_json(args.gap_report),
        )
        write_priority_program_batch_validation_result(
            result,
            args.result_output,
            " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-priority-program-batch"]),
        )
        print("Priority program official batch validation passed")
        return 0

    if args.command == "prepare-priority-program-batch":
        write_priority_program_batch_bundle(
            build_priority_program_batch_bundle(_load_json(args.input)), args.output
        )
        print("Priority program official batch prepared")
        return 0

    if args.command == "validate-official-program-sweep":
        result = validate_official_program_sweep_artifacts(
            [_load_json(path) for path in args.seed_batch],
            _load_json(args.identity_mappings),
            _load_json(args.candidate_observations),
            _load_json(args.coverage_matrix),
            _load_json(args.source_manifest),
            _load_json(args.gap_report),
            _load_json(args.duplicate_dedupe_report),
            args.existing_root,
        )
        write_official_program_sweep_validation_result(
            result,
            args.result_output,
            " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-official-program-sweep"]),
        )
        print("Official program source sweep validation passed")
        return 0

    if args.command == "prepare-official-program-sweep":
        write_official_program_sweep_bundle(
            build_official_program_sweep_bundle(_load_json(args.input), args.existing_root),
            args.output,
        )
        print("Official program source sweep prepared")
        return 0

    if args.command == "validate-program-gap-repair":
        result = validate_program_gap_repair_artifacts(
            [_load_json(path) for path in args.seed_batch],
            _load_json(args.identity_mappings), _load_json(args.candidate_observations),
            _load_json(args.coverage_matrix), _load_json(args.source_manifest),
            _load_json(args.gap_repair_report), _load_json(args.duplicate_dedupe_report),
            args.existing_root,
        )
        write_program_gap_repair_validation_result(
            result, args.result_output,
            " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-program-gap-repair"]),
        )
        print("Program ranking gap repair validation passed")
        return 0

    if args.command == "prepare-program-gap-repair":
        write_program_gap_repair_bundle(
            build_program_gap_repair_bundle(_load_json(args.input), args.existing_root), args.output
        )
        print("Program ranking gap repair bundle prepared")
        return 0

    if args.command == "validate-program-top20-completion-attempt":
        result = validate_program_top20_completion_attempt_artifacts(
            _load_json(args.seed_batches), _load_json(args.identity_mappings),
            _load_json(args.candidate_observations), _load_json(args.coverage_matrix),
            _load_json(args.source_manifest), _load_json(args.gap_report),
            _load_json(args.duplicate_dedupe_report), _load_json(args.manual_seed_needed_report),
            _load_json(args.completion_readiness_summary), args.existing_root,
        )
        write_program_top20_completion_attempt_validation_result(
            result, args.result_output,
            " ".join(["PYTHONPATH=src", "python3", "-m", "pathos_data", "validate-program-top20-completion-attempt"]),
        )
        print("Program Top-20 completion-attempt validation passed")
        return 0

    if args.command == "prepare-program-top20-completion-attempt":
        write_program_top20_completion_attempt_bundle(
            build_program_top20_completion_attempt_bundle(args.existing_root), args.output
        )
        print("Program Top-20 completion-attempt bundle prepared")
        return 0

    if args.command == "generate-universe-candidate-v2":
        artifacts = build_candidate_v2(args.ranking_root, _load_json(args.stage2h_summary))
        validation = validate_candidate_v2_artifacts(
            artifacts, args.ranking_root, _load_json(args.stage2h_summary),
            args.source_policy.read_text(encoding="utf-8"),
        )
        write_candidate_v2_bundle(artifacts, args.output, validation)
        print("Universe candidate v2 generation passed")
        return 0

    if args.command == "validate-universe-candidate-v2":
        artifacts = {
            "candidate-universities.json": _load_json(args.candidate_universities),
            "candidate-memberships.json": _load_json(args.candidate_memberships),
            "candidate-source-manifest.json": _load_json(args.candidate_source_manifest),
            "candidate-identity-mappings.json": _load_json(args.candidate_identity_mappings),
            "candidate-gap-disclosure.json": _load_json(args.candidate_gap_disclosure),
            "candidate-generation-summary.json": _load_json(args.candidate_generation_summary),
            "candidate-dedupe-report.json": _load_json(args.candidate_dedupe_report),
        }
        validation = validate_candidate_v2_artifacts(
            artifacts, args.ranking_root, _load_json(args.stage2h_summary),
            args.source_policy.read_text(encoding="utf-8"),
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Universe candidate v2 validation passed")
        return 0

    if args.command == "generate-stage3-program-mvp":
        artifacts = build_stage3_program_mvp(args.candidate_v2, args.ranking_root, args.ipeds_cache)
        validation = validate_stage3_program_mvp(artifacts, args.candidate_v2, args.ranking_root, args.ipeds_cache)
        write_stage3_program_mvp(artifacts, args.output, validation)
        print("Stage 3 program MVP detail pack generation passed")
        return 0

    if args.command == "validate-stage3-program-mvp":
        artifacts = {
            "program-mvp-universities.json": _load_json(args.universities),
            "program-mvp-programs.json": _load_json(args.programs),
            "program-mvp-tuition.json": _load_json(args.tuition),
            "program-mvp-student-faculty.json": _load_json(args.student_faculty),
            "program-mvp-majors.json": _load_json(args.majors),
            "program-mvp-gap-disclosure.json": _load_json(args.gap_disclosure),
            "program-mvp-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3_program_mvp(artifacts, args.candidate_v2, args.ranking_root, args.ipeds_cache)
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Stage 3 program MVP detail pack validation passed")
        return 0

    if args.command == "generate-stage3b-gap-fill":
        artifacts = build_stage3b_gap_fill(
            candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, ipeds_cache=args.ipeds_cache,
            official_cache=args.official_cache, alias_mappings_path=args.alias_mappings,
            program_observations_path=args.program_observations,
        )
        validation = validate_stage3b_gap_fill(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, ipeds_cache=args.ipeds_cache,
            official_cache=args.official_cache, alias_mappings_path=args.alias_mappings,
            program_observations_path=args.program_observations,
        )
        write_stage3b_gap_fill(artifacts, args.output, validation)
        print("Stage 3B demo-critical gap-fill generation passed")
        return 0

    if args.command == "validate-stage3b-gap-fill":
        artifacts = {
            "stage3b-mvp-universities.json": _load_json(args.universities),
            "stage3b-student-faculty.json": _load_json(args.student_faculty),
            "stage3b-identity-gap-fill.json": _load_json(args.identity_gap_fill),
            "stage3b-tuition-gap-fill.json": _load_json(args.tuition_gap_fill),
            "stage3b-majors-gap-fill.json": _load_json(args.majors_gap_fill),
            "stage3b-program-gap-fill.json": _load_json(args.program_gap_fill),
            "stage3b-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3b-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3b_gap_fill(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, ipeds_cache=args.ipeds_cache,
            official_cache=args.official_cache, alias_mappings_path=args.alias_mappings,
            program_observations_path=args.program_observations,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Stage 3B demo-critical gap-fill validation passed")
        return 0

    if args.command == "generate-stage3c-academic-geo-enrichment":
        artifacts = build_stage3c_academic_geo(
            args.candidate_v2, args.stage3_dir, args.stage3b_dir, args.source_manifest,
            args.major_observations, args.tuition_observations, args.region_mapping,
            args.town_manifest, args.town_cache,
        )
        validation = validate_stage3c_academic_geo(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, stage3b_dir=args.stage3b_dir,
            source_manifest_path=args.source_manifest, major_observations_path=args.major_observations,
            tuition_observations_path=args.tuition_observations, region_mapping_path=args.region_mapping,
            town_manifest_path=args.town_manifest, town_cache=args.town_cache, report_path=args.report,
        )
        write_stage3c_academic_geo(artifacts, args.output, validation)
        print("Stage 3C academic and geo enrichment generation passed")
        return 0

    if args.command == "validate-stage3c-academic-geo-enrichment":
        artifacts = {
            "stage3c-universities.json": _load_json(args.universities),
            "stage3c-official-major-sources.json": _load_json(args.official_major_sources),
            "stage3c-official-majors.json": _load_json(args.official_majors),
            "stage3c-demo-programs-overlay.json": _load_json(args.demo_programs_overlay),
            "stage3c-tuition-deepening.json": _load_json(args.tuition_deepening),
            "stage3c-highest-lowest-tuition.json": _load_json(args.highest_lowest_tuition),
            "stage3c-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3c-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3c_academic_geo(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, stage3b_dir=args.stage3b_dir,
            source_manifest_path=args.source_manifest, major_observations_path=args.major_observations,
            tuition_observations_path=args.tuition_observations, region_mapping_path=args.region_mapping,
            town_manifest_path=args.town_manifest, town_cache=args.town_cache, report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3C academic and geo enrichment validation passed")
        return 0

    if args.command == "generate-stage3c2-nearest-towns":
        artifacts = build_stage3c2_nearest_towns(
            args.candidate_v2, args.stage3c_dir, args.place_source_manifest, args.cache_dir,
        )
        args.report_output.write_text(render_stage3c2_report(artifacts), encoding="utf-8")
        validation = validate_stage3c2_nearest_towns(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            place_manifest_path=args.place_source_manifest, cache_dir=args.cache_dir, report_path=args.report_output,
        )
        write_stage3c2_artifacts(artifacts, args.output, validation)
        print("Stage 3C2 nearest-towns gap repair generation passed")
        return 0

    if args.command == "validate-stage3c2-nearest-towns":
        artifacts = {
            "stage3c2-nearest-towns.json": _load_json(args.nearest_towns),
            "stage3c2-place-source-manifest.json": _load_json(args.place_source),
            "stage3c2-place-observations.json": _load_json(args.place_observations),
            "stage3c2-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3c2-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3c2_nearest_towns(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            place_manifest_path=args.place_source_manifest, cache_dir=args.cache_dir, report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3C2 nearest-towns gap repair validation passed")
        return 0

    if args.command == "generate-stage3d-people-narrative":
        artifacts = build_stage3d_people_narrative(
            args.candidate_v2, args.stage3_dir, args.stage3b_dir, args.stage3c_dir, args.stage3c2_dir,
            args.source_manifest, args.person_mappings, args.program_alias_mappings,
            args.top_program_observations, args.attendance_observations, args.history_observations,
            args.interesting_fact_observations,
        )
        args.report_output.write_text(render_stage3d_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_people_narrative(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, stage3b_dir=args.stage3b_dir,
            stage3c_dir=args.stage3c_dir, stage3c2_dir=args.stage3c2_dir, source_manifest_path=args.source_manifest,
            person_mappings_path=args.person_mappings, program_alias_mappings_path=args.program_alias_mappings,
            top_program_observations_path=args.top_program_observations, attendance_observations_path=args.attendance_observations,
            history_observations_path=args.history_observations, interesting_fact_observations_path=args.interesting_fact_observations,
            report_path=args.report_output,
        )
        write_stage3d_artifacts(artifacts, args.output, validation)
        print("Stage 3D people and narrative overlay generation passed")
        return 0

    if args.command == "validate-stage3d-people-narrative":
        artifacts = {
            "stage3d-universities.json": _load_json(args.universities),
            "stage3d-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-person-identity-mappings.json": _load_json(args.person_mappings_output),
            "stage3d-top-program-notable-students.json": _load_json(args.top_program_students),
            "stage3d-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-history.json": _load_json(args.history),
            "stage3d-interesting-facts.json": _load_json(args.interesting_facts),
            "stage3d-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_people_narrative(
            artifacts, candidate_path=args.candidate_v2, stage3_dir=args.stage3_dir, stage3b_dir=args.stage3b_dir,
            stage3c_dir=args.stage3c_dir, stage3c2_dir=args.stage3c2_dir, source_manifest_path=args.source_manifest,
            person_mappings_path=args.person_mappings, program_alias_mappings_path=args.program_alias_mappings,
            top_program_observations_path=args.top_program_observations, attendance_observations_path=args.attendance_observations,
            history_observations_path=args.history_observations, interesting_fact_observations_path=args.interesting_fact_observations,
            report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D people and narrative validation passed")
        return 0

    if args.command == "generate-stage3d-fill-reviewed-people-narrative":
        artifacts = build_stage3d_fill(
            args.candidate_v2, args.stage3c_dir, args.stage3d_dir, args.source_manifest,
            args.person_mappings, args.program_observations, args.attendance_observations,
            args.history_observations, args.anecdote_observations,
        )
        args.report_output.write_text(render_stage3d_fill_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_fill(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir, stage3d_dir=args.stage3d_dir,
            source_manifest_path=args.source_manifest, person_mappings_path=args.person_mappings,
            program_observations_path=args.program_observations, attendance_observations_path=args.attendance_observations,
            history_observations_path=args.history_observations, anecdote_observations_path=args.anecdote_observations,
            report_path=args.report_output,
        )
        write_stage3d_fill(artifacts, args.output, validation)
        print("Stage 3D-Fill reviewed people and narrative generation passed")
        return 0

    if args.command == "validate-stage3d-fill-reviewed-people-narrative":
        artifacts = {
            "stage3d-fill-program-people.json": _load_json(args.program_people),
            "stage3d-fill-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-history.json": _load_json(args.history),
            "stage3d-fill-anecdotes.json": _load_json(args.anecdotes),
            "stage3d-fill-exclusions.json": _load_json(args.exclusions),
            "stage3d-fill-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir, stage3d_dir=args.stage3d_dir,
            source_manifest_path=args.source_manifest, person_mappings_path=args.person_mappings,
            program_observations_path=args.program_observations, attendance_observations_path=args.attendance_observations,
            history_observations_path=args.history_observations, anecdote_observations_path=args.anecdote_observations,
            report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D-Fill reviewed people and narrative validation passed")
        return 0

    if args.command == "generate-stage3d-fill-batch1-history-anecdotes":
        artifacts = build_stage3d_fill_batch1(
            args.candidate_v2, args.stage3c_dir, args.stage3d_fill_seed_dir, args.source_manifest,
            args.history_observations, args.anecdote_observations, args.attendance_observations,
            args.program_people_observations, args.exclusions,
        )
        args.report_output.write_text(render_stage3d_fill_batch1_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_fill_batch1(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, source_manifest_path=args.source_manifest,
            history_observations_path=args.history_observations, anecdote_observations_path=args.anecdote_observations,
            attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations, exclusions_path=args.exclusions,
            report_path=args.report_output,
        )
        write_stage3d_fill_batch1(artifacts, args.output, validation)
        print("Stage 3D-Fill Batch 1 history and anecdotes generation passed")
        return 0

    if args.command == "validate-stage3d-fill-batch1-history-anecdotes":
        artifacts = {
            "stage3d-fill-batch1-history.json": _load_json(args.history),
            "stage3d-fill-batch1-anecdotes.json": _load_json(args.anecdotes),
            "stage3d-fill-batch1-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-batch1-program-people.json": _load_json(args.program_people),
            "stage3d-fill-batch1-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-batch1-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-batch1-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-batch1-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_batch1(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, source_manifest_path=args.source_manifest,
            history_observations_path=args.history_observations, anecdote_observations_path=args.anecdote_observations,
            attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations, exclusions_path=args.exclusions,
            report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D-Fill Batch 1 history and anecdotes validation passed")
        return 0

    if args.command == "generate-stage3d-fill-batch2-history-anecdotes":
        artifacts = build_stage3d_fill_batch2(
            args.candidate_v2, args.stage3c_dir, args.stage3d_fill_seed_dir, args.batch1_dir,
            args.source_manifest, args.history_observations, args.anecdote_observations,
            args.attendance_observations, args.program_people_observations, args.exclusions,
        )
        args.report_output.write_text(render_stage3d_fill_batch2_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_fill_batch2(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, batch1_dir=args.batch1_dir,
            source_manifest_path=args.source_manifest, history_observations_path=args.history_observations,
            anecdote_observations_path=args.anecdote_observations,
            attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations,
            exclusions_path=args.exclusions, report_path=args.report_output,
        )
        write_stage3d_fill_batch2(artifacts, args.output, validation)
        print("Stage 3D-Fill Batch 2 history and anecdotes generation passed")
        return 0

    if args.command == "validate-stage3d-fill-batch2-history-anecdotes":
        artifacts = {
            "stage3d-fill-batch2-history.json": _load_json(args.history),
            "stage3d-fill-batch2-anecdotes.json": _load_json(args.anecdotes),
            "stage3d-fill-batch2-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-batch2-program-people.json": _load_json(args.program_people),
            "stage3d-fill-batch2-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-batch2-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-batch2-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-batch2-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_batch2(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, batch1_dir=args.batch1_dir,
            source_manifest_path=args.source_manifest, history_observations_path=args.history_observations,
            anecdote_observations_path=args.anecdote_observations,
            attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations,
            exclusions_path=args.exclusions, report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D-Fill Batch 2 history and anecdotes validation passed")
        return 0

    if args.command == "generate-stage3d-fill-people-pilot-notable-attendance":
        artifacts = build_stage3d_fill_people_pilot(
            args.candidate_v2, args.stage3c_dir, args.stage3d_fill_seed_dir, args.batch1_dir, args.batch2_dir,
            args.source_manifest, args.cache_manifest, args.attendance_observations,
            args.program_people_observations, args.exclusions,
        )
        args.report_output.write_text(render_stage3d_fill_people_pilot_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_fill_people_pilot(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, batch1_dir=args.batch1_dir,
            batch2_dir=args.batch2_dir, source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest, attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations,
            exclusions_path=args.exclusions, report_path=args.report_output,
        )
        write_stage3d_fill_people_pilot(artifacts, args.output, validation)
        print("Stage 3D-Fill People Pilot notable-attendance generation passed")
        return 0

    if args.command == "validate-stage3d-fill-people-pilot-notable-attendance":
        artifacts = {
            "stage3d-fill-people-pilot-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-people-pilot-program-people.json": _load_json(args.program_people),
            "stage3d-fill-people-pilot-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-people-pilot-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-people-pilot-reviewed-source-cache-manifest.json": _load_json(args.cache_manifest_output),
            "stage3d-fill-people-pilot-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-people-pilot-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_people_pilot(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir,
            stage3d_fill_seed_dir=args.stage3d_fill_seed_dir, batch1_dir=args.batch1_dir,
            batch2_dir=args.batch2_dir, source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest, attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations,
            exclusions_path=args.exclusions, report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D-Fill People Pilot notable-attendance validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-completion-v2":
        artifacts = build_stage3d_fill_bulk_completion_v2(
            args.candidate_v2, args.stage3c_dir, args.batch1_dir, args.batch2_dir, args.people_pilot_dir,
            args.source_manifest, args.cache_manifest, args.history_observations, args.anecdote_observations,
            args.attendance_observations, args.program_people_observations, args.exclusions,
        )
        args.report_output.write_text(render_stage3d_fill_bulk_completion_v2_report(artifacts), encoding="utf-8")
        validation = validate_stage3d_fill_bulk_completion_v2(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir, batch1_dir=args.batch1_dir,
            batch2_dir=args.batch2_dir, people_pilot_dir=args.people_pilot_dir, source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest, history_observations_path=args.history_observations,
            anecdote_observations_path=args.anecdote_observations, attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations, exclusions_path=args.exclusions,
            report_path=args.report_output,
        )
        write_stage3d_fill_bulk_completion_v2(artifacts, args.output, validation)
        print("Stage 3D-Fill Bulk Completion v2 generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-completion-v2":
        artifacts = {
            "stage3d-fill-bulk-v2-plan.json": _load_json(args.plan), "stage3d-fill-bulk-v2-history.json": _load_json(args.history),
            "stage3d-fill-bulk-v2-anecdotes.json": _load_json(args.anecdotes), "stage3d-fill-bulk-v2-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-bulk-v2-program-people.json": _load_json(args.program_people), "stage3d-fill-bulk-v2-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-bulk-v2-source-manifest.json": _load_json(args.source_manifest_output), "stage3d-fill-bulk-v2-cache-manifest.json": _load_json(args.cache_manifest_output),
            "stage3d-fill-bulk-v2-gap-disclosure.json": _load_json(args.gap_disclosure), "stage3d-fill-bulk-v2-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_bulk_completion_v2(
            artifacts, candidate_path=args.candidate_v2, stage3c_dir=args.stage3c_dir, batch1_dir=args.batch1_dir,
            batch2_dir=args.batch2_dir, people_pilot_dir=args.people_pilot_dir, source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest, history_observations_path=args.history_observations,
            anecdote_observations_path=args.anecdote_observations, attendance_observations_path=args.attendance_observations,
            program_people_observations_path=args.program_people_observations, exclusions_path=args.exclusions, report_path=args.report,
        )
        args.result_output.write_text(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Stage 3D-Fill Bulk Completion v2 validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-people-completion-v1":
        inputs = {
            "candidate_path": args.candidate_v2,
            "people_pilot_dir": args.people_pilot_dir,
            "bulk_v2_dir": args.bulk_v2_dir,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "attendance_observations_path": args.attendance_observations,
            "exclusions_path": args.exclusions,
        }
        artifacts = build_stage3d_fill_bulk_people_completion_v1(**inputs)
        validation = validate_stage3d_fill_bulk_people_completion_v1(artifacts, **inputs)
        write_stage3d_fill_bulk_people_completion_v1(artifacts, args.output, validation)
        args.report_output.write_text(
            render_stage3d_fill_bulk_people_completion_v1_report(artifacts), encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People Completion v1 generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-people-completion-v1":
        artifacts = {
            "stage3d-fill-bulk-people-v1-plan.json": _load_json(args.plan),
            "stage3d-fill-bulk-people-v1-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-bulk-people-v1-program-people.json": _load_json(args.program_people),
            "stage3d-fill-bulk-people-v1-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-bulk-people-v1-cache-manifest.json": _load_json(args.cache_manifest_output),
            "stage3d-fill-bulk-people-v1-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-bulk-people-v1-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-bulk-people-v1-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_bulk_people_completion_v1(
            artifacts,
            candidate_path=args.candidate_v2,
            people_pilot_dir=args.people_pilot_dir,
            bulk_v2_dir=args.bulk_v2_dir,
            source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest,
            attendance_observations_path=args.attendance_observations,
            exclusions_path=args.exclusions,
        )
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People Completion v1 validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-people-v2":
        inputs = {
            "candidate_path": args.candidate_v2,
            "stage3c_programs_path": args.stage3c_programs,
            "bulk_people_v1_dir": args.bulk_people_v1_dir,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        artifacts = build_stage3d_fill_bulk_people_v2(**inputs)
        validation = validate_stage3d_fill_bulk_people_v2(artifacts, **inputs)
        write_stage3d_fill_bulk_people_v2(artifacts, args.output, validation)
        args.report_output.write_text(
            render_stage3d_fill_bulk_people_v2_report(artifacts), encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-people-v2":
        artifacts = {
            "stage3d-fill-bulk-people-v2-plan.json": _load_json(args.plan),
            "stage3d-fill-bulk-people-v2-slot-inventory.json": _load_json(args.slot_inventory),
            "stage3d-fill-bulk-people-v2-people-observations.json": _load_json(args.people_observations),
            "stage3d-fill-bulk-people-v2-program-person-matches.json": _load_json(args.program_person_matches),
            "stage3d-fill-bulk-people-v2-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-bulk-people-v2-cache-manifest.json": _load_json(args.cache_manifest_output),
            "stage3d-fill-bulk-people-v2-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-bulk-people-v2-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-bulk-people-v2-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_bulk_people_v2(
            artifacts,
            candidate_path=args.candidate_v2,
            stage3c_programs_path=args.stage3c_programs,
            bulk_people_v1_dir=args.bulk_people_v1_dir,
            source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest,
            observations_path=args.observations,
            exclusions_path=args.exclusions,
        )
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-people-v2-batch-a":
        inputs = {
            "pipeline_v2_dir": args.pipeline_v2_dir,
            "bulk_people_v1_dir": args.bulk_people_v1_dir,
            "observations_path": args.observations,
        }
        artifacts = build_stage3d_fill_bulk_people_v2_batch_a(**inputs)
        validation = validate_stage3d_fill_bulk_people_v2_batch_a(artifacts, **inputs)
        write_stage3d_fill_bulk_people_v2_batch_a(artifacts, args.output, validation)
        args.report_output.write_text(
            render_stage3d_fill_bulk_people_v2_batch_a_report(artifacts),
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 Batch A generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-people-v2-batch-a":
        artifacts = {
            "stage3d-fill-bulk-people-v2-batch-a-plan.json": _load_json(args.plan),
            "stage3d-fill-bulk-people-v2-batch-a-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-bulk-people-v2-batch-a-slot-inventory.json": _load_json(args.slot_inventory),
            "stage3d-fill-bulk-people-v2-batch-a-people-observations.json": _load_json(args.people_observations),
            "stage3d-fill-bulk-people-v2-batch-a-program-person-matches.json": _load_json(args.program_person_matches),
            "stage3d-fill-bulk-people-v2-batch-a-source-manifest.json": _load_json(args.source_manifest),
            "stage3d-fill-bulk-people-v2-batch-a-cache-manifest.json": _load_json(args.cache_manifest),
            "stage3d-fill-bulk-people-v2-batch-a-exclusions.json": _load_json(args.exclusions),
            "stage3d-fill-bulk-people-v2-batch-a-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-bulk-people-v2-batch-a-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_bulk_people_v2_batch_a(
            artifacts,
            pipeline_v2_dir=args.pipeline_v2_dir,
            bulk_people_v1_dir=args.bulk_people_v1_dir,
            observations_path=args.observations,
        )
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 Batch A validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-people-v2-batch-b":
        inputs = {
            "candidate_path": args.candidate_v2,
            "pipeline_v2_dir": args.pipeline_v2_dir,
            "bulk_people_v1_dir": args.bulk_people_v1_dir,
            "batch_a_dir": args.batch_a_dir,
            "school_manifest_path": args.school_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        artifacts = build_stage3d_fill_bulk_people_v2_batch_b(**inputs)
        validation = validate_stage3d_fill_bulk_people_v2_batch_b(artifacts, **inputs)
        write_stage3d_fill_bulk_people_v2_batch_b(artifacts, args.output, validation)
        args.report_output.write_text(
            render_stage3d_fill_bulk_people_v2_batch_b_report(artifacts),
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 Batch B generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-people-v2-batch-b":
        artifacts = {
            "stage3d-fill-bulk-people-v2-batch-b-plan.json": _load_json(args.plan),
            "stage3d-fill-bulk-people-v2-batch-b-notable-attendance.json": _load_json(args.notable_attendance),
            "stage3d-fill-bulk-people-v2-batch-b-program-people.json": _load_json(args.program_people),
            "stage3d-fill-bulk-people-v2-batch-b-exclusions.json": _load_json(args.exclusions_output),
            "stage3d-fill-bulk-people-v2-batch-b-source-manifest.json": _load_json(args.source_manifest_output),
            "stage3d-fill-bulk-people-v2-batch-b-cache-manifest.json": _load_json(args.cache_manifest_output),
            "stage3d-fill-bulk-people-v2-batch-b-gap-disclosure.json": _load_json(args.gap_disclosure),
            "stage3d-fill-bulk-people-v2-batch-b-summary.json": _load_json(args.summary),
        }
        validation = validate_stage3d_fill_bulk_people_v2_batch_b(
            artifacts,
            candidate_path=args.candidate_v2,
            pipeline_v2_dir=args.pipeline_v2_dir,
            bulk_people_v1_dir=args.bulk_people_v1_dir,
            batch_a_dir=args.batch_a_dir,
            school_manifest_path=args.school_manifest,
            source_manifest_path=args.source_manifest,
            cache_manifest_path=args.cache_manifest,
            observations_path=args.observations,
            exclusions_path=args.exclusions,
        )
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 Batch B validation passed")
        return 0

    if args.command == "generate-stage3d-fill-bulk-people-v2-combined-dedup":
        artifacts = build_stage3d_fill_bulk_people_v2_combined_dedup(
            args.batch_dir, args.pin_manifest
        )
        validation = validate_stage3d_fill_bulk_people_v2_combined_dedup(
            artifacts, args.batch_dir, args.pin_manifest
        )
        write_stage3d_fill_bulk_people_v2_combined_dedup(
            artifacts, args.output, validation
        )
        args.report_output.write_text(
            render_stage3d_fill_bulk_people_v2_combined_dedup_report(artifacts),
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 combined dedup generation passed")
        return 0

    if args.command == "validate-stage3d-fill-bulk-people-v2-combined-dedup":
        artifacts = {
            "stage3d-fill-bulk-people-v2-combined-notable-attendance.json": _load_json(
                args.combined_attendance
            ),
            "stage3d-fill-bulk-people-v2-combined-duplicate-records.json": _load_json(
                args.duplicate_records
            ),
            "stage3d-fill-bulk-people-v2-combined-summary.json": _load_json(
                args.summary
            ),
        }
        validation = validate_stage3d_fill_bulk_people_v2_combined_dedup(
            artifacts, args.batch_dir, args.pin_manifest
        )
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk People v2 combined dedup validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-bulk-completion-wave1",
        "validate-stage3d-fill-bulk-completion-wave1",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "school_manifest_path": args.school_manifest,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-bulk-completion-wave1":
            artifacts = build_stage3d_fill_bulk_completion_wave1(**inputs)
            validation = validate_stage3d_fill_bulk_completion_wave1(artifacts, **inputs)
            write_stage3d_fill_bulk_completion_wave1(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_bulk_completion_wave1_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Bulk Completion Wave 1 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_BULK_COMPLETION_WAVE1_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_bulk_completion_wave1(artifacts, **inputs)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk Completion Wave 1 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-bulk-completion-wave2",
        "validate-stage3d-fill-bulk-completion-wave2",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "school_manifest_path": args.school_manifest,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-bulk-completion-wave2":
            artifacts = build_stage3d_fill_bulk_completion_wave2(**inputs)
            validation = validate_stage3d_fill_bulk_completion_wave2(artifacts, **inputs)
            write_stage3d_fill_bulk_completion_wave2(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_bulk_completion_wave2_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Bulk Completion Wave 2 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_BULK_COMPLETION_WAVE2_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_bulk_completion_wave2(artifacts, **inputs)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk Completion Wave 2 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-bulk-completion-wave3",
        "validate-stage3d-fill-bulk-completion-wave3",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-bulk-completion-wave3":
            artifacts = build_stage3d_fill_bulk_completion_wave3(**inputs)
            validation = validate_stage3d_fill_bulk_completion_wave3(artifacts, **inputs)
            write_stage3d_fill_bulk_completion_wave3(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_bulk_completion_wave3_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Bulk Completion Wave 3 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_BULK_COMPLETION_WAVE3_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_bulk_completion_wave3(artifacts, **inputs)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Bulk Completion Wave 3 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave4",
        "validate-stage3d-fill-program-people-wave4",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave4":
            artifacts = build_stage3d_fill_program_people_wave4(**inputs)
            validation = validate_stage3d_fill_program_people_wave4(artifacts, **inputs)
            write_stage3d_fill_program_people_wave4(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave4_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Program People Wave 4 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE4_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave4(artifacts, **inputs)
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 4 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave5",
        "validate-stage3d-fill-program-people-wave5",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave5":
            artifacts = build_stage3d_fill_program_people_wave5(**inputs)
            validation = validate_stage3d_fill_program_people_wave5(artifacts, **inputs)
            write_stage3d_fill_program_people_wave5(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave5_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Program People Wave 5 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE5_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave5(artifacts, **inputs)
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 5 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave6",
        "validate-stage3d-fill-program-people-wave6",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave6":
            artifacts = build_stage3d_fill_program_people_wave6(**inputs)
            validation = validate_stage3d_fill_program_people_wave6(artifacts, **inputs)
            write_stage3d_fill_program_people_wave6(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave6_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D-Fill Program People Wave 6 generation passed")
            return 0
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE6_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave6(artifacts, **inputs)
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 6 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave7",
        "validate-stage3d-fill-program-people-wave7",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave7":
            validate_stage3d_fill_program_people_wave7_artifact_directory(
                args.output,
                require_complete=False,
            )
            validate_stage3d_fill_program_people_wave7_output_path(
                args.output,
                args.report_output,
            )
            artifacts = build_stage3d_fill_program_people_wave7(**inputs)
            validation = validate_stage3d_fill_program_people_wave7(artifacts, **inputs)
            write_stage3d_fill_program_people_wave7(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave7_report(artifacts), encoding="utf-8"
            )
            validate_stage3d_fill_program_people_wave7_artifact_directory(
                args.output,
                require_complete=True,
            )
            print("Stage 3D-Fill Program People Wave 7 generation passed")
            return 0
        validate_stage3d_fill_program_people_wave7_output_path(
            args.artifact_dir,
            args.result_output,
        )
        validate_stage3d_fill_program_people_wave7_artifact_directory(
            args.artifact_dir,
            require_complete=True,
        )
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE7_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave7(artifacts, **inputs)
        validate_stage3d_fill_program_people_wave7_committed_result(
            args.artifact_dir,
            validation,
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 7 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave8",
        "validate-stage3d-fill-program-people-wave8",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave8":
            validate_stage3d_fill_program_people_wave8_artifact_directory(
                args.output,
                require_complete=False,
            )
            validate_stage3d_fill_program_people_wave8_output_path(
                args.output,
                args.report_output,
            )
            artifacts = build_stage3d_fill_program_people_wave8(**inputs)
            validation = validate_stage3d_fill_program_people_wave8(artifacts, **inputs)
            write_stage3d_fill_program_people_wave8(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave8_report(artifacts), encoding="utf-8"
            )
            validate_stage3d_fill_program_people_wave8_artifact_directory(
                args.output,
                require_complete=True,
            )
            print("Stage 3D-Fill Program People Wave 8 generation passed")
            return 0
        validate_stage3d_fill_program_people_wave8_output_path(
            args.artifact_dir,
            args.result_output,
        )
        validate_stage3d_fill_program_people_wave8_artifact_directory(
            args.artifact_dir,
            require_complete=True,
        )
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE8_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave8(artifacts, **inputs)
        validate_stage3d_fill_program_people_wave8_committed_result(
            args.artifact_dir,
            validation,
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 8 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave9",
        "validate-stage3d-fill-program-people-wave9",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave9":
            validate_stage3d_fill_program_people_wave9_artifact_directory(
                args.output, require_complete=False
            )
            validate_stage3d_fill_program_people_wave9_output_path(
                args.output, args.report_output
            )
            artifacts = build_stage3d_fill_program_people_wave9(**inputs)
            validation = validate_stage3d_fill_program_people_wave9(artifacts, **inputs)
            write_stage3d_fill_program_people_wave9(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave9_report(artifacts), encoding="utf-8"
            )
            validate_stage3d_fill_program_people_wave9_artifact_directory(
                args.output, require_complete=True
            )
            print("Stage 3D-Fill Program People Wave 9 generation passed")
            return 0
        validate_stage3d_fill_program_people_wave9_output_path(
            args.artifact_dir, args.result_output
        )
        validate_stage3d_fill_program_people_wave9_artifact_directory(
            args.artifact_dir, require_complete=True
        )
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE9_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave9(artifacts, **inputs)
        validate_stage3d_fill_program_people_wave9_committed_result(
            args.artifact_dir, validation
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 9 validation passed")
        return 0

    if args.command in {
        "generate-stage3d-fill-program-people-wave10",
        "validate-stage3d-fill-program-people-wave10",
    }:
        inputs = {
            "candidate_path": args.candidate_v2,
            "programs_path": args.programs,
            "input_pin_manifest_path": args.input_pin_manifest,
            "source_manifest_path": args.source_manifest,
            "cache_manifest_path": args.cache_manifest,
            "observations_path": args.observations,
            "exclusions_path": args.exclusions,
        }
        if args.command == "generate-stage3d-fill-program-people-wave10":
            validate_stage3d_fill_program_people_wave10_artifact_directory(
                args.output, require_complete=False
            )
            validate_stage3d_fill_program_people_wave10_output_path(
                args.output, args.report_output
            )
            artifacts = build_stage3d_fill_program_people_wave10(**inputs)
            validation = validate_stage3d_fill_program_people_wave10(artifacts, **inputs)
            write_stage3d_fill_program_people_wave10(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_fill_program_people_wave10_report(artifacts), encoding="utf-8"
            )
            validate_stage3d_fill_program_people_wave10_artifact_directory(
                args.output, require_complete=True
            )
            print("Stage 3D-Fill Program People Wave 10 generation passed")
            return 0
        validate_stage3d_fill_program_people_wave10_output_path(
            args.artifact_dir, args.result_output
        )
        validate_stage3d_fill_program_people_wave10_artifact_directory(
            args.artifact_dir, require_complete=True
        )
        artifacts = {
            name: _load_json(args.artifact_dir / name)
            for name in STAGE3D_FILL_PROGRAM_PEOPLE_WAVE10_OUTPUT_FILES
        }
        validation = validate_stage3d_fill_program_people_wave10(artifacts, **inputs)
        validate_stage3d_fill_program_people_wave10_committed_result(
            args.artifact_dir, validation
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D-Fill Program People Wave 10 validation passed")
        return 0

    if args.command == "stage3d-closing-hardening":
        config = _load_json(args.config)
        if args.mode == "freeze":
            pins = build_stage3d_closing_hardening_pins(args.pipeline_root)
            args.pins.parent.mkdir(parents=True, exist_ok=True)
            args.pins.write_text(
                json.dumps(pins, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print("Stage 3D closing hardening input freeze passed")
            return 0
        validate_stage3d_closing_input_pins(_load_json(args.pins), args.pipeline_root)
        required_inputs = (
            args.intake_metadata, args.anchor_overrides, args.reviewed_exceptions
        )
        if any(path is None for path in required_inputs):
            parser.error("closing intake/generate/validate requires metadata, overrides, and exceptions")
        if args.mode == "intake":
            state = load_stage3d_closing_cumulative_state(args.pipeline_root)
            intake_config = config["live_intake"]
            cache_dir = args.pipeline_root / intake_config["cache_directory"]
            metadata = run_stage3d_closing_live_intake(
                state["positives"], state["sources"], cache_dir,
                pipeline_root=args.pipeline_root,
                timeout_seconds=intake_config["timeout_seconds"],
                max_workers=intake_config["max_workers"],
                max_retries=intake_config["max_retries"],
                user_agent=intake_config["user_agent"],
                expected_source_count=180,
            )
            args.intake_metadata.parent.mkdir(parents=True, exist_ok=True)
            args.intake_metadata.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print("Stage 3D closing hardening live intake completed")
            return 0
        build_inputs = (
            args.pipeline_root, args.config, args.pins, args.intake_metadata,
            args.anchor_overrides, args.reviewed_exceptions,
        )
        if args.mode == "generate":
            if args.output is None or args.report_output is None:
                parser.error("closing generate requires --output and --report-output")
            artifacts = build_stage3d_closing_hardening(*build_inputs)
            validation = validate_stage3d_closing_hardening(artifacts, *build_inputs)
            write_stage3d_closing_hardening(artifacts, args.output, validation)
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                render_stage3d_closing_hardening_report(artifacts), encoding="utf-8"
            )
            print("Stage 3D closing hardening deterministic generation passed")
            return 0
        if args.artifact_dir is None or args.result_output is None:
            parser.error("closing validate requires --artifact-dir and --result-output")
        artifacts = load_stage3d_closing_hardening_artifacts(args.artifact_dir)
        validation = validate_stage3d_closing_hardening(artifacts, *build_inputs)
        validate_committed_closing_result(args.artifact_dir, validation)
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("Stage 3D closing hardening validation passed")
        return 0

    if args.command == "stage4b-unified-official-product-data":
        if args.mode == "generate":
            if args.output is None or args.report_output is None:
                parser.error("Stage 4B generate requires --output and --report-output")
            bundle = build_validated_stage4b(args.repo_root)
            write_stage4b_artifacts(bundle, args.output)
            write_stage4b_reports(bundle, args.report_output)
            print("Stage 4B deterministic generation passed")
            return 0
        if args.artifact_dir is None or args.result_output is None:
            parser.error(
                "Stage 4B validate requires --artifact-dir and --result-output"
            )
        validation = validate_committed_stage4b(
            args.artifact_dir, args.repo_root
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            stage4b_canonical_json(validation), encoding="utf-8"
        )
        print("Stage 4B validation passed")
        return 0

    if args.command == "stage4c-mvp-critical-data-completion":
        if args.mode == "generate":
            if args.output is None or args.report_output is None:
                parser.error("Stage 4C generate requires --output and --report-output")
            bundle = build_validated_stage4c(args.repo_root)
            write_stage4c_artifacts(bundle, args.output)
            write_stage4c_reports(bundle, args.report_output)
            print("Stage 4C deterministic generation passed")
            return 0
        if args.artifact_dir is None or args.result_output is None:
            parser.error(
                "Stage 4C validate requires --artifact-dir and --result-output"
            )
        validation = validate_committed_stage4c(
            args.artifact_dir, args.repo_root
        )
        args.result_output.parent.mkdir(parents=True, exist_ok=True)
        args.result_output.write_text(
            stage4c_canonical_json(validation), encoding="utf-8"
        )
        print("Stage 4C validation passed")
        return 0

    if args.command in {"collect", "discover-rankings", "report"}:
        print(f"{args.command} is a phase-1 dry-run skeleton; no network collection was performed")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
