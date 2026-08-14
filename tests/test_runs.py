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


SCHEMA = {
    "fields": {
        "user_id": {"type": "integer", "required": True},
        "name": {"type": "string", "required": True},
        "email": {"type": "string", "required": True},
    }
}


def _create_active_contract(client, base_url="http://localhost:5000", strictness=None):
    project_id = client.post(
        "/api/projects", json={"name": "My User API", "base_url": base_url}
    ).get_json()["project"]["id"]

    endpoint_id = client.post(
        f"/api/projects/{project_id}/endpoints",
        json={"method": "GET", "path": "/api/users/1"},
    ).get_json()["endpoint"]["id"]

    contract_payload = {"schema_json": SCHEMA, "expected_status": 200}
    if strictness is not None:
        contract_payload["strictness"] = strictness

    contract = client.post(
        f"/api/endpoints/{endpoint_id}/contracts",
        json=contract_payload,
    ).get_json()["contract"]

    target_url = f"{base_url}/api/users/1"
    return contract["id"], target_url


def _run(client, requests_mock, contract_id, target_url, body, status_code=200):
    requests_mock.get(target_url, json=body, status_code=status_code)
    return client.post(f"/api/contracts/{contract_id}/run").get_json()["run"]


def test_list_runs_filter_and_pagination(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)

        pass_body = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}
        drift_body = {"userId": "1", "name": "Souvik", "email": "souvik@example.com"}

        _run(client, requests_mock, contract_id, target_url, pass_body)
        _run(client, requests_mock, contract_id, target_url, pass_body)
        _run(client, requests_mock, contract_id, target_url, drift_body)

        all_runs = client.get(f"/api/contracts/{contract_id}/runs").get_json()
        assert all_runs["total"] == 3
        assert len(all_runs["runs"]) == 3

        drift_only = client.get(f"/api/contracts/{contract_id}/runs?result=drift").get_json()
        assert drift_only["total"] == 1
        assert drift_only["runs"][0]["result"] == "drift"

        page_1 = client.get(f"/api/contracts/{contract_id}/runs?per_page=2&page=1").get_json()
        assert len(page_1["runs"]) == 2

        page_2 = client.get(f"/api/contracts/{contract_id}/runs?per_page=2&page=2").get_json()
        assert len(page_2["runs"]) == 1


def test_list_runs_invalid_filter(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, _ = _create_active_contract(client)
        response = client.get(f"/api/contracts/{contract_id}/runs?result=nonsense")

    assert response.status_code == 400


def test_get_run_detail_includes_diffs(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        drift_body = {"userId": "1", "name": "Souvik", "email": "souvik@example.com"}
        run = _run(client, requests_mock, contract_id, target_url, drift_body)

        response = client.get(f"/api/runs/{run['id']}")

    assert response.status_code == 200
    fetched = response.get_json()["run"]
    assert fetched["id"] == run["id"]
    assert len(fetched["diffs"]) == 2


def test_acknowledge_run(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        drift_body = {"userId": "1", "name": "Souvik", "email": "souvik@example.com"}
        run = _run(client, requests_mock, contract_id, target_url, drift_body)

        assert run["acknowledged"] == 0

        response = client.post(f"/api/runs/{run['id']}/acknowledge")
        assert response.status_code == 200
        assert response.get_json()["run"]["acknowledged"] == 1

        second = client.post(f"/api/runs/{run['id']}/acknowledge")
        assert second.get_json()["run"]["acknowledged"] == 1


def test_list_all_runs_across_contracts(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client)
        pass_body = {"user_id": 1, "name": "Souvik", "email": "souvik@example.com"}
        _run(client, requests_mock, contract_id, target_url, pass_body)

        response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["runs"][0]["project_name"] == "My User API"
    assert payload["runs"][0]["endpoint_path"] == "/api/users/1"


def test_run_lists_include_notice_count(tmp_path, requests_mock):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        contract_id, target_url = _create_active_contract(client, strictness="lenient")
        notice_body = {
            "user_id": 1,
            "name": "Souvik",
            "email": "souvik@example.com",
            "extra": "surprise",
        }
        run = _run(client, requests_mock, contract_id, target_url, notice_body)

        assert run["result"] == "pass"

        per_contract = client.get(f"/api/contracts/{contract_id}/runs").get_json()
        assert per_contract["runs"][0]["result"] == "pass"
        assert per_contract["runs"][0]["notice_count"] == 1

        across = client.get("/api/runs").get_json()
        assert across["runs"][0]["result"] == "pass"
        assert across["runs"][0]["notice_count"] == 1


def test_run_not_found(tmp_path):
    app = _make_app(tmp_path)
    with app.test_client() as client:
        response = client.get("/api/runs/999")

    assert response.status_code == 404
