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


def _create_endpoint(client):
    project_id = client.post(
        "/api/projects",
        json={"name": "My User API", "base_url": "http://localhost:5000"},
    ).get_json()["project"]["id"]

    endpoint_id = client.post(
        f"/api/projects/{project_id}/endpoints",
        json={"method": "GET", "path": "/api/users/1"},
    ).get_json()["endpoint"]["id"]

    return endpoint_id


SIMPLE_SCHEMA = {
    "fields": {
        "user_id": {"type": "integer", "required": True},
        "name": {"type": "string", "required": True},
        "email": {"type": "string", "required": True},
    }
}


def test_create_contract_success(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        response = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA, "expected_status": 200},
        )

    assert response.status_code == 201
    contract = response.get_json()["contract"]
    assert contract["version"] == 1
    assert contract["is_active"] == 1
    assert contract["schema_json"] == SIMPLE_SCHEMA


def test_create_contract_invalid_schema(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        response = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": {"fields": {"bad": {"type": "not-a-type"}}}},
        )

    assert response.status_code == 400


def test_new_contract_version_deactivates_previous(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        first = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA},
        ).get_json()["contract"]

        second_schema = {
            "fields": {
                "userId": {"type": "string", "required": True},
                "name": {"type": "string", "required": True},
                "email": {"type": "string", "required": True},
            }
        }
        second = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": second_schema},
        ).get_json()["contract"]

        assert second["version"] == first["version"] + 1
        assert second["is_active"] == 1

        active = client.get(f"/api/endpoints/{endpoint_id}/contracts/active").get_json()["contract"]
        assert active["id"] == second["id"]

        all_versions = client.get(f"/api/endpoints/{endpoint_id}/contracts").get_json()["contracts"]
        assert len(all_versions) == 2
        first_reloaded = next(c for c in all_versions if c["id"] == first["id"])
        assert first_reloaded["is_active"] == 0


def test_get_contract_by_id(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)
        created = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA},
        ).get_json()["contract"]

        response = client.get(f"/api/contracts/{created['id']}")

    assert response.status_code == 200
    assert response.get_json()["contract"]["id"] == created["id"]


def test_active_contract_404_when_none(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)
        response = client.get(f"/api/endpoints/{endpoint_id}/contracts/active")

    assert response.status_code == 404


def test_create_contract_defaults_to_strict(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        response = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA},
        )

    assert response.status_code == 201
    assert response.get_json()["contract"]["strictness"] == "strict"


def test_create_contract_lenient_strictness(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        response = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA, "strictness": "lenient"},
        )

        assert response.status_code == 201
        contract = response.get_json()["contract"]
        assert contract["strictness"] == "lenient"

        reloaded = client.get(f"/api/contracts/{contract['id']}").get_json()["contract"]
        assert reloaded["strictness"] == "lenient"


def test_create_contract_invalid_strictness(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        endpoint_id = _create_endpoint(client)

        response = client.post(
            f"/api/endpoints/{endpoint_id}/contracts",
            json={"schema_json": SIMPLE_SCHEMA, "strictness": "relaxed"},
        )

    assert response.status_code == 400
    assert "strictness" in response.get_json()["error"]
