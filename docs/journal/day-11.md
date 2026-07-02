# Day 11 — Deployability: Render Blueprint + In-Process Worker Fallback

## Why
User feedback: a URL shortener whose only working demo links are `localhost`
isn't a credible resume artifact — recruiters need something they can actually
click. This session makes the repo deployable instead of just "runnable
locally."

## Implemented
- `render.yaml` — Blueprint: free web service (Docker), free Postgres, free
  Key Value (Redis) with `ipAllowList: []` (no public access). **No separate
  worker service, no Nginx service** — see below.
- `app/core/config.py` — `BASE_URL` now auto-adopts Render's injected
  `RENDER_EXTERNAL_URL` when not explicitly set, so shortened links reflect the
  real deployed domain with zero manual config. Explicit `BASE_URL` still wins.
- `app/services/analytics.py::run_inprocess_worker` — an asyncio-task variant
  of the existing drain loop, for when there's no separate worker process
  (Render's free tier has none at all — paid-only). Runs `process_batch`
  (unchanged) via `asyncio.to_thread` per iteration; uses a distinct consumer
  name (`web-inprocess` vs `worker-1`) so it's safe to coexist with the
  standalone worker.
- `app/main.py` lifespan starts/stops this task when
  `ENABLE_INPROCESS_WORKER=true` (default `false` — Docker Compose is
  completely unaffected, still runs the real `worker` container).
- `docs/deployment.md` — walkthrough + a caveats table: free Postgres expires
  in 30 days (+14-day grace, then deletion), free web services cold-start after
  15 min idle, free Redis has no persistence guarantee, and `TRUST_PROXY`
  should stay `false` until Render's XFF/X-Real-IP behavior is verified live
  (community reports of inconsistency found in research, not verified here).
- Tests: `tests/test_config.py` (BASE_URL fallback logic, 3 cases),
  `tests/test_analytics.py` (in-process worker drains + stops cleanly, distinct
  consumer name). 64 tests total, all passing.

## Decisions
- **Researched before committing to Render specifics** rather than guessing
  blueprint field names from memory: confirmed `dockerCommand`, `keyvalue`
  service type + required `ipAllowList`, default `PORT` (10000), and
  `RENDER_EXTERNAL_URL` auto-injection via web search against Render's current
  docs before writing `render.yaml`.
- **Asked before assuming a cost tradeoff.** Free Postgres expiry and the total
  absence of free Background Workers are real constraints that change the
  architecture; which to accept (pay, skip the worker, or run it in-process)
  is a budget/scope call only the user could make. Chose "free tier, worker
  runs in-process" after asking.
- **No Nginx service in the Render Blueprint** — Render's own edge already is a
  reverse proxy/LB; deploying ours in front of theirs would be a redundant hop.

## Learned
- Redis Streams consumer groups make the "two consumers, same group, different
  process" scenario safe by construction — verified by deliberately running
  both the standalone worker and the in-process task against the same shared
  dev stream, then isolating the in-process one by stopping the container and
  confirming it alone logged `clicks_persisted` for a fresh click.
- Render community threads report inconsistent/unexpected `X-Forwarded-For`
  values from their edge proxy — a good reminder not to assume a platform's
  proxy behavior mirrors Nginx's (which we tuned for in ADR-011) without
  verifying it directly.

## Verified live
- Full suite: 64/64 pass.
- In-process worker: ran a real uvicorn instance with
  `ENABLE_INPROCESS_WORKER=true` against dev Postgres/Redis, shortened +
  redirected a URL, and confirmed `/stats` populated correctly — first with the
  standalone worker also running (both cooperated correctly, no duplication),
  then with the standalone worker stopped (in-process path alone drained it and
  logged `clicks_persisted`).

## Next
- Actually deploy (`Render dashboard → New → Blueprint`) — this is the user's
  action (account creation, clicking deploy), not something done in-session.
- Once live: verify the redirect chain works from the real domain (not just
  localhost) and update the README's "Live Demo" placeholder with the real URL.
