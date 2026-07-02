# URL Shortener

Distributed URL shortener built in three phases:
1. **Core** — FastAPI + PostgreSQL, create + redirect (Base62 of a sequence).
2. **Performance** — Redis cache-aside, per-route rate limiting, structured
   logging + health checks, click analytics worker, link expiration.
3. **Scale** — hardened Docker image, CI (tests + bandit + pip-audit), Nginx
   reverse proxy / load balancer.

Plus a minimal frontend (scope addendum, see `Instrcutions.md`): a shorten form
and a live-links table — no framework, no build step, no auth.

## Live Demo

**Not yet deployed.** `render.yaml` + `docs/deployment.md` make this a
few-clicks deploy on Render (free tier) — see **Deploy** below. Once deployed,
replace this line with the real `https://...onrender.com` (or custom domain)
link. Don't link a `localhost` URL here — it isn't reachable by anyone else.

- API docs (Swagger/OpenAPI): add once deployed, e.g. `https://<your-app>/docs`
- Architecture: [`docs/architecture.md`](docs/architecture.md) ·
  [`docs/diagrams/architecture-v3.md`](docs/diagrams/architecture-v3.md)

## Deploy

```
Render dashboard → New → Blueprint → connect this repo → deploy render.yaml
```

Full walkthrough, free-tier caveats (Postgres expiry, cold starts, why there's
no separate worker service), and how to verify the deployed redirects actually
work: **[`docs/deployment.md`](docs/deployment.md)**. Design rationale: ADR-013.

See `Instrcutions.md` (spec), `docs/architecture.md`, `docs/how-it-works.md`, and
`docs/adr/` for the rest of the design and decisions.

## Development server (local only)

This is for building/testing the app — not a substitute for the deployed demo
above.

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:8000/` (shorten a URL) · `http://localhost:8000/list` (live links table)
- API direct: `http://localhost:8000` · Swagger UI: `http://localhost:8000/docs`
- Via Nginx edge: `http://localhost:8080` (same pages, proxied)

> ⚠️ The frontend has **no authentication** — `/list` and `/api/urls` show every
> live mapping to anyone who can reach the deployment. Fine for local use; do not
> expose this publicly without adding auth. See `docs/threat-model.md`.

Services: `postgres`, `redis`, `api` (runs migrations on start), `worker`
(analytics), `nginx`.

### Without Docker

```bash
docker compose up -d postgres redis      # just the deps
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload            # API
python -m app.worker                     # analytics worker (separate shell)
```

## Endpoints

- `POST /shorten` — `{ "url": "https://...", "custom_alias": "opt", "expires_at": "ISO-8601 opt" }`
- `GET /{code}` — 301 redirect (404 unknown · 410 expired)
- `GET /stats/{code}` — `{ short_code, total_clicks, last_clicked_at }`
- `GET /api/urls?limit=&offset=` — paginated JSON list of live URLs (backs `/list`)
- `GET /health` — readiness (pings Postgres + Redis; 503 if degraded)
- `GET /livez` — liveness
- `GET /docs` — Swagger UI
- `GET /`, `GET /list` — frontend pages (unauthenticated, see warning above)

Rate limits (per-IP, tunable via env): `POST /shorten` 30/min, `GET /{code}` &
`/stats` 120/min, `GET /api/urls` 60/min → `429` + `Retry-After` when exceeded.

## Tests & CI

Tests run against **real** Postgres + Redis (separate `shortener_test` DB and
Redis logical DB `/1`):

```bash
docker compose up -d postgres redis
docker compose exec postgres createdb -U shortener shortener_test
pytest                        # 64 tests
pytest --cov=app              # ~88% coverage
```

CI (`.github/workflows/ci.yml`) runs the suite on real PG/Redis, `bandit`
(blocking) and `pip-audit` (advisory) on every push/PR.
