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
**Status: Not started**

### Planned
- Redis cache on `GET /{code}` — check Redis before Postgres
- Rate limiting on `POST /shorten` — by IP, using Redis
- Analytics worker — async click tracking, `GET /stats/{code}` endpoint

---

## Phase 3 — Scale (Nginx, full Docker, stress testing)
**Status: Not started**
