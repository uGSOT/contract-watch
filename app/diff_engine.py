import re

from typing import Any, Dict, List, Optional


SUPPORTED_DIFF_KINDS = {
    "missing_field",
    "unexpected_field",
    "type_changed",
    "renamed_field",
    "wrong_status",
}


def _normalize_field_name(name: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    normalized = normalized.replace("-", "_").replace(" ", "_")
    normalized = normalized.lower()
    normalized = re.sub(r"[_\s]+", "", normalized)
    return normalized


def _actual_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    return "unknown"


def _validate_schema(schema: Any, path: str = "") -> None:
    if not isinstance(schema, dict):
        raise ValueError("schema must be a JSON object")

    fields = schema.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("schema must contain a fields object")

    if not fields:
        raise ValueError("schema.fields must not be empty")

    for field_name, field_schema in fields.items():
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValueError("field names must be non-empty strings")

        if not isinstance(field_schema, dict):
            raise ValueError(f"schema.fields.{field_name} must be an object")

        field_type = field_schema.get("type")
        if not isinstance(field_type, str) or not field_type.strip():
            raise ValueError(f"schema.fields.{field_name}.type must be a non-empty string")

        if "required" in field_schema and not isinstance(field_schema["required"], bool):
            raise ValueError(f"schema.fields.{field_name}.required must be boolean")

        if field_type == "object" and "fields" in field_schema:
            _validate_schema({"fields": field_schema["fields"]}, path=f"{path}.{field_name}" if path else field_name)

        if field_type == "array" and "items" in field_schema:
            items = field_schema["items"]
            if not isinstance(items, dict):
                raise ValueError(f"schema.fields.{field_name}.items must be an object")
            item_type = items.get("type")
            if not isinstance(item_type, str) or not item_type.strip():
                raise ValueError(f"schema.fields.{field_name}.items.type must be a non-empty string")
            if item_type == "object" and "fields" in items:
                _validate_schema({"fields": items["fields"]}, path=f"{path}.{field_name}" if path else field_name)


def _join_path(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _compare_object_fields(
    schema: Dict[str, Any],
    actual: Any,
    path: str,
    diffs: List[Dict[str, Any]],
) -> None:
    if not isinstance(actual, dict):
        # If actual is not an object, every required field is missing.
        for field_name, field_schema in schema["fields"].items():
            if field_schema.get("required", False):
                diffs.append(
                    {
                        "kind": "missing_field",
                        "field": _join_path(path, field_name),
                        "expected": field_schema.get("type"),
                        "actual": None,
                        "message": f"Expected field '{_join_path(path, field_name)}' is missing",
                    }
                )
        return

    expected_fields = schema["fields"]
    actual_fields = dict(actual)
    unmatched_actual = dict(actual_fields)

    for field_name, field_schema in expected_fields.items():
        current_path = _join_path(path, field_name)
        if field_name in actual_fields:
            unmatched_actual.pop(field_name, None)
            _compare_field(field_schema, actual_fields[field_name], current_path, diffs)
            continue

        rename_match = _find_rename(field_name, field_schema, unmatched_actual)
        if rename_match is not None:
            actual_name, actual_value = rename_match
            unmatched_actual.pop(actual_name, None)
            diffs.append(
                {
                    "kind": "renamed_field",
                    "field": current_path,
                    "expected": field_name,
                    "actual": actual_name,
                    "message": f"Expected field '{current_path}' appears renamed to '{actual_name}'",
                }
            )
            _compare_field(field_schema, actual_value, current_path, diffs)
            continue

        if field_schema.get("required", False):
            diffs.append(
                {
                    "kind": "missing_field",
                    "field": current_path,
                    "expected": field_schema.get("type"),
                    "actual": None,
                    "message": f"Expected field '{current_path}' is missing",
                }
            )

    for actual_name, actual_value in unmatched_actual.items():
        diffs.append(
            {
                "kind": "unexpected_field",
                "field": _join_path(path, actual_name),
                "expected": None,
                "actual": _actual_type_name(actual_value),
                "message": f"Unexpected field '{_join_path(path, actual_name)}' was present",
            }
        )


def _find_rename(field_name: str, field_schema: Dict[str, Any], actual_fields: Dict[str, Any]) -> Optional[tuple[str, Any]]:
    normalized_expected = _normalize_field_name(field_name)
    candidates = []
    for actual_name, actual_value in actual_fields.items():
        normalized_actual = _normalize_field_name(actual_name)
        if normalized_actual == normalized_expected:
            candidates.append((actual_name, actual_value))
    if len(candidates) == 1:
        return candidates[0]
    return None


def _compare_field(
    field_schema: Dict[str, Any],
    actual_value: Any,
    path: str,
    diffs: List[Dict[str, Any]],
) -> None:
    expected_type = field_schema.get("type")
    actual_type = _actual_type_name(actual_value)

    if expected_type == "object":
        if actual_type != "object":
            diffs.append(
                {
                    "kind": "type_changed",
                    "field": path,
                    "expected": "object",
                    "actual": actual_type,
                    "message": f"Field '{path}' changed type from object to {actual_type}",
                }
            )
            return
        if "fields" in field_schema:
            _compare_object_fields(field_schema, actual_value, path, diffs)
        return

    if expected_type == "array":
        if actual_type != "array":
            diffs.append(
                {
                    "kind": "type_changed",
                    "field": path,
                    "expected": "array",
                    "actual": actual_type,
                    "message": f"Field '{path}' changed type from array to {actual_type}",
                }
            )
            return
        items_schema = field_schema.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(actual_value):
                _compare_field(items_schema, item, f"{path}[{index}]", diffs)
        return

    if expected_type != actual_type:
        diffs.append(
            {
                "kind": "type_changed",
                "field": path,
                "expected": expected_type,
                "actual": actual_type,
                "message": f"Field '{path}' changed type from {expected_type} to {actual_type}",
            }
        )


def compare(
    contract_schema: Any,
    actual_response: Any,
    expected_status: Optional[int] = None,
    actual_status: Optional[int] = None,
) -> List[Dict[str, Any]]:
    _validate_schema(contract_schema)
    diffs: List[Dict[str, Any]] = []

    if expected_status is not None and actual_status is not None:
        if expected_status != actual_status:
            diffs.append(
                {
                    "kind": "wrong_status",
                    "field": None,
                    "expected": expected_status,
                    "actual": actual_status,
                    "message": f"Expected status {expected_status} but got {actual_status}",
                }
            )

    if isinstance(actual_response, dict):
        _compare_object_fields(contract_schema, actual_response, "", diffs)
    else:
        # If a top-level object schema exists but actual response is not an object.
        _compare_object_fields(contract_schema, actual_response, "", diffs)

    return diffs
