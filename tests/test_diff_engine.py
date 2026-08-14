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
            "severity": "drift",
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
            "severity": "drift",
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
            "severity": "drift",
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
            "severity": "drift",
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
            "severity": "drift",
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
            "severity": "drift",
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
            "severity": "drift",
            "field": "userId",
            "expected": "user_id",
            "actual": "userId",
            "message": "field 'user_id' appears to have been renamed to 'userId'",
        },
        {
            "kind": "type_changed",
            "severity": "drift",
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
            "severity": "drift",
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


def test_strict_is_the_default_strictness():
    response = {
        "user_id": 1,
        "name": "Souvik",
        "email": "souvik@example.com",
        "extra": "surprise",
    }
    default_result = diff_response(SCHEMA, 200, 200, response)
    strict_result = diff_response(SCHEMA, 200, 200, response, "strict")

    assert default_result == strict_result
    assert default_result[0] == "drift"


def test_lenient_unexpected_field_is_notice_and_passes():
    response = {
        "user_id": 1,
        "name": "Souvik",
        "email": "souvik@example.com",
        "extra": "surprise",
    }
    result, diffs = diff_response(SCHEMA, 200, 200, response, "lenient")

    assert result == "pass"
    assert diffs == [
        {
            "kind": "unexpected_field",
            "severity": "notice",
            "field": "extra",
            "expected": None,
            "actual": "string",
            "message": "unexpected field 'extra' was not defined in the contract",
        }
    ]


def test_lenient_nested_unexpected_field_is_notice():
    schema = {
        "fields": {
            "user": {
                "type": "object",
                "required": True,
                "fields": {
                    "id": {"type": "integer", "required": True},
                },
            }
        }
    }
    response = {"user": {"id": 1, "nickname": "sv"}}
    result, diffs = diff_response(schema, 200, 200, response, "lenient")

    assert result == "pass"
    assert diffs == [
        {
            "kind": "unexpected_field",
            "severity": "notice",
            "field": "user.nickname",
            "expected": None,
            "actual": "string",
            "message": "unexpected field 'user.nickname' was not defined in the contract",
        }
    ]


def test_lenient_missing_field_is_still_drift():
    response = {"user_id": 1, "name": "Souvik", "extra": "surprise"}
    result, diffs = diff_response(SCHEMA, 200, 200, response, "lenient")

    assert result == "drift"
    severities = {diff["kind"]: diff["severity"] for diff in diffs}
    assert severities == {"missing_field": "drift", "unexpected_field": "notice"}


def test_lenient_rename_is_still_drift():
    response = {"userId": "1", "name": "Souvik", "email": "souvik@example.com"}
    result, diffs = diff_response(SCHEMA, 200, 200, response, "lenient")

    assert result == "drift"
    assert {diff["kind"] for diff in diffs} == {"field_renamed", "type_changed"}
    assert all(diff["severity"] == "drift" for diff in diffs)
