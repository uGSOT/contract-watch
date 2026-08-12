from pathlib import Path

from flask import Flask

from app.db import init_db

from .projects import bp as projects_bp
from .endpoints import bp as endpoints_bp

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE_PATH=str(BASE_DIR / "contract_watch.db"),
        MIGRATION_PATH=str(BASE_DIR / "migrations" / "001_initial.sql"),
    )

    if test_config:
        app.config.update(test_config)

    database_path = app.config["DATABASE_PATH"]
    migration_path = app.config["MIGRATION_PATH"]

    init_db(database_path=database_path, migration_path=migration_path)

    app.register_blueprint(projects_bp)
    app.register_blueprint(endpoints_bp)

    @app.route("/")
    def home():
        return "Contract Watch"

    return app