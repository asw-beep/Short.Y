# Day 06 — Phase 2: Link Expiration

## Implemented
- `urls.expires_at` (nullable) + migration `0003` (up/down round-trip verified).
- `ShortenRequest.expires_at` (optional ISO 8601); validator rejects non-future
  values (422) and treats naive datetimes as UTC. `ShortenResponse` echoes it.
- `create_short_url(..., expires_at=)` persists expiry.
- `resolve_long_url` enforces expiry: expired → `URLExpiredError` → **410 Gone**.
  Distinct `EXPIRED` (`\x01`) cache sentinel so repeat hits 410 without the DB;
  positive cache TTL capped at `min(cache_ttl, time-to-expiry)`.
- Tests: `tests/test_expiration.py` (create future, reject past, future redirects,
  expired → 410 + sentinel cached, sentinel short-circuits, service-level raise).

## Decisions
- **Resolve-time enforcement**, not a TTL sweeper — simpler, no scheduler, no
  expiry/delete race. ADR-008.
- **410 Gone** over 404 — preserves the existed-but-gone semantic.
- **Cache TTL capped at time-to-expiry** so the cache never outlives the mapping.

## Learned
- The redirect path now has three terminal states (found / missing / expired),
  each with its own cache sentinel — negative caching generalises cleanly to a
  small sentinel set (`\x00` missing, `\x01` expired).

## Problems
- None substantive; all 48 tests passed on the first run after wiring.

## Solution
- N/A. Migration `0003` applied + downgraded + re-applied against the dev DB.

## Next
- Phase 3: Docker hardening (multi-stage, non-root, HEALTHCHECK), CI (pytest +
  bandit + pip-audit), Nginx reverse proxy; consolidate architecture.md /
  how-it-works.md and bump the diagram.
