def _json_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return "unknown"


def _type_matches(expected_type, actual_value):
    actual_type = _json_type(actual_value)
    if actual_type == expected_type:
        return True
    # a "number" field may legitimately receive a whole number
    if expected_type == "number" and actual_type == "integer":
        return True
    return False


def _normalize_name(name):
    return name.lower().replace("_", "").replace("-", "")


def _diff_array(field_path, items_schema, actual_list, diffs):
    item_type = items_schema.get("type")
    for index, element in enumerate(actual_list):
        element_path = f"{field_path}[{index}]"
        if not _type_matches(item_type, element):
            diffs.append(
                {
                    "kind": "type_changed",
                    "field": element_path,
                    "expected": item_type,
                    "actual": _json_type(element),
                    "message": f"{element_path}: expected {item_type}, got {_json_type(element)}",
                }
            )
            return

        if item_type == "object" and isinstance(items_schema.get("fields"), dict):
            diffs.extend(_diff_fields(items_schema["fields"], element, element_path))


def _diff_fields(schema_fields, actual_obj, path):
    diffs = []
    expected_names = set(schema_fields.keys())
    actual_names = set(actual_obj.keys())

    missing_required = {
        name
        for name in expected_names - actual_names
        if schema_fields[name].get("required", True)
    }
    unexpected = actual_names - expected_names
    common = expected_names & actual_names

    matched_missing = set()
    matched_unexpected = set()

    for missing_name in sorted(missing_required):
        normalized_missing = _normalize_name(missing_name)
        for unexpected_name in sorted(unexpected - matched_unexpected):
            if _normalize_name(unexpected_name) != normalized_missing:
                continue

            field_path = f"{path}.{unexpected_name}" if path else unexpected_name
            diffs.append(
                {
                    "kind": "field_renamed",
                    "field": field_path,
                    "expected": missing_name,
                    "actual": unexpected_name,
                    "message": f"field '{missing_name}' appears to have been renamed to '{unexpected_name}'",
                }
            )

            expected_type = schema_fields[missing_name].get("type")
            actual_value = actual_obj[unexpected_name]
            if not _type_matches(expected_type, actual_value):
                diffs.append(
                    {
                        "kind": "type_changed",
                        "field": field_path,
                        "expected": expected_type,
                        "actual": _json_type(actual_value),
                        "message": f"{field_path}: expected {expected_type}, got {_json_type(actual_value)}",
                    }
                )

            matched_missing.add(missing_name)
            matched_unexpected.add(unexpected_name)
            break

    for missing_name in sorted(missing_required - matched_missing):
        field_path = f"{path}.{missing_name}" if path else missing_name
        diffs.append(
            {
                "kind": "missing_field",
                "field": field_path,
                "expected": schema_fields[missing_name].get("type"),
                "actual": None,
                "message": f"required field '{field_path}' is missing",
            }
        )

    for unexpected_name in sorted(unexpected - matched_unexpected):
        field_path = f"{path}.{unexpected_name}" if path else unexpected_name
        diffs.append(
            {
                "kind": "unexpected_field",
                "field": field_path,
                "expected": None,
                "actual": _json_type(actual_obj[unexpected_name]),
                "message": f"unexpected field '{field_path}' was not defined in the contract",
            }
        )

    for name in sorted(common):
        field_path = f"{path}.{name}" if path else name
        field_schema = schema_fields[name]
        expected_type = field_schema.get("type")
        actual_value = actual_obj[name]

        if not _type_matches(expected_type, actual_value):
            diffs.append(
                {
                    "kind": "type_changed",
                    "field": field_path,
                    "expected": expected_type,
                    "actual": _json_type(actual_value),
                    "message": f"{field_path}: expected {expected_type}, got {_json_type(actual_value)}",
                }
            )
            continue

        if expected_type == "object" and isinstance(field_schema.get("fields"), dict):
            diffs.extend(_diff_fields(field_schema["fields"], actual_value, field_path))

        if expected_type == "array" and isinstance(field_schema.get("items"), dict):
            _diff_array(field_path, field_schema["items"], actual_value, diffs)

    return diffs


def diff_response(schema, expected_status, actual_status, response_json):
    """Compare a parsed JSON response against a contract schema.

    Returns a (result, diffs) tuple where result is "pass" or "drift".
    """
    diffs = []

    if expected_status != actual_status:
        diffs.append(
            {
                "kind": "status_mismatch",
                "field": "status",
                "expected": expected_status,
                "actual": actual_status,
                "message": f"expected status {expected_status}, got {actual_status}",
            }
        )

    schema_fields = (schema or {}).get("fields", {})

    if isinstance(response_json, dict):
        diffs.extend(_diff_fields(schema_fields, response_json, ""))
    else:
        diffs.append(
            {
                "kind": "type_changed",
                "field": "$",
                "expected": "object",
                "actual": _json_type(response_json),
                "message": f"expected the response body to be an object, got {_json_type(response_json)}",
            }
        )

    result = "pass" if not diffs else "drift"
    return result, diffs
