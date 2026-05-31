# Day 01 — Phase 1 Scaffold

## Implemented
- Project skeleton: FastAPI app, SQLAlchemy models, Pydantic schemas.
- `POST /shorten`: validates URL, generates Base62 short code from `urls_id_seq`, supports custom aliases with reserved-word blocking.
- `GET /{code}`: 301 redirect.
- Alembic migration for `urls` table.
- Docker Compose: Postgres + Redis (Redis idle until Phase 2) + API.
- Tests: base62 unit, shortener service, API endpoints.
- Docs: architecture, how-it-works, threat-model, ADRs 001–004.

## Decisions
- 301 (permanent) redirect — mappings are immutable in V1.
- Auto-increment Base62 over random codes — simpler; enumeration risk accepted and documented.
- `BASE_URL` env var so responses return full URLs regardless of how the service is fronted.
- Custom alias rules: 4–32 chars, `[a-zA-Z0-9_-]`, reserved words blocked.

## Learned
- Postgres `nextval()` is a clean way to reserve an ID before INSERT without two round-trips per row.
- Pydantic v2 `HttpUrl` accepts schemes beyond http/https — needed an explicit allowlist validator.

## Problems
- Test DB requires a separate `shortener_test` database. Documented in `README.md` (to be written).

## Solution
- `conftest.py` reads `TEST_DATABASE_URL` env var with a sensible default; truncates between tests with `RESTART IDENTITY` so sequence-derived codes are deterministic.

## Next
- Phase 2: Redis caching + rate limiting + analytics worker.
