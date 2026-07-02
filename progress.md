# Project Progress

## Phase 1 — Core (FastAPI + Postgres)
**Status: Complete ✓**

### What was built
- `POST /shorten` — validates URL, generates Base62 short code from `urls_id_seq`, supports custom aliases
- `GET /{code}` — 301 redirect
- `GET /health` — health check (added during testing phase)
- Alembic migration for `urls` table
- Docker Compose: Postgres + Redis (idle) + API
- Full test suite: 23 tests across base62, shortener service, and API layers

### Tested
- Automated: `python -m pytest` — 23/23 passing
- Manual: `POST /shorten`, `GET /{code}` redirect in browser, `GET /health`

### Known decisions
- 301 (permanent) redirect — mappings are immutable in V1
- Auto-increment Base62 over random codes — no retry loop needed
- Custom alias: 4–32 chars, `[a-zA-Z0-9_-]`, reserved words blocked
- No application-level uniqueness check — TOCTOU bug avoided, DB constraint handles it

---

## Phase 2 — Performance (Redis cache, rate limiting, analytics worker)
**Status: Complete ✓**

### Done
- ✓ Redis cache-aside on `GET /{code}` (day-02) — negative caching, fail-closed.
- ✓ Per-route rate limiting (day-03) — SlowAPI + Redis moving-window, per-IP,
  XFF-aware, 429 + `Retry-After`. ADR-005.
- ✓ Structured logging + health checks (day-04) — structlog JSON, request IDs,
  `/livez` liveness + `/health` readiness (DB+Redis), security event logs. ADR-006.
- ✓ Click analytics worker (day-05) — Redis Streams → consumer-group worker →
  Postgres `clicks`, `GET /stats/{code}`. ADR-007.
- ✓ Link expiration (day-06) — `expires_at`, 410 Gone, cache TTL capped to expiry,
  `EXPIRED` sentinel. ADR-008.

---

## Phase 3 — Scale (Nginx, full Docker, stress testing)
**Status: In progress**

### Planned
- Docker hardening — multi-stage build, non-root user, `HEALTHCHECK`.
- CI — GitHub Actions: pytest + bandit + pip-audit.
- Nginx reverse proxy in front of the API (+ diagram v3).
