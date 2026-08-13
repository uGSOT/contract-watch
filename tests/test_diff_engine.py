from app.diff_engine import diff_response


SCHEMA = {
    "fields": {
        "user_id": {"type": "integer", "required": True},
        "name": {"type": "string", "required": True},
        "email": {"type": "string", "required": True},
    }
}


def test_exact_match_passes():
    response = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}
    result, diffs = diff_response(SCHEMA, 200, 200, response)

    assert result == "pass"
    assert diffs == []


def test_missing_required_field():
    response = {"user_id": 1, "name": "Souvik"}
    result, diffs = diff_response(SCHEMA, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "missing_field",
            "field": "email",
            "expected": "string",
            "actual": None,
            "message": "required field 'email' is missing",
        }
    ]


def test_optional_field_absence_is_not_drift():
    schema = {
        "fields": {
            "user_id": {"type": "integer", "required": True},
            "nickname": {"type": "string", "required": False},
        }
    }
    result, diffs = diff_response(schema, 200, 200, {"user_id": 1})

    assert result == "pass"
    assert diffs == []


def test_unexpected_field():
    response = {
        "user_id": 1,
        "name": "Souvik",
        "email": "souvik@example.com",
        "extra": "surprise",
    }
    result, diffs = diff_response(SCHEMA, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "unexpected_field",
            "field": "extra",
            "expected": None,
            "actual": "string",
            "message": "unexpected field 'extra' was not defined in the contract",
        }
    ]


def test_type_changed():
    response = {"user_id": "1", "name": "Souvik", "email": "souvik@example.com"}
    result, diffs = diff_response(SCHEMA, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "type_changed",
            "field": "user_id",
            "expected": "integer",
            "actual": "string",
            "message": "user_id: expected integer, got string",
        }
    ]


def test_number_field_accepts_integer_value():
    schema = {"fields": {"price": {"type": "number", "required": True}}}
    result, diffs = diff_response(schema, 200, 200, {"price": 10})

    assert result == "pass"
    assert diffs == []


def test_nested_object_diff():
    schema = {
        "fields": {
            "user": {
                "type": "object",
                "required": True,
                "fields": {
                    "id": {"type": "integer", "required": True},
                    "address": {
                        "type": "object",
                        "required": True,
                        "fields": {
                            "zip": {"type": "string", "required": True},
                        },
                    },
                },
            }
        }
    }
    response = {"user": {"id": 1, "address": {"zip": 12345}}}
    result, diffs = diff_response(schema, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "type_changed",
            "field": "user.address.zip",
            "expected": "string",
            "actual": "integer",
            "message": "user.address.zip: expected string, got integer",
        }
    ]


def test_array_item_type_mismatch():
    schema = {
        "fields": {
            "tags": {
                "type": "array",
                "required": True,
                "items": {"type": "string"},
            }
        }
    }
    response = {"tags": ["a", "b", 3]}
    result, diffs = diff_response(schema, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "type_changed",
            "field": "tags[2]",
            "expected": "string",
            "actual": "integer",
            "message": "tags[2]: expected string, got integer",
        }
    ]


def test_array_of_objects_diff():
    schema = {
        "fields": {
            "items": {
                "type": "array",
                "required": True,
                "items": {
                    "type": "object",
                    "fields": {
                        "sku": {"type": "string", "required": True},
                    },
                },
            }
        }
    }
    response = {"items": [{"sku": "abc"}, {}]}
    result, diffs = diff_response(schema, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "missing_field",
            "field": "items[1].sku",
            "expected": "string",
            "actual": None,
            "message": "required field 'items[1].sku' is missing",
        }
    ]


def test_rename_detection_day_7_story():
    response = {"userId": "1", "name": "Souvik", "email": "souvik@example.com"}
    result, diffs = diff_response(SCHEMA, 200, 200, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "field_renamed",
            "field": "userId",
            "expected": "user_id",
            "actual": "userId",
            "message": "field 'user_id' appears to have been renamed to 'userId'",
        },
        {
            "kind": "type_changed",
            "field": "userId",
            "expected": "integer",
            "actual": "string",
            "message": "userId: expected integer, got string",
        },
    ]


def test_status_mismatch():
    response = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}
    result, diffs = diff_response(SCHEMA, 200, 500, response)

    assert result == "drift"
    assert diffs == [
        {
            "kind": "status_mismatch",
            "field": "status",
            "expected": 200,
            "actual": 500,
            "message": "expected status 200, got 500",
        }
    ]


def test_combined_status_and_field_drift():
    response = {"user_id": "1", "name": "Souvik"}
    result, diffs = diff_response(SCHEMA, 200, 404, response)

    assert result == "drift"
    kinds = [diff["kind"] for diff in diffs]
    assert "status_mismatch" in kinds
    assert "missing_field" in kinds
    assert "type_changed" in kinds
