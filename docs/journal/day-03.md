# Day 03 — Phase 2: Per-Route Rate Limiting

## Implemented
- SlowAPI limiter (`app/core/ratelimit.py`) with a **Redis** storage backend and
  the **moving-window** strategy, so limits hold across every worker/replica.
- Per-route, per-IP limits driven from `settings` via callables (tunable, testable):
  `POST /shorten` = 30/min (`rate_limit_shorten`), `GET /{code}` = 120/min
  (`rate_limit_redirect`).
- `client_ip` key func: uses the socket peer, upgrading to the left-most
  `X-Forwarded-For` entry **only** when `trust_proxy` is set (Phase 3 Nginx).
- 429 handler (`app/core/ratelimit_handler.py`): JSON body + `Retry-After` /
  `X-RateLimit-*` headers.
- Wired in `app/main.py` (`app.state.limiter` + exception handler); both routes
  decorated; `shorten` gained a `response: Response` param so SlowAPI can inject
  headers on a Pydantic return.
- Tests: `tests/test_ratelimit.py` — shorten limit, redirect limit, per-IP
  isolation via trusted XFF, and spoofed-XFF-ignored-when-untrusted.

## Decisions
- **SlowAPI + Redis + moving-window** over `fastapi-limiter`, a hand-rolled token
  bucket, or an in-process limiter. See ADR-005 for the full trade-off.
- **Fail-open** on Redis outage (`swallow_errors=True`) — the *opposite* of the
  redirect cache's fail-closed stance. A limiter is protective, not
  correctness-critical, so its outage should not 503 all writes.
- Limits in config, referenced by callables, so tests set tiny limits instead of
  firing hundreds of requests.

## Learned
- SlowAPI can only attach rate-limit headers if the endpoint exposes a mutable
  `response: Response` (or returns a `Response`); a bare Pydantic return raises
  "parameter `response` must be an instance of starlette.responses.Response".
- XFF is attacker-controlled: an IP-keyed limiter is only sound if XFF trust is
  gated on a proxy you actually control.

## Problems
- First test run: 9 failures, all `parameter response must be an instance of ...`
  — SlowAPI header injection had no `Response` to write to on `POST /shorten`.

## Solution
- Added `response: Response` to the `shorten` signature. All 32 tests pass.
- Live-fired a real uvicorn instance: 3 allowed → `429` with `Retry-After: 58`
  and `X-RateLimit-*` headers.

## Next
- Structured logging + readiness `/health` (log 429s and other security events).
- Analytics worker (Redis Streams → worker → Postgres `clicks`) + `GET /stats/{code}`.
- Expiration policies (`expires_at`).
