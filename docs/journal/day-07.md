# Day 07 — Phase 3: Container Hardening

## Implemented
- Multi-stage `Dockerfile`: `builder` installs deps to `/install`; `runtime`
  copies only that (no toolchain, no pip cache). All-wheel deps → no apt/gcc.
- Non-root: system `app` user owns `/code` and runs uvicorn.
- Baked-in `HEALTHCHECK` hitting `/livez`.
- Production-default CMD (`uvicorn`, no reload); compose overrides for dev
  (migrations + `--reload` + bind mount).
- `.dockerignore` (tests/docs/.git/.env out of context).
- Compose: env-parameterised creds (`${POSTGRES_PASSWORD:-…}`), API healthcheck,
  worker `depends_on api: service_healthy`, worker healthcheck disabled.
- `.env.example` expanded (rate limits, trust_proxy, logging, analytics).

## Decisions
- **slim + non-root + multi-stage** over single-stage/distroless. ADR-009.
- **Image = prod-safe by default; compose = dev override** so the shipped image
  never carries `--reload`/bind mounts.
- **Env externalisation** over compose secrets files — right-sized for local dev.

## Learned
- A worker container sharing the API image **inherits the image `HEALTHCHECK`**;
  since the worker serves no HTTP, the `/livez` probe always fails → must
  `healthcheck: disable: true` for it.

## Problems
- Worker showed perpetual `health: starting` (→ would go unhealthy) from the
  inherited HTTP probe.

## Solution
- Disabled the worker healthcheck in compose. Verified live: image builds, runs
  as `app` (non-root), container reports `healthy`; full `docker compose up`
  brings api healthy + worker up; E2E shorten→redirect→stats works through
  compose.

## Next
- CI (GitHub Actions: pytest + bandit + pip-audit).
- Nginx reverse proxy in front of the API; enable `trust_proxy`; diagram v3.
