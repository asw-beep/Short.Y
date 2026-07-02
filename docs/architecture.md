# Architecture

## Current topology (Phase 3)

```
                          ┌─────────── Nginx (edge: TLS-term point, X-Real-IP, limit_req) ───────────┐
Client ─────────────────► │                                                                          │
                          └──────────────────────────────┬───────────────────────────────────────────┘
                                                          ▼
                                            FastAPI app (uvicorn, non-root container)
                                            • per-route rate limiting (SlowAPI + Redis)
                                            • structured logging + request IDs
                                            • /livez (liveness), /health (readiness)
                                                          │
                          ┌───────────────────────────────┼───────────────────────────────┐
                          ▼                                ▼                                ▼
                     Redis  ◄── cache-aside ──►     Redis Streams  ── XADD ──►     PostgreSQL
                 (short_code→long_url,           (clicks:stream)                 (urls, clicks)
                  rate-limit buckets,                    │
                  negative/expired                       ▼
                  sentinels)                     Analytics Worker ── batch INSERT ──► PostgreSQL
                                                 (XREADGROUP consumer group, XACK)
```

See `docs/diagrams/architecture-v3.md` for the Mermaid source.

## Build phases

- **Phase 1 — Core:** `Client → FastAPI → PostgreSQL`. Create + redirect, Base62.
- **Phase 2 — Performance:** Redis cache-aside redirects; per-route rate limiting;
  structured logging + health checks; click analytics worker; link expiration.
- **Phase 3 — Scale:** hardened multi-stage non-root Docker image; CI
  (tests + bandit + pip-audit); Nginx reverse proxy / load-balancer at the edge.
- **Addendum — Frontend:** minimal unauthenticated HTML/JS pages (shorten form,
  live-links table). Scope amendment, not in the original EDD — see
  `Instrcutions.md` addendum and ADR-012.
- **Addendum — Render deployment:** `render.yaml` Blueprint (web + free
  Postgres + free Redis). No separate worker or Nginx service — see
  `docs/deployment.md` and ADR-013 for what differs from the topology above.

## Components

| Component | Responsibility |
|---|---|
| **Nginx** | Reverse proxy / LB edge. Sets `X-Real-IP`/`X-Forwarded-*`, edge `limit_req`, load-balances the `shortener_api` upstream. `nginx/nginx.conf`. |
| **FastAPI app** | HTTP API: `POST /shorten`, `GET /{code}`, `GET /stats/{code}`, `GET /api/urls`, `/livez`, `/health`. Rate limiting, logging, validation. Also serves the frontend: `GET /`, `GET /list`, `/static/*`. |
| **Redis** | (1) cache-aside `short_code → long_url` with negative/expired sentinels; (2) rate-limit buckets (moving-window); (3) `clicks:stream` analytics event log. Pooled client via app lifespan, injected with `get_cache`. |
| **Analytics worker** | Standalone process (`python -m app.worker`) locally/in Compose. Consumer-group drain of `clicks:stream` → batch INSERT into `clicks`. **On Render** (no free Background Workers), the same drain logic runs as an in-process asyncio task in the web service instead (`ENABLE_INPROCESS_WORKER=true`, ADR-013). |
| **PostgreSQL** | Source of truth: `urls` (+ monotonic `urls_id_seq`) and `clicks`. |
| **Alembic** | Schema migrations (`0001` urls, `0002` clicks, `0003` expires_at). |

## Layering

```
app/
  api/routes.py         # HTTP layer only — no SQL
  services/             # business logic: shortener, analytics, base62
  models/               # SQLAlchemy: URL, Click
  schemas/              # Pydantic request/response
  core/                 # config, database, cache, ratelimit(+handler), logging
  web/                  # frontend: index.html, list.html, static/style.css
  main.py               # app wiring, middleware, health, frontend routes
  worker.py             # standalone analytics consumer
```

Dependency injection throughout (`get_db`, `get_cache`), so every collaborator is
overridable in tests. Configuration is a single `pydantic-settings` singleton.

## Data model

`urls`:
- `id BIGSERIAL PRIMARY KEY` — source for Base62 encoding
- `short_code VARCHAR(32) UNIQUE NOT NULL` — indexed
- `long_url TEXT NOT NULL`
- `is_custom BOOLEAN NOT NULL DEFAULT FALSE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `expires_at TIMESTAMPTZ NULL` — NULL = never expires (Phase 2)

`clicks` (written only by the worker):
- `id BIGSERIAL PRIMARY KEY`
- `short_code VARCHAR(32) NOT NULL` — indexed; composite `(short_code, clicked_at)`
- `clicked_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `referrer TEXT NULL`, `user_agent TEXT NULL`
