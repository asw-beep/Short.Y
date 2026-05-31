# URL Shortener

Distributed URL shortener built in three phases:
1. **Core** (current) — FastAPI + PostgreSQL, create + redirect.
2. **Performance** — Redis caching, rate limiting, analytics worker.
3. **Scale** — Nginx load balancing, full Docker, stress testing.

See `Instrcutions.md` and `docs/` for the full design.

## Run locally (Docker)

```bash
cp .env.example .env
docker compose up --build
```

API at `http://localhost:8000`, Swagger UI at `http://localhost:8000/docs`.

## Run locally (without Docker)

```bash
docker compose up -d postgres        # just the DB
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

Tests require a separate Postgres DB called `shortener_test`:

```bash
docker compose exec postgres createdb -U shortener shortener_test
pytest
```

Or override the DB with `TEST_DATABASE_URL`.

## Endpoints

- `POST /shorten` — body: `{ "url": "https://...", "custom_alias": "optional" }`
- `GET /{code}` — 301 redirect
- `GET /health`
- `GET /docs` — Swagger UI
