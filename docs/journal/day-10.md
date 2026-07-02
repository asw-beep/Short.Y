# Day 10 — Scope Addendum: Minimal Frontend

## Implemented
- `GET /` — shorten form (URL, optional custom alias, optional expiry) →
  `fetch`-posts `POST /shorten` → shows the short link + copy button.
- `GET /list` — paginated table of live (non-expired) URLs: short URL, original
  URL, expiry. Backed by new `GET /api/urls?limit=&offset=` (capped 1–200,
  default 50; rate-limited `rate_limit_list` 60/min).
- `app/services/shortener.py::list_live_urls` — `expires_at IS NULL OR > now()`,
  newest first, reads Postgres directly (not the redirect cache — low-traffic
  dashboard view).
- Plain HTML/CSS/vanilla JS in `app/web/` (`index.html`, `list.html`,
  `static/style.css`), no build step. Served via `StaticFiles` mount + two
  `FileResponse` routes in `main.py`, registered before the catch-all router.
  `"list"` added to `RESERVED_WORDS`.
- List rows built via `textContent`/properties, never `innerHTML`, so a
  malicious `long_url` can't inject markup.
- Tests: `tests/test_frontend.py` (pages render, static asset, "list" reserved),
  `tests/test_url_listing.py` (empty, live-only, excludes expired, ordering,
  pagination, oversized-limit 422).

## Decisions
- **Scope addendum, not silent creep.** `Instrcutions.md` (the EDD) has no
  frontend goal; CLAUDE.md's "don't build what's not in the doc" rule guards
  against unrequested scope, not an explicit user ask. Added an addendum section
  to `Instrcutions.md` itself rather than quietly building outside the spec.
  ADR-012.
- **No framework** — two pages, plain fetch() against the existing JSON API.
- **Flagged the security regression rather than hiding it:** `/list` +
  `/api/urls` are a strictly bigger information-disclosure surface than the
  pre-existing enumeration risk — no guessing needed, it's a direct listing.
  Documented prominently in `threat-model.md`, in `list.html`'s own footer, and
  in `interview-notes.md`. No auth exists in this codebase (out of scope), so
  this is accepted for local/portfolio use only.

## Learned
- Serving raw HTML via `FileResponse` (not through the Artifact wrapper) means
  the files need to be complete, valid documents (`<!doctype>`, `<html>`,
  `<head>`, `<body>`) — first draft omitted them; browsers are lenient but a real
  served page should be well-formed.

## Verified live
- Full test suite: 59/59 pass.
- Browser: submitted a real URL via the form on `/`, got back a working short
  link, opened it (redirected correctly through the target's own redirect
  chain), then confirmed it appeared in the `/list` table with the right
  original URL and "Never" expiry.

## Next
- If this deployment is ever exposed beyond localhost: add auth in front of
  `/list` and `/api/urls` first — everything else in the threat model assumes
  that boundary doesn't exist yet.
