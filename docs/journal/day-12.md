# Day 12 — Live on Render

## Implemented
- Deployed the `render.yaml` Blueprint (named `shorty`, region Oregon):
  `shorty-api`, `shorty-db` (PostgreSQL 18), `shorty-redis` (Valkey 8), all
  free plan. Live at <https://shorty-api-z85h.onrender.com>.
- Fixed `dockerCommand` in `render.yaml`: `--port ${PORT:-8000}` →
  `--port $PORT` (commit `108a2d6`).
- README "Live Demo" section now has the real links; `docs/deployment.md` has a
  "Current deployment" table, the `$PORT` gotcha, and a corrected verify step.

## Problems
- First deploy exited with status 2: uvicorn rejected `--port '10000:-8000}'`.
  Migrations had already run, so the database was fine.
- The verify step in `docs/deployment.md` used `curl -sI`, which sends HEAD. The
  redirect route is GET-only, so it returned 405 even though redirects worked.

## Solution
- Render substitutes env vars into `dockerCommand` itself and doesn't
  understand shell `${VAR:-default}` syntax. Plain `$PORT` is enough because
  this command only runs on Render, where `PORT` is always set.
- Switched the doc's verify step to a GET that prints the status code and
  `redirect_url`.

## Learned
- Verification against the live domain passed: `/health` (database ok,
  redis ok), `POST /shorten` returned an `onrender.com` short URL (the
  `RENDER_EXTERNAL_URL` fallback works), `GET /0000001` → 301, and `/stats`
  counted the click, so the in-process worker is draining on Render.

## Next
- Free Postgres expires 2026-10-23 (deleted ~2026-11-06): upgrade it or
  redeploy before then.
- `TRUST_PROXY` is still `false`. Check what Render actually sends in
  `X-Forwarded-For` / `X-Real-IP` before turning it on.
- `/list` and `/api/urls` are now publicly reachable with no auth (ADR-012).
