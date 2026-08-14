# Architecture

## Layout

```
app/
  __init__.py       app factory: creates the Flask app, runs the migration,
                     registers every blueprint
  db.py              sqlite3 connection helper + migration runner
  diff_engine.py     pure functions: schema + response -> (result, diffs)
  projects/          JSON API: /api/projects
  endpoints/         JSON API: /api/projects/<id>/endpoints
  contracts/         JSON API: /api/endpoints/<id>/contracts, /api/contracts/<id>
  runner/            JSON API: POST /api/contracts/<id>/run
  runs/              JSON API: /api/contracts/<id>/runs, /api/runs, /api/runs/<id>
  views/             HTML page routes: /, /projects/<id>, /endpoints/<id>, /history, /runs/<id>
  templates/         Jinja2 templates rendered by views/
  static/css, static/js   plain CSS + vanilla JS, no build step
migrations/*.sql     applied in filename order by db.py's init_db, which
                     records each applied file in schema_migrations so a
                     migration runs exactly once per database
tests/               one test file per backend module
```

Each backend module is a Flask **blueprint**: a self-contained set of
routes that get registered onto the app in `app/__init__.py`. This is why
`app/auth`, before it's implemented, is just an empty `__init__.py` — it's
a placeholder for a blueprint that doesn't exist yet.

**Why `/api` vs plain paths:** the JSON API and the HTML page routes are
separate blueprints, and several of them cover the same resource — e.g.
`GET /api/projects/<id>` (JSON) vs `GET /projects/<id>` (the page that
shows that project). If both blueprints registered the exact same path,
Flask would silently route every request to whichever blueprint was
registered first, and the other would never be reachable. Namespacing the
JSON API under `/api` keeps the two address spaces from colliding, now and
as more routes get added.

## Database access

There's no ORM. `app/db.py` opens a fresh `sqlite3` connection per request
(`get_db()`), sets `row_factory = sqlite3.Row` so rows behave like dicts,
and every route function closes it in a `finally` block. This is
intentionally simple — SQLite handles concurrent reads fine, and a
single-user local tool doesn't need connection pooling.

## Diff engine (`app/diff_engine.py`)

Pure, dependency-free functions — no Flask, no database — so they're easy
to unit test in isolation (`tests/test_diff_engine.py`). The entry point:

```python
diff_response(schema, expected_status, actual_status, response_json, strictness="strict") -> (result, diffs)
```

Walks the schema's `fields` map against the actual response object,
recursively for nested `object` fields and `array` items:

- **status_mismatch** — actual HTTP status != expected
- **missing_field** — a `required` field isn't in the response
- **unexpected_field** — a response field isn't declared in the schema.
  This is the one kind whose severity depends on the contract's
  `strictness`: `"drift"` on a strict contract, `"notice"` on a lenient
  one
- **type_changed** — a field is present in both but its JSON type differs
  (a `number` field accepts an `integer` value, since JSON doesn't
  distinguish them; everything else must match exactly)
- **field_renamed** — a rename heuristic: if a required field is missing
  *and* there's an unexpected field whose name matches after stripping
  underscores/case (`user_id` -> `userid` vs `userId` -> `userid`), that
  pair is reported as one rename instead of a separate missing + unexpected
  pair. The type check still runs on the renamed pair afterward, which is
  why a rename + a type change on the same field show up as two diffs (see
  the `user_id: int` -> `userId: str` example in the README).

Every diff carries a `severity` — `"drift"` or `"notice"`. `result` is
`"pass"` iff no diff has severity `"drift"`, otherwise `"drift"` — so on a
lenient contract, extra fields are recorded but don't fail the run.
`"error"` is never returned by the diff engine — it's set one layer up, by
the runner, for failures that happen *before* there's a response to diff
(timeout, connection refused, non-JSON body).

## Runner (`app/runner/__init__.py`)

`POST /api/contracts/<id>/run` is the only route. Flow:

1. Load the contract -> its endpoint -> its project (three lookups,
   `404` if any is missing).
2. Build the target URL: `project.base_url + endpoint.path`.
3. **Validate the URL** (`validate_target_url`): scheme must be `http` or
   `https`; resolve the hostname and reject it if any resolved address is
   link-local (`ipaddress.ip_address(...).is_link_local`).

   This is the SSRF guard, and its scope is deliberate. v1 is a
   local-first tool with no auth boundary — its entire purpose is
   fetching `http://localhost:...` and other private dev addresses, so
   blocking private/loopback IPs outright would break the core use case.
   What we do block is the actual high-value SSRF target: link-local
   addresses, which covers the cloud metadata endpoint
   (`169.254.169.254`) that AWS, GCP, and Azure all use to serve instance
   credentials. If this project ever runs multi-tenant on a shared server,
   this policy needs to be revisited (see `docs/CONTRIBUTOR_ISSUES.md`).
4. Make the request with `requests.request(method, url, timeout=10,
   allow_redirects=False)`. Redirects are disabled on purpose — a 302
   response could otherwise silently redirect the request to a different
   host after the SSRF check already passed.
5. On timeout / connection error / non-JSON body: save a run with
   `result="error"` and a human-readable `error_message`, skip diffing.
6. Otherwise: call `diff_engine.diff_response(...)`, save the run with the
   result it returns, and bulk-insert every diff into `run_diffs`.
7. Respond with the full run (including its diffs) as JSON — this is what
   the frontend renders directly into the PASS/NOTICE/DRIFT/ERROR panel.

## Frontend

Server-rendered Jinja2 templates (`app/templates/`) plus one vanilla JS
file (`app/static/js/app.js`) — no build step, no framework. Each page
wraps its content in a `<div id="...-page">`; `app.js` checks which of
those ids is present on `DOMContentLoaded` and initializes only that
page's behavior. All data loading and mutation goes through `fetch()`
calls to the `/api/...` JSON routes above; the Jinja templates only
pre-render the handful of values needed for the page shell (IDs, names,
breadcrumbs) to avoid a second round-trip on first paint.

The contract builder (`endpoint.html` + the field-row functions in
`app.js`) builds the `schema_json` shape client-side: each field row can
recursively contain more field rows (for `object`) or declare an item type
(for `array`), and a live `<pre>` preview re-serializes the whole tree on
every input/change event so what you're about to save is never a
surprise.
