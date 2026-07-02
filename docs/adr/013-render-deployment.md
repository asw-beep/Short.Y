# ADR 013 — Render Deployment (Blueprint, In-Process Analytics Worker)

**Status:** Implemented. Config only — actually deploying (creating the Render
account/Blueprint) is the user's action, not something this session performs.

**Context:** a URL shortener whose only working links are `localhost` isn't a
credible resume artifact — a recruiter can't click it. This ADR documents
deploying to Render via `render.yaml` and the real trade-offs of the free tier,
researched rather than assumed (see citations in the deployment doc / session).

**Decision:** `render.yaml` defines a free web service (Docker), free Postgres,
and a free Key Value (Redis) instance. **No separate worker service** and **no
Nginx service** in the Blueprint.

**Why no worker service:** Render's free tier does not offer Background Workers
at any price of $0 — they're paid-only (~$7/mo+). Rather than silently
under-deliver (clicks queue in Redis forever, `/stats` always reads zero) or
force a cost decision unilaterally, this was raised explicitly and the chosen
path is: run the drain loop **inside the web process** as an asyncio task
(`ENABLE_INPROCESS_WORKER=true`), gated so local Docker Compose is byte-for-byte
unaffected (it still runs the real separate `worker` container — this flag
defaults to `false`).

**Why no Nginx service:** Render's own edge already is a reverse proxy / load
balancer for the web service — deploying our Nginx (ADR-011) in front of a
Render web service would be a redundant hop with no benefit.

**In-process worker implementation** (`app/services/analytics.py::run_inprocess_worker`):
- Runs the existing `process_batch` (unchanged) inside a `while` loop via
  `asyncio.to_thread`, so the blocking Redis/DB calls never stall the event loop
  serving HTTP requests.
- Uses a **distinct consumer name** (`INPROCESS_CONSUMER = "web-inprocess"`) from
  the standalone worker's `CONSUMER = "worker-1"`. Both are safe to run
  simultaneously against the same consumer group — Redis Streams consumer groups
  guarantee each pending message is claimed by exactly one consumer regardless of
  name, so there's no duplication if both paths were ever accidentally enabled at
  once. Verified live: with the standalone `worker` container running, it claimed
  a test click before the in-process task could; with the container stopped, the
  in-process task drained it alone and logged `clicks_persisted`.
- `session_factory` and `client` are passed as parameters (not imported globals),
  matching the app's existing DI style (`get_db`/`get_cache`), which is what
  makes this independently unit-testable with the same fixtures as the rest of
  the suite instead of needing a live Postgres+Redis integration test.

**`BASE_URL` auto-detection:** `app/core/config.py` adds a `model_validator`
that adopts Render's auto-injected `RENDER_EXTERNAL_URL` env var when `BASE_URL`
was never explicitly set (still defaults to `http://localhost:8000` for local
dev). This means shortened links returned by `POST /shorten` reflect the real
`*.onrender.com` domain with zero manual configuration on first deploy. An
explicit `BASE_URL` (e.g. after attaching a custom domain) always wins.

**Free-tier caveats surfaced, not hidden** (full detail in `docs/deployment.md`):
- Free Postgres **expires 30 days after creation** (14-day grace period, then
  deletion) — a real risk for a long-lived résumé link.
- Free web services **sleep after 15 min idle** (~30-60s cold start on next hit).
- Free Redis (Key Value) has no persistence guarantee — acceptable since
  analytics was already best-effort (ADR-007); URLs themselves live in Postgres.
- `TRUST_PROXY` is left `false` by default in the Blueprint — Render's edge
  proxy's `X-Forwarded-For`/`X-Real-IP` behavior has documented community reports
  of inconsistency, and this repo has not verified it against a live deployment.
  Flip it only after confirming real behavior on your own instance.

**Alternatives considered:**
- **Pay for Postgres Starter + a paid Background Worker** — gives full parity
  with the documented architecture, no expiry/worker caveats, at real ongoing
  cost. Left as a documented option in `docs/deployment.md`, not the default,
  since committing to a recurring cost is the user's call.
- **Free tier, skip the worker entirely** — simplest, but `/stats` would always
  read zero on the deployed demo, which undersells the analytics feature that
  was built and tested. Rejected once the in-process alternative was on the
  table.
