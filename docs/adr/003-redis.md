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

**Status:** Deferred to Phase 2. Container already provisioned in `docker-compose.yml`.
