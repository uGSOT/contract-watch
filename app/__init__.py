from pathlib import Path

from flask import Flask

from app.db import init_db

from .contracts import bp as contracts_bp
from .endpoints import bp as endpoints_bp
from .projects import bp as projects_bp
from .runner import bp as runner_bp
from .runs import bp as runs_bp
from .views import bp as views_bp


BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE_PATH=str(BASE_DIR / "contract_watch.db"),
        MIGRATIONS_PATH=str(BASE_DIR / "migrations"),
    )

    if test_config:
        app.config.update(test_config)

    database_path = app.config["DATABASE_PATH"]
    migrations_path = app.config["MIGRATIONS_PATH"]

    init_db(database_path=database_path, migrations_path=migrations_path)

    app.register_blueprint(projects_bp)
    app.register_blueprint(endpoints_bp)
    app.register_blueprint(contracts_bp)
    app.register_blueprint(runner_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(views_bp)

    return app