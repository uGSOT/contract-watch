from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

bp = Blueprint("endpoints", __name__)


@bp.get("/projects/<int:project_id>/endpoints")
def list_endpoints(project_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        rows = db.execute(
            """
            SELECT *
            FROM endpoints
            WHERE project_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (project_id,),
        ).fetchall()
    finally:
        db.close()

    return jsonify({"endpoints": [dict(row) for row in rows]})


@bp.post("/projects/<int:project_id>/endpoints")
def create_endpoint(project_id):
    payload = request.get_json(silent=True) or {}
    method = (payload.get("method") or "").strip().upper()
    path = (payload.get("path") or "").strip()
    description = (payload.get("description") or "").strip()

    if not method or not path:
        return jsonify({"error": "method and path are required"}), 400

    if method not in ALLOWED_METHODS:
        return jsonify({"error": "invalid HTTP method"}), 400

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        cursor = db.execute(
            """
            INSERT INTO endpoints (project_id, method, path, description)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, method, path, description),
        )
        db.commit()
        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        db.close()

    return jsonify({"endpoint": dict(endpoint)}), 201
