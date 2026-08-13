from flask import Blueprint, current_app, jsonify, request

from app.db import get_db


bp = Blueprint("projects", __name__, url_prefix="/api/projects")


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


@bp.get("/<int:project_id>")
def get_project(project_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    finally:
        db.close()

    if project is None:
        return jsonify({"error": "project not found"}), 404

    return jsonify({"project": dict(project)})


@bp.put("/<int:project_id>")
def update_project(project_id):
    payload = request.get_json(silent=True) or {}

    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

        if project is None:
            return jsonify({"error": "project not found"}), 404

        name = (payload.get("name") if "name" in payload else project["name"]) or ""
        base_url = (
            payload.get("base_url") if "base_url" in payload else project["base_url"]
        ) or ""
        description = (
            payload.get("description")
            if "description" in payload
            else project["description"]
        ) or ""

        name = name.strip()
        base_url = base_url.strip()
        description = description.strip()

        if not name or not base_url:
            return jsonify({"error": "name and base_url are required"}), 400

        db.execute(
            """
            UPDATE projects
            SET name = ?, base_url = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (name, base_url, description, project_id),
        )
        db.commit()
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    finally:
        db.close()

    return jsonify({"project": dict(project)})


@bp.delete("/<int:project_id>")
def delete_project(project_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

        if project is None:
            return jsonify({"error": "project not found"}), 404

        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        db.commit()
    finally:
        db.close()

    return "", 204
