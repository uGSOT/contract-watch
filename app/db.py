import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "contract_watch.db"
DEFAULT_MIGRATIONS_PATH = BASE_DIR / "migrations"


def get_db(database_path=None):
    resolved_path = database_path or DEFAULT_DATABASE_PATH
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path=None, migrations_path=None):
    """Apply every migration in migrations_path, in filename order.

    Applied filenames are recorded in schema_migrations so each migration
    runs exactly once per database, even though init_db runs on every app
    start.
    """
    resolved_path = database_path or DEFAULT_DATABASE_PATH
    resolved_migrations = Path(migrations_path or DEFAULT_MIGRATIONS_PATH)
    connection = get_db(resolved_path)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            row["filename"]
            for row in connection.execute("SELECT filename FROM schema_migrations")
        }

        for migration in sorted(resolved_migrations.glob("*.sql")):
            if migration.name in applied:
                continue
            connection.executescript(migration.read_text())
            connection.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?)",
                (migration.name,),
            )

        connection.commit()
    finally:
        connection.close()