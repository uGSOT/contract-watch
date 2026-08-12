import json

from app.db import get_db, init_db


def seed():
    init_db()

    db = get_db()

    try:
        # Clear existing seed data
        db.execute("DELETE FROM projects")

        # Create project
        cursor = db.execute(
            """
            INSERT INTO projects (name, base_url, description)
            VALUES (?, ?, ?)
            """,
            (
                "My User API",
                "http://localhost:5001",
                "Sample API used for Contract Watch development",
            ),
        )

        project_id = cursor.lastrowid

        # Create endpoint
        cursor = db.execute(
            """
            INSERT INTO endpoints (
                project_id,
                method,
                path,
                description
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                project_id,
                "GET",
                "/api/users/1",
                "Get a user by ID",
            ),
        )

        endpoint_id = cursor.lastrowid

        # Create contract
        schema = {
            "fields": {
                "user_id": {
                    "type": "integer",
                    "required": True,
                },
                "name": {
                    "type": "string",
                    "required": True,
                },
                "email": {
                    "type": "string",
                    "required": True,
                },
            }
        }

        db.execute(
            """
            INSERT INTO contracts (
                endpoint_id,
                schema_json,
                schema_version,
                expected_status,
                version,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint_id,
                json.dumps(schema),
                1,
                200,
                1,
                1,
            ),
        )

        db.commit()

        print("Seed data created successfully.")
        print(f"Project ID: {project_id}")
        print(f"Endpoint ID: {endpoint_id}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()