# Day 04 — Phase 2: Structured Logging & Health Checks

## Implemented
- `app/core/logging.py`: structlog configured as JSON (prod) / console (dev);
  stdlib + uvicorn logs routed through structlog's `ProcessorFormatter` so
  everything shares one shape. `uvicorn.access` silenced (we log requests).
- Request-logging middleware in `app/main.py`: binds `request_id` (from inbound
  `X-Request-ID` or a fresh uuid) + method/path/client_ip into contextvars, logs
  `request_completed` with status + duration_ms, echoes `X-Request-ID` back.
- Health split: `/livez` (static liveness) and `/health` (readiness — pings
  Postgres + Redis, 503 if degraded). Removed the old trivial `/health`.
- Security event logging: 429 handler now logs `rate_limit_exceeded`.
- Config: `log_level`, `log_json`.
- Tests: `tests/test_observability.py` (livez, readiness ok/degraded, request-id
  present/echoed).

## Decisions
- **Two health endpoints** (liveness vs readiness) so a DB blip doesn't restart
  the container, but a degraded instance still leaves the LB rotation. ADR-006.
- **Own middleware over `asgi-correlation-id`** — ~15 lines with structlog
  contextvars, one fewer dependency.

## Learned
- **Route registration order is match order.** Defining `/livez` and `/health`
  *after* `include_router` let the catch-all `GET /{code}` shadow them → 404s.
  Fix: register fixed system routes before the catch-all router.
- structlog contextvars make request-scoped fields automatic across every log
  line, including those emitted deep in exception handlers.

## Problems
- 4 failures: `/livez` and `/health` returned 404 (shadowed by `/{code}`), and
  the old `test_health` asserted the exact old body shape.

## Solution
- Moved health routes above `include_router`; updated `test_health` to assert
  `status == "ok"` rather than exact equality. All 37 tests pass. Live-fired
  uvicorn: JSON logs carry request_id/client_ip/duration; inbound X-Request-ID
  is honoured.

## Next
- Analytics worker: Redis Streams → consumer-group worker → Postgres `clicks`,
  plus `GET /stats/{code}`.
- Expiration policies (`expires_at`, 410 Gone).
