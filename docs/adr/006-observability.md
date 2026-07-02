# ADR 006 — Structured Logging & Health Checks

**Status:** Implemented (Phase 2).

**Decision:** Emit **structured JSON logs** via `structlog`, correlate every log
line to a **request_id** bound in contextvars by an HTTP middleware, and expose
**two** health endpoints: `/livez` (liveness) and `/health` (readiness).

**Alternatives considered:**
- Stdlib `logging` with a plain format — no structure; log aggregators (Loki,
  Datadog, ELK) can't query fields, and there's no request correlation.
- `asgi-correlation-id` for request IDs — popular, but a ~15-line `@app.middleware`
  using structlog contextvars covers our need without another dependency.

**Reason:**
- **JSON + contextvars**: one consistent, queryable stream. `request_id`,
  `method`, `path`, `client_ip` are bound once per request and appear on every
  line emitted during it — including security events like `rate_limit_exceeded`
  — with no manual plumbing.
- **stdlib routed through structlog's `ProcessorFormatter`**: uvicorn/SQLAlchemy
  logs render in the same shape as app logs. `uvicorn.access` is silenced because
  the middleware logs each request itself (with duration + request_id).
- **`log_json` toggle**: JSON in prod, colourised console in dev.

**Liveness vs readiness (why two endpoints):**
- `/livez` — static `{"status":"ok"}`, no dependency I/O. This is what the
  container `HEALTHCHECK` / orchestrator restart probe should call; a transient DB
  blip must not trigger a pod restart loop.
- `/health` — pings **Postgres** (`SELECT 1`) and **Redis** (`PING`), returns
  **503** if either is down. This is what a load balancer's out-of-rotation probe
  should call, so a degraded instance stops receiving traffic instead of serving
  errors.

**Consequences:**
- `/health` does two dependency round-trips per call; keep probe intervals sane
  (compose uses ~10s).
- Log volume increases (one line per request). At scale, sample or ship to an
  aggregator; fields are already structured for that.

**Security value:** rate-limit violations, readiness degradation, and unhandled
exceptions now log as structured events with client IP and request_id — the
minimum needed to investigate abuse and correlate an incident across requests.
