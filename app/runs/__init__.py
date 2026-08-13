from flask import Blueprint, current_app, jsonify, request

from app.db import get_db
from app.runner import load_run_with_diffs


bp = Blueprint("runs", __name__, url_prefix="/api")

VALID_RESULTS = {"pass", "drift", "error"}
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


@bp.get("/contracts/<int:contract_id>/runs")
def list_runs(contract_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        contract = db.execute(
            "SELECT * FROM contracts WHERE id = ?", (contract_id,)
        ).fetchone()
        if contract is None:
            return jsonify({"error": "contract not found"}), 404

        result_filter = request.args.get("result")
        if result_filter and result_filter not in VALID_RESULTS:
            return jsonify({"error": f"result must be one of {sorted(VALID_RESULTS)}"}), 400

        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            return jsonify({"error": "page must be an integer"}), 400

        try:
            per_page = int(request.args.get("per_page", DEFAULT_PER_PAGE))
        except ValueError:
            return jsonify({"error": "per_page must be an integer"}), 400
        per_page = max(1, min(per_page, MAX_PER_PAGE))

        where_clause = "WHERE contract_id = ?"
        params = [contract_id]
        if result_filter:
            where_clause += " AND result = ?"
            params.append(result_filter)

        total = db.execute(
            f"SELECT COUNT(*) AS count FROM runs {where_clause}", params
        ).fetchone()["count"]

        offset = (page - 1) * per_page
        rows = db.execute(
            f"""
            SELECT * FROM runs
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, per_page, offset),
        ).fetchall()
    finally:
        db.close()

    return jsonify(
        {
            "runs": [dict(row) for row in rows],
            "page": page,
            "per_page": per_page,
            "total": total,
        }
    )


@bp.get("/runs")
def list_all_runs():
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        result_filter = request.args.get("result")
        if result_filter and result_filter not in VALID_RESULTS:
            return jsonify({"error": f"result must be one of {sorted(VALID_RESULTS)}"}), 400

        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            return jsonify({"error": "page must be an integer"}), 400

        try:
            per_page = int(request.args.get("per_page", DEFAULT_PER_PAGE))
        except ValueError:
            return jsonify({"error": "per_page must be an integer"}), 400
        per_page = max(1, min(per_page, MAX_PER_PAGE))

        where_clause = ""
        params = []
        if result_filter:
            where_clause = "WHERE runs.result = ?"
            params.append(result_filter)

        total = db.execute(
            f"SELECT COUNT(*) AS count FROM runs {where_clause}", params
        ).fetchone()["count"]

        offset = (page - 1) * per_page
        rows = db.execute(
            f"""
            SELECT
                runs.*,
                contracts.version AS contract_version,
                endpoints.id AS endpoint_id,
                endpoints.method AS endpoint_method,
                endpoints.path AS endpoint_path,
                projects.id AS project_id,
                projects.name AS project_name
            FROM runs
            JOIN contracts ON runs.contract_id = contracts.id
            JOIN endpoints ON contracts.endpoint_id = endpoints.id
            JOIN projects ON endpoints.project_id = projects.id
            {where_clause}
            ORDER BY runs.created_at DESC, runs.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, per_page, offset),
        ).fetchall()
    finally:
        db.close()

    return jsonify(
        {
            "runs": [dict(row) for row in rows],
            "page": page,
            "per_page": per_page,
            "total": total,
        }
    )


@bp.get("/runs/<int:run_id>")
def get_run(run_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        run = load_run_with_diffs(db, run_id)
    finally:
        db.close()

    if run is None:
        return jsonify({"error": "run not found"}), 404

    return jsonify({"run": run})


@bp.post("/runs/<int:run_id>/acknowledge")
def acknowledge_run(run_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        run = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return jsonify({"error": "run not found"}), 404

        db.execute("UPDATE runs SET acknowledged = 1 WHERE id = ?", (run_id,))
        db.commit()

        updated = load_run_with_diffs(db, run_id)
    finally:
        db.close()

    return jsonify({"run": updated})
