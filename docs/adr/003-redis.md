# ADR 003 — Use Redis (Phase 2)

**Decision:** Add Redis in Phase 2 for caching hot URLs and storing rate-limit counters.

**Alternatives:** No cache; in-process cache; Memcached.

**Reason:**
- Reduce DB reads on hot short codes.
- Improve redirect latency well under the 100ms target.
- Same instance doubles as a rate-limit counter store (Phase 2).

**Consequences:**
- Cache invalidation complexity. For Phase 1 the mappings are immutable, so TTL-based eviction is sufficient.
- Adds an external dependency.

**Status:** Caching implemented in Phase 2 (redirect path). Rate limiting still pending.

---

## Phase 2 update — redirect cache (implemented)

**Pattern:** Cache-aside on `GET /{code}` only. Writes stay DB-only.

**Key/value:** key `url:{code}` (namespaced for forthcoming rate-limit keys); value is the bare `long_url`, or the sentinel `\x00` for a known-missing code (negative caching). Positive TTL `cache_ttl_seconds` (3600s), negative TTL `cache_negative_ttl_seconds` (60s).

**Availability decision — fail-closed:** if Redis errors on the redirect path, the request returns **503** rather than falling through to Postgres. This makes Redis a hard dependency for redirects but protects Postgres from a thundering herd if the cache disappears under load. Consequence: Redis is now a redirect-path SPOF (Phase 3 may add HA). This was a deliberate choice over fail-open.

**Expiration:** intentionally *not* implemented here — deferred to a separate Phase 2 feature. No `expires_at` column yet. Mappings remain immutable, so TTL eviction is the only invalidation needed.

**Client lifecycle:** one pooled `redis.Redis` created in the FastAPI lifespan (`app/core/cache.py`), injected via the `get_cache` dependency — mirrors the `get_db` pattern, overridable in tests.

**Testing:** real Redis on a separate logical DB index (`/1`), `FLUSHDB` between tests — mirrors the real-Postgres testing choice rather than mocking.
