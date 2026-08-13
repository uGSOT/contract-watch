# Candidate issues for contributors

A starting list, grouped by the difficulty tiers in
`.github/ISSUE_TEMPLATE/`. These are ideas, not commitments — turn one
into an actual GitHub issue (using the matching template) before starting
work on it, so two people don't build the same thing.

## Beginner

- **Delete buttons in the UI.** `DELETE /api/projects/<id>` and
  `DELETE /api/projects/<id>/endpoints/<id>` already exist in the backend,
  but there's no button for them on the dashboard/project pages. Wire one
  up with a confirm step.
- **Copy JSON preview to clipboard.** A small button next to the contract
  builder's `<pre id="schema-preview">` that copies its contents.
- **Edit project/endpoint description after creation.** Right now
  `description` can only be set at creation time even though the update
  routes (`PUT /api/projects/<id>`, `PUT .../endpoints/<id>`) support it.
- **Empty-state polish.** Dashboard/history/project pages show a plain
  "no X yet" message — make these more helpful (e.g. point at the form
  above them).

## Intermediate

- **Latest-run badge on the endpoint list.** The project page
  (`project.html`) lists endpoints but you have to open each one to see
  its last run result. Show a PASS/DRIFT/ERROR badge inline, sourced from
  `GET /api/contracts/<id>/runs?per_page=1`.
- **CSV export of run history.** Add an export option to the History page
  — either a new `?format=csv` on `GET /api/runs` or a client-side CSV
  builder from the existing JSON.
- **Auto-refreshing recent runs.** Poll `GET /api/contracts/<id>/runs`
  every N seconds while an endpoint page is open, so a run triggered
  elsewhere (or later, by the scheduler once it exists) shows up without
  a manual reload.
- **Search/filter on the dashboard** once there are many projects — filter
  the project list client-side by name.

## Advanced

These map to Phase 8 (deliberately out of scope for v1) and each needs a
short design writeup in the issue before code, per the advanced template.

- **Scheduler.** Periodic runs without a human clicking the button, using
  [APScheduler](https://apscheduler.readthedocs.io/). Needs: a way to mark
  a contract as scheduled (interval or cron-like), a background job that
  iterates scheduled contracts and calls the same run logic
  `app/runner` already exposes, and a process that keeps running
  independently of any single HTTP request (which also means: this can't
  live inside the Flask request/response cycle the way everything else in
  this repo does — that's what makes it advanced).
- **Alerts.** Once the scheduler exists, post to Slack (webhook) and/or
  send email when a run's `result` is `drift`. Should respect
  `acknowledged` so it doesn't re-alert on a run someone already
  acknowledged.
- **Authentication.** This is currently a single-user local tool with no
  login. Multi-user support means sessions or tokens, and every route in
  `app/projects`, `app/endpoints`, etc. would need to start scoping
  queries by owner.
- **Multiple environments per project.** Right now a project has one
  `base_url`. Real APIs have staging/prod/etc. — this likely means an
  `environments` table and letting a Run choose which one to hit.
- **Schema inference.** Hit an endpoint once and generate a starter
  contract from the actual response shape, instead of building the schema
  by hand in the contract builder.
- **OpenAPI/Swagger import.** Parse a spec file into projects/endpoints/
  contracts automatically.
- **SSRF policy revisit.** The current guard (see
  `docs/ARCHITECTURE.md`) only blocks link-local/metadata addresses and
  intentionally allows private/loopback IPs, because v1 is single-user and
  local-only. If this project ever runs multi-tenant on a shared server,
  that policy needs to change to block private ranges too — worth its own
  issue and discussion before the scheduler makes runs happen without a
  human present to notice something odd.
