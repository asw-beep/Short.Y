# Day 05 — Phase 2: Click Analytics Worker

## Implemented
- `clicks` table + migration `0002` (short_code, clicked_at, referrer,
  user_agent; indexes on short_code and (short_code, clicked_at)).
- `app/services/analytics.py`: `record_click` (best-effort `XADD` to
  `clicks:stream`, MAXLEN-capped), `process_batch` (consumer-group
  `XREADGROUP` → batch INSERT → `XACK`), `get_stats` (COUNT + MAX aggregate).
- `app/worker.py`: standalone process (`python -m app.worker`) looping on
  `process_batch`, blocking on Redis (not busy-wait), clean SIGTERM/SIGINT stop.
- Redirect path now `record_click`s (referrer + UA from headers), off the
  critical path. New `GET /stats/{code}` endpoint + `StatsResponse`.
- Reserved `stats` and `livez`. `worker` service added to docker-compose.
- Tests: `tests/test_analytics.py` (enqueue+persist+stats, zero-for-unknown,
  ack-not-redelivered, metadata capture, best-effort on Redis failure).

## Decisions
- **Redis Streams + consumer group** over sync INSERT / BackgroundTasks / List /
  Celery. Durable, at-least-once, minimal machinery. ADR-007.
- **Ack after commit** → at-least-once (worst case double-count) over ack-first
  (which could drop clicks on a crash).
- **Best-effort producer** — a Redis error while recording must not fail the
  redirect.
- **No client IP stored** — minimise PII; referrer + truncated UA only.

## Learned
- Consumer groups (`XREADGROUP ">"` + `XACK`) turn a stream into a reliable work
  queue with redelivery, without a broker like RabbitMQ/Celery.
- SlowAPI header injection again required a `response: Response` param on the new
  `/stats` endpoint (Pydantic return) — same lesson as `/shorten`.

## Problems
- 2 failures on first run: `/stats` raised the SlowAPI "parameter `response` must
  be a Response" error.

## Solution
- Added `response: Response` to `stats`. All 42 tests pass. Verified the full
  cross-process pipeline live: API + `python -m app.worker`, 3 redirects →
  worker logged 3 `clicks_persisted` → `GET /stats` returned `total_clicks: 3`.

## Next
- Expiration policies (`expires_at`, 410 Gone, cache TTL aligned).
- Then Phase 3: Docker hardening, CI, Nginx.
