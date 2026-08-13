from flask import Blueprint, abort, current_app, render_template

from app.db import get_db


bp = Blueprint("views", __name__)


@bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@bp.get("/projects/<int:project_id>")
def project_detail(project_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    finally:
        db.close()

    if project is None:
        abort(404)

    return render_template("project.html", project=dict(project))


@bp.get("/endpoints/<int:endpoint_id>")
def endpoint_detail(endpoint_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        endpoint = db.execute(
            "SELECT * FROM endpoints WHERE id = ?", (endpoint_id,)
        ).fetchone()
        project = None
        if endpoint is not None:
            project = db.execute(
                "SELECT * FROM projects WHERE id = ?", (endpoint["project_id"],)
            ).fetchone()
    finally:
        db.close()

    if endpoint is None or project is None:
        abort(404)

    return render_template(
        "endpoint.html", endpoint=dict(endpoint), project=dict(project)
    )


@bp.get("/history")
def history():
    return render_template("history.html")


@bp.get("/runs/<int:run_id>")
def run_detail(run_id):
    return render_template("run_detail.html", run_id=run_id)
