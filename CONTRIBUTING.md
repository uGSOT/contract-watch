# Contributing to Contract Watch

Thanks for wanting to help. This project is deliberately small and
readable — please keep changes that way.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest    # should be all green before you start
```

## Workflow

1. Open or claim an issue first for anything non-trivial, so two people
   don't build the same thing. See
   [docs/CONTRIBUTOR_ISSUES.md](docs/CONTRIBUTOR_ISSUES.md) for a curated
   list by difficulty (beginner / intermediate / advanced) if you're
   looking for somewhere to start.
2. Branch off `main`.
3. Write the code, and write or update tests alongside it — every backend
   module in this repo (`app/projects`, `app/endpoints`, `app/contracts`,
   `app/diff_engine`, `app/runner`, `app/runs`) has a matching test file
   in `tests/`. New behavior should follow the same pattern.
4. Run `pytest` and make sure it's green.
5. Open a pull request describing what changed and why.

## Code style

- Match the existing patterns rather than introducing new ones — e.g. every
  API route opens a connection with `get_db()`, does its work in a
  `try/finally`, and returns `jsonify(...)` with an explicit status code.
- No new dependencies without a good reason — this project intentionally
  has a short `requirements.txt`.
- Frontend is plain HTML (Jinja2 templates) + CSS + vanilla JS — no build
  step, no framework. Keep it that way.
- Prefer clarity over cleverness. This codebase is meant to be readable by
  contributors who are new to Flask.

## Reporting bugs

Open an issue with: what you did, what you expected, what happened
instead, and (if relevant) the contract/schema and response body that
triggered it.
