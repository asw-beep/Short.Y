# ADR 011 — Nginx Reverse Proxy

**Status:** Implemented (Phase 3).

**Decision:** Put **Nginx** in front of the FastAPI app as the edge: reverse proxy,
load-balancer for the API upstream, and an edge rate-limit layer.

**Responsibilities:**
- **Upstream/LB:** an `upstream shortener_api` block fronts one-or-more `api`
  replicas (scale by adding `server` lines or `--scale api=N` with the host port
  removed). `keepalive` connections to the app.
- **Client identity:** sets `X-Real-IP $remote_addr` (overwrites any client value,
  so it is unspoofable) and appends `X-Forwarded-For`. The app trusts `X-Real-IP`
  when `TRUST_PROXY=true`.
- **Edge rate limiting:** `limit_req_zone`/`limit_req` (50 r/s, burst 100) blunts
  volumetric floods *before* they reach FastAPI — defense in depth over the app's
  per-IP limiter (ADR-005).
- **JSON access logs** for a uniform log pipeline; `/livez` proxied without log
  noise.

**Alternatives considered:**
- **Traefik / Caddy** — auto-TLS and dynamic config are nice, but Nginx is the
  spec's choice (`Instrcutions.md`) and the most widely understood.
- **App-only rate limiting** — no edge shield; a flood still spends FastAPI worker
  time. Nginx drops it at the edge.

**Security follow-through (found via live testing):** with `$proxy_add_x_forwarded_for`
Nginx *appends* to XFF, so its left-most entry is still client-controlled. Keying
the limiter on left-most XFF would let a client spoof buckets even behind the
proxy. The app was changed to prefer the Nginx-set, non-appendable `X-Real-IP`.
Documented in the threat model.

**Consequences:**
- In production the API should **not** publish a host port — only Nginx is
  exposed; the dev compose still maps `8000` for direct access and `8080` for the
  Nginx path.
- `TRUST_PROXY` must be **false** unless actually behind this proxy, or XFF/real-ip
  headers from a direct client would be believed.
- TLS termination is where this Nginx layer would live; not configured in the
  local compose.
