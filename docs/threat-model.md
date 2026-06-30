# Threat Model

Scope: Phase 2 (create + cache-aside redirect). Rate limit still pending.

| Threat | Status | Mitigation | Notes |
|---|---|---|---|
| Brute-force enumeration of short codes | **Accepted** | Documented | Sequential IDs are guessable. Rate limiting in Phase 2 is the primary control. V2 may switch to random codes. |
| Alias squatting on system routes | Mitigated | Reserved-word list (`api`, `admin`, `health`, `docs`, `openapi`, `redoc`, `static`, `shorten`) | Flagged for expansion as new routes are added. |
| URL injection (non-http schemes, `javascript:`, `data:`) | Mitigated | Pydantic `HttpUrl` + explicit scheme allowlist `{http, https}` | Validated in `app/schemas/url.py`. |
| Open redirect abuse | Inherent / accepted | We redirect to arbitrary stored URLs by design. URL validated at create time. No auth context to steal from victims. | V2: malware/phishing scanning (out of scope per Instructions.md). |
| SQL injection | Mitigated | SQLAlchemy parameterized queries everywhere; no string SQL except a single `nextval('urls_id_seq')` with no user input. | — |
| Spam mass-creation | **Accepted** | None Phase 1 | Phase 2: per-IP rate limit on `POST /shorten`. |
| DDoS | **Accepted** | None Phase 1 | Phase 3: Nginx in front, connection limits. |
| Overly long URL DoS | Mitigated | 2048-char cap on `url` | — |
| Alias collision race | Mitigated | DB UNIQUE constraint + `IntegrityError` → 409 | Atomic at the DB layer; no TOCTOU window. |
| 404 enumeration → DB stampede | Mitigated (Phase 2) | Negative caching: known-missing codes cached as `\x00` for 60s, absorbing sequential-ID scans before they reach Postgres. | Brute-force volume still needs rate limiting (next Phase 2 feature). |
| Cache poisoning | N/A | Redis is populated only from our own validated DB rows; no external write path into the cache. | — |
| Stale negative cache hides a fresh code | Accepted (Phase 2) | A code created within ≤60s of a 404 on the same code is briefly invisible. | Bounded by `cache_negative_ttl_seconds`. Acceptable for a shortener. |
| Redis as redirect SPOF (fail-closed) | **Accepted** | Redis outage → 503 on all redirects (deliberate, ADR-003). Protects Postgres from thundering herd; trades availability. | Phase 3 (Nginx/HA) may revisit. |
| Redis exposed / unauthenticated | Note | Dev compose maps `6379` to host with no AUTH. | Production must not expose Redis publicly; add AUTH/network isolation in Phase 3. |
