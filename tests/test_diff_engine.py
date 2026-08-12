import pytest

from app.diff_engine import compare


BASE_SCHEMA = {
    "fields": {
        "user_id": {"type": "integer", "required": True},
        "name": {"type": "string", "required": True},
        "email": {"type": "string", "required": False},
    }
}


def test_matching_response_has_no_diffs():
    actual = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}
    diffs = compare(BASE_SCHEMA, actual)
    assert diffs == []


def test_missing_required_field():
    actual = {"name": "Souvik", "email": "souvik@example.com"}
    diffs = compare(BASE_SCHEMA, actual)
    assert len(diffs) == 1
    assert diffs[0]["kind"] == "missing_field"
    assert diffs[0]["field"] == "user_id"


def test_missing_optional_field():
    actual = {"user_id": 1, "name": "Souvik"}
    diffs = compare(BASE_SCHEMA, actual)
    assert diffs == []


def test_unexpected_field():
    actual = {"user_id": 1, "name": "Souvik", "nickname": "Sou"}
    diffs = compare(BASE_SCHEMA, actual)
    assert len(diffs) == 1
    assert diffs[0]["kind"] == "unexpected_field"
    assert diffs[0]["field"] == "nickname"


def test_integer_type_detection():
    actual = {"user_id": "1", "name": "Souvik"}
    diffs = compare(BASE_SCHEMA, actual)
    assert any(d["kind"] == "type_changed" and d["field"] == "user_id" for d in diffs)


def test_string_type_detection():
    actual = {"user_id": 1, "name": 123}
    diffs = compare(BASE_SCHEMA, actual)
    assert any(d["kind"] == "type_changed" and d["field"] == "name" for d in diffs)


def test_boolean_type_detection():
    schema = {"fields": {"active": {"type": "boolean", "required": True}}}
    actual = {"active": "true"}
    diffs = compare(schema, actual)
    assert diffs == [
        {
            "kind": "type_changed",
            "field": "active",
            "expected": "boolean",
            "actual": "string",
            "message": "Field 'active' changed type from boolean to string",
        }
    ]


def test_array_type_detection():
    schema = {
        "fields": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "required": True,
            }
        }
    }
    actual = {"tags": ["python", 123]}
    diffs = compare(schema, actual)
    assert any(d["kind"] == "type_changed" and d["field"] == "tags[1]" for d in diffs)


def test_nested_object_detection():
    schema = {
        "fields": {
            "user": {
                "type": "object",
                "required": True,
                "fields": {
                    "id": {"type": "integer", "required": True},
                    "profile": {
                        "type": "object",
                        "fields": {
                            "name": {"type": "string", "required": True}
                        },
                    },
                },
            }
        }
    }
    actual = {"user": {"id": 1, "profile": {"name": 123}}}
    diffs = compare(schema, actual)
    assert len(diffs) == 1
    assert diffs[0]["kind"] == "type_changed"
    assert diffs[0]["field"] == "user.profile.name"


def test_renamed_field_detection():
    actual = {"userId": 1, "name": "Souvik"}
    diffs = compare(BASE_SCHEMA, actual)
    assert any(d["kind"] == "renamed_field" and d["field"] == "user_id" for d in diffs)


def test_changed_type_detection():
    actual = {"user_id": "1", "name": "Souvik", "email": "souvik@example.com"}
    diffs = compare(BASE_SCHEMA, actual)
    assert any(d["kind"] == "type_changed" and d["field"] == "user_id" for d in diffs)


def test_multiple_simultaneous_differences():
    actual = {"userId": "1", "nickname": "Sou"}
    diffs = compare(BASE_SCHEMA, actual)
    kinds = sorted(d["kind"] for d in diffs)
    assert "renamed_field" in kinds
    assert "unexpected_field" in kinds
    assert "missing_field" in kinds


def test_empty_response():
    actual = {}
    diffs = compare(BASE_SCHEMA, actual)
    assert any(d["kind"] == "missing_field" for d in diffs)


def test_invalid_schema_raises_error():
    with pytest.raises(ValueError):
        compare({"fields": "not an object"}, {"foo": "bar"})


def test_wrong_http_status():
    actual = {"user_id": 1, "name": "Souvik"}
    diffs = compare(BASE_SCHEMA, actual, expected_status=200, actual_status=404)
    assert diffs == [
        {
            "kind": "wrong_status",
            "field": None,
            "expected": 200,
            "actual": 404,
            "message": "Expected status 200 but got 404",
        }
    ]
