"""Static audit of numbered PostgreSQL migrations for offline phase-1 validation."""

import re
from pathlib import Path
from typing import Iterable, List

from .schema_validation import SchemaValidationError


PIPELINE_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_ROOT = PIPELINE_ROOT / "migrations"
EXPECTED_TABLES = {
    "sources", "universities", "university_sources", "university_selection_memberships",
    "university_facts", "university_fact_sources", "ranking_snapshots",
    "ranking_snapshot_sources", "university_rankings", "university_ranking_sources",
    "programs", "university_programs", "program_rankings", "program_ranking_sources",
    "tuition_records", "student_faculty_ratio_records", "nearby_places",
    "distinguished_students", "distinguished_student_sources", "public_figures",
    "public_figure_sources", "university_history", "university_history_sources",
    "university_anecdotes", "university_anecdote_sources", "data_quality_issues",
}
EXPECTED_MIGRATIONS = [
    "001_core.sql",
    "002_rankings_and_programs.sql",
    "003_enrichment_and_quality.sql",
    "004_gate1_hardening.sql",
]


def audit_migrations(paths: Iterable[Path] = None) -> List[Path]:
    """Check numbering, required tables and provenance foreign-key declarations."""
    migration_paths = list(paths) if paths is not None else sorted(MIGRATIONS_ROOT.glob("[0-9][0-9][0-9]_*.sql"))
    if [path.name for path in migration_paths] != EXPECTED_MIGRATIONS:
        raise SchemaValidationError("Migration sequence does not match the canonical Gate 1 contract")
    numbers = [int(path.name[:3]) for path in migration_paths]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise SchemaValidationError("Migration files must have unique ascending numeric prefixes")

    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_paths).lower()
    declared = set(re.findall(r"create table\s+([a-z_]+)", sql))
    missing = EXPECTED_TABLES - declared
    if missing:
        raise SchemaValidationError(f"Missing canonical tables: {', '.join(sorted(missing))}")
    if "references sources(source_id)" not in sql:
        raise SchemaValidationError("No foreign key relation to sources")
    if "unique (ranking_system, ranking_family, category, edition)" not in sql:
        raise SchemaValidationError("Ranking snapshot uniqueness is missing")
    hardening_sql = (MIGRATIONS_ROOT / "004_gate1_hardening.sql").read_text(encoding="utf-8").lower()
    if "alter table program_rankings drop column ranking_category" not in hardening_sql:
        raise SchemaValidationError("Program ranking category must be derived from ranking_snapshots")
    return migration_paths
