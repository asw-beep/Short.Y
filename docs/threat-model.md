# Threat Model

Scope: Phase 1 (create + redirect, no cache, no rate limit).

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
