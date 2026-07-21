"""离线审计 PostgreSQL-compatible migration contract。"""

import unittest
from pathlib import Path

from pathos_data.migration_audit import audit_migrations


class MigrationAuditTests(unittest.TestCase):
    def test_numbered_migrations_define_the_required_canonical_contract(self) -> None:
        migrations = audit_migrations()
        self.assertEqual([path.name for path in migrations], [
            "001_core.sql",
            "002_rankings_and_programs.sql",
            "003_enrichment_and_quality.sql",
            "004_gate1_hardening.sql",
        ])

    def test_program_ranking_category_is_derived_only_from_its_snapshot(self) -> None:
        migration = (Path(__file__).resolve().parents[1] / "migrations" / "004_gate1_hardening.sql")
        sql = migration.read_text(encoding="utf-8").lower()
        self.assertIn("alter table program_rankings drop column ranking_category", sql)
