import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "contract_watch.db"
MIGRATION_PATH = BASE_DIR / "migrations" / "001_initial.sql"


def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db()

    try:
        migration_sql = MIGRATION_PATH.read_text()

        connection.executescript(migration_sql)
        connection.commit()
    finally:
        connection.close()