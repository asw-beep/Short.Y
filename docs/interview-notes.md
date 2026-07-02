# Interview Notes

## Why PostgreSQL?
Strong indexing, transactions, atomic UNIQUE constraints (prevents alias-collision races at the DB layer), mature ecosystem. We also use its sequence (`urls_id_seq`) as the source of monotonic IDs for Base62 encoding.

## Why Redis? (Phase 2)
Hot URLs get hit repeatedly. Redis lets us serve redirects without touching Postgres, dropping latency and DB load. Also doubles as a rate-limit counter store. Implemented as cache-aside on the redirect path with positive + negative caching.

## Why not MongoDB?
We don't need document flexibility; we need a UNIQUE constraint that's enforced atomically and a fast sequence. Both are first-class in Postgres.

## Why cache redirects?
Read-heavy workload, immutable mappings. Cache-aside on `short_code → long_url` is a near-perfect fit — immutability means no write-time invalidation, just TTL eviction. We also negative-cache misses (`\x00`, 60s) so 404-enumeration scans don't stampede Postgres.

## Cache-aside vs write-through? Why fail-closed?
Cache-aside: the read path populates the cache on a miss; writes don't touch Redis. Simple, and a cold cache just means a one-time DB read per code. We chose **fail-closed** (503 if Redis is down) over fail-open (fall through to Postgres): under load, a sudden cache loss with fail-open would stampede Postgres. Tradeoff — Redis becomes a redirect-path SPOF, revisited with HA in Phase 3.

## How are collisions prevented?
- Auto-generated codes: derived from a Postgres sequence, so unique by construction.
- Custom aliases: UNIQUE constraint on `short_code`; duplicate inserts raise `IntegrityError` → 409. No application-level race window.

## How would you scale to 10M URLs?
Phase 1 already handles this on a single Postgres node — 10M rows on an indexed `short_code` is small. Add a read replica if read QPS gets high.

## How would you scale to 100k req/sec?
- Redis in front of Postgres (Phase 2).
- Horizontal scale FastAPI behind Nginx (Phase 3).
- Read replicas for Postgres; sharding becomes relevant past ~1B rows.
- The sequence becomes a bottleneck eventually — switch to random codes or sharded ID generation.

## How does rate limiting work, and why per-IP with Redis?
SlowAPI with a **Redis** storage backend and a **moving-window** strategy, applied
per-route via decorators (30/min create, 120/min redirect). Redis storage means
the limit is shared across every worker/replica — an in-process limiter resets per
worker and is bypassed the moment you scale out. Moving-window avoids the
fixed-window burst-at-boundary problem. The key is the client IP; behind Nginx we
trust the **unspoofable `X-Real-IP`** (set by the proxy), not the appendable
`X-Forwarded-For`. The limiter fails **open** on a Redis outage — the opposite of
the redirect cache — because a limiter is protective, not correctness-critical.

## Why an analytics worker instead of writing clicks inline?
The redirect is the <100 ms hot path. A synchronous INSERT per click couples
redirect latency to write-path health and burns the connection pool under
read-heavy load. Instead the redirect does one best-effort `XADD` to a Redis
Stream; a separate worker drains it with a **consumer group** (at-least-once,
`XACK` after commit) and batch-inserts. Stats are eventually consistent — a fair
trade to never block a redirect. Producing is best-effort so analytics can't break
a redirect.

## How is expiration enforced without a cleanup job?
At **resolve time**: `expires_at` is authoritative in Postgres; an expired code
returns **410 Gone**. A distinct `EXPIRED` cache sentinel makes repeat hits fast,
and a live mapping's cache TTL is capped at `min(cache_ttl, time-to-expiry)` so the
cache can never serve a link past its expiry. No sweeper, no expiry/delete race.

## What's the observability story?
`structlog` JSON logs with a per-request `request_id` bound via contextvars (so
every line during a request carries it, including security events like
`rate_limit_exceeded`). `/livez` is liveness (for the container probe), `/health`
is readiness (pings Postgres+Redis, 503 when degraded, for the LB).

## What was the hardest bug?
Two SlowAPI foot-guns and a routing-order trap:
1. **SlowAPI header injection** raised `parameter 'response' must be a Response`
   whenever a limited endpoint returned a Pydantic model — fixed by adding a
   `response: Response` param so the limiter has somewhere to write `X-RateLimit-*`.
2. **Route shadowing:** defining `/livez` and `/health` *after* `include_router`
   let the catch-all `GET /{code}` swallow them (404). Route matching is
   registration-order, so fixed system routes must be registered before the
   catch-all.
3. **XFF spoofing behind Nginx:** live-testing showed a client could still spoof
   its rate-limit bucket via `X-Forwarded-For` (Nginx *appends*, leftmost stays
   client-controlled). Fixed by preferring the Nginx-set `X-Real-IP`.

## How do you keep sequence-derived codes deterministic in tests, now with a cache?
Postgres `urls` is truncated with `RESTART IDENTITY` and Redis (test index `/1`) is `FLUSHDB`-ed between every test — so both the sequence and the cache start clean each test, keeping codes like `0000001` and cache assertions deterministic.

## What would you improve in V2?
- Switch to random Base62 codes to remove enumeration risk.
- Multi-region deployment with geo-DNS.
- URL safety scanning.
