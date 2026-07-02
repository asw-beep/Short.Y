# Deployment (Render)

Local `docker compose` is for development. A résumé/portfolio link needs to
actually work when someone clicks it days or months later — this doc covers
deploying to [Render](https://render.com) using the `render.yaml` Blueprint at
the repo root, and the real caveats of doing that on the free tier.

## Why Render, and why the architecture differs slightly here

- `render.yaml` defines: a **web service** (the FastAPI app), a **free
  PostgreSQL** database, and a **free Key Value (Redis-compatible)** instance.
- **There is no separate worker service in this Blueprint.** Render's free tier
  does not offer Background Workers at all (paid-only, ~$7/mo minimum). Instead,
  the web service runs the analytics drain loop as an **in-process asyncio
  task** (`ENABLE_INPROCESS_WORKER=true` — see `app/services/analytics.py::run_inprocess_worker`
  and ADR-013), which is a deliberate deviation from the documented
  Client→Nginx→API/Redis/Postgres + separate-Worker architecture used for local
  Docker Compose. Compose is unaffected — it still runs a real separate
  `worker` container.
- **No Nginx service in this Blueprint either.** Render's own edge is already a
  reverse proxy / load balancer — that's the role Nginx plays locally (ADR-011).
  Don't deploy a redundant Nginx service in front of a Render web service.

## Steps

1. Push this repo to GitHub (Render deploys from a Git repo, not a local path).
2. In the Render dashboard: **New → Blueprint**, connect the repo, and it will
   read `render.yaml` and propose the three resources (web, Redis, Postgres).
3. Deploy. First build takes a few minutes (Docker build + `alembic upgrade
   head` on boot).
4. Render assigns a URL like `https://shorty-api-xxxx.onrender.com`. Because of
   the `RENDER_EXTERNAL_URL` fallback in `app/core/config.py`, **`short_url` in
   `POST /shorten` responses will automatically reflect this real domain** — no
   manual `BASE_URL` step needed for the default `.onrender.com` host.
5. **Verify the redirect actually works from that live domain** (this is the
   whole point — a shortener whose short links only redirect on `localhost` is
   not a working demo):
   ```bash
   curl -sX POST https://<your-app>.onrender.com/shorten \
     -H "Content-Type: application/json" -d '{"url":"https://github.com/openai"}'
   # -> {"short_url":"https://<your-app>.onrender.com/XXXXXXX", ...}
   curl -sI https://<your-app>.onrender.com/XXXXXXX
   # -> HTTP/2 301, location: https://github.com/openai
   ```

## Free-tier caveats — read before linking this from a résumé

| Caveat | Impact | Mitigation |
|---|---|---|
| **Free Postgres expires 30 days after creation**, then a 14-day grace period, then Render **deletes it** (data included). | A demo that dies silently ~6 weeks in is worse than no demo. | Set a calendar reminder, or upgrade the database to a paid plan before sharing the link long-term. Render emails you before expiry. |
| **Free web services sleep after 15 min of inactivity**; the next request cold-starts in ~30-60s. | A recruiter's first click may hang for up to a minute before the page loads. | Acceptable for a portfolio link if you say so, or upgrade to a paid "Starter" web service to avoid it. |
| **No separate worker on free tier** — analytics run in-process instead (see above). | Functionally equivalent (same consumer-group semantics), but it's a real architectural deviation from what's documented as the "real" system. | Documented here and in ADR-013 rather than silently papering over it — mention this trade-off if asked in an interview. |
| **Redis (Key Value) free instance has no persistence guarantee.** | An instance restart could lose queued-but-undrained click events (URLs themselves are safe — they live in Postgres). | Acceptable: analytics was already documented as best-effort (ADR-007). |
| **`TRUST_PROXY` is left `false`** in `render.yaml`. | Rate limiting will key on whatever IP Render's edge presents as the socket peer to the app — possibly the same for all traffic, making the limiter *more* strict than intended (shared bucket), not exploitable. | Before flipping `TRUST_PROXY=true`, verify what `X-Real-IP`/`X-Forwarded-For` actually look like on your live deployment (log them, or check `docs/threat-model.md`'s note) — Render's proxy behavior here has had documented inconsistencies and isn't something this repo has verified against a live instance. |

## Custom domain

If you attach a custom domain in Render's dashboard, set `BASE_URL` explicitly
(Render dashboard → your web service → Environment) to `https://your-domain`.
An explicit `BASE_URL` always overrides the `RENDER_EXTERNAL_URL` fallback.
