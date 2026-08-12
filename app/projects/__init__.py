from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.get("")
def list_projects():
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        rows = db.execute(
            "SELECT * FROM projects ORDER BY created_at DESC, id DESC"
        ).fetchall()
    finally:
        db.close()

    return jsonify({"projects": [dict(row) for row in rows]})


@bp.post("")
def create_project():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    base_url = (payload.get("base_url") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name or not base_url:
        return jsonify({"error": "name and base_url are required"}), 400

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        cursor = db.execute(
            """
            INSERT INTO projects (name, base_url, description)
            VALUES (?, ?, ?)
            """,
            (name, base_url, description),
        )
        db.commit()
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        db.close()

    return jsonify({"project": dict(project)}), 201
