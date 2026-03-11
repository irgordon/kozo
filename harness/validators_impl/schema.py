from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from harness.codes import OK, SCHEMA_INVALID
from harness.validator import BaseValidator, ValidationResult

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_DIR = _REPO_ROOT / "schemas"
_SCHEMA_PATHS = {
    "todo": _SCHEMA_DIR / "todo.schema.json",
    "runtime": _SCHEMA_DIR / "runtime.schema.json",
    "latest_verify": _SCHEMA_DIR / "latest_verify.schema.json",
    "agent_context": _SCHEMA_DIR / "agent_context.schema.json",
}


def _load_schema(name: str) -> Dict[str, Any]:
    try:
        return json.loads(_SCHEMA_PATHS[name].read_text())
    except KeyError as exc:
        raise ValueError(f"Unknown schema document {name!r}") from exc


def _validate_type(value: Any, expected: str, path: str) -> None:
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    if expected not in checks:
        raise ValueError(f"{path}: unsupported schema type {expected!r}")
    if not checks[expected](value):
        raise ValueError(f"{path}: expected {expected}, got {type(value).__name__}")


def _validate_object(value: Dict[str, Any], schema: Dict[str, Any], path: str) -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for key in required:
        if key not in value:
            raise ValueError(f"{path}: missing required property {key!r}")
    if schema.get("additionalProperties") is False:
        extras = sorted(set(value.keys()) - set(properties.keys()))
        if extras:
            raise ValueError(f"{path}: unexpected properties {extras}")
    for key, subschema in properties.items():
        if key in value:
            _validate_schema(value[key], subschema, f"{path}.{key}")


def _validate_array(value: list[Any], schema: Dict[str, Any], path: str) -> None:
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(value) < min_items:
        raise ValueError(f"{path}: expected at least {min_items} items")
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            _validate_schema(item, item_schema, f"{path}[{index}]")


def _validate_string(value: str, schema: Dict[str, Any], path: str) -> None:
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.search(pattern, value) is None:
        raise ValueError(f"{path}: value does not match pattern {pattern!r}")


def _validate_enum_and_const(value: Any, schema: Dict[str, Any], path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: expected constant value {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: expected one of {schema['enum']!r}")


def _validate_schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        _validate_type(value, expected_type, path)
    _validate_enum_and_const(value, schema, path)
    if expected_type == "object":
        _validate_object(value, schema, path)
    if expected_type == "array":
        _validate_array(value, schema, path)
    if expected_type == "string":
        _validate_string(value, schema, path)


def validate_named_document(name: str, data: Dict[str, Any]) -> None:
    _validate_schema(data, _load_schema(name), name)


class SchemaValidator(BaseValidator):
    name = "schema"
    subsystem = "schema"

    def validate(self, artifact_bundle):
        try:
            validate_named_document("todo", artifact_bundle["todo"])
            validate_named_document("runtime", artifact_bundle["runtime"])
        except (KeyError, ValueError) as exc:
            return ValidationResult.fail(
                code=SCHEMA_INVALID,
                detail=f"Schema validation failed: {exc}",
                action="Align the task artifacts with schemas/*.schema.json",
            )
        return ValidationResult.pass_(code=OK, detail="Task artifacts satisfy the declared schemas")
