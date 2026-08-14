# API reference

All JSON API routes are under `/api`. Page routes (that render HTML) are
listed separately at the bottom and are not under `/api`.

Every response is JSON. Errors are `{"error": "message"}` with a 4xx status.

## Projects

### `GET /api/projects`
List all projects, newest first.

```json
{ "projects": [ { "id": 1, "name": "My User API", "base_url": "http://localhost:5000", "description": "", "created_at": "...", "updated_at": "..." } ] }
```

### `POST /api/projects`
Body: `{ "name": "...", "base_url": "...", "description": "..." }` — `name`
and `base_url` are required. Returns `201` with `{ "project": {...} }`.

### `GET /api/projects/<id>`
`200` with `{ "project": {...} }`, or `404`.

### `PUT /api/projects/<id>`
Partial update — send only the fields you want to change. `404` if missing,
`400` if the resulting `name`/`base_url` would be empty.

### `DELETE /api/projects/<id>`
`204` on success. Cascades to the project's endpoints, contracts, runs, and
run diffs.

## Endpoints

Nested under a project.

### `GET /api/projects/<project_id>/endpoints`
List endpoints for a project. `404` if the project doesn't exist.

### `POST /api/projects/<project_id>/endpoints`
Body: `{ "method": "GET", "path": "/api/users/1", "description": "..." }`.
`method` must be one of `GET/POST/PUT/PATCH/DELETE`, `path` must start with
`/`. `409` if that method+path already exists on the project.

### `GET /api/projects/<project_id>/endpoints/<id>`
### `PUT /api/projects/<project_id>/endpoints/<id>`
### `DELETE /api/projects/<project_id>/endpoints/<id>`

Same shape as projects' get/update/delete.

## Contracts

A contract is a versioned schema for an endpoint. Creating a new contract
deactivates the previous one — old versions stay in the database for
history, they're just no longer the one used by Run.

### Schema shape

```json
{
  "fields": {
    "user_id": { "type": "integer", "required": true },
    "name": { "type": "string", "required": true },
    "address": {
      "type": "object", "required": false,
      "fields": { "zip": { "type": "string", "required": true } }
    },
    "tags": {
      "type": "array", "required": false,
      "items": { "type": "string" }
    }
  }
}
```

Valid `type` values: `string`, `integer`, `number`, `boolean`, `array`,
`object`. `object` fields need a nested `fields` map; `array` fields need
an `items` schema.

### `GET /api/endpoints/<endpoint_id>/contracts`
List every version for an endpoint, newest first.

### `GET /api/endpoints/<endpoint_id>/contracts/active`
The current active contract, or `404` if none exists yet.

### `POST /api/endpoints/<endpoint_id>/contracts`
Body: `{ "schema_json": {...}, "expected_status": 200, "strictness": "strict" }`.
Creates the next version, marks it active, deactivates the previous active
version (if any).

`strictness` is optional and must be `strict` (the default) or `lenient`.
It controls how Run treats fields in the response that the contract
doesn't declare: `strict` counts them as drift, `lenient` records them as
non-failing notices (see Runner below).

### `GET /api/contracts/<contract_id>`
Fetch a single contract version by its own id.

## Runner

### `POST /api/contracts/<contract_id>/run`
Fetches the endpoint's URL (`project.base_url + endpoint.path`), compares
the response to the contract's schema, saves a `run` row (and any
`run_diffs`), and returns it:

```json
{
  "run": {
    "id": 3, "contract_id": 1, "result": "drift",
    "status_code": 200, "response_body": { "...": "..." },
    "duration_ms": 12, "error_message": null, "acknowledged": 0,
    "created_at": "...",
    "diffs": [
      { "kind": "field_renamed", "severity": "drift", "field": "userId", "expected": "user_id", "actual": "userId", "message": "..." }
    ]
  }
}
```

`result` is one of `pass`, `drift`, `error`. `error` covers: unsafe/invalid
URL, DNS failure, connection refused, timeout (10s), or a non-JSON
response body — in all of those cases `diffs` is empty and
`error_message` explains what happened.

Each diff has a `severity`: `drift` diffs fail the run, `notice` diffs
don't. On a `strict` contract every diff is a `drift`. On a `lenient`
contract, `unexpected_field` diffs are recorded as `notice` instead — they
still show up in the run's `diffs`, but a run whose only diffs are notices
has `"result": "pass"`. Everything else (missing fields, type changes,
renames, status mismatches) is a `drift` in both modes.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the SSRF policy this route
enforces before making the request.

## Run history

### `GET /api/contracts/<contract_id>/runs`
Runs for one contract. Query params: `result` (`pass`/`drift`/`error`),
`page` (default 1), `per_page` (default 20, max 100). Each row includes a
`notice_count` — the number of notice-severity diffs on that run — so
list pages can show a passing run with notices differently from a clean
pass without fetching every run's diffs.

### `GET /api/runs`
Same as above but across every contract/project. Each row also includes
`project_id`, `project_name`, `endpoint_id`, `endpoint_method`,
`endpoint_path`, `contract_version` for display purposes.

### `GET /api/runs/<id>`
A single run with its `diffs`.

### `POST /api/runs/<id>/acknowledge`
Sets `acknowledged = 1` on the run. Idempotent.

## Page routes (HTML, not `/api`)

| Route | Renders |
|---|---|
| `GET /` | Dashboard — project list + create form |
| `GET /projects/<id>` | Project detail — endpoint list + create form |
| `GET /endpoints/<id>` | Contract builder, Run button, contract versions, recent runs |
| `GET /history` | Run history across all projects, with filter + pagination |
| `GET /runs/<id>` | Single run detail |
