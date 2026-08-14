from pathlib import Path

from app import create_app


def _make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "contract_watch_test.db"),
            "MIGRATIONS_PATH": str(
                Path(__file__).resolve().parents[1] / "migrations"
            ),
        }
    )


def _create_project(client):
    response = client.post(
        "/api/projects",
        json={"name": "My User API", "base_url": "http://localhost:5000"},
    )
    return response.get_json()["project"]["id"]


def test_list_endpoints_requires_existing_project(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        response = client.get("/api/projects/999/endpoints")

    assert response.status_code == 404


def test_create_and_list_endpoint(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        project_id = _create_project(client)

        create_response = client.post(
            f"/api/projects/{project_id}/endpoints",
            json={"method": "get", "path": "/api/users/1", "description": "Get user"},
        )
        assert create_response.status_code == 201
        endpoint = create_response.get_json()["endpoint"]
        assert endpoint["method"] == "GET"
        assert endpoint["path"] == "/api/users/1"

        list_response = client.get(f"/api/projects/{project_id}/endpoints")
        assert list_response.status_code == 200
        assert len(list_response.get_json()["endpoints"]) == 1


def test_create_endpoint_invalid_method(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        project_id = _create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/endpoints",
            json={"method": "TRACE", "path": "/api/users/1"},
        )

    assert response.status_code == 400


def test_create_endpoint_invalid_path(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        project_id = _create_project(client)
        response = client.post(
            f"/api/projects/{project_id}/endpoints",
            json={"method": "GET", "path": "api/users/1"},
        )

    assert response.status_code == 400


def test_create_duplicate_endpoint_conflicts(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        project_id = _create_project(client)
        payload = {"method": "GET", "path": "/api/users/1"}

        first = client.post(f"/api/projects/{project_id}/endpoints", json=payload)
        assert first.status_code == 201

        second = client.post(f"/api/projects/{project_id}/endpoints", json=payload)
        assert second.status_code == 409


def test_get_update_delete_endpoint(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        project_id = _create_project(client)
        created = client.post(
            f"/api/projects/{project_id}/endpoints",
            json={"method": "GET", "path": "/api/users/1"},
        ).get_json()["endpoint"]
        endpoint_id = created["id"]

        get_response = client.get(f"/api/projects/{project_id}/endpoints/{endpoint_id}")
        assert get_response.status_code == 200

        update_response = client.put(
            f"/api/projects/{project_id}/endpoints/{endpoint_id}",
            json={"description": "Updated description"},
        )
        assert update_response.status_code == 200
        assert update_response.get_json()["endpoint"]["description"] == "Updated description"

        delete_response = client.delete(f"/api/projects/{project_id}/endpoints/{endpoint_id}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/projects/{project_id}/endpoints/{endpoint_id}")
        assert missing_response.status_code == 404
