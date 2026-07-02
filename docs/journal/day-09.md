# Day 09 — Phase 3: Nginx Reverse Proxy + Docs Consolidation

## Implemented
- `nginx/nginx.conf` + `nginx` compose service (`:8080` → `api:8000`):
  `upstream` pool (scalable), `X-Real-IP`/`X-Forwarded-*`, edge `limit_req`
  (50 r/s burst 100), JSON access logs, unthrottled `/livez`.
- **Security hardening (found live):** `client_ip` now prefers the unspoofable
  Nginx-set `X-Real-IP` over the client-appendable `X-Forwarded-For`
  (`$proxy_add_x_forwarded_for` appends, so leftmost XFF is client-controlled).
  New test `test_xrealip_beats_spoofed_xff`.
- Consolidated docs: `architecture.md` (v3 topology + components + layering +
  data model), `how-it-works.md` (rate limit → cache → expiry → analytics →
  health), `docs/diagrams/architecture-v3.md` (Mermaid), `README.md` (all
  endpoints, dev/worker/nginx run, CI), `interview-notes.md` (rate limiting,
  analytics, expiration, observability, hardest bug).

## Decisions
- **Nginx** as the edge (spec choice) — proxy + LB + edge rate limiting. ADR-011.
- **Prefer X-Real-IP** for the limiter key behind the proxy — X-Real-IP is
  overwritten by Nginx and can't be forged; XFF can.

## Learned
- Live-testing the real proxy chain revealed a spoofing gap that the unit tests
  (which only ever sent XFF) had not: behind a proxy that *appends* XFF, keying on
  the leftmost entry is still attacker-controlled. Verification beats assumption.

## Problems
- Sending `X-Forwarded-For: 8.8.8.8` through Nginx made the app log
  `client_ip=8.8.8.8` — i.e. a client could still choose its own rate-limit bucket.

## Solution
- Switched the limiter key to `X-Real-IP` (Nginx-set) with XFF as fallback.
  49 tests pass; live E2E through `:8080` (shorten/redirect/stats) works and the
  app logs the forwarded client IP.

## Result
- **All résumé-claimed features now implemented and verified.** Phase 2 + Phase 3
  complete. See `progress.md`.
