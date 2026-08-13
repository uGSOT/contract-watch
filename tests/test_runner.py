from pathlib import Path

import requests

from app import create_app


def _make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "contract_watch_test.db"),
            "MIGRATION_PATH": str(
                Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"
            ),
        }
    )


SCHEMA = {
    "fields": {
        "user_id": {"type": "integer", "required": True},
        "name": {"type": "string", "required": True},
        "email": {"type": "string", "required": True},
    }
}


def _create_active_contract(client, base_url="http://localhost:5000"):
    project_id = client.post(
        "/api/projects", json={"name": "My User API", "base_url": base_url}
    ).get_json()["project"]["id"]

    endpoint_id = client.post(
        f"/api/projects/{project_id}/endpoints",
        json={"method": "GET", "path": "/api/users/1"},
    ).get_json()["endpoint"]["id"]

    contract = client.post(
        f"/api/endpoints/{endpoint_id}/contracts",
        json={"schema_json": SCHEMA, "expected_status": 200},
    ).get_json()["contract"]

    target_url = f"{base_url}/api/users/1"
    return contract["id"], target_url


def test_run_pass(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        requests_mock.get(
            target_url,
            json={"user_id": 1, "name": "Souvik", "email": "souvik@example.com"},
            status_code=200,
        )

        response = client.post(f"/api/contracts/{contract_id}/run")

    assert response.status_code == 201
    run = response.get_json()["run"]
    assert run["result"] == "pass"
    assert run["diffs"] == []


def test_run_drift_detects_rename(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        requests_mock.get(
            target_url,
            json={"userId": "1", "name": "Souvik", "email": "souvik@example.com"},
            status_code=200,
        )

        response = client.post(f"/api/contracts/{contract_id}/run")

    run = response.get_json()["run"]
    assert run["result"] == "drift"
    kinds = {diff["kind"] for diff in run["diffs"]}
    assert "field_renamed" in kinds
    assert "type_changed" in kinds


def test_run_timeout_is_error(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        requests_mock.get(target_url, exc=requests.exceptions.Timeout)

        response = client.post(f"/api/contracts/{contract_id}/run")

    run = response.get_json()["run"]
    assert run["result"] == "error"
    assert "timed out" in run["error_message"]


def test_run_connection_error_is_error(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        requests_mock.get(target_url, exc=requests.exceptions.ConnectionError)

        response = client.post(f"/api/contracts/{contract_id}/run")

    run = response.get_json()["run"]
    assert run["result"] == "error"
    assert "connection error" in run["error_message"]


def test_run_non_json_body_is_error(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        requests_mock.get(target_url, text="<html>not json</html>", status_code=200)

        response = client.post(f"/api/contracts/{contract_id}/run")

    run = response.get_json()["run"]
    assert run["result"] == "error"
    assert "not valid JSON" in run["error_message"]


def test_run_blocks_metadata_address(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(
            client, base_url="http://169.254.169.254"
        )

        response = client.post(f"/api/contracts/{contract_id}/run")

    run = response.get_json()["run"]
    assert run["result"] == "error"
    assert "link-local" in run["error_message"] or "metadata" in run["error_message"]
    assert not requests_mock.request_history


def test_run_not_found_contract(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        response = client.post("/api/contracts/999/run")

    assert response.status_code == 404
