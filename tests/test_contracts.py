from pathlib import Path

from app import create_app


def _make_app(tmp_path):
    db_path = tmp_path / "contract_watch_test.db"
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "MIGRATION_PATH": str(Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"),
        }
    )


def _create_project(client):
    response = client.post(
        "/projects",
        json={
            "name": "My User API",
            "base_url": "http://localhost:5000",
        },
    )
    assert response.status_code == 201


def _create_endpoint(client):
    response = client.post(
        "/projects/1/endpoints",
        json={
            "method": "GET",
            "path": "/api/users/1",
        },
    )
    assert response.status_code == 201


def test_create_valid_contract(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        response = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                        "name": {"type": "string", "required": True},
                    }
                },
                "expected_status": 200,
                "version": 1,
                "schema_version": 1,
            },
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["contract"]["endpoint_id"] == 1
    assert payload["contract"]["expected_status"] == 200
    assert payload["contract"]["version"] == 1
    assert payload["contract"]["schema_version"] == 1
    assert payload["contract"]["schema_json"]["fields"]["user_id"]["type"] == "integer"


def test_store_and_retrieve_schema_json(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        response = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["contract"]["schema_json"] == {
        "fields": {
            "user_id": {"type": "integer", "required": True}
        }
    }


def test_expected_status_defaults_to_200(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        response = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )

    assert response.status_code == 201
    assert response.get_json()["contract"]["expected_status"] == 200


def test_create_new_contract_version(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        first = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )
        second = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                        "name": {"type": "string", "required": False},
                    }
                },
                "version": 2,
            },
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.get_json()["contract"]["version"] == 2


def test_reject_duplicate_contract_version_for_same_endpoint(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )

        response = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )

    assert response.status_code == 409
    assert "duplicate" in response.get_json()["error"]


def test_reject_contract_for_nonexistent_endpoint(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        response = client.post(
            "/endpoints/900/contracts",
            json={
                "schema": {
                    "fields": {
                        "user_id": {"type": "integer", "required": True},
                    }
                },
                "version": 1,
            },
        )

    assert response.status_code == 404
    assert response.get_json()["error"] == "endpoint not found"


def test_reject_invalid_schema_input(tmp_path):
    app = _make_app(tmp_path)

    with app.test_client() as client:
        _create_project(client)
        _create_endpoint(client)

        response = client.post(
            "/endpoints/1/contracts",
            json={
                "schema": "not a json object",
                "version": 1,
            },
        )

    assert response.status_code == 400
    assert "schema must be a JSON object" in response.get_json()["error"]
