# Day 02 — Phase 2: Redis Redirect Cache

## Implemented
- Cache-aside on `GET /{code}`: check `url:{code}` in Redis → hit serves 301 (or 404 for a negative sentinel); miss queries Postgres, populates the cache, then redirects.
- Negative caching: known-missing codes stored as `\x00` with a short TTL (60s) to absorb 404-enumeration scans.
- Fail-closed: Redis error on the redirect path → 503 (Redis is a hard dependency for redirects).
- `app/core/cache.py`: pooled `redis.Redis` created in the FastAPI lifespan, injected via `get_cache` (mirrors `get_db`).
- Config: `redis_url`, `cache_ttl_seconds` (3600), `cache_negative_ttl_seconds` (60).
- Compose: `REDIS_URL` env + `depends_on: redis (service_healthy)`.
- Tests: `tests/test_cache.py` (populate, serve-from-cache, negative caching, negative short-circuit, fail-closed 503) against a real Redis on logical DB `/1`, flushed between tests.

## Decisions
- **Cache only, expiry deferred.** No `expires_at` column / migration this feature — expiration is a separate Phase 2 item. Keeps the PR small; mappings stay immutable so TTL eviction suffices.
- **Fail-closed over fail-open.** Protect Postgres from a thundering herd if the cache vanishes under load, accepting Redis as a redirect-path SPOF (Phase 3 HA may revisit).
- **Real Redis in tests** (separate DB index), not `fakeredis` — mirrors the deliberate real-Postgres testing choice.
- Cache value is the bare `long_url`; key `url:{code}` is namespaced so the upcoming rate-limit keys won't collide.

## Learned
- Cache-aside + immutable data = no write-time invalidation; TTL is the whole eviction story.
- Negative caching is the cheap, correct answer to enumeration-driven DB stampedes.

## Problems
- `redis` wasn't installed in the local interpreter, so the suite couldn't import the new client.

## Solution
- Added `redis==5.0.8` to `requirements.txt` and installed it locally. All 28 tests pass.

## Next
- Phase 2 feature #2: rate limiting (Redis-backed, per-IP, `X-Forwarded-For`-aware for the eventual Nginx front).
- Then: analytics worker (architecture-v4).
- Bump `docs/diagrams/architecture-v3.png` to reflect Client → API → Redis → DB.
