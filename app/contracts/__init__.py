import json

from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


bp = Blueprint("contracts", __name__, url_prefix="/api")

VALID_TYPES = {"integer", "number", "string", "boolean", "array", "object"}
VALID_STRICTNESS = {"strict", "lenient"}


def _get_endpoint(db, endpoint_id):
    return db.execute(
        "SELECT * FROM endpoints WHERE id = ?",
        (endpoint_id,),
    ).fetchone()


def _validate_field(field_name, field_def, path):
    full_name = f"{path}.{field_name}" if path else field_name

    if not isinstance(field_def, dict):
        return f"schema field '{full_name}' must be an object"

    field_type = field_def.get("type")
    if field_type not in VALID_TYPES:
        return f"schema field '{full_name}' has invalid type '{field_type}'"

    if field_type == "object":
        nested_fields = field_def.get("fields")
        if not isinstance(nested_fields, dict):
            return f"schema field '{full_name}' of type object must define 'fields'"
        for nested_name, nested_def in nested_fields.items():
            error = _validate_field(nested_name, nested_def, full_name)
            if error:
                return error

    if field_type == "array":
        items = field_def.get("items")
        if not isinstance(items, dict) or items.get("type") not in VALID_TYPES:
            return f"schema field '{full_name}' of type array must define valid 'items'"

    return None


def _validate_schema(schema_json):
    if not isinstance(schema_json, dict):
        return "schema must be an object"

    fields = schema_json.get("fields")
    if not isinstance(fields, dict) or not fields:
        return "schema must define a non-empty 'fields' object"

    for field_name, field_def in fields.items():
        error = _validate_field(field_name, field_def, "")
        if error:
            return error

    return None


@bp.get("/endpoints/<int:endpoint_id>/contracts")
def list_contracts(endpoint_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        if _get_endpoint(db, endpoint_id) is None:
            return jsonify({"error": "endpoint not found"}), 404

        rows = db.execute(
            """
            SELECT * FROM contracts
            WHERE endpoint_id = ?
            ORDER BY version DESC
            """,
            (endpoint_id,),
        ).fetchall()
    finally:
        db.close()

    contracts = []
    for row in rows:
        contract = dict(row)
        contract["schema_json"] = json.loads(contract["schema_json"])
        contracts.append(contract)

    return jsonify({"contracts": contracts})


@bp.get("/endpoints/<int:endpoint_id>/contracts/active")
def get_active_contract(endpoint_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        if _get_endpoint(db, endpoint_id) is None:
            return jsonify({"error": "endpoint not found"}), 404

        row = db.execute(
            "SELECT * FROM contracts WHERE endpoint_id = ? AND is_active = 1",
            (endpoint_id,),
        ).fetchone()
    finally:
        db.close()

    if row is None:
        return jsonify({"error": "no active contract for this endpoint"}), 404

    contract = dict(row)
    contract["schema_json"] = json.loads(contract["schema_json"])
    return jsonify({"contract": contract})


@bp.post("/endpoints/<int:endpoint_id>/contracts")
def create_contract(endpoint_id):
    payload = request.get_json(silent=True) or {}
    schema_json = payload.get("schema_json")
    expected_status = payload.get("expected_status", 200)
    schema_version = payload.get("schema_version", 1)
    strictness = payload.get("strictness", "strict")

    schema_error = _validate_schema(schema_json)
    if schema_error:
        return jsonify({"error": schema_error}), 400

    if not isinstance(expected_status, int) or not (100 <= expected_status <= 599):
        return jsonify({"error": "expected_status must be a valid HTTP status integer"}), 400

    if not isinstance(schema_version, int) or schema_version < 1:
        return jsonify({"error": "schema_version must be a positive integer"}), 400

    if strictness not in VALID_STRICTNESS:
        return jsonify({"error": f"strictness must be one of {sorted(VALID_STRICTNESS)}"}), 400

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        if _get_endpoint(db, endpoint_id) is None:
            return jsonify({"error": "endpoint not found"}), 404

        db.execute(
            "UPDATE contracts SET is_active = 0 WHERE endpoint_id = ? AND is_active = 1",
            (endpoint_id,),
        )

        current_max = db.execute(
            "SELECT MAX(version) AS max_version FROM contracts WHERE endpoint_id = ?",
            (endpoint_id,),
        ).fetchone()
        next_version = (current_max["max_version"] or 0) + 1

        cursor = db.execute(
            """
            INSERT INTO contracts (
                endpoint_id, schema_json, schema_version,
                expected_status, strictness, version, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                endpoint_id,
                json.dumps(schema_json),
                schema_version,
                expected_status,
                strictness,
                next_version,
            ),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        db.close()

    contract = dict(row)
    contract["schema_json"] = json.loads(contract["schema_json"])
    return jsonify({"contract": contract}), 201


@bp.get("/contracts/<int:contract_id>")
def get_contract(contract_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        row = db.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (contract_id,),
        ).fetchone()
    finally:
        db.close()

    if row is None:
        return jsonify({"error": "contract not found"}), 404

    contract = dict(row)
    contract["schema_json"] = json.loads(contract["schema_json"])
    return jsonify({"contract": contract})
