# Architecture

## Phase 1 (current)

```
Client → FastAPI → PostgreSQL
```

Single FastAPI service, single Postgres instance, no caching layer yet.

## Planned

- **Phase 2:** Add Redis (caching + rate limiting), analytics worker.
- **Phase 3:** Add Nginx (reverse proxy + load balancing), full Docker deployment, stress testing.

## Components (Phase 1)

| Component | Responsibility |
|---|---|
| FastAPI app | HTTP API: `POST /shorten`, `GET /{code}` |
| PostgreSQL | Persistent storage for URL mappings, source of monotonic IDs via sequence |
| Alembic | Schema migrations |

## Data model

`urls` table:

- `id BIGSERIAL PRIMARY KEY` — source for Base62 encoding
- `short_code VARCHAR(32) UNIQUE NOT NULL` — indexed
- `long_url TEXT NOT NULL`
- `is_custom BOOLEAN NOT NULL DEFAULT FALSE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
