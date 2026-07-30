"""Versioned JSON Schema 的离线验证测试。"""

import json
import unittest
from pathlib import Path

from pathos_data.schema_validation import (
    SchemaValidationError,
    load_schema,
    validate_instance,
    validate_schema_documents,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "test-university-raw.json"


class JsonSchemaTests(unittest.TestCase):
    def test_versioned_schema_documents_are_well_formed(self) -> None:
        validate_schema_documents()

    def test_raw_validation_follows_the_referenced_university_schema(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["university"]["unitid"] = "not-an-ipeds-id"
        with self.assertRaises(SchemaValidationError):
            validate_instance(raw, load_schema("raw-university.json"))
