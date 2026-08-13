---
name: Advanced task
about: Requires a new architectural piece (a background process, a new dependency, a new cross-cutting concern like auth) — needs a short design writeup before code.
title: "[Advanced] "
labels: enhancement
assignees: ""
---

## What

<!-- What should exist after this is done, and what problem does it solve? -->

## Why this is "advanced"

<!-- e.g. "runs outside the request/response cycle", "introduces a new
dependency", "changes a cross-cutting concern like auth or the DB schema" -->

## Proposed approach

<!-- Sketch the design before writing code — libraries you'd use, new
tables/columns if any, how it interacts with existing modules. A
maintainer should sign off on this before the PR gets big. -->

## Acceptance criteria

- [ ]
- [ ]
- [ ] Tests added/updated, `pytest` green
- [ ] Docs updated (`docs/ARCHITECTURE.md` and/or `docs/API.md`) if this
      changes how the system works

## Notes

Check [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) and
[docs/CONTRIBUTOR_ISSUES.md](../../docs/CONTRIBUTOR_ISSUES.md) first —
some advanced ideas (scheduler, alerts, auth) already have a starting
design written down there.
