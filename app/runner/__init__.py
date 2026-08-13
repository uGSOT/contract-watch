import ipaddress
import json
import socket
import time
import urllib.parse

import requests
from flask import Blueprint, current_app, jsonify

from app.db import get_db
from app.diff_engine import diff_response


bp = Blueprint("runner", __name__, url_prefix="/api")

REQUEST_TIMEOUT_SECONDS = 10


class SSRFBlockedError(Exception):
    pass


def validate_target_url(url):
    """Raise SSRFBlockedError if the URL is unsafe to call.

    v1 is a local-first dev tool with no auth boundary, so loopback/private
    addresses (its main use case) stay allowed. We only block the classic
    high-value SSRF target: link-local addresses, which covers the cloud
    metadata endpoint (169.254.169.254) on AWS/GCP/Azure alike.
    """
    parsed = urllib.parse.urlsplit(url)

    if parsed.scheme not in ("http", "https"):
        raise SSRFBlockedError(f"unsupported URL scheme '{parsed.scheme}'")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedError("URL has no hostname")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SSRFBlockedError(f"could not resolve host '{hostname}'") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_obj = ipaddress.ip_address(sockaddr[0])
        if ip_obj.is_link_local:
            raise SSRFBlockedError(
                f"refusing to call link-local/metadata address {sockaddr[0]}"
            )


def _load_contract_chain(db, contract_id):
    contract = db.execute(
        "SELECT * FROM contracts WHERE id = ?", (contract_id,)
    ).fetchone()
    if contract is None:
        return None, None, None

    endpoint = db.execute(
        "SELECT * FROM endpoints WHERE id = ?", (contract["endpoint_id"],)
    ).fetchone()
    project = db.execute(
        "SELECT * FROM projects WHERE id = ?", (endpoint["project_id"],)
    ).fetchone()

    return contract, endpoint, project


def _to_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def save_run(db, contract_id, result, status_code, response_body, duration_ms, error_message, diffs):
    cursor = db.execute(
        """
        INSERT INTO runs (
            contract_id, result, status_code, response_body,
            duration_ms, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (contract_id, result, status_code, response_body, duration_ms, error_message),
    )
    run_id = cursor.lastrowid

    for diff in diffs:
        db.execute(
            """
            INSERT INTO run_diffs (run_id, kind, field, expected, actual, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                diff["kind"],
                diff["field"],
                _to_text(diff.get("expected")),
                _to_text(diff.get("actual")),
                diff.get("message"),
            ),
        )

    return run_id


def load_run_with_diffs(db, run_id):
    row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None

    run = dict(row)
    if run["response_body"]:
        try:
            run["response_body"] = json.loads(run["response_body"])
        except (TypeError, ValueError):
            pass

    diff_rows = db.execute(
        "SELECT * FROM run_diffs WHERE run_id = ? ORDER BY id", (run_id,)
    ).fetchall()
    run["diffs"] = [dict(diff_row) for diff_row in diff_rows]

    return run


@bp.post("/contracts/<int:contract_id>/run")
def run_contract(contract_id):
    db = get_db(current_app.config["DATABASE_PATH"])
    try:
        contract, endpoint, project = _load_contract_chain(db, contract_id)
        if contract is None:
            return jsonify({"error": "contract not found"}), 404

        url = project["base_url"].rstrip("/") + endpoint["path"]
        schema = json.loads(contract["schema_json"])
        expected_status = contract["expected_status"]

        try:
            validate_target_url(url)
        except SSRFBlockedError as exc:
            run_id = save_run(db, contract_id, "error", None, None, None, str(exc), [])
            db.commit()
            return jsonify({"run": load_run_with_diffs(db, run_id)}), 201

        started_at = time.monotonic()
        try:
            response = requests.request(
                endpoint["method"],
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.Timeout:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            run_id = save_run(
                db, contract_id, "error", None, None, duration_ms, "request timed out", []
            )
            db.commit()
            return jsonify({"run": load_run_with_diffs(db, run_id)}), 201
        except requests.ConnectionError as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            run_id = save_run(
                db, contract_id, "error", None, None, duration_ms,
                f"connection error: {exc}", [],
            )
            db.commit()
            return jsonify({"run": load_run_with_diffs(db, run_id)}), 201

        duration_ms = int((time.monotonic() - started_at) * 1000)

        try:
            response_json = response.json()
        except ValueError:
            run_id = save_run(
                db, contract_id, "error", response.status_code,
                response.text[:5000], duration_ms,
                "response was not valid JSON", [],
            )
            db.commit()
            return jsonify({"run": load_run_with_diffs(db, run_id)}), 201

        result, diffs = diff_response(
            schema, expected_status, response.status_code, response_json
        )

        run_id = save_run(
            db, contract_id, result, response.status_code,
            json.dumps(response_json), duration_ms, None, diffs,
        )
        db.commit()

        return jsonify({"run": load_run_with_diffs(db, run_id)}), 201
    finally:
        db.close()
