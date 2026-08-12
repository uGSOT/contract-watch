from time import perf_counter
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests

from app.diff_engine import compare
from app.ssrf import is_hostname_public


DEFAULT_TIMEOUT = 5.0


def _build_url(base_url: str, path: str) -> str:
	if not base_url:
		raise ValueError("base_url is required")
	if not path:
		path = ""
	# urljoin handles edge cases cleanly
	return urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))


def run(endpoint: Dict[str, Any], contract: Dict[str, Any], timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
	"""
	Execute the HTTP request for the given endpoint and contract.

	`endpoint` expected keys: `base_url`, `path`, `method`
	`contract` expected to include parsed schema as `schema_json` or `schema`, and optional `expected_status`.

	Returns a dict with keys: result, status_code, response_body, duration_ms, diffs, error_message
	"""
	method = (endpoint.get('method') or 'GET').upper()
	base_url = endpoint.get('base_url')
	path = endpoint.get('path') or ''

	url = _build_url(base_url, path)

	# SSRF check: validate hostname
	parsed = urlparse(url)
	hostname = parsed.hostname
	if not hostname or not is_hostname_public(hostname):
		return {
			'result': 'error',
			'status_code': None,
			'response_body': None,
			'duration_ms': 0,
			'diffs': [],
			'error_message': 'blocked: hostname resolves to private or non-routable address',
		}

	start = perf_counter()
	try:
		resp = requests.request(method, url, timeout=timeout)
	except Exception as exc:
		duration_ms = int((perf_counter() - start) * 1000)
		return {
			'result': 'error',
			'status_code': None,
			'response_body': None,
			'duration_ms': duration_ms,
			'diffs': [],
			'error_message': str(exc),
		}

	duration_ms = int((perf_counter() - start) * 1000)

	# Parse JSON
	try:
		body = resp.json()
	except Exception as exc:
		# Treat invalid JSON as an error per requirements
		return {
			'result': 'error',
			'status_code': resp.status_code,
			'response_body': None,
			'duration_ms': duration_ms,
			'diffs': [],
			'error_message': 'invalid JSON response',
		}

	# Determine contract schema and expected status
	contract_schema = contract.get('schema_json') or contract.get('schema') or contract
	expected_status = contract.get('expected_status')

	# Call compare
	diffs = compare(contract_schema, body, expected_status=expected_status, actual_status=resp.status_code)

	result = 'drift' if diffs else 'pass'

	return {
		'result': result,
		'status_code': resp.status_code,
		'response_body': body,
		'duration_ms': duration_ms,
		'diffs': diffs,
		'error_message': None,
	}
