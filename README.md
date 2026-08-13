# Contract Watch

Contract Watch watches an API you depend on and tells you the moment its
responses stop matching what you expect — before your app breaks in front
of someone.

## The idea

1. **Register a project** — the API you want to watch (name + base URL).
2. **Add an endpoint** — a specific route on that API, e.g. `GET /api/users/1`.
3. **Write a contract** — the JSON shape you expect back: field names, types,
   which fields are required, the expected HTTP status.
4. **Click Run.** Contract Watch calls the real endpoint, compares the real
   response against your contract, and shows **PASS**, **DRIFT**, or **ERROR**.
5. Every run is saved. The **History** page shows exactly when something
   broke and what changed, so you know precisely what to tell your teammate
   ("you renamed `user_id` to `userId` and it's now a string, on Thursday
   at 2pm").
6. If a change was intentional, **Acknowledge** the run — it stays in
   history but stops being flagged as a new problem.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit
together, and [docs/API.md](docs/API.md) for the full route reference.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                   # creates contract_watch.db with sample data
python run.py                    # starts the dev server on http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in a browser. The seed script gives you one
project, one endpoint, and one contract to start from — or create your own
from the dashboard.

## Running the tests

```bash
pytest
```

## What's here

| Layer | Where |
|---|---|
| Projects / Endpoints / Contracts CRUD | `app/projects`, `app/endpoints`, `app/contracts` |
| Diff engine (schema comparison) | `app/diff_engine.py` |
| Runner (makes the HTTP call, saves the run) | `app/runner` |
| Run history, filtering, acknowledge | `app/runs` |
| Frontend (server-rendered pages + vanilla JS) | `app/templates`, `app/static` |
| Database schema | `migrations/001_initial.sql` |

## Scope

This is v1: everything runs on your own machine, and a run only happens
when you click the button. There's no scheduler, no alerts, and no auth —
see [docs/CONTRIBUTOR_ISSUES.md](docs/CONTRIBUTOR_ISSUES.md) for what's
planned next and how to help build it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
