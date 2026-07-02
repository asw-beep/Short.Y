# ADR 012 — Minimal Frontend (Shorten Form + Live-Links Table)

**Status:** Implemented (scope addendum — see note below).

**Decision:** Serve two plain HTML/CSS/vanilla-JS pages directly from the FastAPI
app: `GET /` (a form to shorten a URL, with optional custom alias / expiry) and
`GET /list` (a paginated table of all **live**, i.e. non-expired, short↔long URL
mappings with their expiry). A new `GET /api/urls` endpoint backs the table.

**Scope note:** `Instrcutions.md` (the authoritative EDD) has no frontend goal —
CLAUDE.md's rule is "if a feature isn't in that doc, don't build it." The user
explicitly requested this frontend in-session, which is the one authority that
can expand the doc's scope. Treated as an addendum to the EDD rather than a
silent scope violation.

**Alternatives considered:**
- **React/Vite SPA** — real tooling overhead (build step, bundler, node_modules)
  for two static pages and one list view. Rejected as overkill.
- **Jinja2 server-rendered templates** — a reasonable alternative, but the pages
  are simple enough that plain HTML + `fetch()` against the existing JSON API
  avoids adding a templating dependency and keeps the API/UI cleanly separated
  (the UI is just another API client).
- **Server-side pagination via Jinja** vs **client-side fetch + JS pagination**
  — chose client-side: simpler, and the API already returns JSON the UI can page
  through with `limit`/`offset` query params.

**Implementation:**
- `app/web/index.html`, `app/web/list.html`, `app/web/static/style.css` — no
  build step, no framework. Static assets served via `StaticFiles` mount at
  `/static`; the two pages via `FileResponse`.
- Registered **before** `include_router(router)` (like `/livez`/`/health`), since
  the catch-all `GET /{code}` would otherwise shadow `/list`. `"list"` added to
  `RESERVED_WORDS` so it can never collide with a custom alias.
- `GET /api/urls` (`limit` 1–200 default 50, `offset`): reads `URL` rows where
  `expires_at IS NULL OR expires_at > now()`, ordered newest-first. Rate-limited
  (`rate_limit_list`, default 60/min) like the other read endpoints.
- List queries Postgres directly (not the Redis cache) — this is a low-traffic
  dashboard view, not the redirect hot path, so cache-aside isn't warranted.
- All DOM insertion in `list.html` uses `textContent`/property assignment, never
  `innerHTML` with server data, so a malicious `long_url` can't inject markup.

**Theme:** light, cream background (`#f7f1e3`), olive-green accent family
(`--accent`/`--success`), warm charcoal text — user-directed palette, not the
original dark theme. Headings use a system serif stack (Georgia/Palatino) at a
larger base size (18px) for a more editorial, "professional" feel; body/UI text
uses a system sans stack. All system font stacks — no web-font download, works
offline, no external CSP exception needed.

**Security finding — flagged, not silently shipped:** `GET /list` and
`GET /api/urls` are **unauthenticated** and expose every live mapping's real
destination to anyone who can reach the deployment. This is a **new and larger**
information-disclosure surface than the pre-existing enumeration risk (no
guessing required — the table lists everything). Documented prominently in
`threat-model.md` and in-page (`list.html` footer notice). No auth exists
anywhere in this codebase yet (out of EDD scope), so this is accepted for
local/portfolio use only; **do not deploy `/list` publicly without adding auth.**

**Consequences:**
- Two more fixed routes to keep ahead of the catch-all if it's ever reordered.
- `/api/urls` adds a third public read surface (besides `/{code}` and
  `/stats/{code}`) an attacker could scrape; capped `limit<=200` and rate-limited,
  but no auth means the cap only slows scraping, not stops it.
