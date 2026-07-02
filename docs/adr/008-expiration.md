# ADR 008 — Link Expiration

**Status:** Implemented (Phase 2).

**Decision:** Support an optional `expires_at` on a short link. Expiry is enforced
**at resolve time** (redirect returns **410 Gone**), not by a background sweep.

**Alternatives considered:**
- **TTL sweeper job** deleting expired rows — needs a scheduler, and a race where a
  link resolves between expiry and deletion. Resolve-time checks are simpler and
  correct without extra infrastructure.
- **Store TTL only in Redis** — loses the source of truth on cache eviction; DB
  must hold expiry authoritatively.
- **404 for expired** — loses the semantic distinction; 410 Gone tells clients the
  resource existed and is intentionally gone.

**Reason & mechanics:**
- Authoritative expiry lives in Postgres (`urls.expires_at`, nullable = never).
- `resolve_long_url` checks expiry on the DB read; expired → raises
  `URLExpiredError` → 410.
- **Cache stays consistent with expiry two ways:** (1) a distinct `EXPIRED`
  sentinel (`\x01`) is cached so repeat hits 410 without touching the DB; (2) a
  live mapping's positive cache TTL is capped at `min(cache_ttl, time-to-expiry)`,
  so the cache can never serve a link past its expiry.
- Input validation rejects a non-future `expires_at` (422), so the API can't mint
  an already-dead link; naive datetimes are treated as UTC.

**Consequences:**
- Expired rows are not reaped; they linger until a future cleanup job. Fine at V1
  scale, revisit for storage hygiene.
- Expiry precision is bounded by the negative-sentinel TTL for the *repeat*-hit
  path (a link may 410 from cache up to `cache_negative_ttl_seconds` after a clock
  tick), which is acceptable.
