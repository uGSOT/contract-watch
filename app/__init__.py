from flask import Flask

from .db import init_db


def create_app():
    app = Flask(__name__)

    init_db()

    @app.route("/")
    def home():
        return "Contract Watch"

    return app