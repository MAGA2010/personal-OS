"""Small, dependency-free validator for the JSON Schema features used here."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable


PIPELINE_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = PIPELINE_ROOT / "schemas" / "v1"


class SchemaValidationError(ValueError):
    """Raised when a schema document or record violates its contract."""


def load_schema(name: str) -> Dict[str, Any]:
    """Load one versioned local schema by file name."""
    path = SCHEMA_ROOT / name
    if not path.is_file():
        raise SchemaValidationError(f"Unknown schema: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_local_ref(reference: str) -> Dict[str, Any]:
    """Resolve a schema file reference; phase 1 deliberately has no remote refs."""
    filename, _, fragment = reference.partition("#")
    if fragment not in ("", "/"):
        raise SchemaValidationError(f"Unsupported JSON Pointer reference: {reference}")
    if not filename:
        raise SchemaValidationError(f"Unsupported same-document reference: {reference}")
    return load_schema(filename)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SchemaValidationError(f"Unsupported schema type: {expected}")


def validate_instance(instance: Any, schema: Dict[str, Any], path: str = "$") -> None:
    """Validate the documented JSON Schema subset used by pipeline payloads."""
    if "$ref" in schema:
        validate_instance(instance, _resolve_local_ref(schema["$ref"]), path)
        schema = {key: value for key, value in schema.items() if key != "$ref"}

    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(instance, item) for item in expected_types):
            raise SchemaValidationError(f"{path}: expected {expected}, got {type(instance).__name__}")

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value is not in enum")

    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{path}: value does not equal const")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaValidationError(f"{path}: string is too short")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise SchemaValidationError(f"{path}: string does not match pattern")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"{path}: number is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"{path}: number exceeds maximum")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaValidationError(f"{path}: array has too few items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                validate_instance(item, item_schema, f"{path}[{index}]")

    if isinstance(instance, dict):
        for required in schema.get("required", []):
            if required not in instance:
                raise SchemaValidationError(f"{path}: missing required property '{required}'")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                validate_instance(value, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise SchemaValidationError(f"{path}: unexpected property '{key}'")


def validate_schema_documents(paths: Iterable[Path] = None) -> None:
    """Statically validate versioning metadata without a PostgreSQL service."""
    schema_paths = list(paths) if paths is not None else sorted(SCHEMA_ROOT.glob("*.json"))
    identifiers = set()
    for path in schema_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        for field in ("$schema", "$id", "title", "type"):
            if field not in document:
                raise SchemaValidationError(f"{path.name}: missing {field}")
        if document["$id"] in identifiers:
            raise SchemaValidationError(f"Duplicate schema id: {document['$id']}")
        identifiers.add(document["$id"])
        for reference in _collect_references(document):
            _resolve_local_ref(reference)


def _collect_references(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for nested in value.values():
            yield from _collect_references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _collect_references(nested)
