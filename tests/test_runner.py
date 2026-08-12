import socket
import types
import pytest

import app.runner as runner_mod
from app.runner import run


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, json_exc=None):
        self.status_code = status_code
        self._json_data = json_data
        self._json_exc = json_exc

    def json(self):
        if self._json_exc:
            raise self._json_exc
        return self._json_data


def _make_endpoint(base_url='http://example.com', path='/api/users/1', method='GET'):
    return {'base_url': base_url, 'path': path, 'method': method}


def _make_contract(schema, expected_status=None):
    c = {'schema_json': schema}
    if expected_status is not None:
        c['expected_status'] = expected_status
    return c


# Helper to monkeypatch socket.getaddrinfo to return specified addresses
def _patch_getaddrinfo(monkeypatch, addrs):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        res = []
        for addr in addrs:
            if ':' in addr:
                # IPv6
                sockaddr = (addr, 0, 0, 0)
                res.append((socket.AF_INET6, None, None, '', sockaddr))
            else:
                sockaddr = (addr, 0)
                res.append((socket.AF_INET, None, None, '', sockaddr))
        return res

    monkeypatch.setattr(socket, 'getaddrinfo', fake_getaddrinfo)


def test_successful_request_pass(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}, 'name': {'type': 'string', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    # Mock DNS to return a public IP
    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    # Mock requests.request
    def fake_request(method, url, timeout):
        assert method == 'GET'
        assert url == 'http://example.com/api/users/1'
        assert timeout == 5.0
        return DummyResponse(status_code=200, json_data={'user_id': 1, 'name': 'Souvik'})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['result'] == 'pass'
    assert res['status_code'] == 200
    assert res['diffs'] == []
    assert res['error_message'] is None
    assert isinstance(res['duration_ms'], int)


def test_valid_response_with_drift(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}, 'name': {'type': 'string', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        return DummyResponse(status_code=200, json_data={'userId': '1', 'name': 'Souvik'})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['result'] == 'drift'
    assert res['status_code'] == 200
    assert any(d['kind'] in ('renamed_field', 'type_changed') for d in res['diffs'])


def test_wrong_http_status_results_in_drift(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        return DummyResponse(status_code=404, json_data={'user_id': 1})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['result'] == 'drift'
    assert res['status_code'] == 404
    assert any(d['kind'] == 'wrong_status' for d in res['diffs'])


def test_connection_failure_returns_error(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        raise Exception('connection failed')

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['result'] == 'error'
    assert res['status_code'] is None
    assert res['error_message'] is not None


def test_timeout_returns_error(monkeypatch):
    import requests

    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        raise requests.exceptions.Timeout('timed out')

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract, timeout=0.1)
    assert res['result'] == 'error'
    assert 'timed out' in res['error_message']


def test_invalid_json_response_returns_error(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        return DummyResponse(status_code=200, json_exc=ValueError('no json'))

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['result'] == 'error'
    assert res['error_message'] == 'invalid JSON response'


def test_url_construction_variants(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    contract = _make_contract(schema, expected_status=200)

    # base_url with trailing slash and path with leading slash
    endpoint = _make_endpoint(base_url='http://example.com/', path='/api/users/1')
    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    called = {}

    def fake_request(method, url, timeout):
        called['url'] = url
        return DummyResponse(status_code=200, json_data={'user_id': 1})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert called['url'] == 'http://example.com/api/users/1'
    assert res['result'] == 'pass'

    # base_url without trailing slash and path without leading slash
    endpoint2 = _make_endpoint(base_url='http://example.com', path='api/users/1')
    called.clear()

    res = run(endpoint2, contract)
    assert called['url'] == 'http://example.com/api/users/1'


def test_configurable_timeout_passed_to_requests(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        assert timeout == 1.23
        return DummyResponse(status_code=200, json_data={'user_id': 1, 'name': 'Souvik'})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract, timeout=1.23)
    # extra fields in the response cause diffs (unexpected_field), producing 'drift'
    assert res['result'] == 'drift'


def test_private_ip_blocked(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint(base_url='http://internal.local', path='/api')
    contract = _make_contract(schema, expected_status=200)

    # DNS resolves to private IP
    _patch_getaddrinfo(monkeypatch, ['10.0.0.5'])

    res = run(endpoint, contract)
    assert res['result'] == 'error'
    assert 'blocked' in res['error_message']


def test_loopback_ipv6_blocked(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint(base_url='http://[::1]', path='/api')
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['::1'])

    res = run(endpoint, contract)
    assert res['result'] == 'error'
    assert 'blocked' in res['error_message']


def test_diff_engine_called_with_correct_args(monkeypatch):
    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = {'schema_json': schema, 'expected_status': 200}

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    # Mock requests
    def fake_request(method, url, timeout):
        return DummyResponse(status_code=200, json_data={'user_id': 1})

    monkeypatch.setattr('requests.request', fake_request)

    # Monkeypatch compare to capture args
    captured = {}

    def fake_compare(schema_arg, actual_response_arg, expected_status=None, actual_status=None):
        captured['schema'] = schema_arg
        captured['actual'] = actual_response_arg
        captured['expected_status'] = expected_status
        captured['actual_status'] = actual_status
        return []

    monkeypatch.setattr('app.runner.compare', fake_compare)

    res = run(endpoint, contract)
    assert res['result'] == 'pass'
    assert captured['schema'] == schema
    assert captured['actual'] == {'user_id': 1}
    assert captured['expected_status'] == 200
    assert captured['actual_status'] == 200


def test_duration_recorded(monkeypatch):
    import time

    schema = {'fields': {'user_id': {'type': 'integer', 'required': True}}}
    endpoint = _make_endpoint()
    contract = _make_contract(schema, expected_status=200)

    _patch_getaddrinfo(monkeypatch, ['1.2.3.4'])

    def fake_request(method, url, timeout):
        time.sleep(0.01)
        return DummyResponse(status_code=200, json_data={'user_id': 1})

    monkeypatch.setattr('requests.request', fake_request)

    res = run(endpoint, contract)
    assert res['duration_ms'] >= 10
