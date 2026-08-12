from pathlib import Path

from app import create_app


def test_list_endpoints_for_project_is_empty(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        response = client.get("/projects/1/endpoints")

    assert response.status_code == 200
    assert response.get_json()["endpoints"] == []


def test_create_endpoint_success(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        client.post(
            "/projects",
            json={
                "name": "My User API",
                "base_url": "http://localhost:5000",
            },
        )

        response = client.post(
            "/projects/1/endpoints",
            json={
                "method": "GET",
                "path": "/api/users/1",
                "description": "Get a user by ID",
            },
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["endpoint"]["method"] == "GET"
    assert payload["endpoint"]["path"] == "/api/users/1"
    assert payload["endpoint"]["description"] == "Get a user by ID"


def test_create_endpoint_requires_method_and_path(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        client.post(
            "/projects",
            json={
                "name": "My User API",
                "base_url": "http://localhost:5000",
            },
        )

        response = client.post(
            "/projects/1/endpoints",
            json={
                "method": "",
                "path": "",
            },
        )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_endpoint_rejects_invalid_http_method(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        client.post(
            "/projects",
            json={
                "name": "My User API",
                "base_url": "http://localhost:5000",
            },
        )

        response = client.post(
            "/projects/1/endpoints",
            json={
                "method": "INVALID",
                "path": "/api/users/1",
            },
        )

    assert response.status_code == 400
    assert "error" in response.get_json()
