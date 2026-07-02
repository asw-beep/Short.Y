# ADR 005 — Per-Route Rate Limiting

**Status:** Implemented (Phase 2).

**Decision:** Enforce per-IP, per-route rate limits using **SlowAPI** with a
**Redis** storage backend and the **moving-window** strategy.

**Alternatives considered:**
- `fastapi-limiter` — async, Redis-based. Comparable, but couples limits to
  `Depends()` and is async-only; our routes are sync (Phase 1 decision).
- Hand-rolled Redis token bucket / `INCR`+`EXPIRE` — more control, more code and
  more edge cases (atomicity, window boundaries) to get right.
- In-process limiter (no Redis) — resets per worker and is bypassed the moment we
  run more than one API replica (Phase 3). Rejected outright.

**Reason:**
- **Redis storage** means every FastAPI worker/replica shares one counter, so the
  limit holds under the multi-replica topology Phase 3 introduces. Redis is
  already a dependency (ADR-003), so no new infrastructure.
- **Moving-window** avoids the fixed-window burst problem (2× the limit across a
  boundary). `limits` implements it atomically in Redis.
- **SlowAPI** is the most widely used FastAPI limiter, gives decorator-based
  per-route limits, and emits standard `Retry-After` / `X-RateLimit-*` headers.

**Configuration:**
- Limits live in `settings` (`rate_limit_shorten` = 30/min, `rate_limit_redirect`
  = 120/min), referenced by the decorators via **callables** so they are tunable
  per environment and overridable in tests without touching decorators.
- `POST /shorten` is the stricter limit (creation is the abuse-expensive path —
  spam mass-creation). `GET /{code}` is more generous but still bounded to blunt
  sequential-ID enumeration scans.

**Client identity — `client_ip`:**
The limiter key is the client IP. Directly, that is the socket peer. **Behind the
Phase 3 Nginx proxy the peer is Nginx**, so the real client is the left-most
`X-Forwarded-For` entry — but XFF is attacker-controllable, so we only honour it
when `trust_proxy` is enabled (i.e. we know a proxy we control sets it). With
`trust_proxy` off, a spoofed XFF is ignored and cannot mint a fresh bucket.

**Availability:** `swallow_errors=True` — if Redis is unreachable, the limiter
fails **open** rather than 500-ing every request. Rationale: a limiter outage
should degrade abuse protection, not availability. This is deliberately the
*opposite* trade-off from the redirect cache (ADR-003, fail-closed), because the
cache is correctness-critical for redirects while the limiter is protective only.

**Consequences:**
- Every limited request does one extra Redis round-trip. On the redirect hot path
  this is additive to the existing cache `GET`; acceptable well under the 100 ms
  target.
- Limits are per-IP, so clients behind a shared NAT/CGNAT share a bucket. Accepted
  for V1 (no auth/API keys yet; per-user limits are a V2 item).
