# How It Works

## Create Short URL — `POST /shorten`

1. **Rate limit** (SlowAPI, per-IP, moving-window; `rate_limit_shorten`, default
   30/min). Over limit → **429** with `Retry-After`.
2. Pydantic validates: only `http`/`https` schemes, max 2048 chars, optional
   `expires_at` must be in the future (else 422).
3. If `custom_alias` provided: regex `[a-zA-Z0-9_-]{4,32}`, reserved-word check,
   insert; UNIQUE constraint rejects duplicates → **409** (no TOCTOU check).
4. Otherwise: `SELECT nextval('urls_id_seq')` → Base62 (7 chars) → single INSERT.
5. Return `{ short_url, short_code, long_url, expires_at }`.

## Redirect — `GET /{code}` (cache-aside)

1. **Rate limit** (`rate_limit_redirect`, default 120/min).
2. Look up `url:{code}` in Redis:
   - **URL value** → 301 immediately (Postgres untouched).
   - **Negative sentinel `\x00`** → 404 immediately (absorbs enumeration scans).
   - **Expired sentinel `\x01`** → 410 immediately.
3. **Miss:** query Postgres by `short_code` (indexed):
   - Not found → cache `\x00` (TTL `cache_negative_ttl_seconds`) → **404**.
   - Found but `expires_at` past → cache `\x01` → **410 Gone**.
   - Found & live → cache `long_url` with TTL `min(cache_ttl_seconds, time-to-expiry)`
     → **301**.
4. On a successful 301, **record a click**: best-effort `XADD` to `clicks:stream`
   (referrer + truncated UA). Never blocks or fails the redirect.
5. **Redis unavailable:** the redirect **fails closed** → 503 (ADR-003). The
   limiter, by contrast, fails **open** (ADR-005).

## Analytics — worker + `GET /stats/{code}`

1. Each redirect appends an event to the Redis Stream `clicks:stream` (MAXLEN-capped).
2. The **worker** (`python -m app.worker`) `XREADGROUP`s as a consumer group,
   batch-INSERTs into `clicks`, and `XACK`s **after** the DB commit (at-least-once).
3. `GET /stats/{code}` aggregates `COUNT` + `MAX(clicked_at)` from `clicks` —
   **eventually consistent** (reflects drained events).

## Health

- `GET /livez` — liveness, static, no I/O (container `HEALTHCHECK`).
- `GET /health` — readiness: pings Postgres + Redis; **503** if either is down
  (so a load balancer drops a degraded instance).

## Frontend — `GET /`, `GET /list` (scope addendum, ADR-012)

Plain HTML/CSS/JS, no build step, served directly by FastAPI.

1. `GET /` — a form (`fetch`-posts to `POST /shorten`) that shows the resulting
   short link + a copy button.
2. `GET /list` — fetches `GET /api/urls?limit=&offset=` and renders a paginated
   table: short URL, original URL, expiry (or "Never"). Reads Postgres directly
   (not the redirect cache) — a low-traffic dashboard view, not the hot path.
   Rows are built with `textContent`, never `innerHTML`, so a malicious
   `long_url` can't inject markup into the page.
3. **No authentication.** Anyone who can reach the deployment can see every live
   mapping via this page or the API directly. See `threat-model.md` — this is
   flagged as a real, larger information-disclosure surface than the pre-existing
   code-enumeration risk, and is called out in the page itself.

## Design notes

- **301 permanent:** mappings are immutable (aside from expiry), so a permanent
  redirect is correct and reduces repeat traffic. Expiry is enforced at resolve
  time and the cache TTL is capped so the cache can't outlive the mapping.
- **Base62 of a sequence:** no collision logic; the UNIQUE column is a safety net;
  7 chars ≈ 3.5T IDs. Codes are enumerable — bounded now by per-IP rate limiting
  plus negative caching (see `threat-model.md`).
- **Behind Nginx:** set `TRUST_PROXY=true` so the limiter keys on the real client.
  The app prefers the unspoofable `X-Real-IP` (Nginx-set) over the appendable
  `X-Forwarded-For`.
