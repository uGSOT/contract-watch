import sqlite3

from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


bp = Blueprint("endpoints", __name__, url_prefix="/api/projects/<int:project_id>/endpoints")

VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _get_project(db, project_id):
    return db.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()


@bp.get("")
def list_endpoints(project_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        if _get_project(db, project_id) is None:
            return jsonify({"error": "project not found"}), 404

        rows = db.execute(
            """
            SELECT * FROM endpoints
            WHERE project_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (project_id,),
        ).fetchall()
    finally:
        db.close()

    return jsonify({"endpoints": [dict(row) for row in rows]})


@bp.post("")
def create_endpoint(project_id):
    payload = request.get_json(silent=True) or {}
    method = (payload.get("method") or "").strip().upper()
    path = (payload.get("path") or "").strip()
    description = (payload.get("description") or "").strip()

    if method not in VALID_METHODS:
        return jsonify({"error": f"method must be one of {sorted(VALID_METHODS)}"}), 400

    if not path.startswith("/"):
        return jsonify({"error": "path must start with /"}), 400

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        if _get_project(db, project_id) is None:
            return jsonify({"error": "project not found"}), 404

        try:
            cursor = db.execute(
                """
                INSERT INTO endpoints (project_id, method, path, description)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, method, path, description),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return (
                jsonify({"error": "an endpoint with this method and path already exists"}),
                409,
            )

        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        db.close()

    return jsonify({"endpoint": dict(endpoint)}), 201


@bp.get("/<int:endpoint_id>")
def get_endpoint(project_id, endpoint_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ? AND project_id = ?",
            (endpoint_id, project_id),
        ).fetchone()
    finally:
        db.close()

    if endpoint is None:
        return jsonify({"error": "endpoint not found"}), 404

    return jsonify({"endpoint": dict(endpoint)})


@bp.put("/<int:endpoint_id>")
def update_endpoint(project_id, endpoint_id):
    payload = request.get_json(silent=True) or {}

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ? AND project_id = ?",
            (endpoint_id, project_id),
        ).fetchone()

        if endpoint is None:
            return jsonify({"error": "endpoint not found"}), 404

        method = (
            payload.get("method") if "method" in payload else endpoint["method"]
        ) or ""
        path = (payload.get("path") if "path" in payload else endpoint["path"]) or ""
        description = (
            payload.get("description")
            if "description" in payload
            else endpoint["description"]
        ) or ""

        method = method.strip().upper()
        path = path.strip()
        description = description.strip()

        if method not in VALID_METHODS:
            return jsonify({"error": f"method must be one of {sorted(VALID_METHODS)}"}), 400

        if not path.startswith("/"):
            return jsonify({"error": "path must start with /"}), 400

        try:
            db.execute(
                """
                UPDATE endpoints
                SET method = ?, path = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (method, path, description, endpoint_id),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return (
                jsonify({"error": "an endpoint with this method and path already exists"}),
                409,
            )

        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ?",
            (endpoint_id,),
        ).fetchone()
    finally:
        db.close()

    return jsonify({"endpoint": dict(endpoint)})


@bp.delete("/<int:endpoint_id>")
def delete_endpoint(project_id, endpoint_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ? AND project_id = ?",
            (endpoint_id, project_id),
        ).fetchone()

        if endpoint is None:
            return jsonify({"error": "endpoint not found"}), 404

        db.execute("DELETE FROM endpoints WHERE id = ?", (endpoint_id,))
        db.commit()
    finally:
        db.close()

    return "", 204
