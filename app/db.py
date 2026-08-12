import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "contract_watch.db"
DEFAULT_MIGRATION_PATH = BASE_DIR / "migrations" / "001_initial.sql"


def get_db(database_path=None):
    resolved_path = database_path or DEFAULT_DATABASE_PATH
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path=None, migration_path=None):
    resolved_path = database_path or DEFAULT_DATABASE_PATH
    resolved_migration = migration_path or DEFAULT_MIGRATION_PATH
    connection = get_db(resolved_path)

    try:
        migration_sql = Path(resolved_migration).read_text()

        connection.executescript(migration_sql)
        connection.commit()
    finally:
        connection.close()