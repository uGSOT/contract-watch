import json

from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


bp = Blueprint("contracts", __name__)


def _validate_schema(schema):
    if not isinstance(schema, dict):
        return "schema must be a JSON object"

    fields = schema.get("fields")
    if not isinstance(fields, dict):
        return "schema must contain a fields object"

    if not fields:
        return "schema.fields must not be empty"

    for field_name, field_schema in fields.items():
        if not isinstance(field_name, str) or not field_name.strip():
            return "field names must be non-empty strings"

        if not isinstance(field_schema, dict):
            return f"schema.fields.{field_name} must be an object"

        field_type = field_schema.get("type")
        if not isinstance(field_type, str) or not field_type.strip():
            return f"schema.fields.{field_name}.type must be a non-empty string"

        if "required" in field_schema and not isinstance(field_schema["required"], bool):
            return f"schema.fields.{field_name}.required must be boolean"

    return None


@bp.post("/endpoints/<int:endpoint_id>/contracts")
def create_contract(endpoint_id):
    payload = request.get_json(silent=True) or {}
    schema = payload.get("schema")
    expected_status = payload.get("expected_status", 200)
    version = payload.get("version", 1)
    schema_version = payload.get("schema_version", 1)

    if schema is None:
        return jsonify({"error": "schema is required"}), 400

    error = _validate_schema(schema)
    if error:
        return jsonify({"error": error}), 400

    if not isinstance(expected_status, int) or expected_status <= 0:
        return jsonify({"error": "expected_status must be a positive integer"}), 400

    if not isinstance(version, int) or version <= 0:
        return jsonify({"error": "version must be a positive integer"}), 400

    if not isinstance(schema_version, int) or schema_version <= 0:
        return jsonify({"error": "schema_version must be a positive integer"}), 400

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        endpoint = db.execute(
            "SELECT id FROM endpoints WHERE id = ?",
            (endpoint_id,),
        ).fetchone()

        if endpoint is None:
            return jsonify({"error": "endpoint not found"}), 404

        duplicate = db.execute(
            "SELECT id FROM contracts WHERE endpoint_id = ? AND version = ?",
            (endpoint_id, version),
        ).fetchone()

        if duplicate is not None:
            return jsonify({"error": "duplicate contract version for this endpoint"}), 409

        schema_json = json.dumps(schema)
        cursor = db.execute(
            """
            INSERT INTO contracts (
                endpoint_id,
                schema_json,
                schema_version,
                expected_status,
                version,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (endpoint_id, schema_json, schema_version, expected_status, version, 1),
        )
        db.commit()
        contract = db.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        db.close()

    contract_data = dict(contract)
    contract_data["schema_json"] = json.loads(contract_data["schema_json"])

    return jsonify({"contract": contract_data}), 201
