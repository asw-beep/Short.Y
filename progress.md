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

### Done
- ✓ Docker hardening (day-07) — multi-stage, non-root, `HEALTHCHECK`, env-based
  secrets, worker service. ADR-009.
- ✓ CI (day-08) — GitHub Actions: pytest+coverage (≈88%) on real PG/Redis, bandit
  (blocking), pip-audit (advisory). ADR-010.
- ✓ Nginx reverse proxy (day-09) — edge proxy/LB, `limit_req`, `X-Real-IP`;
  limiter hardened to prefer unspoofable `X-Real-IP`. ADR-011. Diagram v3.

**Phase 3 complete.** All résumé-claimed features implemented + verified.

---

## Addendum — Minimal Frontend
**Status: Complete ✓** (scope amendment requested by the user, day-10)

- ✓ `GET /` shorten form, `GET /list` live-links table (short URL, original URL,
  expiry), `GET /api/urls` (paginated JSON backing the table). Plain HTML/CSS/JS,
  no build step, no auth. ADR-012.
- **Flagged, not hidden:** `/list` + `/api/urls` are unauthenticated and expose
  every live mapping — a bigger information-disclosure surface than the
  pre-existing enumeration risk. See `docs/threat-model.md`. Do not expose this
  deployment publicly without adding auth first.
- 59/59 tests pass. Verified live in a real browser: shorten → redirect →
  appears correctly in the table.

---

## Addendum — Deployability (Render Blueprint)
**Status: Config complete ✓, actual deploy pending** (user feedback, day-11)

- ✓ `render.yaml` Blueprint: free web + free Postgres + free Redis
  (`ipAllowList: []`). No separate worker or Nginx service (ADR-013).
- ✓ `BASE_URL` auto-adopts Render's `RENDER_EXTERNAL_URL` when unset — short
  links reflect the real deployed domain automatically.
- ✓ In-process analytics worker fallback (`ENABLE_INPROCESS_WORKER`) for
  Render's free tier, which has no Background Workers at all. Docker Compose
  unaffected (still runs the real separate `worker` container).
- ✓ `docs/deployment.md` — walkthrough + free-tier caveats (Postgres 30-day
  expiry, cold starts, unverified Render proxy headers).
- 64/64 tests pass. Verified live: in-process worker drains clicks correctly
  both alongside and in isolation from the standalone worker container.
- **Not done:** actually creating the Render account and clicking deploy — the
  user's action. README's "Live Demo" section is a placeholder until then.
