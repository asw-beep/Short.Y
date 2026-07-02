# Threat Model

Scope: Phase 2 (create + cache-aside redirect + per-route rate limiting).

| Threat | Status | Mitigation | Notes |
|---|---|---|---|
| Brute-force enumeration of short codes | Mitigated | Per-IP rate limit on `GET /{code}` (`rate_limit_redirect`, moving-window, Redis) + negative caching absorbs DB load | Sequential IDs are still guessable, but scan *rate* is now bounded per IP. Distributed scans across many IPs remain possible (Phase 3 Nginx conn-limits + V2 random codes). See ADR-005. |
| Alias squatting on system routes | Mitigated | Reserved-word list (`api`, `admin`, `health`, `docs`, `openapi`, `redoc`, `static`, `shorten`) | Flagged for expansion as new routes are added. |
| URL injection (non-http schemes, `javascript:`, `data:`) | Mitigated | Pydantic `HttpUrl` + explicit scheme allowlist `{http, https}` | Validated in `app/schemas/url.py`. |
| Open redirect abuse | Inherent / accepted | We redirect to arbitrary stored URLs by design. URL validated at create time. No auth context to steal from victims. | V2: malware/phishing scanning (out of scope per Instructions.md). |
| SQL injection | Mitigated | SQLAlchemy parameterized queries everywhere; no string SQL except a single `nextval('urls_id_seq')` with no user input. | — |
| Spam mass-creation | Mitigated | Per-IP rate limit on `POST /shorten` (`rate_limit_shorten`, 30/min default, moving-window, Redis) → 429 + `Retry-After` | Stricter than the redirect limit because creation is the abuse-expensive path. Per-IP only; shared-NAT clients share a bucket. See ADR-005. |
| DDoS | Partially mitigated | App-level per-IP rate limiting blunts single-source floods | Volumetric/distributed DDoS still needs edge controls: Phase 3 Nginx connection limits + `limit_req`. Limiter fails **open** on Redis outage (availability over protection, ADR-005). |
| Overly long URL DoS | Mitigated | 2048-char cap on `url` | — |
| Alias collision race | Mitigated | DB UNIQUE constraint + `IntegrityError` → 409 | Atomic at the DB layer; no TOCTOU window. |
| 404 enumeration → DB stampede | Mitigated (Phase 2) | Negative caching: known-missing codes cached as `\x00` for 60s, absorbing sequential-ID scans before they reach Postgres. Now paired with per-IP redirect rate limiting. | Both the DB-load and the scan-rate vectors are now addressed. |
| Rate-limit key spoofing (XFF) | Mitigated | `client_ip` only trusts `X-Forwarded-For` when `trust_proxy` is set; otherwise uses the socket peer. Prevents a client spoofing XFF to dodge or poison a bucket. | Enable `trust_proxy` **only** behind a proxy we control (Phase 3 Nginx). Tested in `test_ratelimit.py`. |
| Rate limiter as DoS lever (Redis outage) | Accepted | Limiter `swallow_errors=True` → fails **open** on Redis error, so a cache outage disables limits rather than 503-ing all writes. | Deliberate trade-off (protection < availability). Opposite of the redirect cache's fail-closed stance. See ADR-005. |
| Cache poisoning | N/A | Redis is populated only from our own validated DB rows; no external write path into the cache. | — |
| Stale negative cache hides a fresh code | Accepted (Phase 2) | A code created within ≤60s of a 404 on the same code is briefly invisible. | Bounded by `cache_negative_ttl_seconds`. Acceptable for a shortener. |
| Redis as redirect SPOF (fail-closed) | **Accepted** | Redis outage → 503 on all redirects (deliberate, ADR-003). Protects Postgres from thundering herd; trades availability. | Phase 3 (Nginx/HA) may revisit. |
| Redis exposed / unauthenticated | Note | Dev compose maps `6379` to host with no AUTH. | Production must not expose Redis publicly; add AUTH/network isolation in Phase 3. |
| Analytics PII collection | Mitigated (minimised) | Click events store `referrer` + `user_agent` (UA truncated to 512 chars). **Client IP is deliberately NOT stored.** | Referrer/UA are low-sensitivity; no IP linkage. If richer analytics is added, revisit retention + a privacy note. |
| Analytics stream unbounded growth (worker down) | Mitigated | `XADD ... MAXLEN ~100000` caps stream size; old events trimmed. | A prolonged worker outage drops the oldest un-drained clicks (analytics is best-effort). |
| Analytics event injection (header spoofing) | Accepted | `referrer`/`user_agent` come from client headers and are attacker-controlled, stored as-is. | They are only ever rendered as data in JSON stats, never executed/interpolated into SQL (ORM-parameterised). No stored-XSS sink in the API. |
