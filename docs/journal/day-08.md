# Day 08 — Phase 3: CI Pipeline

## Implemented
- `.github/workflows/ci.yml` — two jobs:
  - **test**: postgres + redis service containers, test DB created via psycopg2,
    `pytest --cov=app` (≈88% coverage).
  - **security**: `bandit -r app -ll` (blocking, clean) + `pip-audit` (advisory).
- `requirements-dev.txt` (pytest-cov, bandit, pip-audit) — keeps scan/test tooling
  out of the runtime image.
- Remediation: bumped `python-dotenv` 1.0.1 → 1.2.2 (direct, CVE-2026-28684).

## Decisions
- **pip-audit advisory, bandit blocking** — gate our own code hard; treat
  third-party CVEs as visible-but-non-blocking to avoid red builds on unrelated
  PRs. ADR-010.
- **Real Postgres/Redis in CI**, not SQLite/fakeredis — mirror prod (nextval()).
- **psycopg2 step to create the test DB** — no dependency on a preinstalled psql.

## Learned
- `pip-audit` flags transitive `starlette` CVEs pinned by FastAPI 0.115's version
  cap — a real dependency-management constraint worth documenting rather than
  papering over. Tracked for a future FastAPI bump.

## Problems
- pip-audit reported 10 vulns across python-dotenv, pytest, starlette.

## Solution
- Bumped the one direct, low-risk dep (python-dotenv); made the audit advisory and
  documented the transitive ones. Verified locally: 48 tests pass with coverage,
  bandit clean, YAML valid.

## Next
- Nginx reverse proxy in front of the API (+ `trust_proxy=true` behind it).
- Consolidate architecture.md / how-it-works.md + bump the diagram to v3.
