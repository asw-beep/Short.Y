# Architecture

## Phase 2 (current)

```
Client → FastAPI → Redis → PostgreSQL   (architecture-v3)
```

Redirects are served cache-aside from Redis; writes (`POST /shorten`) go straight to Postgres. Redis is a hard dependency for the redirect path (fail-closed → 503 on outage). Rate limiting and the analytics worker (also Phase 2) are not yet built.

## History / Planned

- **Phase 1:** `Client → FastAPI → PostgreSQL` (no cache).
- **Phase 2 (current):** Redis read-through cache for redirects. Next: rate limiting, analytics worker.
- **Phase 3:** Add Nginx (reverse proxy + load balancing), full Docker deployment, stress testing.

## Components

| Component | Responsibility |
|---|---|
| FastAPI app | HTTP API: `POST /shorten`, `GET /{code}` |
| Redis | Cache-aside store for `short_code → long_url` (positive + negative). Pooled client created in app lifespan; injected via `get_cache`. |
| PostgreSQL | Persistent storage for URL mappings, source of monotonic IDs via sequence |
| Alembic | Schema migrations |

## Data model

`urls` table:

- `id BIGSERIAL PRIMARY KEY` — source for Base62 encoding
- `short_code VARCHAR(32) UNIQUE NOT NULL` — indexed
- `long_url TEXT NOT NULL`
- `is_custom BOOLEAN NOT NULL DEFAULT FALSE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
