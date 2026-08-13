from pathlib import Path

from app import create_app


def test_projects_list_is_empty_by_default(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.get_json()["projects"] == []


def test_create_project_success(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        response = client.post(
            "/api/projects",
            json={
                "name": "My User API",
                "base_url": "http://localhost:5000",
                "description": "Demo project",
            },
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["project"]["name"] == "My User API"
    assert payload["project"]["base_url"] == "http://localhost:5000"
    assert payload["project"]["description"] == "Demo project"


def test_create_project_requires_name_and_base_url(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )

    with app.test_client() as client:
        response = client.post(
            "/api/projects",
            json={
                "name": "",
                "base_url": "",
            },
        )

    assert response.status_code == 400
    assert "error" in response.get_json()
